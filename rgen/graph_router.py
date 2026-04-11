"""
Graph Router — Route queries through agent dependency graphs.

Enables cascade routing where agent A can invoke dependent agents B, C, etc.
Supports:
- Dependency graph building from routing-map.json
- Cycle detection (prevents A→B→A loops)
- Context forwarding between agents
- Execution plan generation (DAG)
"""

from __future__ import annotations

from typing import Any


class GraphRouter:
    """
    Route queries through agent dependency graph.

    Detects multi-domain needs, builds execution plan (DAG),
    forwards context between agents.
    """

    def __init__(self, routes: dict[str, Any], route_query_fn=None):
        """
        Initialize graph router with routing map.

        Args:
            routes: routing-map.json structure
                {
                    "scenario_name": {
                        "agent": "primary_agent",
                        "keywords": [...],
                        "dependencies": ["agent_b", "agent_c"],  # optional
                        "files": [...],
                        "context": "..."
                    },
                    ...
                }
            route_query_fn: Optional callable to route individual queries
                            Signature: route_query_fn(query, context=None) -> dict
        """
        self.routes = routes
        self.graph = self._build_dependency_graph()
        self.route_query_fn = route_query_fn

    def _build_dependency_graph(self) -> dict[str, list[str]]:
        """
        Create scenario → [dependent_scenarios] mapping.

        Converts agent names to scenario names for cycle detection.

        Returns:
            Adjacency list: {scenario: [dep_scenario1, dep_scenario2, ...], ...}
        """
        # First, build agent -> scenario mapping
        agent_to_scenario = {}
        for scenario, data in self.routes.items():
            agent = data.get("agent")
            if agent:
                agent_to_scenario[agent] = scenario

        # Then, convert dependencies from agent names to scenario names
        graph = {}
        for scenario, data in self.routes.items():
            dep_agents = data.get("dependencies", [])
            dep_scenarios = []
            for agent in (dep_agents if isinstance(dep_agents, list) else []):
                if agent in agent_to_scenario:
                    dep_scenarios.append(agent_to_scenario[agent])
            graph[scenario] = dep_scenarios

        return graph

    def _detect_cycles(self) -> list[list[str]]:
        """
        Find circular dependencies using DFS (Depth-First Search).

        Returns:
            List of cycles found. Each cycle is a list of scenarios.
            Empty list if graph is acyclic (DAG).

        Example:
            If A→B→A exists, returns: [['A', 'B', 'A']]
        """
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: list[str]) -> None:
            """DFS helper to detect cycles."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path[:])
                elif neighbor in rec_stack:
                    # Found cycle: from neighbor back to itself
                    cycle_start_idx = path.index(neighbor)
                    cycle = path[cycle_start_idx:] + [neighbor]
                    cycles.append(cycle)

            rec_stack.remove(node)

        # Run DFS from each unvisited node
        for scenario in self.graph:
            if scenario not in visited:
                dfs(scenario, [])

        return cycles

    def is_acyclic(self) -> bool:
        """
        Check if dependency graph is acyclic (safe for cascade routing).

        Returns:
            True if no cycles, False if cycles detected.
        """
        return len(self._detect_cycles()) == 0

    def get_execution_plan(
        self, primary_scenario: str, max_depth: int = 3
    ) -> list[str]:
        """
        Build execution plan (ordered list of agents to invoke).

        Performs BFS to collect all dependent agents, respecting depth limit.

        Args:
            primary_scenario: Starting scenario
            max_depth: Maximum cascade depth (prevent infinite loops)

        Returns:
            Ordered list of agents: [primary_agent, dep_agent1, dep_agent2, ...]

        Raises:
            ValueError: If primary_scenario not found in routes
            RuntimeError: If cycles detected
        """
        if primary_scenario not in self.routes:
            raise ValueError(f"Scenario '{primary_scenario}' not found in routes")

        if not self.is_acyclic():
            cycles = self._detect_cycles()
            raise RuntimeError(f"Circular dependencies detected: {cycles}")

        plan = []
        visited = set()
        queue = [(primary_scenario, 0)]  # (scenario, depth)

        while queue:
            scenario, depth = queue.pop(0)

            if scenario in visited or depth > max_depth:
                continue

            visited.add(scenario)
            agent = self.routes[scenario].get("agent")
            if agent:
                plan.append(agent)

            # Add dependent scenarios to queue
            for dep_scenario in self.graph.get(scenario, []):
                if dep_scenario not in visited:
                    queue.append((dep_scenario, depth + 1))

        return plan

    def validate_dependencies(self) -> tuple[bool, list[str]]:
        """
        Validate that all declared dependencies exist as agents in routes.

        Returns:
            (is_valid, error_messages)
            is_valid: True if all dependencies are valid
            error_messages: List of validation errors (empty if valid)
        """
        errors = []
        available_agents = set()

        # Collect all available agent names
        for scenario, data in self.routes.items():
            agent = data.get("agent")
            if agent:
                available_agents.add(agent)

        # Validate that dependencies reference existing agents
        for scenario, data in self.routes.items():
            dep_agents = data.get("dependencies", [])
            for dep_agent in (dep_agents if isinstance(dep_agents, list) else []):
                if dep_agent not in available_agents:
                    errors.append(
                        f"Scenario '{scenario}' depends on '{dep_agent}' "
                        f"but no agent with that name exists"
                    )

        return len(errors) == 0, errors

    def get_graph_stats(self) -> dict[str, Any]:
        """
        Get statistics about the dependency graph.

        Returns:
            {
                "total_scenarios": int,
                "scenarios_with_deps": int,
                "total_dependencies": int,
                "is_acyclic": bool,
                "max_depth": int,
                "cycles": list[list[str]]
            }
        """
        scenarios_with_deps = sum(1 for deps in self.graph.values() if deps)
        total_deps = sum(len(deps) for deps in self.graph.values())
        cycles = self._detect_cycles()

        # Calculate max depth (longest path)
        max_depth = 0
        for scenario in self.routes:
            depth = self._calculate_depth(scenario, set())
            max_depth = max(max_depth, depth)

        return {
            "total_scenarios": len(self.routes),
            "scenarios_with_deps": scenarios_with_deps,
            "total_dependencies": total_deps,
            "is_acyclic": len(cycles) == 0,
            "max_depth": max_depth,
            "cycles": cycles,
        }

    def _calculate_depth(self, scenario: str, visited: set[str]) -> int:
        """
        Calculate depth of a scenario in dependency graph.

        Args:
            scenario: Scenario name
            visited: Set of already visited scenarios (prevent infinite recursion)

        Returns:
            Depth (number of levels in dependency chain)
        """
        if scenario in visited:
            return 0

        visited.add(scenario)
        deps = self.graph.get(scenario, [])

        if not deps:
            return 1

        max_dep_depth = 0
        for dep_agent in deps:
            # Find scenarios that have this agent
            for scenario_name, scenario_data in self.routes.items():
                if scenario_data.get("agent") == dep_agent:
                    dep_depth = self._calculate_depth(scenario_name, visited.copy())
                    max_dep_depth = max(max_dep_depth, dep_depth)

        return 1 + max_dep_depth

    def route_with_graph(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Execute cascade routing with dependency graph.

        Routes a query through primary and secondary agents based on graph dependencies.

        Args:
            query: User query string
            context: Optional prior context from previous stage
                     {
                         "prior_agent": "backend",
                         "prior_confidence": 0.87,
                         "prior_context": "...",
                         "prior_files": [...]
                     }

        Returns:
            {
                "mode": "graph",
                "primary": {
                    "agent": "backend",
                    "scenario": "deployment",
                    "confidence": 0.87,
                    "files": [...],
                    "context": "..."
                },
                "secondary": [
                    {
                        "agent": "devops",
                        "scenario": "infrastructure",
                        "confidence": 0.75,
                        "files": [...],
                        "context": "..."
                    }
                ],
                "execution_plan": ["backend", "devops"],
                "context_forwarding": {
                    "prior_agent": "...",
                    "prior_confidence": 0.87,
                    "prior_context": "..."
                },
                "cascade_success": true
            }
        """
        if not self.route_query_fn:
            raise RuntimeError("route_query_fn not provided to GraphRouter")

        # Stage 1: Route primary query
        primary = self.route_query_fn(query, context=context)
        primary_agent = primary.get("agent")
        primary_scenario = primary.get("scenario")

        # Stage 2: Look up dependencies
        deps = self.routes.get(primary_scenario, {}).get("dependencies", [])

        # If no secondary agents, return primary only
        if not deps:
            return {
                "mode": "graph",
                "primary": primary,
                "secondary": [],
                "execution_plan": [primary_agent],
                "context_forwarding": None,
                "cascade_success": True,
            }

        # Stage 3: Validate DAG
        try:
            plan = self.get_execution_plan(primary_scenario)
        except RuntimeError as e:
            # Cycles detected, return primary only
            return {
                "mode": "graph",
                "primary": primary,
                "secondary": [],
                "execution_plan": [primary_agent],
                "context_forwarding": None,
                "cascade_success": False,
                "error": str(e),
            }

        # Stage 4: Forward context to secondary agents
        forwarded_context = {
            "prior_agent": primary_agent,
            "prior_confidence": primary.get("confidence", 0.0),
            "prior_context": primary.get("context", ""),
            "prior_files": primary.get("files", []),
            "prior_scenario": primary_scenario,
        }

        secondary_results = []
        for secondary_agent in plan[1:]:  # Skip primary agent
            try:
                secondary = self.route_query_fn(query, context=forwarded_context)
                secondary_results.append(secondary)
                # Update context for next agent
                forwarded_context["prior_agent"] = secondary_agent
                forwarded_context["prior_confidence"] = secondary.get("confidence", 0.0)
                forwarded_context["prior_context"] = secondary.get("context", "")
            except Exception as e:
                # If secondary routing fails, continue with what we have
                secondary_results.append({
                    "agent": secondary_agent,
                    "error": str(e),
                    "confidence": 0.0,
                })

        return {
            "mode": "graph",
            "primary": primary,
            "secondary": secondary_results,
            "execution_plan": plan,
            "context_forwarding": forwarded_context,
            "cascade_success": len(secondary_results) == len(plan[1:]),
        }
