"""
Unit tests for RouterWeightCalibrator.

Tests cover:
- Success rate calculation with decay
- Keyword weight computation
- Minimum sample gating
- Dry-run mode
- Weight export/import
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from rgen.weight_calibrator import RouterWeightCalibrator


@pytest.fixture
def mock_interventions():
    """Create mock intervention store with test data."""

    class MockInterventionStore:
        def __init__(self):
            self.data = []

        def recent(self, limit: int = 20):
            return self.data[-limit:] if limit else self.data

        def close(self):
            pass

    store = MockInterventionStore()

    # Create test data:
    # Scenario A: 80% success (8/10)
    # Scenario B: 40% success (2/5)
    # Scenario C: insufficient data (only 3 samples)
    now = datetime.now()

    data = []

    # Scenario A: high success
    for i in range(8):
        data.append({
            "ts": (now - timedelta(days=2-i)).isoformat() + "Z",
            "agent": "backend",
            "scenario": "query_optimization",
            "query": f"optimize {i}",
            "outcome": "success",
        })
    for i in range(2):
        data.append({
            "ts": (now - timedelta(days=10+i)).isoformat() + "Z",
            "agent": "backend",
            "scenario": "query_optimization",
            "query": f"optimize fail {i}",
            "outcome": "failed",
        })

    # Scenario B: lower success
    for i in range(2):
        data.append({
            "ts": (now - timedelta(days=1)).isoformat() + "Z",
            "agent": "devops",
            "scenario": "config_validation",
            "query": f"config {i}",
            "outcome": "success",
        })
    for i in range(3):
        data.append({
            "ts": (now - timedelta(days=5)).isoformat() + "Z",
            "agent": "devops",
            "scenario": "config_validation",
            "query": f"config fail {i}",
            "outcome": "failed",
        })

    # Scenario C: too few samples
    for i in range(3):
        data.append({
            "ts": (now - timedelta(days=3)).isoformat() + "Z",
            "agent": "dev",
            "scenario": "rare_scenario",
            "query": f"rare {i}",
            "outcome": "success",
        })

    store.data = data
    return store


def test_success_rate_calculation(mock_interventions):
    """Test success rate is computed correctly."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=3)

    rates = calibrator._compute_scenario_success_rate()

    # Should include query_optimization (recent, high success)
    # config_validation may be below min_samples after decay (older data)
    # rare_scenario is excluded (only 3 samples, at threshold)
    assert "query_optimization" in rates

    success_rate, count = rates["query_optimization"]
    assert 0.5 < success_rate < 1.0  # decay applied
    assert count >= 3


def test_keyword_boost_calculation(mock_interventions):
    """Test keyword boosts are computed from success rates."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=3)

    scenario_rates = calibrator._compute_scenario_success_rate()
    keyword_boosts = calibrator._compute_keyword_weights(scenario_rates)

    # Should have boosts for scenarios with sufficient data
    assert len(keyword_boosts) > 0

    # query_optimization should be included (high data, recent)
    assert "query_optimization" in keyword_boosts


def test_minimum_samples_gate(mock_interventions):
    """Test scenarios with < min_samples are excluded."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=5)

    rates = calibrator._compute_scenario_success_rate()

    # rare_scenario has only 3 samples, should be excluded
    assert "rare_scenario" not in rates

    # Lower threshold
    calibrator2 = RouterWeightCalibrator(mock_interventions, min_samples=2)
    rates2 = calibrator2._compute_scenario_success_rate()

    # Now rare_scenario should be included
    assert "rare_scenario" in rates2


def test_decay_function():
    """Test exponential decay favors recent data."""
    calibrator = RouterWeightCalibrator(intervention_store=None)

    now = datetime.now().isoformat()
    one_day_ago = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
    ten_days_ago = (datetime.now() - timedelta(days=10)).isoformat() + "Z"

    # Decay should be higher for recent timestamps
    decay_now = calibrator._decay_function(now)
    decay_1d = calibrator._decay_function(one_day_ago)
    decay_10d = calibrator._decay_function(ten_days_ago)

    assert decay_now >= decay_1d  # Now should be highest
    assert decay_1d > decay_10d  # 1 day > 10 days


def test_calibrate_returns_expected_structure(mock_interventions):
    """Test calibrate() returns dict with required keys."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=5)

    result = calibrator.calibrate()

    assert "calibrated_weights" in result
    assert "success_rate_by_scenario" in result
    assert "data_freshness" in result
    assert "scenarios_included" in result
    assert "total_samples" in result
    assert "confidence" in result

    assert isinstance(result["calibrated_weights"], dict)
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0


def test_dry_run_no_persistence(mock_interventions):
    """Test dry_run() doesn't modify internal state."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=5)

    # Before dry-run
    assert calibrator._calibrated_weights is None

    result1 = calibrator.dry_run()

    # After dry-run, internal state should remain None
    assert calibrator._calibrated_weights is None

    result2 = calibrator.dry_run()

    # Results should be consistent
    assert result1["confidence"] == result2["confidence"]


def test_export_weights_to_file(mock_interventions, tmp_path):
    """Test exporting calibrated weights to JSON."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=5)
    calibrator.calibrate()

    export_file = tmp_path / "weights.json"
    calibrator.export_weights(str(export_file))

    assert export_file.exists()

    # Verify JSON structure
    with open(export_file) as f:
        data = json.load(f)

    assert "calibrated_at" in data
    assert "keyword_boosts" in data
    assert isinstance(data["keyword_boosts"], dict)


def test_load_weights_from_file(mock_interventions, tmp_path):
    """Test loading calibrated weights from JSON."""
    # First export
    calibrator1 = RouterWeightCalibrator(mock_interventions, min_samples=5)
    calibrator1.calibrate()

    export_file = tmp_path / "weights.json"
    calibrator1.export_weights(str(export_file))

    # Then load
    calibrator2 = RouterWeightCalibrator(intervention_store=None)
    loaded_weights = calibrator2.load_weights(str(export_file))

    assert len(loaded_weights) > 0
    assert "query_optimization" in loaded_weights


def test_calibrator_context_manager(mock_interventions):
    """Test calibrator works as context manager."""
    with RouterWeightCalibrator(mock_interventions, min_samples=5) as calibrator:
        result = calibrator.calibrate()
        assert result["scenarios_included"] > 0


def test_calibrator_no_store():
    """Test calibrator handles None store gracefully."""
    calibrator = RouterWeightCalibrator(intervention_store=None)

    result = calibrator.calibrate()

    assert result["scenarios_included"] == 0
    assert result["confidence"] == 0.0


def test_higher_success_rate_higher_boost(mock_interventions):
    """Test scenarios with higher success rates get higher boosts."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=3)

    scenario_rates = calibrator._compute_scenario_success_rate()
    keyword_boosts = calibrator._compute_keyword_weights(scenario_rates)

    # query_optimization has high success rate
    # Should have boost > 1.0
    if len(keyword_boosts) > 0:
        assert any(v > 1.0 for v in keyword_boosts.values())


def test_insufficient_data_returns_empty(mock_interventions):
    """Test with very high min_samples threshold."""
    calibrator = RouterWeightCalibrator(mock_interventions, min_samples=1000)

    result = calibrator.calibrate()

    # No scenarios have 1000 samples
    assert result["scenarios_included"] == 0
    assert len(result["calibrated_weights"]) == 0


def test_load_nonexistent_file():
    """Test load_weights handles missing file gracefully."""
    calibrator = RouterWeightCalibrator(intervention_store=None)

    weights = calibrator.load_weights("/tmp/nonexistent.json")

    assert weights == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
