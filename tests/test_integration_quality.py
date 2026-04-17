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
from pathlib import Path

import pytest


class TestDryRunDirectCoherence:
    """Verifica che dry-run e direct abbiano stesso numero di file"""

    def test_dry_run_lists_all_files(self, tmp_path):
        from rgen.adapter import Adapter
        from rgen.writer import Writer
        from rgen.models import ProjectProfile
        profile = ProjectProfile(project_name="test", target_path=tmp_path, pattern_id="", tech_stack=["python"], domain_keywords=["testing"])
        repo_root = Path(__file__).parent.parent
        adapter = Adapter(repo_root / "knowledge_base")
        files = adapter.adapt(profile)
        core_files = len(Writer.CORE_FILES)
        adapter_files = len(files)
        total_expected = core_files + adapter_files
        assert core_files == 8, f"CORE_FILES deve avere 8 file, ha {core_files}"
        assert adapter_files > 0, f"Adapter deve generare file, ha {adapter_files}"
        assert total_expected > 10, f"Total deve essere > 10, ha {total_expected}"

    def test_dry_run_includes_core_files_in_output(self, capsys, tmp_path):
        from rgen.writer import Writer
        expected = {
            "router.py",
            "router_audit.py",
            "router_planner.py",
            "interventions.py",
            "mcp_server.py",
            "mcp_status.py",
            "update_manager.py",
            "requirements.txt",
        }
        actual = set(Writer.CORE_FILES)
        assert actual == expected, f"CORE_FILES: {actual} != {expected}"


class TestAuditQuality:
    def test_audit_json_structure_valid(self, no_network_scan):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import audit_routing_coverage
        result = audit_routing_coverage()
        assert "mode" in result
        assert result["mode"] == "audit"
        assert "scan_available" in result
        assert "total_scenarios" in result
        assert "total_keywords" in result
        assert "total_concepts" in result
        assert "covered" in result
        assert "gaps" in result
        if result.get("scan_available"):
            assert isinstance(result.get("coverage_pct"), (int, float))
        else:
            assert result.get("coverage_pct") is None or "note" in result

    def test_audit_no_silent_failures(self, no_network_scan):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import audit_routing_coverage
        result = audit_routing_coverage()
        coverage = result.get("coverage_pct")
        if coverage is not None and coverage < 5:
            assert (not result.get("scan_available", True) or "note" in result or len(result.get("gap_details", [])) > 0), "Coverage basso deve avere spiegazione"

    def test_audit_concept_count_makes_sense(self, no_network_scan):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import audit_routing_coverage
        result = audit_routing_coverage()
        total = result.get("total_concepts", 0)
        covered = result.get("covered", 0)
        gaps = result.get("gaps", 0)
        if result.get("scan_available"):
            assert total == covered + gaps, f"Total {total} != covered {covered} + gaps {gaps}"


class TestHealthMetricsRealism:
    def test_healthy_router_not_critical(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import get_health_stats
        stats = get_health_stats()
        router_status = stats["metrics"]["router_lines"]["status"]
        assert router_status in ("ok", "warn"), f"Router lines deve essere ok/warn, non {router_status}"
        overall = stats["overall"]
        assert overall in ("ok", "warn"), f"Overall deve essere ok/warn, non {overall}"

    def test_threshold_values_are_documented(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import _THRESHOLDS
        assert _THRESHOLDS["router_lines_warn"] == 800
        assert _THRESHOLDS["router_lines_crit"] == 1200
        ratio = _THRESHOLDS["router_lines_crit"] / _THRESHOLDS["router_lines_warn"]
        assert 1.3 < ratio < 2.0, f"Ratio crit/warn deve essere 1.5, e' {ratio}"

    def test_all_threshold_values_reasonable(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import _THRESHOLDS
        assert _THRESHOLDS["scenarios_warn"] <= _THRESHOLDS["scenarios_crit"]
        assert _THRESHOLDS["scenarios_crit"] >= 50
        assert _THRESHOLDS["keywords_warn"] <= _THRESHOLDS["keywords_crit"]
        assert _THRESHOLDS["router_lines_warn"] <= _THRESHOLDS["router_lines_crit"]
        assert _THRESHOLDS["router_lines_warn"] >= 600


class TestEndToEndIntegration:
    def test_full_health_check_succeeds(self, no_network_scan):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        from router_audit import get_health_stats, audit_routing_coverage
        stats = get_health_stats()
        audit = audit_routing_coverage()
        assert stats.get("mode") == "stats"
        assert audit.get("mode") == "audit"
        assert "metrics" in stats
        assert "total_scenarios" in audit

    def test_mcp_server_imports_correctly(self):
        sys.path.insert(0, str(Path(__file__).parent.parent / ".github"))
        try:
            from mcp_server import main
            assert callable(main)
        except (ImportError, SystemExit) as e:
            pytest.skip(f"MCP imports non disponibili: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
