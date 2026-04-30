"""
Router Metrics Collector — real-time routing health analytics.

Collects statistics from interventions.db to feed dashboard and monitoring.
Metrics computed:
  - confidence_trend: rolling average confidence scores
  - scenario_usage: frequency distribution per scenario
  - agent_overlap: keywords shared between agents
  - dead_zones: unmatched or low-confidence queries
  - error_rate: success vs fail vs reverted interventions
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, stdev
from typing import Any

# Import from core (sibling to rgen)
import sys
from pathlib import Path as PathlibPath

_core_path = PathlibPath(__file__).parent.parent / "core"
if str(_core_path) not in sys.path:
    sys.path.insert(0, str(_core_path))

try:
    from interventions import InterventionStore
except ImportError:
    # Fallback if not importable at runtime
    InterventionStore = None


_MISSING = object()


class RouterMetricsCollector:
    """
    Collects metrics from intervention history to monitor routing health.

    Metrics:
    - confidence_trend: rolling average confidence from recent queries
    - scenario_usage: count of interventions per scenario
    - agent_overlap: keywords shared between agents
    - dead_zones: unmatched or low-confidence queries
    - error_rate: outcome distribution (success/partial/failed/reverted)
    """

    def __init__(
        self,
        intervention_store=_MISSING,
        history_window: int = 50,
        db_path: Path | str | None = None,
    ):
        """
        Initialize metrics collector.

        Args:
            intervention_store: InterventionStore instance, None to disable store,
                                 or omit to auto-create from db_path or default DB.
            history_window: number of recent interventions to analyze
            db_path: path to interventions.db (only used if store is not provided)
        """
        self.window = history_window
        self.store: Any
        if intervention_store is _MISSING:
            # Auto-create store (default behaviour)
            self.store = (
                InterventionStore(db_path) if (InterventionStore and db_path)
                else (InterventionStore() if InterventionStore else None)
            )
        else:
            # Explicit value (including None) → use as-is
            self.store = intervention_store
        self._confidence_cache = []
        self._refresh_confidence_cache()

    def _refresh_confidence_cache(self):
        """Populate confidence cache from interventions."""
        if not self.store:
            self._confidence_cache = []
            return

        recent = self.store.recent(limit=self.window)
        # For now, derive confidence from outcome (will be real confidence once logged)
        self._confidence_cache = [
            self._outcome_to_confidence(item.get("outcome", "success"))
            for item in recent
        ]

    @staticmethod
    def _outcome_to_confidence(outcome: str) -> float:
        """Map outcome to confidence score (0.0 to 1.0)."""
        outcome_scores = {
            "success": 1.0,
            "partial": 0.7,
            "failed": 0.3,
            "reverted": 0.2,
        }
        return outcome_scores.get(outcome, 0.5)

    def confidence_trend(self) -> dict:
        """
        Compute confidence statistics from recent interventions.

        Returns:
            {
                "values": [0.87, 0.92, 0.61, ...],
                "mean": 0.8,
                "stdev": 0.15,
                "recent_5_mean": 0.85,
                "trend": "stable" | "improving" | "degrading"
            }
        """
        if not self._confidence_cache:
            return {
                "values": [],
                "mean": 0.0,
                "stdev": 0.0,
                "recent_5_mean": 0.0,
                "trend": "unknown",
                "buckets": {"0_25": 0, "25_50": 0, "50_75": 0, "75_100": 0},
            }

        values = self._confidence_cache
        mean_val = mean(values)
        stdev_val = stdev(values) if len(values) > 1 else 0.0

        # Recent 5 average
        recent_5 = values[:5] if len(values) >= 5 else values
        recent_5_mean = mean(recent_5) if recent_5 else 0.0

        # Trend: compare first half vs second half
        mid = len(values) // 2
        if mid > 0:
            first_half_mean = mean(values[mid:])
            second_half_mean = mean(values[:mid])
            if second_half_mean > first_half_mean + 0.1:
                trend = "degrading"
            elif second_half_mean < first_half_mean - 0.1:
                trend = "improving"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Confidence bucket distribution (0-25%, 25-50%, 50-75%, 75-100%)
        buckets = {"0_25": 0, "25_50": 0, "50_75": 0, "75_100": 0}
        for v in values:
            if v < 0.25:
                buckets["0_25"] += 1
            elif v < 0.50:
                buckets["25_50"] += 1
            elif v < 0.75:
                buckets["50_75"] += 1
            else:
                buckets["75_100"] += 1

        return {
            "values": [round(v, 2) for v in values],
            "mean": round(mean_val, 2),
            "stdev": round(stdev_val, 2),
            "recent_5_mean": round(recent_5_mean, 2),
            "trend": trend,
            "buckets": buckets,
        }

    def scenario_usage(self) -> dict:
        """
        Get usage frequency per scenario (recent window).

        Returns:
            {
                "top_scenarios": [
                    {"scenario": "query_optimization", "count": 12},
                    {"scenario": "config_validation", "count": 8},
                ],
                "total_unique": 7,
                "distribution": {"query_optimization": 12, ...}
            }
        """
        if not self.store:
            return {"top_scenarios": [], "total_unique": 0, "distribution": {}}

        recent = self.store.recent(limit=self.window)
        scenario_counts = {}

        for item in recent:
            scenario = item.get("scenario", "unknown")
            scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1

        sorted_scenarios = sorted(
            scenario_counts.items(), key=lambda x: x[1], reverse=True
        )

        return {
            "top_scenarios": [
                {"scenario": s, "count": c} for s, c in sorted_scenarios[:10]
            ],
            "total_unique": len(scenario_counts),
            "distribution": scenario_counts,
        }

    def agent_overlap(self) -> dict:
        """
        Detect which agents handle overlapping scenarios/keywords.

        For now, uses scenario + agent mapping from interventions.
        Returns:
            {
                "overlaps": [
                    {"agents": ["agent_a", "agent_b"], "shared_scenarios": ["scenario_x"]},
                ],
                "overlap_count": 3
            }
        """
        if not self.store:
            return {"overlaps": [], "overlap_count": 0}

        recent = self.store.recent(limit=self.window)
        agent_scenarios = {}

        for item in recent:
            agent = item.get("agent", "unknown")
            scenario = item.get("scenario", "unknown")
            if agent not in agent_scenarios:
                agent_scenarios[agent] = set()
            agent_scenarios[agent].add(scenario)

        # Find overlaps
        overlaps = []
        agents = list(agent_scenarios.keys())
        for i, agent_a in enumerate(agents):
            for agent_b in agents[i + 1 :]:
                shared = agent_scenarios[agent_a] & agent_scenarios[agent_b]
                if shared:
                    overlaps.append(
                        {
                            "agents": [agent_a, agent_b],
                            "shared_scenarios": sorted(list(shared)),
                            "count": len(shared),
                        }
                    )

        return {"overlaps": overlaps, "overlap_count": len(overlaps)}

    def dead_zones(self, confidence_threshold: float = 0.5) -> dict:
        """
        Identify interventions with low confidence or unmatched queries.

        Returns:
            {
                "dead_zone_count": 3,
                "threshold": 0.5,
                "items": [
                    {"query": "obscure term", "confidence": 0.15, "agent": "unknown"}
                ]
            }
        """
        if not self._confidence_cache:
            return {"dead_zone_count": 0, "threshold": confidence_threshold, "items": []}

        if not self.store:
            return {"dead_zone_count": 0, "threshold": confidence_threshold, "items": []}

        recent = self.store.recent(limit=self.window)
        dead_zones = []

        for item, conf in zip(recent, self._confidence_cache):
            if conf < confidence_threshold:
                dead_zones.append(
                    {
                        "query": item.get("query", "")[:80],  # truncate
                        "confidence": round(conf, 2),
                        "agent": item.get("agent", "unknown"),
                        "scenario": item.get("scenario", "unknown"),
                        "ts": item.get("ts", ""),
                    }
                )

        return {
            "dead_zone_count": len(dead_zones),
            "threshold": confidence_threshold,
            "items": dead_zones,
        }

    def error_rate(self) -> dict:
        """
        Compute success vs fail rate from recent interventions.

        Returns:
            {
                "outcome_distribution": {
                    "success": 35,
                    "partial": 8,
                    "failed": 5,
                    "reverted": 2
                },
                "success_rate": 0.78,
                "error_rate": 0.22
            }
        """
        if not self.store:
            return {
                "outcome_distribution": {},
                "success_rate": 0.0,
                "error_rate": 0.0,
            }

        recent = self.store.recent(limit=self.window)
        outcome_dist = {}

        for item in recent:
            outcome = item.get("outcome", "success")
            outcome_dist[outcome] = outcome_dist.get(outcome, 0) + 1

        total = sum(outcome_dist.values())
        success_count = outcome_dist.get("success", 0)
        error_count = total - success_count

        return {
            "outcome_distribution": outcome_dist,
            "success_rate": round(success_count / total, 2) if total > 0 else 0.0,
            "error_rate": round(error_count / total, 2) if total > 0 else 0.0,
        }

    def fallback_rate(self) -> dict:
        """
        Compute the rate of _fallback scenario in recent interventions.

        Returns:
            {
                "fallback_count": 3,
                "total": 50,
                "fallback_rate": 0.06
            }
        """
        if not self.store:
            return {"fallback_count": 0, "total": 0, "fallback_rate": 0.0}

        recent = self.store.recent(limit=self.window)
        total = len(recent)
        fallback_count = sum(
            1 for item in recent if item.get("scenario") == "_fallback"
        )

        return {
            "fallback_count": fallback_count,
            "total": total,
            "fallback_rate": round(fallback_count / total, 3) if total > 0 else 0.0,
        }

    def full_snapshot(self) -> dict:
        """
        Return comprehensive metrics snapshot (all of the above).

        Returns:
            {
                "timestamp": "2026-04-06T14:23:15Z",
                "window": 50,
                "confidence": {...},
                "scenario_usage": {...},
                "agent_overlap": {...},
                "dead_zones": {...},
                "error_rate": {...}
            }
        """
        self._refresh_confidence_cache()

        return {
            "timestamp": datetime.now().isoformat() + "Z",
            "window": self.window,
            "confidence": self.confidence_trend(),
            "scenario_usage": self.scenario_usage(),
            "agent_overlap": self.agent_overlap(),
            "dead_zones": self.dead_zones(),
            "error_rate": self.error_rate(),
            "fallback_rate": self.fallback_rate(),
        }

    def close(self):
        """Close the underlying intervention store."""
        if self.store:
            self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
