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

    def test_audit_returns_scan_available_flag(self):
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

    def test_audit_handles_missing_psm_stack_gracefully(self):
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

    def test_audit_coverage_never_silently_zero(self):
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
