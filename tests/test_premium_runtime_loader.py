"""Tests for optional premium runtime loader boundary."""

from __future__ import annotations

from types import SimpleNamespace

from rgen.premium_runtime_loader import (
    load_dashboard_ui,
    load_graph_router,
    load_metrics_collector,
    load_scenario_clusterer,
    load_weight_calibrator,
)


def test_loader_uses_private_runtime_when_available(monkeypatch):
    class PrivateWeightCalibrator:
        pass

    def fake_import(name: str):
        if name == "agentpilot_intelligence.runtime":
            return SimpleNamespace(RouterWeightCalibrator=PrivateWeightCalibrator)
        raise ImportError(name)

    monkeypatch.setattr("rgen.premium_runtime_loader.import_module", fake_import)

    assert load_weight_calibrator() is PrivateWeightCalibrator


def test_loader_falls_back_to_bundled_runtime(monkeypatch):
    class FallbackGraphRouter:
        pass

    def fake_import(name: str):
        if name == "agentpilot_intelligence.runtime":
            raise ImportError(name)
        if name == "rgen.graph_router":
            return SimpleNamespace(GraphRouter=FallbackGraphRouter)
        raise ImportError(name)

    monkeypatch.setattr("rgen.premium_runtime_loader.import_module", fake_import)

    assert load_graph_router() is FallbackGraphRouter


def test_loader_returns_none_when_symbol_missing_everywhere(monkeypatch):
    monkeypatch.setattr(
        "rgen.premium_runtime_loader.import_module",
        lambda _name: SimpleNamespace(),
    )

    assert load_scenario_clusterer() is None


def test_loader_loads_metrics_and_dashboard_symbols(monkeypatch):
    class PrivateMetricsCollector:
        pass

    class PrivateDashboardUI:
        pass

    def fake_import(name: str):
        if name == "agentpilot_intelligence.runtime":
            return SimpleNamespace(
                RouterMetricsCollector=PrivateMetricsCollector,
                DashboardUI=PrivateDashboardUI,
            )
        raise ImportError(name)

    monkeypatch.setattr("rgen.premium_runtime_loader.import_module", fake_import)

    assert load_metrics_collector() is PrivateMetricsCollector
    assert load_dashboard_ui() is PrivateDashboardUI