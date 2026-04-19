"""Scenario Evolution: detect recurring unmatched query patterns."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "about",
    "your", "please", "need", "help", "make", "create", "build", "issue",
    "error", "debug", "fix", "una", "uno", "per", "con", "degli", "delle",
    "della", "dello", "dati", "come", "fare", "need", "improve", "improving",
}

_TOKEN_NORMALIZATION = {
    "sql": "database",
    "postgres": "database",
    "postgresql": "database",
    "db": "database",
    "latency": "performance",
    "slow": "performance",
    "speed": "performance",
    "oauth": "auth",
    "login": "auth",
    "token": "auth",
    "session": "auth",
    "authentication": "auth",
}


class ScenarioClusterer:
    """Detects similar query clusters and suggests new scenarios."""

    def __init__(
        self,
        store: Any,
        min_cluster_size: int = 3,
        similarity_threshold: float = 0.35,
        min_confidence: float = 0.0,
    ):
        self.store = store
        self.min_cluster_size = min_cluster_size
        self.similarity_threshold = similarity_threshold
        self.min_confidence = min_confidence

    def load_interventions(self, limit: int = 100) -> list[dict]:
        """Load recent interventions from store."""
        if not hasattr(self.store, "recent"):
            return []
        rows = self.store.recent(limit=limit)
        return [r for r in rows if isinstance(r, dict) and r.get("query")]

    def vectorize_query(self, query: str) -> Counter[str]:
        """Converts a query to sparse token-frequency vector."""
        tokens = self._tokenize(query)
        return Counter(tokens)

    def cluster_queries(self, queries: list[str]) -> dict[int, list[str]]:
        """Groups similar queries using Jaccard similarity on token sets."""
        clusters: list[dict[str, Any]] = []

        for q in queries:
            q_tokens = set(self._tokenize(q))
            if not q_tokens:
                continue

            best_idx = -1
            best_score = -1.0
            for i, c in enumerate(clusters):
                score = max(self._jaccard(q_tokens, ts) for ts in c["token_sets"])
                if score > best_score:
                    best_score = score
                    best_idx = i

            if best_idx >= 0 and best_score >= self.similarity_threshold:
                clusters[best_idx]["queries"].append(q)
                clusters[best_idx]["token_sets"].append(q_tokens)
            else:
                clusters.append({"queries": [q], "token_sets": [q_tokens]})

        return {i: c["queries"] for i, c in enumerate(clusters)}

    def suggest_scenarios(self, limit: int = 100, unmatched_only: bool = True) -> list[dict]:
        """Returns candidate scenarios derived from unmatched clusters."""
        interventions = self.load_interventions(limit=limit)
        if not interventions:
            return []

        if unmatched_only:
            unmatched_queries = [
                i["query"] for i in interventions
                if self._is_unmatched_scenario(str(i.get("scenario", "")))
            ]
            queries = unmatched_queries if unmatched_queries else [i["query"] for i in interventions]
        else:
            queries = [i["query"] for i in interventions]

        clustered = self.cluster_queries(queries)
        suggestions: list[dict] = []

        for cluster_id, cluster_queries in clustered.items():
            size = len(cluster_queries)
            if size < self.min_cluster_size:
                continue

            keywords = self._extract_keywords(cluster_queries)
            if not keywords:
                continue

            scenario_name = "_".join(keywords[:3])
            confidence = self._cluster_confidence(cluster_queries)
            if confidence < self.min_confidence:
                continue
            suggestions.append(
                {
                    "cluster_id": cluster_id,
                    "queries": cluster_queries,
                    "keywords": keywords,
                    "suggested_scenario": scenario_name,
                    "confidence": round(confidence, 3),
                    "size": size,
                }
            )

        suggestions.sort(key=lambda s: (s["size"], s["confidence"]), reverse=True)
        return suggestions

    def _extract_keywords(self, queries: list[str], top_k: int = 8) -> list[str]:
        counts: Counter[str] = Counter()
        for q in queries:
            counts.update(self._tokenize(q))
        return [w for w, _ in counts.most_common(top_k)]

    def _cluster_confidence(self, cluster_queries: list[str]) -> float:
        if len(cluster_queries) <= 1:
            return 0.0
        token_sets = [set(self._tokenize(q)) for q in cluster_queries]
        sims: list[float] = []
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                sims.append(self._jaccard(token_sets[i], token_sets[j]))
        if not sims:
            return 0.0
        mean_sim = sum(sims) / len(sims)
        size_bonus = min(0.25, (len(cluster_queries) - self.min_cluster_size) * 0.05)
        return min(0.99, mean_sim + size_bonus)

    def _tokenize(self, text: str) -> list[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{2,}", text.lower())
        normalized = [_TOKEN_NORMALIZATION.get(w, w) for w in words]
        return [w for w in normalized if w not in _STOPWORDS]

    def _jaccard(self, a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _is_unmatched_scenario(self, scenario: str) -> bool:
        s = scenario.strip().lower()
        if not s:
            return True
        return s.startswith("_") or s in {"general", "unknown", "unmatched"}
