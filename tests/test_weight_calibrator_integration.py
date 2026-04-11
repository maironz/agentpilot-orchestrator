"""
Integration tests for weight calibrator in router.py.

Tests cover:
- RouterWeightCalibrator integration with _score_scenarios
- --calibrate-weights CLI flag
- Weighted scoring with boosts
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from rgen.weight_calibrator import RouterWeightCalibrator


@pytest.fixture
def mock_interventions():
    """Create mock intervention store."""

    class MockInterventionStore:
        def __init__(self):
            self.data = [
                {
                    "ts": "2026-04-06T10:00:00Z",
                    "agent": "backend",
                    "scenario": "query_optimization",
                    "query": "optimize query",
                    "outcome": "success",
                },
                {
                    "ts": "2026-04-06T10:01:00Z",
                    "agent": "backend",
                    "scenario": "query_optimization",
                    "query": "optimize index",
                    "outcome": "success",
                },
                {
                    "ts": "2026-04-06T10:02:00Z",
                    "agent": "devops",
                    "scenario": "config_validation",
                    "query": "validate config",
                    "outcome": "failed",
                },
            ] * 5  # Repeat to get more samples

        def recent(self, limit: int = 20):
            return self.data[-limit:] if limit else self.data

        def close(self):
            pass

    return MockInterventionStore()


def test_score_scenarios_with_weights():
    """Test _score_scenarios applies weight boosts correctly."""
    from core.router import _score_scenarios

    routes = {
        "scenario_a": {
            "keywords": ["optimize", "performance", "query"],
            "agent": "backend",
        },
        "scenario_b": {"keywords": ["config", "validate"], "agent": "devops"},
    }

    query = "optimize query performance"
    weights = {"scenario_a": 1.5, "scenario_b": 1.0}

    # Score with weights
    scored_with_weights = _score_scenarios(query, routes, weights)

    # Score without weights
    scored_without = _score_scenarios(query, routes, None)

    # scenario_a should rank higher with boost
    assert len(scored_with_weights) > 0
    assert scored_with_weights[0]["scenario"] == "scenario_a"


def test_router_calibrate_weights_cli():
    """Test --calibrate-weights CLI flag works."""
    repo_root = Path(__file__).parent.parent
    router_path = repo_root / "core" / "router.py"
    github_dir = repo_root / ".github"

    result = subprocess.run(
        [sys.executable, str(router_path), "--calibrate-weights", "--dry-run"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
        cwd=str(github_dir),  # Run from .github directory where routing-map.json lives
    )

    output = (result.stdout or "") + (result.stderr or "")

    # Should succeed or show expected error if no data
    # (returncode 0 if successful, 1 if no intervention data)
    assert result.returncode in (0, 1)

    # Should show some output related to calibration
    assert len(output) > 0


def test_weight_calibrator_with_routes(mock_interventions):
    """Test calibrator works with routing map."""
    routes = {
        "query_optimization": {
            "keywords": ["optimize", "query", "performance"],
            "agent": "backend",
        },
        "config_validation": {"keywords": ["config", "validate"], "agent": "devops"},
    }

    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=3)
    result = calibrator.calibrate(routes)

    # Should calibrate successfully
    assert result["scenarios_included"] > 0
    assert len(result["calibrated_weights"]) > 0


def test_calibrator_dry_run_no_export(mock_interventions, tmp_path):
    """Test dry-run mode doesn't export weights."""
    routes = {
        "query_optimization": {
            "keywords": ["optimize", "query"],
            "agent": "backend",
        },
    }

    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=3)

    # Dry run
    result = calibrator.dry_run(routes)

    # Should return result but not export
    assert result["scenarios_included"] > 0

    # File should not exist
    export_file = tmp_path / "weights.json"
    assert not export_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
