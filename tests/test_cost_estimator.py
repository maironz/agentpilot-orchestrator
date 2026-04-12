"""Tests for rgen.cost_estimator — P3.2 Cost Estimator."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rgen.cost_estimator import CostEstimator, _DEFAULT_PRICING


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_store(interventions: list[dict]):
    """Crea un store mock con interventi predefiniti."""
    store = MagicMock()
    store.recent.return_value = interventions
    return store


def _make_interventions(scenario: str, query: str, response: str, n: int = 5) -> list[dict]:
    return [{"scenario": scenario, "query": query, "response": response, "outcome": "success"}
            for _ in range(n)]


# ---------------------------------------------------------------------------
# Unit tests — CostEstimator base behaviour
# ---------------------------------------------------------------------------

class TestCostEstimatorInit:
    def test_default_model_is_gpt4o_mini(self):
        est = CostEstimator()
        assert est.model == "gpt-4o-mini"

    def test_list_models_includes_known_models(self):
        est = CostEstimator()
        models = est.list_models()
        assert "gpt-4o" in models
        assert "claude-3-5-sonnet" in models
        assert "gpt-4o-mini" in models

    def test_custom_model_is_stored(self):
        est = CostEstimator(model="gpt-4o")
        assert est.model == "gpt-4o"

    def test_pricing_db_missing_file_uses_defaults(self, tmp_path):
        est = CostEstimator(pricing_db_path=tmp_path / "nonexistent.json")
        assert "gpt-4o-mini" in est._pricing

    def test_pricing_db_invalid_json_uses_defaults(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not valid json{{{", encoding="utf-8")
        est = CostEstimator(pricing_db_path=bad)
        assert "gpt-4o-mini" in est._pricing

    def test_unknown_model_falls_back_to_gpt4o_mini_pricing(self):
        est = CostEstimator(model="totally-unknown-model-xyz")
        pricing = est._model_pricing()
        assert pricing["input_per_1k"] == _DEFAULT_PRICING["gpt-4o-mini"]["input_per_1k"]

    def test_pricing_db_override(self, tmp_path):
        custom_pricing = {"custom-model": {"input_per_1k": 0.001, "output_per_1k": 0.002, "context_window": 32000}}
        db = tmp_path / "pricing.json"
        db.write_text(json.dumps(custom_pricing), encoding="utf-8")
        est = CostEstimator(pricing_db_path=db)
        assert "custom-model" in est._pricing
        # Default models still present
        assert "gpt-4o-mini" in est._pricing

    def test_premium_pricing_is_merged_when_available(self):
        premium = {
            "premium-model": {
                "input_per_1k": 0.02,
                "output_per_1k": 0.05,
                "context_window": 200000,
            }
        }
        with patch("rgen.cost_estimator.load_premium_pricing", return_value=premium):
            est = CostEstimator()
        assert "premium-model" in est._pricing

    def test_pricing_db_has_precedence_over_premium(self, tmp_path):
        premium = {
            "premium-model": {
                "input_per_1k": 0.02,
                "output_per_1k": 0.05,
                "context_window": 200000,
            }
        }
        db_payload = {
            "premium-model": {
                "input_per_1k": 0.01,
                "output_per_1k": 0.03,
                "context_window": 128000,
            }
        }
        db = tmp_path / "pricing.json"
        db.write_text(json.dumps(db_payload), encoding="utf-8")

        with patch("rgen.cost_estimator.load_premium_pricing", return_value=premium):
            est = CostEstimator(pricing_db_path=db)

        assert est._pricing["premium-model"]["input_per_1k"] == 0.01
        assert est._pricing["premium-model"]["output_per_1k"] == 0.03


class TestCostEstimatorNoHistory:
    def test_estimate_without_store(self):
        est = CostEstimator(store=None, monthly_queries=500)
        result = est.estimate()
        assert result["data_source"] == "heuristic"
        assert result["model"] == "gpt-4o-mini"
        assert result["monthly_queries"] == 500
        assert isinstance(result["total_estimated_monthly_cost_usd"], float)
        assert result["total_estimated_monthly_cost_usd"] >= 0
        assert len(result["scenarios"]) >= 1

    def test_estimate_structure(self):
        est = CostEstimator(store=None)
        result = est.estimate()
        assert "scenarios" in result
        assert "pricing_snapshot" in result
        assert "accuracy_note" in result
        assert "input_per_1k_usd" in result["pricing_snapshot"]

    def test_empty_history_falls_back_to_heuristic(self):
        store = _make_store([])
        est = CostEstimator(store=store)
        result = est.estimate()
        assert result["data_source"] == "heuristic"

    def test_store_exception_falls_back_to_heuristic(self):
        store = MagicMock()
        store.recent.side_effect = RuntimeError("db locked")
        est = CostEstimator(store=store)
        result = est.estimate()
        assert result["data_source"] == "heuristic"


class TestCostEstimatorWithHistory:
    def test_estimate_with_history_uses_history_source(self):
        ivns = _make_interventions("python_code", "fix this bug", "here is the fix", n=10)
        store = _make_store(ivns)
        est = CostEstimator(store=store, monthly_queries=100)
        result = est.estimate()
        assert result["data_source"] == "history"

    def test_single_scenario_aggregation(self):
        ivns = _make_interventions("auth", "login issue", "response here", n=20)
        store = _make_store(ivns)
        est = CostEstimator(store=store, monthly_queries=200)
        result = est.estimate()
        scenarios = {s["name"]: s for s in result["scenarios"]}
        assert "auth" in scenarios
        assert scenarios["auth"]["history_count"] == 20

    def test_multiple_scenarios_sorted_by_cost(self):
        ivns = (
            _make_interventions("python_code", "short", "short resp", n=5) +
            _make_interventions("database", "long query " * 50, "long response " * 100, n=20)
        )
        store = _make_store(ivns)
        est = CostEstimator(store=store, monthly_queries=500)
        result = est.estimate()
        costs = [s["estimated_monthly_cost_usd"] for s in result["scenarios"]]
        assert costs == sorted(costs, reverse=True)

    def test_total_cost_equals_sum_of_scenarios(self):
        ivns = (
            _make_interventions("auth", "q", "r", n=10) +
            _make_interventions("backend", "query", "response", n=10)
        )
        store = _make_store(ivns)
        est = CostEstimator(store=store, monthly_queries=100)
        result = est.estimate()
        total = sum(s["estimated_monthly_cost_usd"] for s in result["scenarios"])
        assert abs(result["total_estimated_monthly_cost_usd"] - total) < 0.0001

    def test_cost_is_non_negative(self):
        ivns = _make_interventions("testing", "run tests", "all passed", n=5)
        store = _make_store(ivns)
        est = CostEstimator(store=store)
        result = est.estimate()
        for s in result["scenarios"]:
            assert s["estimated_monthly_cost_usd"] >= 0


class TestConsolidationHints:
    def test_consolidation_hint_for_known_pair(self):
        ivns = (
            _make_interventions("performance", "slow query", "optimize idx", n=5) +
            _make_interventions("database", "db timeout", "add index", n=5)
        )
        store = _make_store(ivns)
        est = CostEstimator(store=store, monthly_queries=100)
        result = est.estimate()
        hints = {s["name"]: s.get("optimization_hint") for s in result["scenarios"]}
        assert hints.get("performance") is not None
        assert "database" in hints["performance"]

    def test_no_hint_for_single_scenario(self):
        ivns = _make_interventions("auth", "login", "ok", n=5)
        store = _make_store(ivns)
        est = CostEstimator(store=store)
        result = est.estimate()
        for s in result["scenarios"]:
            assert s.get("optimization_hint") is None


class TestAccuracyFixture:
    """Verifica accuratezza +/- 10% su dataset noto con token count esatti."""

    def test_accuracy_known_fixture(self):
        """
        Fixture: 100 interventi, query=400 chars (≈100 tok input), response=1000 chars (≈250 tok output).
        Model gpt-4o-mini: 0.00015/1k input, 0.0006/1k output.
        Expected cost per query ≈ (100/1000)*0.00015 + (250/1000)*0.0006 = 0.000015 + 0.00015 = 0.000165 USD.
        Per 100 query = 0.0165 USD.
        """
        query = "a" * 400        # 400 chars ≈ 100 tokens
        response = "b" * 1000   # 1000 chars ≈ 250 tokens
        ivns = _make_interventions("python_code", query, response, n=100)
        store = _make_store(ivns)
        est = CostEstimator(store=store, model="gpt-4o-mini", monthly_queries=100)
        result = est.estimate()

        scenarios = {s["name"]: s for s in result["scenarios"]}
        assert "python_code" in scenarios
        estimated = scenarios["python_code"]["estimated_monthly_cost_usd"]
        # All 100 history entries → 100% of 100 monthly queries = 100 queries
        # input ≈ 100 tok, output ≈ 250 tok
        expected = (100 / 1000 * 0.00015) + (250 / 1000 * 0.0006)  # per query
        expected_total = expected * 100  # 100 queries
        error_pct = abs(estimated - expected_total) / expected_total if expected_total > 0 else 0
        assert error_pct <= 0.10, f"Accuracy {error_pct:.1%} exceeds +/-10% (estimated={estimated}, expected={expected_total})"


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestCostReportCLI:
    def test_cost_report_flag_json_output(self, tmp_path, capsys):
        from rgen.cli import main
        result = main(["--cost-report", "--target", str(tmp_path), "--cost-format", "json"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "total_estimated_monthly_cost_usd" in data

    def test_cost_report_text_output(self, tmp_path, capsys):
        from rgen.cli import main
        result = main(["--cost-report", "--target", str(tmp_path), "--cost-format", "text"])
        assert result == 0
        captured = capsys.readouterr()
        assert "Cost Report" in captured.out
        assert "Total estimated" in captured.out

    def test_cost_report_saves_to_file(self, tmp_path, capsys):
        from rgen.cli import main
        output_file = tmp_path / "cost.json"
        result = main(["--cost-report", "--target", str(tmp_path), "--cost-output", str(output_file)])
        assert result == 0
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "scenarios" in data

    def test_cost_report_custom_model(self, tmp_path, capsys):
        from rgen.cli import main
        result = main(["--cost-report", "--target", str(tmp_path), "--cost-model", "gpt-4o"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["model"] == "gpt-4o"

    def test_cost_report_custom_monthly_queries(self, tmp_path, capsys):
        from rgen.cli import main
        result = main(["--cost-report", "--target", str(tmp_path), "--cost-monthly-queries", "2000"])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["monthly_queries"] == 2000

    def test_pricing_db_custom_file(self, tmp_path, capsys):
        from rgen.cli import main
        custom = {"test-model": {"input_per_1k": 0.001, "output_per_1k": 0.002, "context_window": 4000}}
        pricing_file = tmp_path / "pricing.json"
        pricing_file.write_text(json.dumps(custom), encoding="utf-8")
        result = main([
            "--cost-report", "--target", str(tmp_path),
            "--cost-model", "test-model",
            "--pricing-db", str(pricing_file),
        ])
        assert result == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["model"] == "test-model"
