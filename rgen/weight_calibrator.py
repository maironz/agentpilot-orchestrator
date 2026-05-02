"""
Router Weight Calibrator — auto-calibrate routing weights from intervention history.

Uses intervention success/failure outcomes to boost weights for high-performing
scenarios and keywords. Implements exponential decay to favor recent data.

Usage:
    from rgen.weight_calibrator import RouterWeightCalibrator
    from core.interventions import InterventionStore

    store = InterventionStore()
    calibrator = RouterWeightCalibrator(store)
    weights = calibrator.calibrate()
    print(weights)
    store.close()
"""

from __future__ import annotations

import json
from datetime import datetime
from math import exp
from pathlib import Path

import sys
from pathlib import Path as PathlibPath

_core_path = PathlibPath(__file__).parent.parent / "core"
if str(_core_path) not in sys.path:
    sys.path.insert(0, str(_core_path))

try:
    from interventions import InterventionStore
except ImportError:
    InterventionStore = None


class RouterWeightCalibrator:
    """
    Calibrate routing weights based on intervention success history.

    Learns which scenarios have high success rates and boosts their keyword
    weights to improve routing accuracy over time.
    """

    def __init__(
        self,
        intervention_store: InterventionStore | None = None,
        min_samples: int = 5,
        decay_alpha: float = 0.1,
    ):
        """
        Initialize weight calibrator.

        Args:
            intervention_store: InterventionStore instance
            min_samples: minimum interventions per scenario to calibrate
            decay_alpha: decay rate for exponential decay (0.1 = 10% per day)
        """
        self.store = intervention_store
        self.min_samples = min_samples
        self.decay_alpha = decay_alpha
        self._calibrated_weights = None
        self._calibration_time = None

    def _decay_function(self, timestamp: str) -> float:
        """
        Exponential decay favoring recent interventions.

        Args:
            timestamp: ISO format timestamp (from intervention)

        Returns:
            Decay factor (0.0 to 1.0), higher = more recent
        """
        try:
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
            days_old = (now - ts).days
            # Decay: exp(-alpha * days) gives e.g. 0.9 at 1 day, 0.37 at 10 days
            return max(0.0, exp(-self.decay_alpha * days_old))
        except (ValueError, TypeError):
            return 1.0  # Assume recent if parsing fails

    def _compute_scenario_success_rate(self) -> dict[str, tuple[float, int]]:
        """
        Compute success rate per scenario with decay applied.

        Returns:
            {
                "scenario_name": (success_rate, total_count),
                ...
            }

        success_rate = weighted_success_count / weighted_total_count
        (weights applied via decay function)
        """
        if not self.store:
            return {}

        all_interventions = self.store.recent(limit=10000)  # Large window
        scenario_stats = {}

        for intervention in all_interventions:
            scenario = intervention.get("scenario", "unknown")
            outcome = intervention.get("outcome", "success")
            ts = intervention.get("ts", "")

            decay = self._decay_function(ts)

            if scenario not in scenario_stats:
                scenario_stats[scenario] = {"success": 0.0, "total": 0.0, "raw_total": 0}

            scenario_stats[scenario]["total"] += decay
            scenario_stats[scenario]["raw_total"] += 1

            if outcome == "success":
                scenario_stats[scenario]["success"] += decay

        # Convert to success rate
        result = {}
        for scenario, stats in scenario_stats.items():
            total = stats["total"]
            raw_total = stats.get("raw_total", 0)
            # Gate by sample cardinality, not by decayed mass, otherwise
            # older-but-plentiful scenarios can be incorrectly excluded.
            if raw_total >= self.min_samples and total > 0:
                success_rate = stats["success"] / total
                result[scenario] = (success_rate, raw_total)

        return result

    def _compute_keyword_weights(
        self, scenario_success_rates: dict[str, tuple[float, int]], routes: dict | None = None
    ) -> dict[str, float]:
        """
        Compute keyword weight boosts from scenario success rates.

        Args:
            scenario_success_rates: output from _compute_scenario_success_rate()
            routes: routing map (optional, for keyword extraction)

        Returns:
            {
                "keyword": 1.5,  # 50% boost
                ...
            }
        """
        keyword_boosts = {}

        # For each scenario with high success rate, boost its keywords
        for scenario, (success_rate, count) in scenario_success_rates.items():
            # Boost factor: 1.0 = no change, 2.0 = 100% boost
            # Use sqrt to smooth the boost (success_rate 0.8 → boost 1.35)
            boost = 1.0 + (success_rate ** 0.5) * 0.5

            # If we have routing map, extract keywords; otherwise use scenario name
            if routes and scenario in routes:
                keywords = routes[scenario].get("keywords", [])
                for kw in keywords:
                    kw_lower = kw.lower()
                    keyword_boosts[kw_lower] = keyword_boosts.get(kw_lower, 1.0) * boost
            else:
                # Fallback: use scenario name as keyword
                keyword_boosts[scenario.lower()] = boost

        return keyword_boosts

    def calibrate(self, routes: dict | None = None) -> dict:
        """
        Compute calibrated weights from intervention history.

        Args:
            routes: optional routing map (improves accuracy)

        Returns:
            {
                "calibrated_weights": {...},
                "success_rate_by_scenario": {...},
                "data_freshness": "2026-04-06T10:23:15Z",
                "scenarios_included": 5,
                "total_samples": 127,
                "confidence": 0.87
            }
        """
        if not self.store:
            return {
                "calibrated_weights": {},
                "success_rate_by_scenario": {},
                "data_freshness": None,
                "scenarios_included": 0,
                "total_samples": 0,
                "confidence": 0.0,
            }

        # Compute success rates per scenario
        scenario_success_rates = self._compute_scenario_success_rate()

        # Compute keyword boosts
        keyword_weights = self._compute_keyword_weights(scenario_success_rates, routes)

        # Calculate overall confidence (mean success rate across scenarios)
        if scenario_success_rates:
            mean_success = sum(sr for sr, _ in scenario_success_rates.values()) / len(
                scenario_success_rates
            )
            total_samples = sum(count for _, count in scenario_success_rates.values())
        else:
            mean_success = 0.0
            total_samples = 0

        self._calibrated_weights = keyword_weights
        self._calibration_time = datetime.now().isoformat()

        return {
            "calibrated_weights": keyword_weights,
            "success_rate_by_scenario": {
                s: round(sr, 2) for s, (sr, _) in scenario_success_rates.items()
            },
            "data_freshness": self._calibration_time,
            "scenarios_included": len(scenario_success_rates),
            "total_samples": total_samples,
            "confidence": round(mean_success, 2),
        }

    def dry_run(self, routes: dict | None = None) -> dict:
        """
        Compute calibrated weights WITHOUT persistence.

        Same as calibrate() but doesn't modify state or disk.

        Args:
            routes: optional routing map

        Returns:
            Calibration result dict
        """
        # Compute but don't persist to internal state
        # Save current state, compute, restore
        old_weights = self._calibrated_weights
        old_time = self._calibration_time

        result = self.calibrate(routes)

        # Restore state (undo the calibrate side effects)
        self._calibrated_weights = old_weights
        self._calibration_time = old_time

        return result

    def export_weights(self, filepath: str):
        """
        Export calibrated weights to JSON file.

        Args:
            filepath: path to write JSON
        """
        if not self._calibrated_weights:
            # Run calibration first if needed
            result = self.calibrate()
            weights = result.get("calibrated_weights", {})
        else:
            weights = self._calibrated_weights

        output = {
            "calibrated_at": self._calibration_time or datetime.now().isoformat(),
            "keyword_boosts": weights,
        }

        with open(filepath, "w", encoding="utf-8") as f:  # fs-policy: ok
            json.dump(output, f, indent=2, ensure_ascii=False)

    def load_weights(self, filepath: str) -> dict:
        """
        Load previously calibrated weights from JSON file.

        Args:
            filepath: path to read JSON

        Returns:
            Keyword boosts dict
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._calibrated_weights = data.get("keyword_boosts", {})
            return self._calibrated_weights
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def close(self):
        """Close the underlying intervention store."""
        if self.store:
            self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
