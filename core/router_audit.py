#!/usr/bin/env python3
"""
PSM Stack Router — Audit & Health Stats Module

Extracted from router.py to keep the main router under the line-count threshold.
Provides:
  - audit_routing_coverage(): scan codebase for routing-map gaps
  - get_health_stats(): compute routing system health metrics
"""

import json
import re
from pathlib import Path

# Paths — can be overridden for testing
ROUTING_MAP = Path(__file__).parent / "routing-map.json"
ROUTER_FILE = Path(__file__).parent / "router.py"


def _load_routes() -> dict:
    """Load routing map in flat or sectioned format, skipping metadata entries."""
    with open(ROUTING_MAP, "r", encoding="utf-8") as f:
        payload = json.load(f)

    routes = {k: v for k, v in payload.items() if isinstance(v, dict) and "keywords" in v}

    sections = payload.get("_sections") if isinstance(payload, dict) else None
    if isinstance(sections, dict):
        for _, section_items in sections.items():
            if not isinstance(section_items, dict):
                continue
            for scenario_id, scenario_data in section_items.items():
                if isinstance(scenario_data, dict) and "keywords" in scenario_data:
                    routes[scenario_id] = scenario_data

    return routes


# ─── Audit: Routing Coverage Gap Detection ───

# Scan paths (try Z:\ first, fall back to ~/pms-stack mapped paths)
_SCAN_CONFIGS = [
    {
        "label": "PHP Namespaces (src/)",
        "paths": ["Z:/www/src", "/var/www/html/src"],
        "pattern": r"^namespace\s+([\w\\]+);",
        "glob": "**/*.php",
        "extract": "namespace",
    },
    {
        "label": "CLI Scripts (cli/)",
        "paths": ["Z:/www/cli", "/var/www/html/cli"],
        "pattern": None,
        "glob": "*.php",
        "extract": "filename",
    },
    {
        "label": "DB Tables (CREATE TABLE)",
        "paths": ["Z:/www/src", "/var/www/html/src"],
        "pattern": r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`'\"]?(?:\w+\.)?([a-z][a-z0-9_]+)[`'\"]?\s*\(",
        "glob": "**/*.php",
        "extract": "regex_group",
    },
]


def _resolve_scan_path(candidates: list) -> Path | None:
    """Find first existing path from candidates."""
    for p in candidates:
        path = Path(p)
        if path.exists():
            return path
    return None


def _extract_concepts(config: dict) -> list[dict]:
    """Extract concepts from a scan config."""
    base = _resolve_scan_path(config["paths"])
    if not base:
        return []

    concepts = []
    glob_pattern = config["glob"]

    for filepath in base.rglob(glob_pattern) if "**" in glob_pattern else base.glob(glob_pattern):
        if config["extract"] == "filename":
            name = filepath.stem
            concepts.append({
                "concept": name,
                "source": str(filepath.relative_to(base)),
                "type": config["label"],
            })
        elif config["extract"] in ("namespace", "regex_group"):
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for match in re.finditer(config["pattern"], content, re.IGNORECASE):
                value = match.group(1)
                concepts.append({
                    "concept": value,
                    "source": str(filepath.relative_to(base)),
                    "type": config["label"],
                })

    return concepts


def _concept_to_keywords(concept: str, concept_type: str) -> list[str]:
    """
    Convert a concept (namespace, filename, table name) into search terms
    that should ideally match at least one routing-map keyword.
    """
    terms = set()
    name = concept.strip()

    if "Namespace" in concept_type:
        # PSM\Core\Mail\Mailer → ["mail", "mailer", "core"]
        parts = name.replace("PSM\\", "").split("\\")
        for p in parts:
            low = p.lower()
            if low not in ("core", "components", "config", "utils", "interfaces"):
                terms.add(low)
    elif "CLI" in concept_type:
        # notify-due-invoices → ["notify", "due", "invoices", "notify-due-invoices"]
        terms.add(name.lower())
        for part in re.split(r"[-_]", name):
            if len(part) > 2:
                terms.add(part.lower())
    elif "Table" in concept_type:
        # np2gn_psm_mail → ["psm_mail", "mail"]
        # Strip common prefixes
        clean = re.sub(r"^[a-z0-9]+_", "", name)  # strip table prefix
        terms.add(clean.lower())
        for part in clean.split("_"):
            if len(part) > 2:
                terms.add(part.lower())

    return list(terms)


def audit_routing_coverage() -> dict:
    """
    Scan codebase for concepts (namespaces, CLI scripts, DB tables) and check
    whether each is covered by at least one routing-map keyword.
    Returns a structured report of gaps.
    """
    routes = _load_routes()

    # Flatten all keywords into a single lowercase set
    all_keywords = set()
    for data in routes.values():
        for kw in data.get("keywords", []):
            all_keywords.add(kw.lower())

    # Also collect scenario names
    scenario_names = set(routes.keys())

    # Scan codebase
    scan_paths_found = any(
        _resolve_scan_path(config["paths"]) is not None
        for config in _SCAN_CONFIGS
    )
    if not scan_paths_found:
        return {
            "mode": "audit",
            "scan_available": False,
            "note": "Nessun percorso di scansione disponibile (sorgenti PSM Stack non trovate)",
            "total_concepts": 0,
            "covered": 0,
            "gaps": 0,
            "gap_details": [],
            "coverage_pct": None,
            "total_scenarios": len(routes),
            "total_keywords": len(all_keywords),
            "_covered_details": [],
        }

    all_concepts = []
    for config in _SCAN_CONFIGS:
        all_concepts.extend(_extract_concepts(config))

    # Deduplicate by concept name
    seen = set()
    unique_concepts = []
    for c in all_concepts:
        key = (c["concept"], c["type"])
        if key not in seen:
            seen.add(key)
            unique_concepts.append(c)

    # Check coverage
    covered = []
    gaps = []

    for c in unique_concepts:
        search_terms = _concept_to_keywords(c["concept"], c["type"])
        matched_keywords = [t for t in search_terms if t in all_keywords]

        if matched_keywords:
            covered.append({
                "concept": c["concept"],
                "type": c["type"],
                "matched_by": matched_keywords,
            })
        else:
            gaps.append({
                "concept": c["concept"],
                "type": c["type"],
                "source": c["source"],
                "suggested_keywords": search_terms,
            })

    return {
        "mode": "audit",
        "scan_available": True,
        "total_concepts": len(unique_concepts),
        "covered": len(covered),
        "gaps": len(gaps),
        "gap_details": gaps,
        "coverage_pct": round(len(covered) / max(len(unique_concepts), 1) * 100, 1),
        "total_scenarios": len(routes),
        "total_keywords": len(all_keywords),
        "_covered_details": covered,  # used by pretty-printer, not in JSON output
    }


# ─── Stats: Health Metrics ───

# Thresholds for health indicators
_THRESHOLDS = {
    "scenarios_warn": 50,
    "scenarios_crit": 60,
    "keywords_warn": 450,
    "keywords_crit": 550,
    "overlap_pct_warn": 15,
    "overlap_pct_crit": 20,
    "router_lines_warn": 800,
    "router_lines_crit": 1200,
    "routing_map_kb_warn": 25,
    "routing_map_kb_crit": 35,
}


def get_health_stats(router_file: Path | None = None) -> dict:
    """
    Compute routing system health metrics:
    - Scenario/keyword counts
    - Keyword overlap %
    - File sizes (routing-map.json, router.py)
    - Status per metric: ok / warn / crit

    router_file: override path for router.py line counting.
                 Defaults to the companion router.py.
    """
    routes = _load_routes()

    # Scenarios and keywords
    total_scenarios = len(routes)
    all_kw_list = []
    kw_to_scenarios = {}
    for key, data in routes.items():
        for kw in data.get("keywords", []):
            kw_lower = kw.lower()
            all_kw_list.append(kw_lower)
            kw_to_scenarios.setdefault(kw_lower, []).append(key)

    unique_keywords = len(set(all_kw_list))
    shared_kw = sum(1 for kw, scns in kw_to_scenarios.items() if len(scns) > 1)
    overlap_pct = round(shared_kw / max(unique_keywords, 1) * 100, 1)

    # File sizes
    rm_size_kb = round(ROUTING_MAP.stat().st_size / 1024, 1)

    # Count router.py lines (main entry point — modules tracked separately)
    rf = router_file or ROUTER_FILE
    total_lines = len(rf.read_text(encoding="utf-8").splitlines()) if rf.exists() else 0

    # Evaluate status per metric
    def _status(value, warn_key, crit_key):
        if value >= _THRESHOLDS[crit_key]:
            return "crit"
        if value >= _THRESHOLDS[warn_key]:
            return "warn"
        return "ok"

    metrics = {
        "scenarios":     {"value": total_scenarios, "status": _status(total_scenarios, "scenarios_warn", "scenarios_crit")},
        "keywords":      {"value": unique_keywords, "status": _status(unique_keywords, "keywords_warn", "keywords_crit")},
        "overlap_pct":   {"value": overlap_pct, "status": _status(overlap_pct, "overlap_pct_warn", "overlap_pct_crit")},
        "router_lines":  {"value": total_lines, "status": _status(total_lines, "router_lines_warn", "router_lines_crit")},
        "routing_map_kb": {"value": rm_size_kb, "status": _status(rm_size_kb, "routing_map_kb_warn", "routing_map_kb_crit")},
    }

    # Overall status: worst of all
    statuses = [m["status"] for m in metrics.values()]
    if "crit" in statuses:
        overall = "crit"
    elif "warn" in statuses:
        overall = "warn"
    else:
        overall = "ok"

    return {
        "mode": "stats",
        "overall": overall,
        "metrics": metrics,
        "thresholds": _THRESHOLDS,
    }
