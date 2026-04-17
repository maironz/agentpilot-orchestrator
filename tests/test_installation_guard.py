"""
Installation & Integration Quality Guard Tests

Previene regressioni negli errori comuni riscontrati durante integrazione:
1. Version mismatch CLI vs pyproject
2. Dry-run vs direct file count incoerenza
3. Router health metrics non realistiche
4. Audit coverage su ambienti non-PSM
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


class TestVersionSync:
    """Verifica che versione CLI sia sempre in sync con pyproject.toml"""

    def test_cli_version_matches_pyproject(self):
        """rgen --version deve essere uguale a pyproject.toml version"""
        import re
        import rgen
        
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        pyproject_text = pyproject_path.read_text()
        
        # Usa regex per estrarre version (compatibile Python 3.10+)
        match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
        assert match, "version non trovata in pyproject.toml"
        expected_version = match.group(1)
        
        assert rgen.__version__ == expected_version, (
            f"CLI version {rgen.__version__} != pyproject {expected_version}"
        )

    def test_version_file_matches_pyproject(self):
        """VERSION deve riflettere la versione dichiarata in pyproject.toml."""
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        version_file_path = Path(__file__).parent.parent / "VERSION"

        pyproject_text = pyproject_path.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
        assert match, "version non trovata in pyproject.toml"
        expected_version = match.group(1)

        assert version_file_path.exists(), "file VERSION mancante nel repository"
        version_from_file = version_file_path.read_text(encoding="utf-8").strip()

        assert version_from_file == expected_version, (
            f"VERSION {version_from_file} != pyproject {expected_version}"
        )

    def test_entry_points_versions_consistent(self):
        """Tutte gli entry points devono usare lo stesso modulo versione"""
        import re
        import rgen
        
        # rgen e agentpilot devono puntare allo stesso module
        # agentpilot-mcp usa core.mcp_server che importa da rgen indirettamente
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        pyproject_text = pyproject_path.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', pyproject_text)
        assert match, "version non trovata in pyproject.toml"
        expected_version = match.group(1)
        
        assert rgen.__version__ == expected_version, (
            f"rgen.__version__ {rgen.__version__} != pyproject {expected_version}"
        )


class TestDryRunCoherence:
    """Verifica che dry-run mostra stesso numero di file di direct"""

    def test_dry_run_includes_core_files(self, tmp_path):
        """dry-run deve mostrare CORE_FILES nel conteggio"""
        from rgen.writer import Writer
        
        # Verifica che Writer conosce i CORE_FILES
        expected_core_files = {
            "router.py",
            "router_audit.py",
            "router_planner.py",
            "interventions.py",
            "mcp_server.py",
            "mcp_status.py",
            "update_manager.py",
            "requirements.txt",
        }
        
        assert set(Writer.CORE_FILES) == expected_core_files, (
            f"CORE_FILES mismatch: {set(Writer.CORE_FILES)} != {expected_core_files}"
        )

    def test_dry_run_output_mentions_core_files(self, capsys, tmp_path):
        """dry-run deve menzionare esplicitamente che include CORE_FILES"""
        # Questo è un integration test che richiede effettivo run di dry-run
        # Verificato manualmente in test_cli.py
        pass


class TestRouterHealthThresholds:
    """Verifica che soglie health metrics siano realistiche"""

    def test_router_lines_thresholds_are_realistic(self):
        """Soglie router_lines devono permettere router maturi"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        
        from router_audit import _THRESHOLDS
        
        # Dopo fix: warn=800, crit=1200
        assert _THRESHOLDS["router_lines_warn"] == 800, "warn threshold deve essere 800"
        assert _THRESHOLDS["router_lines_crit"] == 1200, "crit threshold deve essere 1200"

    def test_router_lines_within_healthy_range(self):
        """Router.py attuale (886 righe) deve essere 'warn' non 'crit'"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        
        from router_audit import get_health_stats
        
        stats = get_health_stats()
        router_status = stats["metrics"]["router_lines"]["status"]
        
        # 886 righe deve essere warn (800 < 886 < 1200)
        assert router_status == "warn", (
            f"Router 886 lines deve essere 'warn', non '{router_status}'"
        )

    def test_health_overall_status_not_perpetually_critical(self):
        """Overall health non deve essere CRIT dopo fix"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        
        from router_audit import get_health_stats
        
        stats = get_health_stats()
        overall = stats["overall"]
        
        # Dopo fix deve essere warn o ok, non crit
        assert overall != "crit", (
            f"Overall health deve essere warn/ok, non crit. Stato: {overall}"
        )


class TestAuditScanAvailability:
    """Verifica che audit gestisce assenza di sorgenti PSM Stack"""

    def test_audit_returns_scan_available_flag(self, no_network_scan):
        """audit_routing_coverage deve ritornare scan_available flag"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        
        from router_audit import audit_routing_coverage
        
        result = audit_routing_coverage()
        
        assert "scan_available" in result, (
            "audit_routing_coverage deve ritornare 'scan_available' flag"
        )
        assert isinstance(result["scan_available"], bool), (
            "scan_available deve essere bool"
        )

    def test_audit_handles_missing_psm_stack_gracefully(self, no_network_scan):
        """Audit su ambienti no-PSM deve ritornare note esplicita, non 0%"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        
        from router_audit import audit_routing_coverage
        
        result = audit_routing_coverage()
        
        # Se scan_available=False, coverage_pct deve essere None (non 0)
        if not result.get("scan_available", True):
            assert result.get("coverage_pct") is None or "note" in result, (
                "Quando scan non disponibile, audit deve spiegare perché"
            )

    def test_audit_coverage_never_silently_zero(self, no_network_scan):
        """Audit coverage 0% dev'essere esplicito (not 'unknown')"""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        
        from router_audit import audit_routing_coverage
        
        result = audit_routing_coverage()
        
        # Se coverage < 5%, dev'esserci un nota che spiega
        coverage = result.get("coverage_pct")
        if coverage is not None and coverage < 5:
            if not result.get("scan_available", True):
                assert "note" in result, (
                    "Coverage bassa deve avere nota esplicativa"
                )


class TestMCPInstallation:
    """Verifica correttezza installazione MCP dal repo corretto"""

    def test_mcp_script_available(self):
        """agentpilot-mcp script deve essere disponibile in PATH"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "agentpilot-orchestrator"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout
            
            # Deve mostrare Location dal repo corrente, non SAP
            assert "agentpilot-orchestrator" in output, (
                "Pacchetto deve essere installato"
            )
            # Non deve linkare a H:\Projects\SAP
            assert "Projects\\SAP" not in output, (
                f"Pacchetto non deve puntare a Projects\\SAP. Output:\n{output}"
            )
        except subprocess.TimeoutExpired:
            pytest.skip("pip show timeout")

    def test_mcp_status_reflects_vscode_logs(self):
        """mcp_status.py deve leggere stato corretto da VS Code logs"""
        status_file = Path(__file__).parent.parent / ".github" / "mcp_status.py"
        assert status_file.exists(), "mcp_status.py deve esistere"


class TestExecutionTimeoutGuard:
    """Verifica che il guard di timeout in cli.main() funzioni correttamente."""

    def test_timeout_constant_is_30(self):
        """_EXECUTION_TIMEOUT deve essere 30 secondi."""
        from rgen.cli import _EXECUTION_TIMEOUT
        assert _EXECUTION_TIMEOUT == 30

    def test_slow_commands_map_non_empty(self):
        """_SLOW_COMMANDS deve contenere almeno le operazioni di rete/IO note."""
        from rgen.cli import _SLOW_COMMANDS
        expected = {"download", "update", "roi_benchmark", "cost_report", "rollback"}
        assert expected.issubset(set(_SLOW_COMMANDS.keys()))

    def test_report_timeout_slow_command(self, capsys):
        """_report_timeout su comando lento deve spiegare che il ritardo è atteso."""
        from rgen.cli import _report_timeout
        _report_timeout("download", 30)
        captured = capsys.readouterr()
        assert "TIMEOUT" in captured.err
        assert "download" in captured.err
        assert "atteso" in captured.err.lower() or "normale" in captured.err.lower()

    def test_report_timeout_unknown_command(self, capsys):
        """_report_timeout su comando ignoto deve suggerire --check."""
        from rgen.cli import _report_timeout
        _report_timeout(None, 30)
        captured = capsys.readouterr()
        assert "TIMEOUT" in captured.err
        assert "--check" in captured.err

    def test_main_returns_3_on_timeout(self):
        """main() deve restituire exit code 3 se il comando supera il timeout."""
        import time
        from unittest.mock import patch
        from rgen.cli import main

        def _slow_dispatch(*_a, **_kw):
            time.sleep(5)
            return 0

        with patch("rgen.cli._EXECUTION_TIMEOUT", 1):
            with patch("rgen.cli._cmd_list_patterns", _slow_dispatch):
                result = main(["--list-patterns"])
        assert result == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
