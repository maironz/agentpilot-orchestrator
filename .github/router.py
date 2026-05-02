#!/usr/bin/env python3
"""
PSM Stack Dynamic Router — with Planner Integration + Subagent Optimization

Modes:
  python .github/router.py "query"              → Planner workflow (first request)
  python .github/router.py --direct "query"     → Direct keyword routing (no planner)
  python .github/router.py --follow-up "query"  → Minimal context for same-session follow-ups
  python .github/router.py --subagent "query"   → Compact brief for runSubagent prompts
  python .github/router.py --audit              → Scan codebase for routing map gaps
  python .github/router.py --stats              → Health metrics
  python .github/router.py PLAN_APPROVED        → Execute approved plan
  python .github/router.py PLAN_REJECTED: reason → Replan

Note: copilot-instructions.md is auto-loaded by VS Code into the system prompt.
      It is NOT included in router output to avoid redundant reads.
"""

import json
import sys
import re
import time
from pathlib import Path

# Modular imports (split from monolithic router.py)
from router_audit import audit_routing_coverage, get_health_stats
from router_planner import handle_plan_approved, handle_plan_rejected, handle_new_query
from interventions import InterventionStore
try:
    from recovery_engine import RecoveryEngine as _RecoveryEngine
    _recovery_engine = _RecoveryEngine()
except ImportError:  # graceful: recovery_engine not available in generated targets
    _recovery_engine = None  # type: ignore[assignment]

# Premium runtime boundary (prefer private implementations when installed)
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from rgen.policy_engine import DefaultPolicyProvider, PolicyInput
    from rgen.premium_policy_loader import load_policy_provider
    from rgen.premium_runtime_loader import (
        load_dashboard_ui,
        load_graph_router,
        load_metrics_collector,
        load_weight_calibrator,
    )

    RouterWeightCalibrator = load_weight_calibrator()
    GraphRouter = load_graph_router()
    RouterMetricsCollector = load_metrics_collector()
    DashboardUI = load_dashboard_ui()
    POLICY_PROVIDER = load_policy_provider()
except ImportError:
    RouterWeightCalibrator = None
    GraphRouter = None
    RouterMetricsCollector = None
    DashboardUI = None
    DefaultPolicyProvider = None
    PolicyInput = None
    POLICY_PROVIDER = None

ROUTING_MAP = Path(__file__).parent / "routing-map.json"
ROUTING_MAP_LOCAL = Path(__file__).parent / "routing-map.local.json"
SUBAGENT_BRIEF = Path(__file__).parent / "subagent-brief.md"
CONFIDENCE_GATE = 0.55
PLANS_LOCAL_DIR = Path(__file__).parent / "plans-local"
PLANS_SHARED_DIR = Path(__file__).parent / "plans"

# Agent → expert file mapping (single source of truth)
AGENT_EXPERT_MAP = {
    "fullstack":      ".github/esperti/esperto_fullstack.md",
    "sistemista":     ".github/esperti/esperto_sistemista.md",
    "documentazione": ".github/esperti/esperto_documentazione.md",
    "orchestratore":  ".github/esperti/esperto_orchestratore.md",
}

# Critical constraints that subagents must always respect
SUBAGENT_CONSTRAINTS = [
    "Non toccare WInApp/ (progetto Visual Studio separato)",
    "Let's Encrypt: NON abilitare mTLS su router pubblici, porta 80 aperta per ACME",
    "Sync VM↔NAS disabilitato — VM è source of truth",
    "Samba/CIFS first: modificare file da Windows (Z:\\), SSH solo per runtime",
    "Backup prima di modifiche production",
]

REPO_EXPLORATION_TRIGGERS = [
    "nessun scenario matchato",
    "routing ambiguo",
    "confidence sotto soglia",
    "file instradati insufficienti o incoerenti con il repo reale",
]


def _load_routes() -> dict:
    """Load routing map in flat or sectioned format, skipping metadata entries."""
    with open(ROUTING_MAP, "r", encoding="utf-8") as f:
        payload = json.load(f)

    routes = {k: v for k, v in payload.items() if isinstance(v, dict) and "keywords" in v}

    # Optional grouped format:
    # {
    #   "_sections": {
    #       "backend": {
    #           "database": {"keywords": [...], ...}
    #       }
    #   }
    # }
    sections = payload.get("_sections") if isinstance(payload, dict) else None
    if isinstance(sections, dict):
        for _, section_items in sections.items():
            if not isinstance(section_items, dict):
                continue
            for scenario_id, scenario_data in section_items.items():
                if isinstance(scenario_data, dict) and "keywords" in scenario_data:
                    routes[scenario_id] = scenario_data

    if ROUTING_MAP_LOCAL.exists():
        with open(ROUTING_MAP_LOCAL, "r", encoding="utf-8") as f:
            local_payload = json.load(f)

        local_routes = {k: v for k, v in local_payload.items() if isinstance(v, dict) and "keywords" in v}
        local_sections = local_payload.get("_sections") if isinstance(local_payload, dict) else None
        if isinstance(local_sections, dict):
            for _, section_items in local_sections.items():
                if not isinstance(section_items, dict):
                    continue
                for scenario_id, scenario_data in section_items.items():
                    if isinstance(scenario_data, dict) and "keywords" in scenario_data:
                        local_routes[scenario_id] = scenario_data
        routes.update(local_routes)

    return routes


def extract_capability(content: str, capability: str) -> str:
    """
    Extract a capability block from an expert file.
    Blocks are delimited by <!-- CAPABILITY:NAME --> ... <!-- END CAPABILITY -->
    Returns the block content stripped, or empty string if not found.
    """
    if not capability:
        return ""
    pattern = rf"<!-- CAPABILITY:{re.escape(capability)} -->(.*?)<!-- END CAPABILITY -->"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _resolve_capability(scenario_data: dict, agent: str) -> tuple[str | None, str]:
    """
    Resolve capability for a scenario.
    Returns (capability_name, capability_instructions) tuple.
    capability_name is None if not defined in scenario.
    capability_instructions is empty string if block not found in expert file.
    """
    capability = scenario_data.get("capability")
    if not capability:
        return None, ""

    expert_file = AGENT_EXPERT_MAP.get(agent)
    if not expert_file:
        return capability, ""

    # Resolve expert file path relative to this script's directory
    expert_path = Path(__file__).parent.parent / expert_file
    if not expert_path.exists():
        # Try relative to workspace root
        expert_path = Path(expert_file)
    if not expert_path.exists():
        import warnings
        warnings.warn(f"Expert file not found for capability {capability}: {expert_file}", stacklevel=2)
        return capability, ""

    try:
        content = expert_path.read_text(encoding="utf-8")
    except Exception:
        return capability, ""

    instructions = extract_capability(content, capability)
    if not instructions:
        # Silent warning: capability declared but block not found in expert file
        import sys
        print(f"[WARN] Capability {capability} declared but no block found in {expert_file}", file=sys.stderr)

    return capability, instructions


def _enrich_with_prior(result: dict, query: str, max_results: int = 3) -> dict:
    """Enrich routing result with prior interventions from memory."""
    try:
        store = InterventionStore()
        prior = store.search(query, limit=max_results)
        store.close()
        if prior:
            result["prior_interventions"] = [
                {
                    "ts": p["ts"],
                    "scenario": p["scenario"],
                    "resolution": p["resolution"][:200],
                    "outcome": p["outcome"],
                }
                for p in prior
            ]
    except Exception:
        pass  # Memory is optional — never block routing
    return result


def _score_scenarios(query: str, routes: dict, weighted_boosts: dict | None = None) -> list[dict]:
    """
    Score scenarios with optional weight calibration.

    Args:
        query: user query string
        routes: routing map
        weighted_boosts: optional calibrated keyword boosts {keyword: boost_factor, ...}

    Returns:
        List of scored scenarios sorted by score/ratio
    """
    q = (query or "").lower()
    scored = []
    for key, data in routes.items():
        keywords = data.get("keywords", [])
        matched = [kw for kw in keywords if kw.lower() in q]
        score = len(matched)

        # Apply calibrated weight boost if available
        if score > 0 and weighted_boosts:
            boost_factor = weighted_boosts.get(key.lower(), 1.0)
            score *= boost_factor

        if score > 0:
            ratio = round(score / max(len(keywords), 1), 3)
            scored.append({
                "score": score,
                "ratio": ratio,
                "scenario": key,
                "data": data,
                "matched_keywords": matched,
            })
    scored.sort(reverse=True, key=lambda x: (x["score"], x["ratio"]))
    return scored


def _compute_confidence(scored: list[dict]) -> float:
    """Compute confidence in [0, 1] from top candidates and score margin."""
    if not scored:
        return 0.0

    best = scored[0]
    second = scored[1] if len(scored) > 1 else None
    best_score = best["score"]
    second_score = second["score"] if second else 0

    # Balance score margin and coverage ratio to avoid overconfident ties.
    margin_component = (best_score - second_score) / max(best_score, 1)
    ratio_component = best["ratio"]

    confidence = (0.65 * margin_component) + (0.35 * ratio_component)
    return round(max(0.0, min(confidence, 1.0)), 3)


def _is_ambiguous(scored: list[dict], confidence: float) -> bool:
    """Detect routing ambiguity when top scenarios are too close."""
    if len(scored) < 2:
        return False

    best = scored[0]
    second = scored[1]
    close_scores = (best["score"] - second["score"]) <= 1
    close_ratio = abs(best["ratio"] - second["ratio"]) <= 0.08

    return confidence < 0.45 or (close_scores and close_ratio)


def _build_routing_debug(scored: list[dict], max_candidates: int = 3) -> list[dict]:
    """Return compact routing traces to explain why a scenario won."""
    out = []
    for c in scored[:max_candidates]:
        out.append({
            "scenario": c["scenario"],
            "score": c["score"],
            "ratio": c["ratio"],
            "matched_keywords": c["matched_keywords"][:8],
            "agent": c["data"].get("agent", "orchestratore"),
        })
    return out


def _build_clarification_payload(scored: list[dict], mode: str) -> dict:
    """Create an orchestrator handoff payload with deterministic clarifying questions."""
    cands = _build_routing_debug(scored, max_candidates=2)
    option_lines = [
        {
            "label": f"{c['scenario']} ({c['agent']})",
            "description": f"match:{c['score']} ratio:{c['ratio']} kw:{', '.join(c['matched_keywords'][:3])}",
        }
        for c in cands
    ]

    return {
        "agent": "orchestratore",
        "files": [AGENT_EXPERT_MAP["orchestratore"]],
        "context": "Ambiguità routing: scenario multipli con score simile",
        "priority": "medium",
        "scenario": "_ambiguity_router",
        "mode": mode,
        "needs_clarification": True,
        "clarification": {
            "reason": "Top scenario troppo vicini per routing affidabile automatico",
            "questions": [
                {
                    "header": "dominio",
                    "question": "Quale dominio vuoi privilegiare per questa richiesta?",
                    "options": option_lines,
                }
            ],
            "candidates": cands,
        },
        "repo_exploration": _build_repo_exploration_policy(
            mode=mode,
            confidence=0.0,
            ambiguous=True,
        ),
    }


def _build_repo_exploration_policy(
    mode: str,
    confidence: float,
    *,
    fallback: bool = False,
    ambiguous: bool = False,
) -> dict:
    """Describe when the agent may widen search from routed files to the full repo."""
    if fallback:
        return {
            "allowed": True,
            "recommended_scope": "repo-fallback",
            "reason": "Nessuno scenario ha matchato la query: e' consentita esplorazione repo per autocorrezione.",
            "confidence_gate": CONFIDENCE_GATE,
            "triggers": REPO_EXPLORATION_TRIGGERS,
        }

    if ambiguous:
        return {
            "allowed": True,
            "recommended_scope": "clarify-then-repo-search",
            "reason": "Routing ambiguo: chiarisci il dominio o amplia la ricerca se i file instradati non bastano.",
            "confidence_gate": CONFIDENCE_GATE,
            "triggers": REPO_EXPLORATION_TRIGGERS,
        }

    if confidence < CONFIDENCE_GATE:
        return {
            "allowed": True,
            "recommended_scope": "routed-files-then-repo-search",
            "reason": "Confidence sotto soglia: parti dai file instradati e allarga al repo solo se emergono contraddizioni o buchi.",
            "confidence_gate": CONFIDENCE_GATE,
            "triggers": REPO_EXPLORATION_TRIGGERS,
        }

    return {
        "allowed": False,
        "recommended_scope": "routed-files-only",
        "reason": "Confidence sufficiente: usa prima i file instradati e amplia solo se il contesto reale li smentisce.",
        "confidence_gate": CONFIDENCE_GATE,
        "triggers": REPO_EXPLORATION_TRIGGERS,
    }


def _estimate_complexity(
    query: str,
    priority: str,
    repo_exploration: dict,
    routing_debug: list[dict] | None = None,
) -> dict:
    """Return a lightweight complexity hint to guide plan depth and parallelism.

    This is a fast pre-execution heuristic, not a runtime profiler.
    """
    q = (query or "").lower()
    dbg = routing_debug or []
    reasons: list[str] = []
    score = 0

    if priority == "high":
        score += 2
        reasons.append("scenario ad alta priorita")
    elif priority == "medium":
        score += 1

    if repo_exploration.get("allowed"):
        score += 1
        reasons.append("possibile esplorazione oltre i file instradati")

    if len(dbg) > 1:
        score += 1
        reasons.append("routing con candidati multipli")

    long_markers = (
        "refactor",
        "migraz",
        "migration",
        "architett",
        "architecture",
        "multi",
        "end-to-end",
        "e2e",
        "performance",
        "benchmark",
    )
    if any(m in q for m in long_markers):
        score += 2
        reasons.append("query con indicatori di lavoro esteso")

    if len(q.split()) >= 30:
        score += 1
        reasons.append("richiesta lunga")

    if score >= 5:
        level = "long"
    elif score >= 3:
        level = "medium"
    else:
        level = "short"

    return {
        "level": level,
        "requires_plan": level != "short",
        "suggest_parallel_subagents": level == "long",
        "analysis_mode": "initial_heuristic",
        "reasons": reasons or ["segnali di complessita limitati"],
    }


def _apply_policy(result: dict, query: str) -> dict:
    """Attach public policy metadata to routing results."""
    if not isinstance(result, dict):
        return result

    # OSS fallback: ensure policy contract is always present even without optional modules.
    if PolicyInput is None or DefaultPolicyProvider is None:
        confidence = float(result.get("confidence", 0.0) or 0.0)
        scenario = str(result.get("scenario", "_fallback"))
        result["policy"] = {
            "fallback_strategy": "repo-search" if scenario == "_fallback" else "routed-files",
            "governance_mode": "strict" if confidence >= 0.85 else ("guarded" if confidence >= CONFIDENCE_GATE else "standard"),
            "source": "oss-fallback",
        }
        return result

    provider = POLICY_PROVIDER or DefaultPolicyProvider()
    policy_input = PolicyInput(
        query=query,
        mode=str(result.get("mode", "direct")),
        scenario=str(result.get("scenario", "_fallback")),
        priority=str(result.get("priority", "low")),
        confidence=float(result.get("confidence", 0.0) or 0.0),
        needs_clarification=bool(result.get("needs_clarification", False)),
        repo_scope=str(result.get("repo_exploration", {}).get("recommended_scope", "routed-files-only")),
        routing_debug=list(result.get("routing_debug", [])),
    )

    try:
        decision = provider.evaluate(policy_input)
    except Exception:
        decision = DefaultPolicyProvider().evaluate(policy_input)

    result["policy"] = decision.as_dict() if hasattr(decision, "as_dict") else decision
    return result


def route_query(query: str, use_calibration: bool = False) -> dict:
    """
    Direct keyword routing (no planner). Returns full context for first request.

    Args:
        query: user query
        use_calibration: if True, apply calibrated weights from intervention history

    Returns:
        Routing result dict
    """
    _t0 = time.perf_counter()
    routes = _load_routes()

    # Load calibrated weights if requested and available
    weighted_boosts = None
    if use_calibration and RouterWeightCalibrator:
        try:
            store = InterventionStore()
            calibrator = RouterWeightCalibrator(store)
            calibration = calibrator.calibrate(routes)
            weighted_boosts = calibration.get("calibrated_weights", {})
            store.close()
        except Exception:
            pass  # Calibration is optional — never block routing

    scored = _score_scenarios(query, routes, weighted_boosts)

    if not scored:
        _recovery = _recovery_engine.evaluate("ambiguity", retry_count=0) if _recovery_engine else None
        fallback_result = {
            "agent": "orchestratore",
            "files": [AGENT_EXPERT_MAP["orchestratore"]],
            "context": "Fallback generico — nessuno scenario matchato",
            "priority": "low",
            "scenario": "_fallback",
            "mode": "direct",
            "confidence": 0.0,
            "routing_latency_ms": round((time.perf_counter() - _t0) * 1000, 2),
            "recovery": _recovery.as_dict() if _recovery else None,
            "repo_exploration": _build_repo_exploration_policy(
                mode="direct",
                confidence=0.0,
                fallback=True,
            ),
        }
        fallback_result["complexity"] = _estimate_complexity(
            query,
            fallback_result.get("priority", "low"),
            fallback_result.get("repo_exploration", {}),
            [],
        )
        return _apply_policy(fallback_result, query)

    top = scored[0]
    score = top["score"]
    scenario_key = top["scenario"]
    best = top["data"]
    agent = best.get("agent")
    confidence = _compute_confidence(scored)
    routing_debug = _build_routing_debug(scored)

    if _is_ambiguous(scored, confidence):
        amb = _build_clarification_payload(scored, mode="direct")
        amb["confidence"] = confidence
        amb["routing_debug"] = routing_debug
        amb["repo_exploration"] = _build_repo_exploration_policy(
            mode="direct",
            confidence=confidence,
            ambiguous=True,
        )
        amb = _enrich_with_prior(amb, query)
        return _apply_policy(amb, query)

    result = {
        "agent": agent,
        "files": best.get("files", []),
        "context": best.get("context", ""),
        "priority": best.get("priority", "medium"),
        "scenario": scenario_key,
        "score": score,
        "confidence": confidence,
        "routing_latency_ms": round((time.perf_counter() - _t0) * 1000, 2),
        "routing_debug": routing_debug,
        "mode": "direct",
        "repo_exploration": _build_repo_exploration_policy(
            mode="direct",
            confidence=confidence,
        ),
    }
    result["complexity"] = _estimate_complexity(
        query,
        result.get("priority", "medium"),
        result.get("repo_exploration", {}),
        routing_debug,
    )

    # Capability layer: extract if defined
    cap_name, cap_instructions = _resolve_capability(best, agent)
    if cap_name:
        result["capability"] = cap_name
    if cap_instructions:
        result["capability_instructions"] = cap_instructions

    # Intervention memory: enrich with prior similar interventions
    result = _enrich_with_prior(result, query)

    return _apply_policy(result, query)


def route_follow_up(query: str) -> dict:
    """
    Follow-up mode: for subsequent requests in the same session.
    Returns ONLY the agent-specific expert file — base context is already loaded.
    Skips supplementary files (checklists, vision, subdetails) that were loaded on first call.
    """
    routes = _load_routes()
    scored = _score_scenarios(query, routes)

    if not scored:
        fallback_result = {
            "agent": "orchestratore",
            "files": [AGENT_EXPERT_MAP["orchestratore"]],
            "context": "Follow-up fallback",
            "priority": "low",
            "mode": "follow-up",
            "confidence": 0.0,
            "repo_exploration": _build_repo_exploration_policy(
                mode="follow-up",
                confidence=0.0,
                fallback=True,
            ),
        }
        fallback_result["complexity"] = _estimate_complexity(
            query,
            fallback_result.get("priority", "low"),
            fallback_result.get("repo_exploration", {}),
            [],
        )
        return _apply_policy(fallback_result, query)

    top = scored[0]
    scenario_key = top["scenario"]
    best = top["data"]
    agent = best.get("agent", "orchestratore")
    confidence = _compute_confidence(scored)
    routing_debug = _build_routing_debug(scored)

    if _is_ambiguous(scored, confidence):
        amb = _build_clarification_payload(scored, mode="follow-up")
        amb["confidence"] = confidence
        amb["routing_debug"] = routing_debug
        amb["repo_exploration"] = _build_repo_exploration_policy(
            mode="follow-up",
            confidence=confidence,
            ambiguous=True,
        )
        amb = _enrich_with_prior(amb, query)
        return _apply_policy(amb, query)

    # In follow-up mode: load ONLY the agent expert file
    # Supplementary files were already loaded in the initial request
    expert_file = AGENT_EXPERT_MAP.get(agent)
    files = [expert_file] if expert_file else []

    result = {
        "agent": agent,
        "files": files,
        "context": best.get("context", ""),
        "priority": best.get("priority", "medium"),
        "scenario": scenario_key,
        "confidence": confidence,
        "routing_debug": routing_debug,
        "mode": "follow-up",
        "note": "Solo file agente — contesto base già in sessione",
        "repo_exploration": _build_repo_exploration_policy(
            mode="follow-up",
            confidence=confidence,
        ),
    }
    result["complexity"] = _estimate_complexity(
        query,
        result.get("priority", "medium"),
        result.get("repo_exploration", {}),
        routing_debug,
    )

    # Capability layer: maintain from scenario if same session
    cap_name, cap_instructions = _resolve_capability(best, agent)
    if cap_name:
        result["capability"] = cap_name
    if cap_instructions:
        result["capability_instructions"] = cap_instructions

    # Intervention memory: enrich with prior similar interventions
    result = _enrich_with_prior(result, query)

    return _apply_policy(result, query)


def route_subagent(query: str) -> dict:
    """
    Subagent mode: returns a compact context blob for runSubagent prompts.
    Includes:
    - subagent_brief: path to the ultra-compact project context file
    - subagent_prompt_prefix: pre-built text to prepend to subagent prompts
    - constraints: critical rules the subagent must respect
    - files: minimal file set (just the expert file, no base)
    """
    routes = _load_routes()
    scored = _score_scenarios(query, routes)

    if not scored:
        agent = "orchestratore"
        context = "Generic subagent task"
        scenario_key = "_fallback"
        confidence = 0.0
    else:
        top = scored[0]
        scenario_key = top["scenario"]
        best = top["data"]
        agent = best.get("agent", "orchestratore")
        context = best.get("context", "")
        confidence = _compute_confidence(scored)

    expert_file = AGENT_EXPERT_MAP.get(agent)

    # Build the prompt prefix that the main agent should prepend to subagent prompts
    brief_path = str(SUBAGENT_BRIEF)
    prompt_prefix = _build_subagent_prompt_prefix(agent, context)

    result = {
        "agent": agent,
        "files": [expert_file] if expert_file else [],
        "context": context,
        "scenario": scenario_key,
        "mode": "subagent",
        "subagent_brief": ".github/subagent-brief.md",
        "subagent_prompt_prefix": prompt_prefix,
        "constraints": SUBAGENT_CONSTRAINTS,
        "confidence": confidence,
        "repo_exploration": _build_repo_exploration_policy(
            mode="subagent",
            confidence=confidence,
            fallback=not scored,
        ),
        "usage": (
            "Include subagent_prompt_prefix at the start of your runSubagent prompt. "
            "Read subagent-brief.md ONLY if the subagent needs project structure knowledge. "
            "For pure code searches or simple edits, the prompt_prefix alone is sufficient."
        )
    }
    result["complexity"] = _estimate_complexity(
        query,
        result.get("priority", "low"),
        result.get("repo_exploration", {}),
        _build_routing_debug(scored) if scored else [],
    )

    return _apply_policy(result, query)


def _build_subagent_prompt_prefix(agent: str, context: str) -> str:
    """Build a minimal context prefix for subagent prompts."""
    return (
        f"[Progetto PSM Stack — {context}]\n"
        f"Ruolo: {agent} | VM: <SERVER_IP> | App: <APP_SHARE> (Samba) | Docs: <BACKUP_PATH>\\proxmoxConfig\n"
        f"Stack: Docker (Traefik + Apache/Joomla + MariaDB) su Ubuntu/Proxmox\n"
        f"Vincoli: Non toccare WInApp/. Let's Encrypt attivo (no mTLS pubblico). VM è source of truth.\n"
    )



# ─── CLI ───

def main():
    # Force UTF-8 output (avoid cp1252 encoding issues on Windows)
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # type: ignore

    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print("""
╔════════════════════════════════════════════════════════════════╗
║       PSM Stack Router + Planner + Subagent Optimization      ║
╚════════════════════════════════════════════════════════════════╝

MODES:
  python .github/router.py "query"              → Planner workflow
  python .github/router.py --direct "query"     → Direct routing (skip planner)
  python .github/router.py --follow-up "query"  → Minimal context (same session)
  python .github/router.py --subagent "query"   → Compact brief for subagents
  python .github/router.py --graph-mode "query" → Graph cascade routing (multi-agent)

HEALTH & MONITORING:
  python .github/router.py --stats              → Health metrics (session start)
  python .github/router.py --audit              → Scan codebase for routing gaps
  python .github/router.py --dashboard          → Live metrics dashboard (TUI)
  python .github/router.py --calibrate-weights  → Show calibrated keyword boosts
  python .github/router.py --calibrate-weights --dry-run → Preview without save

MEMORY:
  python .github/router.py --history "query"    → Search intervention memory (FTS5)
  python .github/router.py --history            → Intervention stats
  python .github/router.py --log-intervention   → Log new intervention

PLANNER:
  python .github/router.py PLAN_APPROVED
  python .github/router.py "PLAN_REJECTED: motivo"

PLANS (local-first):
    .github/plans-local/   → personal plans (gitignored)
    .github/plans/         → shared/public plans

EXAMPLES:
  python .github/router.py --direct "fix login API"
  python .github/router.py --follow-up "aggiungi validazione input"
  python .github/router.py --subagent "cerca tutti i file PHP con query SQL"
  python .github/router.py --dashboard
        """)
        sys.exit(0)

    # Parse mode flag
    mode = None
    if args[0] in ("--direct", "--follow-up", "--subagent", "--audit", "--stats", "--history", "--log-intervention", "--dashboard", "--calibrate-weights", "--graph-mode"):
        mode = args[0].lstrip("-").replace("-", "_")
        query = " ".join(args[1:]).strip() if len(args) > 1 else ""
    else:
        query = " ".join(args).strip()

    # Handle stats mode (no query needed)
    if mode == "stats":
        stats = get_health_stats()
        # Compact one-liner for session header
        icons = {"ok": "[OK]", "warn": "[!!]", "crit": "[XX]"}
        m = stats["metrics"]
        line = (
            f"Routing: {m['scenarios']['value']}scn/{m['keywords']['value']}kw "
            f"| overlap:{m['overlap_pct']['value']}% "
            f"| router:{m['router_lines']['value']}L "
            f"| map:{m['routing_map_kb']['value']}KB "
            f"| {icons[stats['overall']]} {stats['overall'].upper()}"
        )
        print(line)
        # Warnings detail
        warns = [(k, v) for k, v in m.items() if v["status"] != "ok"]
        if warns:
            for k, v in warns:
                th_w = stats['thresholds'].get(f'{k}_warn', '?')
                th_c = stats['thresholds'].get(f'{k}_crit', '?')
                print(f"  {icons[v['status']]} {k}: {v['value']} (warn:{th_w} crit:{th_c})")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Handle audit mode (no query needed)
    if mode == "audit":
        # Force UTF-8 output (avoid cp1252 encoding issues on Windows redirect)
        if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace') # type: ignore

        result = audit_routing_coverage()
        # Pretty-print audit results
        print(f"\n{'='*60}")
        print(f"🔍 ROUTING MAP AUDIT")
        print(f"{'='*60}")
        print(f"Scenari: {result['total_scenarios']} | Keywords: {result['total_keywords']}")

        if not result.get("scan_available", True):
            print(f"\n⚠️  {result.get('note', 'Sorgenti di scansione non disponibili')}")
            print("\n✅ Nessun gap rilevabile (sorgenti assenti).")
        else:
            print(f"Concetti trovati: {result['total_concepts']} | Coperti: {result['covered']} | Gap: {result['gaps']}")
            print(f"Copertura: {result['coverage_pct']}%")
            if result['gap_details']:
                print(f"\n{'─'*60}")
                print("⚠️  CONCETTI NON COPERTI:")
                print(f"{'─'*60}")
                for g in result['gap_details']:
                    print(f"  • {g['concept']} ({g['type']})")
                    print(f"    File: {g['source']}")
                    print(f"    Keywords suggerite: {', '.join(g['suggested_keywords'])}")
            else:
                print("\n✅ Tutti i concetti sono coperti dalla routing map.")

            if result['_covered_details']:
                print(f"\n{'─'*60}")
                print("📋 CONCETTI COPERTI:")
                print(f"{'─'*60}")
                for c in result['_covered_details']:
                    print(f"  ✓ {c['concept']} ({c['type']}) → {', '.join(c['matched_by'])}")

        print(f"\n{'='*60}")
        # JSON output: exclude internal _covered_details
        json_result = {k: v for k, v in result.items() if not k.startswith('_')}
        print("\nJSON:")
        print(json.dumps(json_result, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Handle dashboard mode (metrics visualization)
    if mode == "dashboard":
        try:
            if not RouterMetricsCollector or not DashboardUI:
                raise ImportError("premium/runtime dashboard components unavailable")
            collector = RouterMetricsCollector()
            ui = DashboardUI(collector)
            ui.run()
        except ImportError as e:
            print(f"Dashboard requires: pip install rich>=13.0", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(0)
        sys.exit(0)

    # Handle weight calibration mode
    if mode == "calibrate_weights":
        if not RouterWeightCalibrator:
            print("Weight calibration requires RouterWeightCalibrator (should be bundled)", file=sys.stderr)
            sys.exit(1)

        try:
            routes = _load_routes()
            store = InterventionStore()
            calibrator = RouterWeightCalibrator(store)
            weights_file = Path(__file__).parent / "calibrated_weights.json"

            # Check for --dry-run flag
            dry_run = "--dry-run" in query or "--dry-run" in " ".join(args[1:])

            if dry_run:
                result = calibrator.dry_run(routes)
            else:
                result = calibrator.calibrate(routes)
                # Export weights if not dry-run
                calibrator.export_weights(str(weights_file))

            store.close()

            # Pretty print results
            print("\n" + "="*60)
            print("🧠 WEIGHT CALIBRATION REPORT")
            print("="*60)
            print(f"Scenarios included: {result['scenarios_included']}")
            print(f"Total samples: {result['total_samples']}")
            print(f"Overall confidence: {result['confidence']}")
            print(f"Data freshness: {result['data_freshness']}")

            if result["success_rate_by_scenario"]:
                print(f"\n{'─'*60}")
                print("SUCCESS RATES PER SCENARIO:")
                print(f"{'─'*60}")
                for scenario, rate in sorted(result["success_rate_by_scenario"].items(), key=lambda x: x[1], reverse=True):
                    print(f"  {scenario:40} → {rate:.1%}")

            if result["calibrated_weights"]:
                print(f"\n{'─'*60}")
                print("KEYWORD BOOSTS (top 15):")
                print(f"{'─'*60}")
                sorted_weights = sorted(result["calibrated_weights"].items(), key=lambda x: x[1], reverse=True)
                for idx, (keyword, boost) in enumerate(sorted_weights[:15]):
                    boost_pct = (boost - 1.0) * 100
                    print(f"  {idx+1:2}. {keyword:30} → +{boost_pct:5.0f}% (boost: {boost:.2f}x)")

            print(f"\n{'='*60}")
            if not dry_run:
                print(f"✅ Weights exported to: {weights_file}")
            else:
                print("ℹ️  DRY-RUN: weights NOT persisted")
            print(f"{'='*60}\n")

            print(json.dumps(result, indent=2, ensure_ascii=False))
            sys.exit(0)

        except Exception as e:
            print(f"Error during calibration: {e}", file=sys.stderr)
            sys.exit(1)

    # Handle intervention memory modes
    if mode == "history":
        store = InterventionStore()
        if query:
            results = store.search(query)
            if not results:
                print("Nessun intervento trovato.")
            else:
                for r in results:
                    print(f"  [{r['ts'][:10]}] {r['agent']}/{r['scenario']}: {r['query'][:80]}")
                    if r.get('resolution'):
                        print(f"    → {r['resolution'][:120]}")
        else:
            print(json.dumps(store.stats(), indent=2, ensure_ascii=False))
        store.close()
        sys.exit(0)

    if mode == "log_intervention":
        # Expected format: --log-intervention agent|scenario|query|resolution|files|tags|outcome
        parts = query.split("|")
        if len(parts) < 4:
            print("Formato: --log-intervention agent|scenario|query|resolution[|files_csv|tags_csv|outcome]")
            sys.exit(1)
        store = InterventionStore()
        files = parts[4].split(",") if len(parts) > 4 and parts[4] else []
        tags = parts[5].split(",") if len(parts) > 5 and parts[5] else []
        outcome = parts[6].strip() if len(parts) > 6 and parts[6].strip() else "success"
        rid = store.log(
            agent=parts[0].strip(),
            scenario=parts[1].strip(),
            query=parts[2].strip(),
            resolution=parts[3].strip(),
            files_touched=files,
            tags=tags,
            outcome=outcome,
        )
        print(json.dumps({"logged": True, "id": rid}, indent=2))
        store.close()
        sys.exit(0)

    # Handle planner commands
    if query.lower() == "plan_approved":
        result = handle_plan_approved()
    elif query.lower().startswith("plan_rejected:"):
        reason = query[len("plan_rejected:"):].strip()
        result = handle_plan_rejected(reason)
    # Handle mode-specific routing
    elif mode == "direct":
        result = route_query(query)
    elif mode == "follow_up":
        result = route_follow_up(query)
    elif mode == "subagent":
        result = route_subagent(query)
    elif mode == "graph_mode":
        # Graph cascade routing
        if not GraphRouter:
            print("Graph routing requires GraphRouter (bundled with rgen)", file=sys.stderr)
            sys.exit(1)

        try:
            routes = _load_routes()
            graph_router = GraphRouter(routes, route_query_fn=route_query)
            result = graph_router.route_with_graph(query)
        except Exception as e:
            result = {
                "mode": "graph",
                "error": str(e),
                "primary": None,
                "secondary": [],
                "execution_plan": [],
                "cascade_success": False,
            }
            result = _apply_policy(result, query)
    else:
        # Default: planner workflow
        result = handle_new_query(query)

    # Expose plan lookup paths for planner-aware workflows (local-first).
    if isinstance(result, dict) and "plan_paths" not in result:
        result["plan_paths"] = [
            ".github/plans-local",
            ".github/plans",
        ]

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
