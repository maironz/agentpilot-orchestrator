"""Optional loader for premium/private runtime components.

This module defines stable boundaries for monetizable runtime pieces.
If a private package is installed, the core can consume its implementations.
Otherwise the bundled open-core fallback remains active.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any


def _load_symbol(
    symbol_name: str,
    fallback_module: str,
    private_module: str = "agentpilot_intelligence.runtime",
) -> Any:
    """Load a symbol from the private runtime first, then bundled fallback."""
    for module_name in (private_module, fallback_module):
        try:
            module = import_module(module_name)
        except Exception:
            continue

        symbol = getattr(module, symbol_name, None)
        if symbol is not None:
            return symbol

    return None


def load_weight_calibrator() -> Any:
    """Load RouterWeightCalibrator from premium runtime or open-core fallback."""
    return _load_symbol("RouterWeightCalibrator", "rgen.weight_calibrator")


def load_graph_router() -> Any:
    """Load GraphRouter from premium runtime or open-core fallback."""
    return _load_symbol("GraphRouter", "rgen.graph_router")


def load_scenario_clusterer() -> Any:
    """Load ScenarioClusterer from premium runtime or open-core fallback."""
    return _load_symbol("ScenarioClusterer", "rgen.scenario_clusterer")


def load_metrics_collector() -> Any:
    """Load RouterMetricsCollector from premium runtime or open-core fallback."""
    return _load_symbol("RouterMetricsCollector", "rgen.metrics_collector")


def load_dashboard_ui() -> Any:
    """Load DashboardUI from premium runtime or open-core fallback."""
    return _load_symbol("DashboardUI", "rgen.dashboard_ui")