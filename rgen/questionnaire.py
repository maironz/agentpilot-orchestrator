"""Interactive questionnaire -- produces a ProjectProfile."""

from __future__ import annotations

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
        self._print("=== routing-generator: nuovo progetto ===")
        self._print("")

        use_pattern = self._ask(
            "use_pattern",
            "Vuoi partire da un pattern esistente?",
            default="y",
            choices=("y", "n", "yes", "no"),
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
        raw_tech = self._ask(
            "tech_stack",
            "Tecnologie usate (virgola-separate, es: python,docker,postgres)",
            default="",
        )
        raw_domains = self._ask(
            "domain_keywords",
            "Domini principali (virgola-separati, es: auth,billing,reporting)",
            default="",
        )

        tech_stack = [t.strip() for t in raw_tech.split(",") if t.strip()]
        domain_keywords = [d.strip() for d in raw_domains.split(",") if d.strip()]

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
    ) -> str:
        if self._overrides is not None:
            return self._overrides.get(key, default)

        suffix = f" [{default}]" if default else ""
        if choices:
            suffix += f" ({'/'.join(choices)})"
        while True:
            raw = input(f"{prompt}{suffix}: ").strip()
            value = raw if raw else default
            if choices and value.lower() not in [c.lower() for c in choices]:
                print(f"  Risposta non valida. Scegli tra: {', '.join(choices)}")
                continue
            return value

    def _print(self, msg: str) -> None:
        if self._overrides is None:
            print(msg)
