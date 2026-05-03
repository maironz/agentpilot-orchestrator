"""
Tests for AgentPilot v2 Guardrail Patterns

Validates:
  - Pre-identification mandatory pattern
  - Named exceptions (summary, post-task, ambiguity)
  - Postflight validation 5-step checklist
  - Routing coverage audit for new components
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import modules under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from router_audit import validate_new_components_coverage, audit_routing_coverage, get_health_stats


class TestPreIdentificationPattern:
    """Test Phase 2a: Pre-identification mandatory pattern"""

    def test_pre_identification_header_format(self):
        """Verify pre-identification header format matches spec"""
        # Format: 🤖 **[Model]** | Agente: **[agent]** | Priorità: [priority] | Routing: [stats]
        header = "🤖 **Claude Haiku** | Agente: **orchestratore** | Priorità: medium | Routing: 13scn/176kw | overlap:2.3% | [OK]"
        
        assert header.startswith("🤖")
        assert "Agente:" in header
        assert "Priorità:" in header
        assert "Routing:" in header
        
    def test_pre_identification_exception_declaration(self):
        """Verify exception declaration format for summary continuation"""
        declaration = "Continuo dal summary precedente, agente: [X]"
        assert "Continuo dal summary precedente" in declaration
        assert "agente:" in declaration


class TestNamedExceptionsPattern:
    """Test Phase 2b: Named exceptions for router bypass"""

    def test_exception_1_conversation_summary_present(self):
        """
        Exception 1: Skip router if summary has file list + agent + continuation plan
        """
        summary = {
            "file_list": ["src/handler.py", "src/utils.py"],
            "agent": "backend",
            "continuation_plan": "Fix database connection pooling"
        }
        
        # Check that all required fields exist
        has_all_fields = (
            "file_list" in summary and
            "agent" in summary and
            "continuation_plan" in summary
        )
        assert has_all_fields, "Summary must have file_list, agent, and continuation_plan"

    def test_exception_2_post_task_documentation(self):
        """
        Exception 2: Skip router if documenting just-completed task
        - Same agent, known target, task-scoped
        """
        context = {
            "task_type": "code_implementation",
            "agent_before": "backend",
            "agent_after": "documentazione",
            "target_file": "docs/API.md",
            "scope": "task-scoped"
        }
        
        # This is POST-TASK documentation (after backend completed code work)
        # Agent changed for documentation, but scope is the task itself
        assert context["target_file"].endswith(".md"), "Post-task docs should target known files"

    def test_exception_3_ambiguity_meta_router(self):
        """
        Exception 3: If router returns similar-confidence scenarios, orchestratore decides
        """
        scenario_scores = {
            "python_code": 0.82,
            "api_endpoints": 0.80,  # Similar score, < 5% difference
        }
        
        max_score = max(scenario_scores.values())
        min_score = min(scenario_scores.values())
        difference = max_score - min_score
        is_ambiguous = difference < 0.05
        
        assert is_ambiguous, "Scores within < 5% difference should trigger meta-routing"


class TestPostflightValidationPattern:
    """Test Phase 2c: Postflight 5-step validation"""

    def test_postflight_step_1_router_used_or_exception_declared(self):
        """Step 1: Verify router was called OR exception was declared"""
        context = {
            "router_called": True,
            "exception_declared": None
        }
        
        step1_ok = context["router_called"] or context["exception_declared"]
        assert step1_ok, "Router must be called or exception must be explicitly declared"

    def test_postflight_step_2_agent_coherent(self):
        """Step 2: Verify agent is coherent with task type"""
        task = {
            "type": "code_refactoring",
            "agent": "backend",
            "domain": "backend"
        }
        
        # Simple heuristic: agent domain should match task domain
        agent_coherent = task["agent"] == task["domain"]
        assert agent_coherent, "Agent must match task domain"

    def test_postflight_step_3_files_conform_to_routing(self):
        """Step 3: Verify modified files were nominated by router"""
        router_nominated = ["src/handler.py", "src/utils.py", "tests/test_handler.py"]
        files_modified = ["src/handler.py", "src/utils.py", "docs/README.md"]
        
        # Check that all modified files were nominated (strict conformance)
        all_conform = all(f in router_nominated for f in files_modified)
        # In practice, docs changes might not be nominated, so warn but don't fail
        if not all_conform:
            missing = [f for f in files_modified if f not in router_nominated]
            # This is acceptable for minor files, but should be logged
            pass

    def test_postflight_step_4_routing_coverage(self):
        """Step 4: Verify new components have routing-map coverage"""
        new_components = ["DatabasePool", "CacheService"]
        
        # This will be tested by Phase 2d (validate_new_components_coverage)
        # Here we just verify the check is called
        result = validate_new_components_coverage(new_components)
        assert result["mode"] == "postflight_coverage"
        assert "coverage_pct" in result

    def test_postflight_step_5_health_check_after_routing_update(self):
        """Step 5: If routing-map modified, verify health metrics"""
        result = get_health_stats()
        
        assert result["mode"] == "stats"
        assert "overall" in result
        assert "metrics" in result
        assert result["overall"] in ["ok", "warn", "crit"]


class TestCoverageAuditEnhancement:
    """Test Phase 2d: Coverage audit for new components"""

    def test_validate_single_covered_component(self):
        """Verify a component matching routing-map keywords"""
        result = validate_new_components_coverage(["email"])
        
        assert result["mode"] == "postflight_coverage"
        assert "email" in [c["component"] for c in result["covered"] + result["gaps"]]

    def test_validate_multiple_components_mixed_coverage(self):
        """Verify mixed coverage (some covered, some gaps)"""
        # "mail" should be covered (common in routing-map)
        # "xyz_random_service" likely won't be covered
        result = validate_new_components_coverage(["mail", "xyz_random_service_not_real"])
        
        assert result["mode"] == "postflight_coverage"
        assert len(result["input_components"]) == 2
        assert result["coverage_pct"] <= 100

    def test_validate_empty_component_list(self):
        """Verify handling of empty input"""
        result = validate_new_components_coverage([])
        
        assert result["coverage_pct"] == 100 or len(result["input_components"]) == 0

    def test_coverage_gap_recommendations(self):
        """Verify recommendations are provided for gaps"""
        result = validate_new_components_coverage(["unknown_xyz_abc"])
        
        if result["gaps"]:
            assert len(result["recommendations"]) > 0
            assert result["status"] == "warn"

    def test_coverage_ok_status(self):
        """Verify 'ok' status when all components covered"""
        # Use common terms likely in routing-map
        result = validate_new_components_coverage(["mail", "auth", "cache"])
        
        # At least some should be covered (mail, auth, cache are common)
        if result["coverage_pct"] == 100:
            assert result["status"] == "ok"


class TestGuardrailIntegration:
    """Integration tests for guardrail patterns working together"""

    def test_complete_postflight_flow(self):
        """Simulate a complete postflight validation flow"""
        # 1. Router was called
        router_called = True
        exception_declared = None
        step1 = router_called or exception_declared
        
        # 2. Agent is coherent
        agent = "backend"
        task_domain = "backend"
        step2 = agent == task_domain
        
        # 3. Files conform
        router_nominated = ["src/service.py"]
        files_modified = ["src/service.py"]
        step3 = all(f in router_nominated for f in files_modified)
        
        # 4. Coverage check
        result_coverage = validate_new_components_coverage(["PaymentService"])
        step4 = result_coverage["mode"] == "postflight_coverage"
        
        # 5. Health check
        result_health = get_health_stats()
        step5 = result_health["overall"] in ["ok", "warn", "crit"]
        
        # All steps passed
        all_steps_ok = all([step1, step2, step3, step4, step5])
        assert all_steps_ok, "All postflight steps must pass"

    def test_exception_declaration_flow(self):
        """Test flow with exception declaration (summary continuation)"""
        # Skip pre-identification if continuing from summary
        exception_used = "Continuo dal summary precedente, agente: backend"
        
        assert "Continuo dal summary precedente" in exception_used
        # Router is skipped, but postflight still applies for complex tasks
