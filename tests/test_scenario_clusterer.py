from __future__ import annotations

from rgen.scenario_clusterer import ScenarioClusterer


class FakeStore:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def recent(self, limit: int = 100) -> list[dict]:
        return self._rows[:limit]


def test_vectorize_query_basic() -> None:
    store = FakeStore([])
    c = ScenarioClusterer(store)
    v = c.vectorize_query("optimize database query performance")
    assert v["optimize"] == 1
    assert v["database"] == 1


def test_cluster_queries_finds_similar() -> None:
    c = ScenarioClusterer(FakeStore([]), similarity_threshold=0.2)
    queries = [
        "optimize postgres query performance",
        "improve database query speed",
        "speed up sql query",
        "deploy docker container",
    ]
    clusters = c.cluster_queries(queries)
    sizes = sorted((len(v) for v in clusters.values()), reverse=True)
    assert sizes[0] >= 3


def test_cluster_queries_returns_empty_for_dissimilar() -> None:
    c = ScenarioClusterer(FakeStore([]), similarity_threshold=0.5)
    queries = ["apple banana carrot", "docker nginx kubernetes", "invoice payment stripe"]
    clusters = c.cluster_queries(queries)
    assert all(len(group) == 1 for group in clusters.values())


def test_suggest_scenarios_returns_candidates() -> None:
    rows = [
        {"scenario": "_fallback", "query": "optimize postgres query performance"},
        {"scenario": "_fallback", "query": "improve database query speed"},
        {"scenario": "_fallback", "query": "speed up database operations"},
        {"scenario": "_fallback", "query": "database query too slow"},
    ]
    c = ScenarioClusterer(FakeStore(rows), min_cluster_size=3, similarity_threshold=0.2)
    out = c.suggest_scenarios()
    assert len(out) >= 1
    assert out[0]["size"] >= 3
    assert out[0]["suggested_scenario"]


def test_min_cluster_size_filter() -> None:
    rows = [
        {"scenario": "_fallback", "query": "optimize postgres query performance"},
        {"scenario": "_fallback", "query": "improve database query speed"},
    ]
    c = ScenarioClusterer(FakeStore(rows), min_cluster_size=3, similarity_threshold=0.2)
    assert c.suggest_scenarios() == []


def test_clustering_accuracy_gt_80() -> None:
    db_queries = [
        "optimize postgres query performance",
        "improve database query speed",
        "speed up sql query planner",
        "reduce database latency",
        "fix slow postgres joins",
    ]
    auth_queries = [
        "oauth callback returns 401",
        "fix login token refresh",
        "session expires too early",
        "auth middleware rejects valid token",
        "improve authentication flow",
    ]
    all_queries = db_queries + auth_queries

    c = ScenarioClusterer(FakeStore([]), similarity_threshold=0.18)
    clusters = c.cluster_queries(all_queries)

    predicted: dict[str, int] = {}
    for cid, group in clusters.items():
        for q in group:
            predicted[q] = cid

    correct_pairs = 0
    total_pairs = 0
    for group in (db_queries, auth_queries):
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                total_pairs += 1
                if predicted[group[i]] == predicted[group[j]]:
                    correct_pairs += 1

    accuracy = correct_pairs / total_pairs
    assert accuracy >= 0.8
