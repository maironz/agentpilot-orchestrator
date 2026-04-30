#!/usr/bin/env python3
"""
PSM Stack — Recovery Engine (Milestone 2)

Implements the error_class → recovery_action decision matrix.
Provides deterministic, policy-driven recovery decisions for routing failures.

Recovery matrix:
  error_class   | recovery_action | max_retries | notes
  --------------|-----------------|-------------|------
  timeout       | retry           | 2           | transient, safe to retry
  network       | retry           | 2           | transient, safe to retry
  ambiguity     | fallback        | 0           | needs clarification, not retry
  policy        | abort           | 0           | governance violation, do not retry
  unknown       | fallback        | 1           | conservative default

Design decisions:
- Pure policy layer: no I/O, no DB. Inject result into InterventionStore at call site.
- Deterministic: same error_class → same action every time (no randomness).
- Extendable: override matrix via RecoveryEngine(custom_matrix={...}).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ErrorClass = Literal["timeout", "network", "ambiguity", "policy", "unknown"]
RecoveryAction = Literal["retry", "fallback", "abort", "none"]


@dataclass(frozen=True)
class RecoveryPolicy:
    """Immutable recovery policy for a single error class."""

    error_class: str
    action: RecoveryAction
    max_retries: int
    reason: str


@dataclass
class RecoveryDecision:
    """Result of a recovery evaluation."""

    error_class: str
    action: RecoveryAction
    should_retry: bool
    retries_remaining: int
    reason: str
    policy_source: str = "default"

    def as_dict(self) -> dict:
        return {
            "error_class": self.error_class,
            "action": self.action,
            "should_retry": self.should_retry,
            "retries_remaining": self.retries_remaining,
            "reason": self.reason,
            "policy_source": self.policy_source,
        }


# Default recovery matrix
DEFAULT_MATRIX: dict[str, RecoveryPolicy] = {
    "timeout": RecoveryPolicy(
        error_class="timeout",
        action="retry",
        max_retries=2,
        reason="Transient timeout — safe to retry up to 2 times",
    ),
    "network": RecoveryPolicy(
        error_class="network",
        action="retry",
        max_retries=2,
        reason="Transient network error — safe to retry up to 2 times",
    ),
    "ambiguity": RecoveryPolicy(
        error_class="ambiguity",
        action="fallback",
        max_retries=0,
        reason="Routing ambiguity — use fallback scenario, do not retry",
    ),
    "policy": RecoveryPolicy(
        error_class="policy",
        action="abort",
        max_retries=0,
        reason="Governance/policy violation — abort, do not retry",
    ),
    "unknown": RecoveryPolicy(
        error_class="unknown",
        action="fallback",
        max_retries=1,
        reason="Unknown error class — conservative fallback with one retry allowed",
    ),
}


class RecoveryEngine:
    """
    Deterministic recovery decision engine.

    Usage:
        engine = RecoveryEngine()
        decision = engine.evaluate(error_class="timeout", retry_count=0)
        if decision.should_retry:
            # re-route
        elif decision.action == "fallback":
            # use _fallback scenario
        elif decision.action == "abort":
            # surface error to user
    """

    def __init__(self, custom_matrix: dict[str, RecoveryPolicy] | None = None):
        self._matrix: dict[str, RecoveryPolicy] = {**DEFAULT_MATRIX}
        if custom_matrix:
            self._matrix.update(custom_matrix)

    def evaluate(
        self,
        error_class: str,
        retry_count: int = 0,
    ) -> RecoveryDecision:
        """
        Evaluate the recovery action for a given error class and retry count.

        Args:
            error_class: One of: timeout | network | ambiguity | policy | unknown
            retry_count: How many retries have already been attempted.

        Returns:
            RecoveryDecision with action, should_retry, retries_remaining.
        """
        policy = self._matrix.get(error_class) or self._matrix["unknown"]
        retries_remaining = max(0, policy.max_retries - retry_count)
        should_retry = (policy.action == "retry") and (retries_remaining > 0)

        return RecoveryDecision(
            error_class=error_class,
            action=policy.action if not should_retry else "retry",
            should_retry=should_retry,
            retries_remaining=retries_remaining,
            reason=policy.reason,
            policy_source="custom" if custom_matrix_used(self._matrix, error_class) else "default",
        )

    def classify_routing_result(self, routing_result: dict) -> str:
        """
        Infer an error_class from a routing result dict.

        Rules:
        - scenario == "_fallback" AND confidence == 0.0 → "ambiguity"
        - needs_clarification == True → "ambiguity"
        - policy.governance_mode == "strict" AND confidence < 0.55 → "policy"
        - else → "unknown"

        Returns:
            error_class string.
        """
        scenario = routing_result.get("scenario", "")
        confidence = float(routing_result.get("confidence", 0.0) or 0.0)
        needs_clarification = bool(routing_result.get("needs_clarification", False))
        policy = routing_result.get("policy", {}) or {}
        governance = policy.get("governance_mode", "standard")

        if needs_clarification:
            return "ambiguity"
        if scenario == "_fallback" and confidence == 0.0:
            return "ambiguity"
        if governance == "strict" and confidence < 0.55:
            return "policy"
        if scenario == "_fallback":
            return "unknown"
        return "none"  # no error — routing succeeded

    def matrix_summary(self) -> list[dict]:
        """Return the full recovery matrix as a list of dicts (for MCP/CLI output)."""
        return [
            {
                "error_class": p.error_class,
                "action": p.action,
                "max_retries": p.max_retries,
                "reason": p.reason,
            }
            for p in self._matrix.values()
        ]


def custom_matrix_used(matrix: dict, error_class: str) -> bool:
    """Check if a given error_class uses a non-default policy."""
    default = DEFAULT_MATRIX.get(error_class)
    current = matrix.get(error_class)
    if default is None or current is None:
        return True
    return current != default
