"""ROI benchmark helpers for comparing routing strategies."""

from __future__ import annotations

from dataclasses import dataclass

from rgen.cost_estimator import _DEFAULT_PRICING
from rgen.policy_engine import DefaultPolicyProvider, PolicyDecision, PolicyInput


@dataclass(frozen=True)
class BenchmarkRequest:
    query: str
    scenario: str
    priority: str
    confidence: float
    needs_clarification: bool
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    requests: int
    llm_cost_usd: float
    op_cost_usd: float
    total_cost_usd: float


def build_demo_requests() -> list[BenchmarkRequest]:
    """Build 10 representative requests for ROI comparison."""
    return [
        BenchmarkRequest(
            query="optimize database indexes for slow API",
            scenario="database",
            priority="high",
            confidence=0.72,
            needs_clarification=False,
            input_tokens=1200,
            output_tokens=700,
        ),
        BenchmarkRequest(
            query="fix login token expiration issue",
            scenario="auth",
            priority="high",
            confidence=0.64,
            needs_clarification=False,
            input_tokens=1000,
            output_tokens=600,
        ),
        BenchmarkRequest(
            query="write docker deployment checklist",
            scenario="docker_infra",
            priority="medium",
            confidence=0.61,
            needs_clarification=False,
            input_tokens=700,
            output_tokens=500,
        ),
        BenchmarkRequest(
            query="add tests for router fallback paths",
            scenario="testing",
            priority="medium",
            confidence=0.58,
            needs_clarification=False,
            input_tokens=850,
            output_tokens=550,
        ),
        BenchmarkRequest(
            query="debug ambiguous routing between performance and database",
            scenario="_ambiguity_router",
            priority="medium",
            confidence=0.23,
            needs_clarification=True,
            input_tokens=900,
            output_tokens=650,
        ),
        BenchmarkRequest(
            query="create mcp contract changelog entry",
            scenario="documentazione",
            priority="low",
            confidence=0.74,
            needs_clarification=False,
            input_tokens=600,
            output_tokens=450,
        ),
        BenchmarkRequest(
            query="investigate production incident and fallback strategy",
            scenario="performance",
            priority="high",
            confidence=0.42,
            needs_clarification=True,
            input_tokens=1300,
            output_tokens=800,
        ),
        BenchmarkRequest(
            query="refactor policy boundary interfaces",
            scenario="python_code",
            priority="medium",
            confidence=0.68,
            needs_clarification=False,
            input_tokens=950,
            output_tokens=700,
        ),
        BenchmarkRequest(
            query="generate release notes summary",
            scenario="documentazione",
            priority="low",
            confidence=0.79,
            needs_clarification=False,
            input_tokens=500,
            output_tokens=400,
        ),
        BenchmarkRequest(
            query="plan multi-tenant governance controls",
            scenario="orchestratore",
            priority="high",
            confidence=0.55,
            needs_clarification=False,
            input_tokens=1100,
            output_tokens=750,
        ),
    ]


def _token_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = _DEFAULT_PRICING[model]
    return (input_tokens / 1000 * pricing["input_per_1k"]) + (
        output_tokens / 1000 * pricing["output_per_1k"]
    )


def _free_model_from_decision(decision: PolicyDecision) -> str:
    if decision.model_profile == "quality":
        return "gpt-4o"
    return "gpt-4o-mini"


def _premium_model_from_request(req: BenchmarkRequest) -> str:
    if req.priority == "high" or req.confidence < 0.45:
        return "gpt-4o"
    return "gpt-4o-mini"


def _op_cost_no_routing(req: BenchmarkRequest) -> float:
    base = 0.22
    if req.needs_clarification:
        base += 0.28
    if req.priority == "high":
        base += 0.12
    return base


def _op_cost_free(decision: PolicyDecision) -> float:
    base = 0.10
    if decision.fallback_strategy == "clarify-first":
        base += 0.15
    elif decision.fallback_strategy == "repo-search":
        base += 0.08

    if decision.execution_strategy == "governed-multistep":
        base += 0.03
    return base


def _op_cost_premium(req: BenchmarkRequest) -> float:
    # Premium keeps a smaller manual overhead thanks to richer policy/fallback controls.
    base = 0.05
    if req.needs_clarification:
        base += 0.05
    if req.priority == "high":
        base += 0.02
    return base


def compare_roi_strategies(requests: list[BenchmarkRequest] | None = None) -> dict[str, StrategyResult]:
    """Compare 3 strategies on the same 10-request batch.

    Strategies:
    - no_routing: naive baseline, always premium model and higher manual overhead
    - free_routing: open-core policy engine
    - paid_routing: premium-style policy selection with lower ops overhead
    """
    reqs = requests or build_demo_requests()
    free_provider = DefaultPolicyProvider()

    no_routing_llm = 0.0
    no_routing_ops = 0.0
    free_llm = 0.0
    free_ops = 0.0
    paid_llm = 0.0
    paid_ops = 0.0

    for req in reqs:
        no_routing_llm += _token_cost_usd("gpt-4o", req.input_tokens, req.output_tokens)
        no_routing_ops += _op_cost_no_routing(req)

        decision = free_provider.evaluate(
            PolicyInput(
                query=req.query,
                mode="direct",
                scenario=req.scenario,
                priority=req.priority,
                confidence=req.confidence,
                needs_clarification=req.needs_clarification,
            )
        )
        free_model = _free_model_from_decision(decision)
        free_llm += _token_cost_usd(free_model, req.input_tokens, req.output_tokens)
        free_ops += _op_cost_free(decision)

        paid_model = _premium_model_from_request(req)
        paid_llm += _token_cost_usd(paid_model, req.input_tokens, req.output_tokens)
        paid_ops += _op_cost_premium(req)

    def _mk(name: str, llm: float, ops: float) -> StrategyResult:
        total = llm + ops
        return StrategyResult(
            strategy=name,
            requests=len(reqs),
            llm_cost_usd=round(llm, 4),
            op_cost_usd=round(ops, 4),
            total_cost_usd=round(total, 4),
        )

    return {
        "no_routing": _mk("no_routing", no_routing_llm, no_routing_ops),
        "free_routing": _mk("free_routing", free_llm, free_ops),
        "paid_routing": _mk("paid_routing", paid_llm, paid_ops),
    }
