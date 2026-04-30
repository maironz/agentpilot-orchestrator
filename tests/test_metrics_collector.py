"""
Unit tests for RouterMetricsCollector.

Tests cover:
- confidence_trend calculation
- scenario_usage frequency
- agent_overlap detection
- dead_zones identification
- error_rate computation
- full_snapshot integration
"""

from __future__ import annotations

from pathlib import Path
from statistics import mean

import pytest

# Import the collector and mock InterventionStore
from rgen.metrics_collector import RouterMetricsCollector


@pytest.fixture
def mock_interventions(tmp_path):
    """Create mock intervention data for testing."""

    class MockInterventionStore:
        def __init__(self):
            self.data = []

        def recent(self, limit: int = 20):
            return self.data[-limit:] if limit else self.data

        def close(self):
            pass

    store = MockInterventionStore()
    # Pre-populate with test data
    # 15 items:
    # - i=0-11: success@query_optimization (12 items)
    # - i=12: partial@query_optimization (1 item)
    # - i=13-14: success@config_validation (2 items)
    store.data = [
        {
            "id": i,
            "ts": f"2026-04-06T10:{i:02d}:00Z",
            "agent": "backend" if i % 3 == 0 else "devops",
            "scenario": "query_optimization" if i < 13 else "config_validation",
            "query": f"Test query {i}",
            "resolution": f"Fixed {i}",
            "outcome": "partial" if i == 12 else "success",
            "files_touched": [],
            "tags": [],
        }
        for i in range(15)
    ]
    return store


def test_confidence_trend_with_data(mock_interventions):
    """Test that confidence_trend calculates mean and stdev."""
    collector = RouterMetricsCollector(
        intervention_store=mock_interventions, history_window=15
    )

    trend = collector.confidence_trend()

    assert "values" in trend
    assert "mean" in trend
    assert "stdev" in trend
    assert "recent_5_mean" in trend
    assert "trend" in trend

    # Should have 15 values (14 success @1.0, 1 partial @0.7)
    # mean = (14*1.0 + 1*0.7) / 15 = 14.7 / 15 = 0.98
    assert trend["mean"] == pytest.approx(0.98, abs=0.01)
    assert trend["trend"] in ("stable", "improving", "degrading")


def test_confidence_trend_empty(mock_interventions):
    """Test confidence_trend with no data."""
    mock_interventions.data = []
    collector = RouterMetricsCollector(intervention_store=mock_interventions)

    trend = collector.confidence_trend()

    assert trend["mean"] == 0.0
    assert trend["stdev"] == 0.0
    assert trend["recent_5_mean"] == 0.0
    assert trend["trend"] == "unknown"


def test_scenario_usage_distribution(mock_interventions):
    """Test scenario_usage returns correct frequency distribution."""
    collector = RouterMetricsCollector(intervention_store=mock_interventions)

    usage = collector.scenario_usage()

    assert "top_scenarios" in usage
    assert "total_unique" in usage
    assert "distribution" in usage

    # Should have 2 unique scenarios
    assert usage["total_unique"] == 2

    # query_optimization should be first (13 count vs 2 for config_validation)
    assert usage["top_scenarios"][0]["scenario"] == "query_optimization"
    assert usage["top_scenarios"][0]["count"] == 13


def test_agent_overlap_detection(mock_interventions):
    """Test agent_overlap finds shared scenarios."""
    collector = RouterMetricsCollector(intervention_store=mock_interventions)

    overlaps = collector.agent_overlap()

    assert "overlaps" in overlaps
    assert "overlap_count" in overlaps

    # backend and devops both handle query_optimization and config_validation
    # so they should have overlaps
    assert overlaps["overlap_count"] > 0

    if overlaps["overlaps"]:
        overlap_item = overlaps["overlaps"][0]
        assert "agents" in overlap_item
        assert "shared_scenarios" in overlap_item


def test_dead_zones_identification(mock_interventions):
    """Test dead_zones identifies low-confidence items."""
    collector = RouterMetricsCollector(
        intervention_store=mock_interventions, history_window=15
    )

    dead_zones = collector.dead_zones(confidence_threshold=0.5)

    assert "dead_zone_count" in dead_zones
    assert "threshold" in dead_zones
    assert "items" in dead_zones

    # With threshold 0.5, success (1.0) and partial (0.7) all pass
    assert dead_zones["dead_zone_count"] == 0

    # Test with high threshold (0.95)
    # Only 1 partial (0.7) would be caught
    dead_zones_strict = collector.dead_zones(confidence_threshold=0.95)
    assert dead_zones_strict["dead_zone_count"] == 1  # the partial at i=12


def test_error_rate_computation(mock_interventions):
    """Test error_rate calculates success vs fail distribution."""
    collector = RouterMetricsCollector(intervention_store=mock_interventions)

    error_rate = collector.error_rate()

    assert "outcome_distribution" in error_rate
    assert "success_rate" in error_rate
    assert "error_rate" in error_rate

    # 14 success, 1 partial out of 15
    # success_rate = 14/15 = 0.933
    assert error_rate["success_rate"] == pytest.approx(14 / 15, abs=0.01)
    assert error_rate["error_rate"] == pytest.approx(1 / 15, abs=0.01)


def test_full_snapshot_integration(mock_interventions):
    """Test full_snapshot aggregates all metrics."""
    collector = RouterMetricsCollector(intervention_store=mock_interventions)

    snapshot = collector.full_snapshot()

    assert "timestamp" in snapshot
    assert "window" in snapshot
    assert "confidence" in snapshot
    assert "scenario_usage" in snapshot
    assert "agent_overlap" in snapshot
    assert "dead_zones" in snapshot
    assert "error_rate" in snapshot

    # Verify all sub-sections have expected keys
    assert snapshot["confidence"]["mean"] >= 0
    assert snapshot["scenario_usage"]["total_unique"] == 2
    assert isinstance(snapshot["agent_overlap"]["overlap_count"], int)
    assert snapshot["error_rate"]["success_rate"] >= 0


def test_metrics_collector_no_store():
    """Test collector handles None intervention_store gracefully."""
    # Create collector with no store
    collector = RouterMetricsCollector(intervention_store=None)

    # Should not crash, return empty/zero metrics
    assert collector.confidence_trend()["mean"] == 0.0
    assert collector.scenario_usage()["total_unique"] == 0
    assert collector.agent_overlap()["overlap_count"] == 0


def test_metrics_collector_context_manager(mock_interventions):
    """Test collector works as context manager."""
    with RouterMetricsCollector(intervention_store=mock_interventions) as collector:
        snapshot = collector.full_snapshot()
        assert "timestamp" in snapshot

    # After exit, should be closed (no exception)


def test_outcome_to_confidence_mapping():
    """Test confidence score mapping from outcomes."""
    scores = {
        "success": 1.0,
        "partial": 0.7,
        "failed": 0.3,
        "reverted": 0.2,
        "unknown": 0.5,
    }

    for outcome, expected_score in scores.items():
        score = RouterMetricsCollector._outcome_to_confidence(outcome)
        assert score == expected_score


def test_scenario_usage_sorting(mock_interventions):
    """Test scenario_usage sorts by frequency descending."""
    # Create unbalanced data
    mock_interventions.data = [
        {
            "id": i,
            "ts": f"2026-04-06T10:{i:02d}:00Z",
            "agent": "backend",
            "scenario": "rare_scenario" if i == 0 else "common_scenario",
            "query": f"Query {i}",
            "resolution": "Done",
            "outcome": "success",
            "files_touched": [],
            "tags": [],
        }
        for i in range(10)
    ]

    collector = RouterMetricsCollector(intervention_store=mock_interventions)
    usage = collector.scenario_usage()

    # common_scenario should be first (9 count)
    assert usage["top_scenarios"][0]["scenario"] == "common_scenario"
    assert usage["top_scenarios"][0]["count"] == 9


def test_dead_zones_truncation(mock_interventions):
    """Test dead_zones truncates long queries."""
    mock_interventions.data = [
        {
            "id": 1,
            "ts": "2026-04-06T10:00:00Z",
            "agent": "unknown",
            "scenario": "unmatched",
            "query": "x" * 200,  # very long query
            "resolution": "Failed",
            "outcome": "failed",  # low confidence (0.3)
            "files_touched": [],
            "tags": [],
        }
    ]

    collector = RouterMetricsCollector(intervention_store=mock_interventions)
    dead_zones = collector.dead_zones(confidence_threshold=0.5)

    assert dead_zones["dead_zone_count"] == 1
    # Query should be truncated to 80 chars
    assert len(dead_zones["items"][0]["query"]) <= 80


# ─── Milestone 1: New metrics tests ───

def test_fallback_rate_with_fallbacks(mock_interventions):
    """Test fallback_rate counts _fallback scenario correctly."""
    # Add 3 _fallback items to the existing 15
    fallback_items = [
        {
            "id": 100 + i,
            "ts": f"2026-04-06T11:{i:02d}:00Z",
            "agent": "orchestratore",
            "scenario": "_fallback",
            "query": f"Unmatched query {i}",
            "resolution": "Fallback used",
            "outcome": "success",
            "files_touched": [],
            "tags": [],
        }
        for i in range(3)
    ]
    mock_interventions.data += fallback_items

    collector = RouterMetricsCollector(
        intervention_store=mock_interventions, history_window=50
    )
    result = collector.fallback_rate()

    assert result["fallback_count"] == 3
    assert result["total"] == 18
    assert result["fallback_rate"] == pytest.approx(3 / 18, abs=0.001)


def test_fallback_rate_no_fallbacks(mock_interventions):
    """Test fallback_rate returns 0.0 when no _fallback scenarios exist."""
    collector = RouterMetricsCollector(
        intervention_store=mock_interventions, history_window=50
    )
    result = collector.fallback_rate()

    assert result["fallback_count"] == 0
    assert result["total"] == 15
    assert result["fallback_rate"] == 0.0


def test_fallback_rate_no_store():
    """Test fallback_rate returns zero-state when no store."""
    collector = RouterMetricsCollector(intervention_store=None)
    result = collector.fallback_rate()

    assert result["fallback_count"] == 0
    assert result["total"] == 0
    assert result["fallback_rate"] == 0.0


def test_confidence_trend_buckets(mock_interventions):
    """Test that confidence_trend includes bucket distribution."""
    collector = RouterMetricsCollector(
        intervention_store=mock_interventions, history_window=15
    )
    trend = collector.confidence_trend()

    assert "buckets" in trend
    buckets = trend["buckets"]
    assert set(buckets.keys()) == {"0_25", "25_50", "50_75", "75_100"}

    # 14 success (1.0) → 75_100 bucket; 1 partial (0.7) → 50_75 bucket
    assert buckets["75_100"] == 14
    assert buckets["50_75"] == 1
    assert buckets["0_25"] == 0
    assert buckets["25_50"] == 0

    # Sum of all buckets equals number of values
    assert sum(buckets.values()) == len(trend["values"])


def test_confidence_trend_buckets_empty():
    """Test confidence_trend buckets when no data."""
    collector = RouterMetricsCollector(intervention_store=None)
    trend = collector.confidence_trend()

    assert "buckets" in trend
    assert all(v == 0 for v in trend["buckets"].values())


def test_full_snapshot_includes_fallback_rate(mock_interventions):
    """Test full_snapshot now includes fallback_rate."""
    collector = RouterMetricsCollector(intervention_store=mock_interventions)
    snapshot = collector.full_snapshot()

    assert "fallback_rate" in snapshot
    assert "fallback_count" in snapshot["fallback_rate"]
    assert "fallback_rate" in snapshot["fallback_rate"]

