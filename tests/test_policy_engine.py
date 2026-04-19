"""Tests for public policy engine contracts and default provider."""

from __future__ import annotations

from rgen.policy_engine import DefaultPolicyProvider, PolicyInput


def test_default_policy_provider_high_complexity() -> None:
    provider = DefaultPolicyProvider()
    decision = provider.evaluate(
        PolicyInput(
            query="design a multi-step policy and governance architecture for database migration fallback",
            mode="direct",
            scenario="database",
            priority="high",
            confidence=0.82,
            repo_scope="routed-files-only",
        )
    )

    assert decision.complexity == "high"
    assert decision.model_profile == "quality"
    assert decision.cost_tier == "premium"
    assert decision.execution_strategy == "governed-multistep"
    assert decision.governance_mode == "strict"


def test_default_policy_provider_clarification_path() -> None:
    provider = DefaultPolicyProvider()
    decision = provider.evaluate(
        PolicyInput(
            query="not sure whether this is backend or docs",
            mode="direct",
            scenario="_ambiguity_router",
            priority="medium",
            confidence=0.12,
            needs_clarification=True,
            repo_scope="clarify-then-repo-search",
        )
    )

    assert decision.fallback_strategy == "clarify-first"
    assert decision.execution_strategy == "human-in-the-loop"
    assert decision.model_profile == "balanced"
    assert "clarify" in decision.tags


def test_default_policy_provider_subagent_mode() -> None:
    provider = DefaultPolicyProvider()
    decision = provider.evaluate(
        PolicyInput(
            query="search related files for auth bug",
            mode="subagent",
            scenario="auth",
            priority="low",
            confidence=0.61,
            repo_scope="routed-files-then-repo-search",
        )
    )

    assert decision.execution_strategy == "delegated-subagent"
    assert decision.governance_mode == "guarded"
