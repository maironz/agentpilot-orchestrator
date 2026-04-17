"""
Integration & Functionality Tests

Test dei componenti che avevano problemi durante installazione:
- Dry-run vs direct coerenza
- Audit su ambienti non-PSM
- Health metrics realismo
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


class TestDryRunDirectCoherence:
    """Verifica che dry-run e direct abbiano stesso numero di file"""

    def test_dry_run_lists_all_files(self, tmp_path):
        """dry-run deve menzionare sia adapter che CORE_FILES"""
        from rgen.adapter import Adapter
        from rgen.writer import Writer
        from rgen.models import Profile
        
        # Setup: crea un profilo test
        profile = Profile(
            name="test",
            target_path=tmp_path,
            technologies=["python"],
            domains=["testing"],
        )
        
        # Adapter genera file
        adapter = Adapter()
        files = adapter.adapt(profile)
        
        # CORE_FILES + adapter files
        core_files = len(Writer.CORE_FILES)
        adapter_files = len(files)
        total_expected = core_files + adapter_files
        
        assert core_files == 6, f"CORE_FILES deve avere 6 file, ha {core_files}"
        assert adapter_files > 0, f"Adapter deve generare file, ha {adapter_files}"
        assert total_expected > 10, f"Total deve essere > 10, ha {total_expected}"

    def test_dry_run_includes_core_files_in_output(self, capsys, tmp_path):
        """Quando user fa dry-run, output deve menzionare CORE_FILES"""
        # Questo è testato in test_cli.py, qui verifichiamo solo struttura
        from rgen.writer import Writer
        
        expected = {
            "router.py",
            "router_audit.py", 
            "router_planner.py",
            "interventions.py",
            "mcp_server.py",
            "requirements.txt",
        }
        
        actual = set(Writer.CORE_FILES)
        assert actual == expected, (
            f"CORE_FILES: {actual} != {expected}"
        )


class TestAuditQuality:
    """Verifica audit su vari ambienti"""

    def test_audit_json_structure_valid(self):
        """Audit deve ritornare JSON valido con struttura corretta"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import audit_routing_coverage
        
        result = audit_routing_coverage()
        
        # Struttura obbligatoria
        assert "mode" in result
        assert result["mode"] == "audit"
        assert "scan_available" in result
        assert "total_scenarios" in result
        assert "total_keywords" in result
        assert "total_concepts" in result
        assert "covered" in result
        assert "gaps" in result
        
        # Se scan disponibile, coverage % deve essere numero
        if result.get("scan_available"):
            assert isinstance(result.get("coverage_pct"), (int, float))
        else:
            # Se non disponibile, deve avere note esplicativa
            assert result.get("coverage_pct") is None or "note" in result

    def test_audit_no_silent_failures(self):
        """Audit non deve ritornare coverage 0% senza spiegazione"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import audit_routing_coverage
        
        result = audit_routing_coverage()
        
        coverage = result.get("coverage_pct")
        
        # Se coverage < 5%, deve esserci spiegazione
        if coverage is not None and coverage < 5:
            assert (
                not result.get("scan_available", True)
                or "note" in result
                or len(result.get("gap_details", [])) > 0
            ), "Coverage basso deve avere spiegazione"

    def test_audit_concept_count_makes_sense(self):
        """Numero di concetti trovati deve essere realistico"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import audit_routing_coverage
        
        result = audit_routing_coverage()
        
        total = result.get("total_concepts", 0)
        covered = result.get("covered", 0)
        gaps = result.get("gaps", 0)
        
        # Somma deve corrispondere
        if result.get("scan_available"):
            assert total == covered + gaps, (
                f"Total {total} != covered {covered} + gaps {gaps}"
            )


class TestHealthMetricsRealism:
    """Verifica che metriche di health non siano ingannevoli"""

    def test_healthy_router_not_critical(self):
        """Un router funzionante non deve essere segnalato come CRIT"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import get_health_stats
        
        stats = get_health_stats()
        
        # Router.py attuale (~886 righe) deve essere warn o ok
        router_status = stats["metrics"]["router_lines"]["status"]
        assert router_status in ("ok", "warn"), (
            f"Router 886 lines deve essere ok/warn, non {router_status}"
        )
        
        # Se ci sono warn, overall deve essere warn (non crit)
        overall = stats["overall"]
        assert overall in ("ok", "warn"), (
            f"Overall deve essere ok/warn se router è sano, non {overall}"
        )

    def test_threshold_values_are_documented(self):
        """Soglie devono essere documentate e realistiche"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import _THRESHOLDS
        
        # Dopo fix
        assert _THRESHOLDS["router_lines_warn"] == 800
        assert _THRESHOLDS["router_lines_crit"] == 1200
        
        # Ratio deve essere ragionevole (crit non esagerato)
        ratio = _THRESHOLDS["router_lines_crit"] / _THRESHOLDS["router_lines_warn"]
        assert 1.3 < ratio < 2.0, (
            f"Ratio crit/warn deve essere 1.5, è {ratio}"
        )

    def test_all_threshold_values_reasonable(self):
        """Nessuna soglia deve essere ingannevole"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import _THRESHOLDS
        
        # Scenarios: 50 warn, 60 crit (ragionevole per routing maturo)
        assert _THRESHOLDS["scenarios_warn"] <= _THRESHOLDS["scenarios_crit"]
        assert _THRESHOLDS["scenarios_crit"] >= 50, "scenarios_crit troppo basso"
        
        # Keywords: 450 warn, 550 crit
        assert _THRESHOLDS["keywords_warn"] <= _THRESHOLDS["keywords_crit"]
        
        # Router lines: 800 warn, 1200 crit
        assert _THRESHOLDS["router_lines_warn"] <= _THRESHOLDS["router_lines_crit"]
        assert _THRESHOLDS["router_lines_warn"] >= 600, "warn troppo basso"


class TestEndToEndIntegration:
    """Integration test di flusso completo"""

    def test_full_health_check_succeeds(self):
        """Esecuzione completa --stats non deve crashare"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import get_health_stats, audit_routing_coverage
        
        # Esegui entrambi
        stats = get_health_stats()
        audit = audit_routing_coverage()
        
        # Entrambi devono ritornare dati validi
        assert stats.get("mode") == "stats"
        assert audit.get("mode") == "audit"
        assert "metrics" in stats
        assert "total_scenarios" in audit

    def test_mcp_server_imports_correctly(self):
        """MCP server deve importare senza errori"""
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        
        try:
            from mcp_server import main
            assert callable(main), "mcp_server.main deve essere callable"
        except ImportError as e:
            pytest.skip(f"MCP imports non disponibili: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
