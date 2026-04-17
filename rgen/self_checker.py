"""Self-checker -- validates generated output post-generation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable

from rgen.models import CheckReport


class SelfChecker:
    """Runs 8 post-generation checks on a generated project directory.

    Args:
        target_dir: Project root (the directory that contains ``.github/``).
    """

    REQUIRED_FILES = (
        ".github/router.py",
        ".github/routing-map.json",
        ".github/copilot-instructions.md",
        ".github/AGENT_REGISTRY.md",
        ".github/subagent-brief.md",
        ".github/interventions.py",
        ".github/mcp_server.py",
    )

    MIN_SCENARIOS = 3

    def __init__(self, target_dir: Path) -> None:
        self._dir = Path(target_dir)

    @property
    def github_dir(self) -> Path:
        return self._dir / ".github"

    def run_all(self) -> CheckReport:
        """Executes all 8 checks and returns a consolidated CheckReport."""
        report = CheckReport()
        checks: list[tuple[str, Callable[[CheckReport], None]]] = [
            ("required_files", self._check_required_files),
            ("routing_map", self._check_routing_map),
            ("expert_files", self._check_expert_files),
            ("agent_registry", self._check_agent_registry),
            ("copilot_instructions", self._check_copilot_instructions),
            ("template_vars", self._check_template_vars),
            ("core_files", self._check_core_files),
            ("router_stats", self._check_router_stats),
        ]
        for name, fn in checks:
            before_errors = len(report.errors)
            try:
                fn(report)
            except Exception as exc:
                report.errors.append(f"{name}: unexpected error: {exc}")
            if len(report.errors) == before_errors:
                report.passed.append(name)
        return report

    # ------------------------------------------------------------------
    # Check 1 — required files
    # ------------------------------------------------------------------

    def _check_required_files(self, report: CheckReport) -> None:
        for rel in self.REQUIRED_FILES:
            dest = self._dir / rel
            if not dest.exists():
                report.errors.append(f"required_files: missing {rel}")

    # ------------------------------------------------------------------
    # Check 2 — routing_map validity
    # ------------------------------------------------------------------

    def _check_routing_map(self, report: CheckReport) -> None:
        path = self.github_dir / "routing-map.json"
        if not path.exists():
            report.errors.append("routing_map: file missing")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            report.errors.append(f"routing_map: invalid JSON: {exc}")
            return

        scenarios = {k: v for k, v in data.items() if not k.startswith("_")}
        if len(scenarios) < self.MIN_SCENARIOS:
            report.errors.append(
                f"routing_map: only {len(scenarios)} scenarios (min {self.MIN_SCENARIOS})"
            )
        for sid, scenario in scenarios.items():
            for field in ("agent", "keywords", "files"):
                if field not in scenario:
                    report.errors.append(f"routing_map: scenario '{sid}' missing field '{field}'")

    # ------------------------------------------------------------------
    # Check 3 — expert files exist for each declared agent
    # ------------------------------------------------------------------

    def _check_expert_files(self, report: CheckReport) -> None:
        path = self.github_dir / "routing-map.json"
        if not path.exists():
            return
        data = json.loads(path.read_text(encoding="utf-8"))
        agents = {
            v["agent"]
            for k, v in data.items()
            if not k.startswith("_") and "agent" in v
        }
        for agent in agents:
            expert_file = self.github_dir / "esperti" / f"esperto_{agent}.md"
            if not expert_file.exists():
                report.errors.append(f"expert_files: missing esperto_{agent}.md")

    # ------------------------------------------------------------------
    # Check 4 — AGENT_REGISTRY.md lists all agents
    # ------------------------------------------------------------------

    def _check_agent_registry(self, report: CheckReport) -> None:
        registry_path = self.github_dir / "AGENT_REGISTRY.md"
        routing_path = self.github_dir / "routing-map.json"
        if not registry_path.exists() or not routing_path.exists():
            return
        registry = registry_path.read_text(encoding="utf-8")
        data = json.loads(routing_path.read_text(encoding="utf-8"))
        agents = {
            v["agent"]
            for k, v in data.items()
            if not k.startswith("_") and "agent" in v
        }
        for agent in agents:
            if agent not in registry:
                report.warnings.append(
                    f"agent_registry: agent '{agent}' not mentioned in AGENT_REGISTRY.md"
                )

    # ------------------------------------------------------------------
    # Check 5 — copilot-instructions.md has DISPATCHER section
    # ------------------------------------------------------------------

    def _check_copilot_instructions(self, report: CheckReport) -> None:
        path = self.github_dir / "copilot-instructions.md"
        if not path.exists():
            report.errors.append("copilot_instructions: file missing")
            return
        content = path.read_text(encoding="utf-8")
        if "DISPATCHER" not in content:
            report.errors.append("copilot_instructions: missing DISPATCHER section")
        if "router.py" not in content:
            report.warnings.append("copilot_instructions: no router.py reference found")

    # ------------------------------------------------------------------
    # Check 6 — no leftover {{VAR}} template placeholders
    # ------------------------------------------------------------------

    def _check_template_vars(self, report: CheckReport) -> None:
        pattern = re.compile(r"\{\{[A-Z_]+\}\}")
        for md_file in self.github_dir.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8", errors="replace")
            found = pattern.findall(content)
            if found:
                rel = md_file.relative_to(self._dir)
                report.warnings.append(
                    f"template_vars: {rel} still contains {found}"
                )

    # ------------------------------------------------------------------
    # Check 7 — core files copied
    # ------------------------------------------------------------------

    def _check_core_files(self, report: CheckReport) -> None:
        for name in ("router.py", "interventions.py", "mcp_server.py", "mcp_status.py", "update_manager.py"):
            dest = self.github_dir / name
            if not dest.exists():
                report.errors.append(f"core_files: missing .github/{name}")

    # ------------------------------------------------------------------
    # Check 8 — router.py --stats runs successfully
    # ------------------------------------------------------------------

    def _check_router_stats(self, report: CheckReport) -> None:
        router = self.github_dir / "router.py"
        if not router.exists():
            return  # covered by required_files check
        try:
            proc = subprocess.run(
                [sys.executable, str(router), "--stats"],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(self._dir),
            )
        except subprocess.TimeoutExpired:
            report.errors.append("router_stats: timed out after 15s")
            return
        if proc.returncode != 0:
            report.errors.append(
                f"router_stats: exit {proc.returncode} -- {proc.stderr[:200]}"
            )
            return
        # Validate JSON payload in stdout.
        # router --stats prints a human header plus pretty-printed JSON.
        stdout = proc.stdout.strip()
        if not stdout:
            report.warnings.append("router_stats: no output produced")
            return
        try:
            data = self._extract_json_from_stats_output(stdout)
            if "overall" not in data:
                report.warnings.append("router_stats: JSON missing 'overall' key")
        except json.JSONDecodeError:
            report.warnings.append("router_stats: output is not valid JSON")

    def _extract_json_from_stats_output(self, stdout: str) -> dict:
        """Extracts stats JSON from mixed human-readable + JSON output."""
        # Fast path: pure JSON payload.
        try:
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Fallback: take the last JSON object block printed in stdout.
        start = stdout.rfind("{")
        end = stdout.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise json.JSONDecodeError("No JSON object found", stdout, 0)

        # Walk back to the outermost opening brace for the final JSON block.
        depth = 0
        outer_start = -1
        for i in range(end, -1, -1):
            ch = stdout[i]
            if ch == '}':
                depth += 1
            elif ch == '{':
                depth -= 1
                if depth == 0:
                    outer_start = i
                    break
        if outer_start == -1:
            raise json.JSONDecodeError("Unbalanced JSON braces", stdout, start)

        payload = stdout[outer_start:end + 1]
        data = json.loads(payload)
        if not isinstance(data, dict):
            raise json.JSONDecodeError("Stats payload is not a JSON object", payload, 0)
        return data
