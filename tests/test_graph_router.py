"""
Unit tests for GraphRouter — dependency graph routing.

Tests cover:
- Dependency graph building
- Cycle detection
- Execution plan generation
- Validation
"""

from __future__ import annotations

import pytest

from rgen.graph_router import GraphRouter


@pytest.fixture
def sample_routes():
    """Sample routing map with dependencies."""
    return {
        "auth_fix": {
            "agent": "backend",
            "keywords": ["auth", "login"],
            "files": ["backend.md"],
            "context": "Auth issues",
        },
        "deployment": {
            "agent": "backend",
            "keywords": ["deploy"],
            "dependencies": ["devops"],
            "files": ["backend.md"],
            "context": "Deployment task",
        },
        "infrastructure": {
            "agent": "devops",
            "keywords": ["infra", "docker"],
            "files": ["devops.md"],
            "context": "Infrastructure",
        },
        "database": {
            "agent": "db_admin",
            "keywords": ["database", "migrate"],
            "files": ["db.md"],
            "context": "Database",
        },
    }


@pytest.fixture
def circular_routes():
    """Routing map with circular dependencies."""
    return {
        "scenario_a": {
            "agent": "agent_a",
            "keywords": ["a"],
            "dependencies": ["agent_b"],
            "files": ["a.md"],
        },
        "scenario_b": {
            "agent": "agent_b",
            "keywords": ["b"],
            "dependencies": ["agent_a"],
            "files": ["b.md"],
        },
    }


class TestGraphBuilding:
    """Test dependency graph construction."""

    def test_build_dependency_graph_valid(self, sample_routes):
        """Test graph is built correctly from routes."""
        router = GraphRouter(sample_routes)

        assert "auth_fix" in router.graph
        assert router.graph["auth_fix"] == []
        # deployment depends on devops agent, which is the infrastructure scenario
        assert router.graph["deployment"] == ["infrastructure"]

    def test_build_dependency_graph_empty_routes(self):
        """Test graph with empty routing map."""
        router = GraphRouter({})
        assert router.graph == {}

    def test_build_dependency_graph_no_deps(self, sample_routes):
        """Test scenarios with no dependencies."""
        router = GraphRouter(sample_routes)

        assert router.graph["auth_fix"] == []
        assert router.graph["infrastructure"] == []
        assert router.graph["database"] == []


class TestCycleDetection:
    """Test cycle detection in dependency graph."""

    def test_detect_cycles_acyclic_graph(self, sample_routes):
        """Test no cycles detected in valid DAG."""
        router = GraphRouter(sample_routes)
        cycles = router._detect_cycles()

        assert len(cycles) == 0

    def test_detect_cycles_finds_circular_deps(self, circular_routes):
        """Test cycles are detected in circular dependencies."""
        router = GraphRouter(circular_routes)
        cycles = router._detect_cycles()

        assert len(cycles) > 0
        # Should contain at least one cycle involving both scenarios
        assert any("scenario_a" in str(cycle) and "scenario_b" in str(cycle) for cycle in cycles)

    def test_is_acyclic_true(self, sample_routes):
        """Test is_acyclic returns True for DAG."""
        router = GraphRouter(sample_routes)
        assert router.is_acyclic() is True

    def test_is_acyclic_false(self, circular_routes):
        """Test is_acyclic returns False for circular graph."""
        router = GraphRouter(circular_routes)
        assert router.is_acyclic() is False

    def test_self_loop_detection(self):
        """Test detection of self-referencing dependency."""
        routes = {
            "scenario_a": {
                "agent": "agent_a",
                "keywords": ["a"],
                "dependencies": ["agent_a"],
                "files": ["a.md"],
            }
        }
        router = GraphRouter(routes)
        cycles = router._detect_cycles()

        assert len(cycles) > 0


class TestExecutionPlan:
    """Test execution plan generation."""

    def test_get_execution_plan_no_deps(self, sample_routes):
        """Test plan for scenario with no dependencies."""
        router = GraphRouter(sample_routes)
        plan = router.get_execution_plan("auth_fix")

        assert "backend" in plan
        assert len(plan) >= 1

    def test_get_execution_plan_with_deps(self, sample_routes):
        """Test plan includes dependent agents."""
        router = GraphRouter(sample_routes)
        plan = router.get_execution_plan("deployment")

        # Should include both primary (backend) and secondary (devops)
        assert "backend" in plan
        assert "devops" in plan

    def test_get_execution_plan_invalid_scenario(self, sample_routes):
        """Test error when scenario doesn't exist."""
        router = GraphRouter(sample_routes)

        with pytest.raises(ValueError, match="not found in routes"):
            router.get_execution_plan("nonexistent_scenario")

    def test_get_execution_plan_with_cycles_raises(self, circular_routes):
        """Test error when circular dependencies exist."""
        router = GraphRouter(circular_routes)

        with pytest.raises(RuntimeError, match="Circular dependencies"):
            router.get_execution_plan("scenario_a")

    def test_get_execution_plan_respects_max_depth(self, sample_routes):
        """Test execution plan respects maximum depth limit."""
        router = GraphRouter(sample_routes)
        plan = router.get_execution_plan("deployment", max_depth=1)

        # Should still include primary and direct deps
        assert len(plan) > 0


class TestValidation:
    """Test graph validation."""

    def test_validate_dependencies_valid(self, sample_routes):
        """Test validation passes for valid dependencies."""
        router = GraphRouter(sample_routes)
        is_valid, errors = router.validate_dependencies()

        assert is_valid is True
        assert len(errors) == 0

    def test_validate_dependencies_invalid_agent(self):
        """Test validation fails for non-existent dependent agent."""
        routes = {
            "scenario_a": {
                "agent": "agent_a",
                "keywords": ["a"],
                "dependencies": ["nonexistent_agent"],
                "files": ["a.md"],
            }
        }
        router = GraphRouter(routes)
        is_valid, errors = router.validate_dependencies()

        assert is_valid is False
        assert len(errors) > 0
        assert "nonexistent_agent" in errors[0]

    def test_validate_dependencies_multiple_errors(self):
        """Test validation reports multiple errors."""
        routes = {
            "scenario_a": {
                "agent": "agent_a",
                "keywords": ["a"],
                "dependencies": ["nonexistent_1", "nonexistent_2"],
                "files": ["a.md"],
            }
        }
        router = GraphRouter(routes)
        is_valid, errors = router.validate_dependencies()

        assert is_valid is False
        assert len(errors) == 2


class TestGraphStats:
    """Test graph statistics."""

    def test_get_graph_stats_basic(self, sample_routes):
        """Test basic statistics collection."""
        router = GraphRouter(sample_routes)
        stats = router.get_graph_stats()

        assert stats["total_scenarios"] == 4
        assert stats["scenarios_with_deps"] >= 1
        assert stats["is_acyclic"] is True
        assert "cycles" in stats

    def test_get_graph_stats_with_cycles(self, circular_routes):
        """Test stats show cycles."""
        router = GraphRouter(circular_routes)
        stats = router.get_graph_stats()

        assert stats["is_acyclic"] is False
        assert len(stats["cycles"]) > 0

    def test_get_graph_stats_depth(self, sample_routes):
        """Test max depth calculation."""
        router = GraphRouter(sample_routes)
        stats = router.get_graph_stats()

        assert "max_depth" in stats
        assert stats["max_depth"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
