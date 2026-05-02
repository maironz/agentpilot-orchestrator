"""Runtime tests for the generated router policy in .github/."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def runtime_router():
    repo_root = Path(__file__).parent.parent
    github_dir = repo_root / ".github"
    sys.path.insert(0, str(github_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "runtime_router_for_tests",
            github_dir / "router.py",
        )
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.remove(str(github_dir))


def test_route_query_fallback_allows_repo_exploration(runtime_router, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_router, "_load_routes", lambda: {})
    monkeypatch.setattr(runtime_router, "_enrich_with_prior", lambda result, query: result)

    result = runtime_router.route_query("zzqv unmatched semantic token")

    assert result["scenario"] == "_fallback"
    assert result["confidence"] == 0.0
    assert result["repo_exploration"]["allowed"] is True
    assert result["repo_exploration"]["recommended_scope"] == "repo-fallback"
    assert result["policy"]["fallback_strategy"] == "repo-search"
    assert result["complexity"]["analysis_mode"] == "initial_heuristic"


def test_route_query_high_confidence_keeps_scope_restricted(runtime_router, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runtime_router, "_enrich_with_prior", lambda result, query: result)
    monkeypatch.setattr(
        runtime_router,
        "_load_routes",
        lambda: {
            "backup_restore": {
                "agent": "sistemista",
                "keywords": ["backup", "restore", "snapshot"],
                "files": [".github/esperti/esperto_sistemista.md"],
                "context": "Backup operations",
                "priority": "high",
            }
        },
    )

    query = "backup restore snapshot"
    result = runtime_router.route_query(query)

    assert result["scenario"] != "_fallback"
    assert result["confidence"] >= runtime_router.CONFIDENCE_GATE
    assert result["repo_exploration"]["allowed"] is False
    assert result["repo_exploration"]["recommended_scope"] == "routed-files-only"
    assert result["policy"]["governance_mode"] in {"standard", "guarded", "strict"}
    assert result["complexity"]["level"] in {"short", "medium", "long"}


def test_load_routes_supports_sectioned_routing_map(runtime_router, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    routing_map = {
        "_base_autoloaded": {"note": "test"},
        "flat_scenario": {
            "agent": "orchestratore",
            "keywords": ["flat"],
            "files": [".github/esperti/esperto_orchestratore.md"],
            "context": "Flat",
            "priority": "low",
        },
        "_sections": {
            "backend": {
                "database": {
                    "agent": "backend",
                    "keywords": ["sql", "migration"],
                    "files": [".github/esperti/esperto_backend.md"],
                    "context": "DB",
                    "priority": "high",
                }
            }
        },
    }
    map_path = tmp_path / "routing-map.json"
    map_path.write_text(json.dumps(routing_map), encoding="utf-8")

    monkeypatch.setattr(runtime_router, "ROUTING_MAP", map_path)
    routes = runtime_router._load_routes()

    assert "flat_scenario" in routes
    assert "database" in routes
    assert routes["database"]["agent"] == "backend"


def test_load_routes_merges_local_companion_file(runtime_router, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base_map = {
        "python_code": {
            "agent": "backend",
            "keywords": ["python"],
            "files": [".github/esperti/esperto_backend.md"],
            "context": "Base",
            "priority": "high",
        }
    }
    local_map = {
        "ledger_add_event": {
            "agent": "backend",
            "keywords": ["ledger", "event"],
            "files": [".github/esperti/esperto_backend.md"],
            "context": "Host project custom scenario",
            "priority": "high",
        }
    }
    map_path = tmp_path / "routing-map.json"
    local_path = tmp_path / "routing-map.local.json"
    map_path.write_text(json.dumps(base_map), encoding="utf-8")
    local_path.write_text(json.dumps(local_map), encoding="utf-8")

    monkeypatch.setattr(runtime_router, "ROUTING_MAP", map_path)
    monkeypatch.setattr(runtime_router, "ROUTING_MAP_LOCAL", local_path)

    routes = runtime_router._load_routes()

    assert "python_code" in routes
    assert "ledger_add_event" in routes
    assert routes["ledger_add_event"]["context"] == "Host project custom scenario"
