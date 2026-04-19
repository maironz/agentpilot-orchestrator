"""Public policy engine contracts and open-core fallback implementation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, Sequence


@dataclass(slots=True)
class PolicyInput:
    """Normalized input for policy evaluation."""

    query: str
    mode: str
    scenario: str
    priority: str
    confidence: float
    needs_clarification: bool = False
    repo_scope: str = "routed-files-only"
    routing_debug: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class PolicyDecision:
    """Serializable policy evaluation result."""

    policy_name: str
    policy_version: str
    complexity: str
    model_profile: str
    cost_tier: str
    fallback_strategy: str
    execution_strategy: str
    governance_mode: str
    rationale: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class PolicyProvider(Protocol):
    """Public contract for policy evaluation providers."""

    def evaluate(self, policy_input: PolicyInput) -> PolicyDecision:
        """Evaluate routing context and return a policy decision."""
        ...


class ModelProvider(Protocol):
    """Public contract for mapping policy decisions to models/providers."""

    def choose_model(
        self,
        decision: PolicyDecision,
        available_models: Sequence[str] | None = None,
    ) -> str | None:
        """Return the selected model identifier for a policy decision."""
        ...


class ExecutionStrategy(Protocol):
    """Public contract for execution plans derived from policy decisions."""

    def plan(self, decision: PolicyDecision) -> dict[str, Any]:
        """Return execution metadata for the selected policy decision."""
        ...


class DefaultPolicyProvider:
    """Deterministic open-core policy engine.

    The public implementation stays intentionally conservative:
    it classifies complexity and fallback posture without embedding
    proprietary scoring or provider-specific monetization rules.
    """

    _HIGH_SIGNAL_TERMS = {
        "architecture",
        "auth",
        "cluster",
        "compliance",
        "database",
        "fallback",
        "governance",
        "graph",
        "incident",
        "migration",
        "multi-step",
        "orchestrazione",
        "performance",
        "policy",
        "security",
        "tenant",
    }

    def evaluate(self, policy_input: PolicyInput) -> PolicyDecision:
        complexity, complexity_notes = self._classify_complexity(policy_input)
        fallback_strategy = self._fallback_strategy(policy_input, complexity)
        execution_strategy = self._execution_strategy(policy_input, complexity)
        model_profile = self._model_profile(policy_input, complexity)
        cost_tier = self._cost_tier(complexity, model_profile)
        governance_mode = self._governance_mode(policy_input, complexity)

        rationale = complexity_notes + [
            f"fallback={fallback_strategy}",
            f"execution={execution_strategy}",
            f"repo_scope={policy_input.repo_scope}",
        ]

        tags = [
            f"mode:{policy_input.mode}",
            f"scenario:{policy_input.scenario}",
            f"complexity:{complexity}",
            f"governance:{governance_mode}",
        ]
        if policy_input.needs_clarification:
            tags.append("clarify")
        if policy_input.confidence < 0.45:
            tags.append("low-confidence")

        return PolicyDecision(
            policy_name="open-core-default",
            policy_version="1",
            complexity=complexity,
            model_profile=model_profile,
            cost_tier=cost_tier,
            fallback_strategy=fallback_strategy,
            execution_strategy=execution_strategy,
            governance_mode=governance_mode,
            rationale=rationale,
            tags=tags,
        )

    def _classify_complexity(self, policy_input: PolicyInput) -> tuple[str, list[str]]:
        score = 0
        rationale: list[str] = []

        priority = (policy_input.priority or "").lower()
        if priority == "high":
            score += 2
            rationale.append("priority=high")
        elif priority == "medium":
            score += 1
            rationale.append("priority=medium")

        token_count = len((policy_input.query or "").split())
        if token_count >= 20:
            score += 1
            rationale.append("query=long")

        lowered = (policy_input.query or "").lower()
        matched_terms = sum(1 for term in self._HIGH_SIGNAL_TERMS if term in lowered)
        if matched_terms >= 3:
            score += 2
            rationale.append("query=multiple-high-signal")
        elif matched_terms >= 1:
            score += 1
            rationale.append("query=high-signal")

        if policy_input.needs_clarification:
            score += 1
            rationale.append("needs_clarification")

        if policy_input.confidence < 0.3:
            score += 1
            rationale.append("confidence=very-low")

        if score >= 4:
            return "high", rationale
        if score >= 2:
            return "medium", rationale
        return "low", rationale or ["priority=low"]

    def _fallback_strategy(self, policy_input: PolicyInput, complexity: str) -> str:
        if policy_input.needs_clarification:
            return "clarify-first"
        if policy_input.confidence < 0.45:
            return "repo-search"
        if complexity == "high" and policy_input.mode != "follow-up":
            return "graph-cascade-ready"
        return "single-agent"

    def _execution_strategy(self, policy_input: PolicyInput, complexity: str) -> str:
        if policy_input.needs_clarification:
            return "human-in-the-loop"
        if policy_input.mode == "subagent":
            return "delegated-subagent"
        if complexity == "high":
            return "governed-multistep"
        if policy_input.repo_scope != "routed-files-only":
            return "assisted-repo-exploration"
        return "standard-routing"

    def _model_profile(self, policy_input: PolicyInput, complexity: str) -> str:
        if policy_input.needs_clarification or policy_input.confidence < 0.45:
            return "balanced"
        if complexity == "high":
            return "quality"
        if complexity == "medium":
            return "balanced"
        return "economy"

    def _cost_tier(self, complexity: str, model_profile: str) -> str:
        if complexity == "high" or model_profile == "quality":
            return "premium"
        if complexity == "medium":
            return "balanced"
        return "low"

    def _governance_mode(self, policy_input: PolicyInput, complexity: str) -> str:
        if policy_input.needs_clarification or complexity == "high":
            return "strict"
        if policy_input.mode == "subagent" or policy_input.confidence < 0.55:
            return "guarded"
        return "standard"