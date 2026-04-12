"""
Cost Estimator — stima il costo operativo per scenario basandosi su history.

Usage:
    rgen --cost-report --target ./my-app
    rgen --cost-report --target ./my-app --cost-model gpt-4o
    rgen --cost-report --target ./my-app --cost-format text
    rgen --cost-report --target ./my-app --cost-output artifacts/cost.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Default pricing registry (token cost per 1K tokens, USD)
# Aggiornabile tramite pricing_db_path o override constructor.
# ---------------------------------------------------------------------------
_DEFAULT_PRICING: dict[str, dict] = {
    "gpt-4o": {
        "input_per_1k": 0.005,
        "output_per_1k": 0.015,
        "context_window": 128000,
    },
    "gpt-4o-mini": {
        "input_per_1k": 0.00015,
        "output_per_1k": 0.0006,
        "context_window": 128000,
    },
    "gpt-4-turbo": {
        "input_per_1k": 0.01,
        "output_per_1k": 0.03,
        "context_window": 128000,
    },
    "claude-3-5-sonnet": {
        "input_per_1k": 0.003,
        "output_per_1k": 0.015,
        "context_window": 200000,
    },
    "claude-3-haiku": {
        "input_per_1k": 0.00025,
        "output_per_1k": 0.00125,
        "context_window": 200000,
    },
    "gemini-1.5-pro": {
        "input_per_1k": 0.00125,
        "output_per_1k": 0.005,
        "context_window": 1000000,
    },
}

# Heuristic: average tokens per intervention when no history is available
_FALLBACK_INPUT_TOKENS = 1500
_FALLBACK_OUTPUT_TOKENS = 500

# Scenarios that are often redundant and consolidatable
_CONSOLIDATION_PAIRS: list[tuple[str, str]] = [
    ("performance", "database"),
    ("testing", "python_code"),
    ("api_endpoints", "backend"),
    ("docker_infra", "devops"),
]


class CostEstimator:
    """
    Stima il costo mensile per scenario da intervention history.

    Attributi:
        store: InterventionStore per leggere history
        model: modello AI usato per il pricing (default: gpt-4o-mini)
        monthly_queries: stima query mensili se non rilevabili da history
        pricing_db_path: path ad un JSON pricing esterno (opzionale, sovrascrive defaults)
    """

    def __init__(
        self,
        store=None,  # InterventionStore | None
        model: str = "gpt-4o-mini",
        monthly_queries: int = 1000,
        pricing_db_path: Path | str | None = None,
    ):
        self.store = store
        self.model = model
        self.monthly_queries = monthly_queries
        self._pricing = self._load_pricing(pricing_db_path)

    def _load_pricing(self, pricing_db_path: Path | str | None) -> dict:
        """Carica pricing da file esterno o usa i defaults."""
        if pricing_db_path is None:
            return dict(_DEFAULT_PRICING)
        path = Path(pricing_db_path)
        if not path.exists():
            return dict(_DEFAULT_PRICING)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            merged = dict(_DEFAULT_PRICING)
            merged.update(data)
            return merged
        except (json.JSONDecodeError, OSError):
            return dict(_DEFAULT_PRICING)

    def list_models(self) -> list[str]:
        """Restituisce la lista dei modelli nel pricing registry."""
        return sorted(self._pricing.keys())

    def _model_pricing(self) -> dict:
        """Restituisce pricing per il modello corrente, con fallback su gpt-4o-mini."""
        return self._pricing.get(self.model) or self._pricing.get("gpt-4o-mini") or {
            "input_per_1k": 0.001,
            "output_per_1k": 0.002,
            "context_window": 128000,
        }

    def _get_interventions(self) -> list[dict]:
        if self.store is None:
            return []
        try:
            return self.store.recent(limit=10000)
        except Exception:
            return []

    def _aggregate_by_scenario(self, interventions: list[dict]) -> dict[str, dict]:
        """
        Aggrega token e conteggio per scenario da history.

        Returns:
            {
                "python_code": {
                    "count": int,
                    "total_input_tokens": int,
                    "total_output_tokens": int,
                }
            }
        """
        stats: dict[str, dict] = {}
        for item in interventions:
            scenario = item.get("scenario") or "unknown"
            query = item.get("query") or ""
            response = item.get("response") or ""

            # Stima token: ~1 token per 4 caratteri (conservativo)
            input_tokens = max(len(query) // 4, 1)
            output_tokens = max(len(response) // 4, 1)

            if scenario not in stats:
                stats[scenario] = {
                    "count": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                }
            stats[scenario]["count"] += 1
            stats[scenario]["total_input_tokens"] += input_tokens
            stats[scenario]["total_output_tokens"] += output_tokens
        return stats

    def _estimate_scenario_cost(
        self,
        scenario: str,
        scenario_stats: dict,
        total_count: int,
        pricing: dict,
    ) -> dict:
        """
        Calcola costo stimato per un singolo scenario proiettato su base mensile.
        """
        count = scenario_stats["count"]
        fraction = count / total_count if total_count > 0 else 0.0

        if count > 0:
            avg_input = scenario_stats["total_input_tokens"] / count
            avg_output = scenario_stats["total_output_tokens"] / count
        else:
            avg_input = _FALLBACK_INPUT_TOKENS
            avg_output = _FALLBACK_OUTPUT_TOKENS

        monthly = round(fraction * self.monthly_queries)
        monthly_input = avg_input * monthly
        monthly_output = avg_output * monthly

        cost = (
            monthly_input / 1000 * pricing["input_per_1k"]
            + monthly_output / 1000 * pricing["output_per_1k"]
        )

        return {
            "name": scenario,
            "history_count": count,
            "avg_input_tokens": round(avg_input),
            "avg_output_tokens": round(avg_output),
            "estimated_monthly_queries": monthly,
            "estimated_monthly_input_tokens": round(monthly_input),
            "estimated_monthly_output_tokens": round(monthly_output),
            "estimated_monthly_cost_usd": round(cost, 4),
        }

    def _consolidation_hints(self, scenario_names: list[str]) -> dict[str, str]:
        """
        Suggerisce scenari candidati a consolidamento sulla base di coppie note.
        """
        hints: dict[str, str] = {}
        for a, b in _CONSOLIDATION_PAIRS:
            if a in scenario_names and b in scenario_names:
                hints[a] = f"consider consolidating with '{b}'"
        return hints

    def estimate(self) -> dict:
        """
        Calcola il report di stima costi.

        Returns:
            {
                "model": str,
                "monthly_queries": int,
                "total_estimated_monthly_cost_usd": float,
                "scenarios": [
                    {
                        "name": str,
                        "history_count": int,
                        "avg_input_tokens": int,
                        "avg_output_tokens": int,
                        "estimated_monthly_queries": int,
                        "estimated_monthly_input_tokens": int,
                        "estimated_monthly_output_tokens": int,
                        "estimated_monthly_cost_usd": float,
                        "optimization_hint": str | None,
                    }
                ],
                "pricing_snapshot": { ... },
                "data_source": "history" | "heuristic",
                "accuracy_note": str,
            }
        """
        interventions = self._get_interventions()
        pricing = self._model_pricing()

        if interventions:
            stats = self._aggregate_by_scenario(interventions)
            total_count = sum(s["count"] for s in stats.values())
            data_source = "history"
        else:
            # Nessuna history: scenario sintetico basato su fallback
            stats = {
                "unknown": {
                    "count": self.monthly_queries,
                    "total_input_tokens": _FALLBACK_INPUT_TOKENS * self.monthly_queries,
                    "total_output_tokens": _FALLBACK_OUTPUT_TOKENS * self.monthly_queries,
                }
            }
            total_count = self.monthly_queries
            data_source = "heuristic"

        hints = self._consolidation_hints(list(stats.keys()))

        scenario_reports = []
        for scenario, s_stats in sorted(stats.items()):
            entry = self._estimate_scenario_cost(scenario, s_stats, total_count, pricing)
            entry["optimization_hint"] = hints.get(scenario)
            scenario_reports.append(entry)

        # Ordina per costo decrescente
        scenario_reports.sort(
            key=lambda x: x["estimated_monthly_cost_usd"], reverse=True
        )

        total_cost = sum(s["estimated_monthly_cost_usd"] for s in scenario_reports)

        return {
            "model": self.model,
            "monthly_queries": self.monthly_queries,
            "total_estimated_monthly_cost_usd": round(total_cost, 4),
            "scenarios": scenario_reports,
            "pricing_snapshot": {
                "input_per_1k_usd": pricing["input_per_1k"],
                "output_per_1k_usd": pricing["output_per_1k"],
            },
            "data_source": data_source,
            "accuracy_note": (
                "Estimates are based on historical token usage via ~1 token/4 chars heuristic. "
                "Accuracy target: +/- 10% on known fixtures. "
                "For billing-accurate figures, use provider dashboards."
            ),
        }
