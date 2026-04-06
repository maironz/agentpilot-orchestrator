"""
Integration tests for GraphRouter with context forwarding.

Tests cover:
- route_with_graph() cascade routing
- Context forwarding between agents
- Primary-only routing when no dependencies
- Error handling in secondary routing
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
    }


@pytest.fixture
def mock_route_query():
    """Mock route_query_fn for testing."""

    def _route_query(query: str, context: dict | None = None) -> dict:
        """Simulate routing behavior."""
        if "auth" in query.lower():
            return {
                "agent": "backend",
                "scenario": "auth_fix",
                "confidence": 0.92,
                "files": ["backend.md"],
                "context": "Authentication fix",
                "prior_context": context.get("prior_context", "") if context else "",
            }
        elif "deploy" in query.lower():
            return {
                "agent": "backend",
                "scenario": "deployment",
                "confidence": 0.85,
                "files": ["backend.md"],
                "context": "Deployment workflow",
                "prior_context": context.get("prior_context", "") if context else "",
            }
        elif "infra" in query.lower() or "docker" in query.lower():
            return {
                "agent": "devops",
                "scenario": "infrastructure",
                "confidence": 0.78,
                "files": ["devops.md"],
                "context": "Infrastructure management",
                "prior_context": context.get("prior_context", "") if context else "",
            }
        else:
            return {
                "agent": "backend",
                "scenario": "auth_fix",
                "confidence": 0.5,
                "files": ["backend.md"],
                "context": "Generic fallback",
            }

    return _route_query


class TestGraphRouterInit:
    """Test GraphRouter initialization."""

    def test_init_without_route_query_fn(self, sample_routes):
        """Test router can be initialized without route_query_fn."""
        router = GraphRouter(sample_routes)
        assert router.route_query_fn is None

    def test_init_with_route_query_fn(self, sample_routes, mock_route_query):
        """Test router can be initialized with route_query_fn."""
        router = GraphRouter(sample_routes, route_query_fn=mock_route_query)
        assert router.route_query_fn is mock_route_query

    def test_init_preserves_graph(self, sample_routes):
        """Test graph is built correctly during init."""
        router = GraphRouter(sample_routes)
        assert "deployment" in router.graph
        assert "infrastructure" in router.graph["deployment"]


class TestRouteWithGraph:
    """Test cascade routing with graph."""

    def test_route_with_graph_no_route_query_fn(self, sample_routes):
        """Test error when route_query_fn not provided."""
        router = GraphRouter(sample_routes)
        with pytest.raises(RuntimeError, match="route_query_fn"):
            router.route_with_graph("test query")

    def test_route_with_graph_primary_only(self, sample_routes, mock_route_query):
        """Test routing for scenario with no dependencies."""
        router = GraphRouter(sample_routes, route_query_fn=mock_route_query)
        result = router.route_with_graph("fix auth bug")

        assert result["mode"] == "graph"
        assert result["primary"]["agent"] == "backend"
        assert result["primary"]["scenario"] == "auth_fix"
        assert len(result["secondary"]) == 0
        assert result["execution_plan"] == ["backend"]
        assert result["cascade_success"] is True

    def test_route_with_graph_primary_and_secondary(
        self, sample_routes, mock_route_query
    ):
        """Test routing with cascade to secondary agents."""
        router = GraphRouter(sample_routes, route_query_fn=mock_route_query)
        result = router.route_with_graph("deploy to production")

        assert result["mode"] == "graph"
        assert result["primary"]["agent"] == "backend"
        assert result["primary"]["scenario"] == "deployment"
        # Secondary should include devops (from dependencies)
        assert len(result["secondary"]) > 0
        # The execution plan should include both agents
        assert "backend" in result["execution_plan"]
        assert result["cascade_success"] is True

    def test_route_with_graph_context_forwarding(
        self, sample_routes, mock_route_query
    ):
        """Test context forwarding between agents."""
        router = GraphRouter(sample_routes, route_query_fn=mock_route_query)
        result = router.route_with_graph("deploy to production")

        # Context should be forwarded
        assert result["context_forwarding"] is not None
        # After cascade, prior_agent should be from execution chain
        assert "prior_agent" in result["context_forwarding"]
        assert result["context_forwarding"]["prior_confidence"] > 0

    def test_route_with_graph_initial_context(
        self, sample_routes, mock_route_query
    ):
        """Test routing with initial context."""
        initial_context = {
            "prior_agent": "api_gateway",
            "prior_confidence": 0.95,
            "prior_context": "Previous: Load balancer configuration",
        }

        router = GraphRouter(sample_routes, route_query_fn=mock_route_query)
        result = router.route_with_graph("deploy to production", context=initial_context)

        assert result["mode"] == "graph"
        assert result["cascade_success"] is True

    def test_route_with_graph_structure(self, sample_routes, mock_route_query):
        """Test output structure contains all required fields."""
        router = GraphRouter(sample_routes, route_query_fn=mock_route_query)
        result = router.route_with_graph("deploy to production")

        # Verify all required fields present
        assert "mode" in result
        assert "primary" in result
        assert "secondary" in result
        assert "execution_plan" in result
        assert "context_forwarding" in result
        assert "cascade_success" in result

        # Verify primary structure
        assert "agent" in result["primary"]
        assert "scenario" in result["primary"]
        assert "confidence" in result["primary"]
        assert "files" in result["primary"]

    def test_route_with_graph_secondary_structure(
        self, sample_routes, mock_route_query
    ):
        """Test secondary agent results have proper structure."""
        router = GraphRouter(sample_routes, route_query_fn=mock_route_query)
        result = router.route_with_graph("deploy to production")

        if result["secondary"]:
            secondary = result["secondary"][0]
            assert "agent" in secondary
            assert "confidence" in secondary


class TestRouteWithGraphEdgeCases:
    """Test edge cases in cascade routing."""

    def test_route_with_graph_circular_deps(self):
        """Test cascade routing gracefully handles circular dependencies."""
        circular_routes = {
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

        def mock_route_query(query: str, context: dict | None = None) -> dict:
            return {
                "agent": "agent_a",
                "scenario": "scenario_a",
                "confidence": 0.8,
                "files": ["a.md"],
                "context": "Test",
            }

        router = GraphRouter(circular_routes, route_query_fn=mock_route_query)
        result = router.route_with_graph("test query")

        # Should fail gracefully
        assert result["cascade_success"] is False
        assert "error" in result

    def test_route_with_graph_empty_routes(self, mock_route_query):
        """Test cascade routing with empty routing map."""
        router = GraphRouter({}, route_query_fn=mock_route_query)

        # Should handle gracefully (route_query_fn returns a result anyway)
        result = router.route_with_graph("test query")
        assert result["mode"] == "graph"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
