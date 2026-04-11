#!/usr/bin/env python3
"""
PSM Stack Router — Planner Integration Module

Extracted from router.py. Handles:
  - handle_plan_approved()  → Execute approved plan from planner-output.json
  - handle_plan_rejected()  → Trigger replanning with feedback
  - handle_new_query()      → Start planner workflow for new queries
"""

import json
from pathlib import Path

PLANNER_OUTPUT = Path(__file__).parent / "planner-output.json"
PLANS_LOCAL_DIR = Path(__file__).parent / "plans-local"
PLANS_SHARED_DIR = Path(__file__).parent / "plans"


def handle_plan_approved() -> dict:
    """Legge planner-output.json e esegue il piano approvato."""
    try:
        with open(PLANNER_OUTPUT, 'r', encoding='utf-8') as f:
            plan = json.load(f)
        execution_plan = plan.get("execution_plan", {})
        agents = execution_plan.get("agents_involved", [])
        return {
            "phase": "EXECUTION",
            "plan_approved": True,
            "agents_sequence": [a.get("agent_name") for a in agents],
            "status": "Ready to execute",
            "planner_output": plan,
        }
    except FileNotFoundError:
        return {
            "error": "No planner-output.json found",
            "status": "FAILED",
            "hint": "First run planner for your query",
        }


def handle_plan_rejected(reason: str = "") -> dict:
    """Torna a planner per replanning."""
    return {
        "phase": "PLANNER",
        "rejection_reason": reason,
        "status": "Replanning needed",
        "action": "Planner will revise based on feedback",
    }


def handle_new_query(query: str) -> dict:
    """Nuova query: chiama planner."""
    print("\n" + "="*70)
    print("🔄 ROUTER: Calling Planner Agent...")
    print("="*70)
    return {
        "phase": "PLANNING",
        "action": f"Run: python .github/planner.py \"{query}\"",
        "status": "Next: Run planner to generate plan",
        "plan_paths": [
            str(PLANS_LOCAL_DIR).replace("\\", "/"),
            str(PLANS_SHARED_DIR).replace("\\", "/"),
        ],
        "plan_lookup_policy": "local-first",
        "next_steps": [
            f"1. python .github/planner.py \"{query}\"",
            "2. (Planner generates plan in planner-output.json)",
            "2b. If needed, keep personal drafts in .github/plans-local/ and sync approved decisions to .github/plans/",
            "3. UMANO LEGGE E DECIDE:",
            "   - Approva: python .github/router.py 'PLAN_APPROVED'",
            "   - Rifiuta: python .github/router.py 'PLAN_REJECTED: motivo'",
        ],
    }
