"""Interactive questionnaire -- produces a ProjectProfile."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Any

from rgen.adapter import PatternLoader
from rgen.models import ProjectProfile


class Questionnaire:
    """Guided interview that produces a :class:`ProjectProfile`.

    Two modes of operation:

    - :meth:`run` -- fully interactive (reads from stdin)
    - :meth:`run_with_defaults` -- non-interactive, uses ``overrides`` dict;
      missing keys fall back to hard-coded defaults (used in tests and CI)

    Args:
        knowledge_base_dir: Path to the ``knowledge_base/`` directory.
    """

    def __init__(self, knowledge_base_dir: Path) -> None:
        self._kb = Path(knowledge_base_dir)
        self._loader = PatternLoader(self._kb)
        self._overrides: dict[str, str] | None = None

    # Timeout only for the first project-selection question.
    _PROJECT_SELECTION_TIMEOUT_SECONDS = 30

    SUGGESTED_TECH_STACK: tuple[str, ...] = (
        "python",
        "fastapi",
        "flask",
        "django",
        "nodejs",
        "typescript",
        "react",
        "vue",
        "php",
        "laravel",
        "postgresql",
        "mysql",
        "mariadb",
        "mongodb",
        "redis",
        "docker",
        "nginx",
        "traefik",
        "kubernetes",
    )

    SUGGESTED_DOMAINS: tuple[str, ...] = (
        "informatica",
        "api",
        "database",
        "auth",
        "caching",
        "testing",
        "security",
        "performance",
        "docker_infra",
        "frontend_components",
        "dependency_management",
        "git_version_control",
        "docs",
        "troubleshooting",
    )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> ProjectProfile:
        """Runs the interactive interview and returns a ProjectProfile."""
        self._overrides = None
        return self._interview()

    def run_with_defaults(self, overrides: dict[str, str] | None = None) -> ProjectProfile:
        """Runs the interview non-interactively.

        Args:
            overrides: Maps question keys to pre-set answers.
                       Missing keys use built-in defaults.
        """
        self._overrides = overrides or {}
        return self._interview()

    # ------------------------------------------------------------------
    # Interview
    # ------------------------------------------------------------------

    def _interview(self) -> ProjectProfile:
        self._print("")
        self._print("=== AgentPilot Orchestrator: nuovo progetto ===")
        self._print("")

        use_pattern = self._ask(
            "use_pattern",
            "Vuoi partire da un pattern esistente?",
            default="y",
            choices=("y", "n", "yes", "no"),
            timeout_seconds=self._PROJECT_SELECTION_TIMEOUT_SECONDS,
        ).lower().startswith("y")

        if use_pattern:
            return self._path_a()
        return self._path_b()

    # ------------------------------------------------------------------
    # Path A: from existing pattern
    # ------------------------------------------------------------------

    def _path_a(self) -> ProjectProfile:
        available = self._loader.list_patterns()
        if not available:
            self._print("Nessun pattern disponibile. Passo alla creazione da zero.")
            return self._path_b()

        self._print(f"\nPattern disponibili: {', '.join(available)}")
        pattern_id = self._ask(
            "pattern_id",
            "Quale pattern vuoi usare?",
            default=available[0],
        )
        if pattern_id not in available:
            self._print(f"Pattern '{pattern_id}' non trovato. Uso '{available[0]}'.")
            pattern_id = available[0]

        pattern = self._loader.load(pattern_id)
        meta = pattern["metadata"]

        self._print(f"\nPattern: {meta['name']}")
        self._print(f"Stack:   {', '.join(meta['tech_stack'])}")
        self._print(f"Agenti:  {', '.join(meta['agents'])}")
        self._print("")

        project_name = self._ask(
            "project_name",
            "Nome del progetto",
            default="my-project",
        )
        target_path = Path(self._ask(
            "target_path",
            "Directory di output (crea .github/ qui dentro)",
            default=str(Path.cwd()),
        ))

        # Optional: rename agents
        agent_renames: dict[str, str] = {}
        for agent in meta["agents"]:
            rename = self._ask(
                f"rename_agent_{agent}",
                f"Rinomina agente '{agent}' (invio = mantieni)",
                default=agent,
            )
            if rename != agent:
                agent_renames[agent] = rename

        template_vars: dict[str, str] = {
            "PROJECT_NAME": project_name,
        }
        for old, new in agent_renames.items():
            template_vars[f"RENAME_{old.upper()}"] = new

        return ProjectProfile(
            project_name=project_name,
            target_path=target_path,
            pattern_id=pattern_id,
            template_vars=template_vars,
            tech_stack=list(meta.get("tech_stack", [])),
            domain_keywords=[],
        )

    # ------------------------------------------------------------------
    # Path B: from scratch
    # ------------------------------------------------------------------

    def _path_b(self) -> ProjectProfile:
        self._print("\n=== Creazione routing da zero ===\n")

        project_name = self._ask(
            "project_name",
            "Nome del progetto",
            default="my-project",
        )
        target_path = Path(self._ask(
            "target_path",
            "Directory di output (crea .github/ qui dentro)",
            default=str(Path.cwd()),
        ))

        self._print("Tecnologie suggerite:")
        self._print(self._format_numbered_options(self.SUGGESTED_TECH_STACK))
        self._print("Inserisci numeri separati da virgola (es: 1,6,11) o testo libero.")
        raw_tech = self._ask(
            "tech_stack",
            "Tecnologie usate",
            default="",
        )

        self._print("\nDomini suggeriti:")
        self._print(self._format_numbered_options(self.SUGGESTED_DOMAINS))
        self._print("Inserisci numeri separati da virgola (es: 1,2,4) o testo libero.")
        raw_domains = self._ask(
            "domain_keywords",
            "Domini principali",
            default="informatica",
        )

        tech_stack = self._parse_multi_select(raw_tech, self.SUGGESTED_TECH_STACK)
        domain_keywords = self._parse_multi_select(raw_domains, self.SUGGESTED_DOMAINS)

        return ProjectProfile(
            project_name=project_name,
            target_path=target_path,
            pattern_id="",
            template_vars={"PROJECT_NAME": project_name},
            tech_stack=tech_stack,
            domain_keywords=domain_keywords,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ask(
        self,
        key: str,
        prompt: str,
        default: str = "",
        choices: tuple[str, ...] | None = None,
        timeout_seconds: int | None = None,
    ) -> str:
        if self._overrides is not None:
            return self._overrides.get(key, default)

        suffix = f" [{default}]" if default else ""
        if choices:
            suffix += f" ({'/'.join(choices)})"
        while True:
            full_prompt = f"{prompt}{suffix}: "
            raw_value = self._read_input_with_timeout(full_prompt, timeout_seconds)
            if raw_value is None:
                self._print(f"  Timeout dopo {timeout_seconds}s: uso default '{default}'.")
                return default

            raw = raw_value.strip()
            value = raw if raw else default
            if choices and value.lower() not in [c.lower() for c in choices]:
                print(f"  Risposta non valida. Scegli tra: {', '.join(choices)}")
                continue
            return value

    @staticmethod
    def _format_numbered_options(options: tuple[str, ...]) -> str:
        return "\n".join(f"  {idx}. {item}" for idx, item in enumerate(options, start=1))

    @staticmethod
    def _parse_multi_select(raw: str, options: tuple[str, ...]) -> list[str]:
        selected: list[str] = []
        for token in [part.strip() for part in raw.split(",") if part.strip()]:
            if token.isdigit():
                idx = int(token)
                if 1 <= idx <= len(options):
                    selected.append(options[idx - 1])
                continue
            selected.append(token)

        normalized: list[str] = []
        seen: set[str] = set()
        for item in selected:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            normalized.append(key)
        return normalized

    @staticmethod
    def _read_input_with_timeout(prompt: str, timeout_seconds: int | None) -> str | None:
        if timeout_seconds is None:
            return input(prompt)

        q: queue.Queue[str] = queue.Queue(maxsize=1)

        def _reader() -> None:
            try:
                q.put(input(prompt))
            except EOFError:
                q.put("")

        thread = threading.Thread(target=_reader, daemon=True)
        thread.start()
        try:
            return q.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

    def _print(self, msg: str) -> None:
        if self._overrides is None:
            print(msg)
