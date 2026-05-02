"""Utilities for open-core cutover dry runs."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


PRIVATE_PREFIXES = (
    "artifacts/",
    ".claude/",
    ".continue/",
    ".continuerules",
    ".discussioni/",
    ".github/.rgen-backups/",
    ".github/plans-local/",
    ".github/interventions.db",
    ".vscode/settings.json",
    "knowledge_base/psm_stack/",
    "knowledge_base/psm_stack/esperti/",
)

INTERNAL_PREFIXES = (
    "README_AGENTPILOT_ORCHESTRATOR_EN.md",
    ".github/ASSET_CLASSIFICATION.md",
    ".github/BRANCH_HYGIENE_POLICY.md",
    ".github/copilot-instructions.md",
    ".github/ROADMAP.md",
    ".github/RELEASE_NOTES.md",
    ".github/decision-priority.md",
    ".github/token-budget-allocation.md",
    ".github/versioning-strategy.md",
    ".github/AGENT_REGISTRY.md",
    ".github/KNOWHOW_EXPOSURE_AUDIT_2026-04-11.md",
    ".github/kpi/",
    ".github/plans/",
    ".github/standard/",
    ".github/skills.sh",
    ".github/subagent-brief.md",
)

IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
}

IGNORED_SUFFIXES = {
    ".db",
    ".sqlite",
}


def classify_repo_path(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in PRIVATE_PREFIXES):
        return "private"
    if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in INTERNAL_PREFIXES):
        return "internal"
    return "public"


def build_cutover_manifest(root: Path, include_internal: bool = False) -> dict[str, object]:
    included: list[str] = []
    excluded_private: list[str] = []
    excluded_internal: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        scope = classify_repo_path(rel)

        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if any(part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES and scope == "public":
            continue

        if scope == "private":
            excluded_private.append(rel)
            continue
        if scope == "internal" and not include_internal:
            excluded_internal.append(rel)
            continue
        included.append(rel)

    return {
        "root": str(root),
        "include_internal": include_internal,
        "summary": {
            "included": len(included),
            "excluded_private": len(excluded_private),
            "excluded_internal": len(excluded_internal),
        },
        "included": included,
        "excluded_private": excluded_private,
        "excluded_internal": excluded_internal,
    }


def export_cutover_snapshot(
    root: Path,
    output_dir: Path,
    include_internal: bool = False,
    clean_output: bool = False,
    write_manifest: bool = False,
) -> dict[str, object]:
    manifest = build_cutover_manifest(root, include_internal=include_internal)

    if output_dir.exists() and clean_output:
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for rel in manifest["included"]:
        src = root / rel
        dst = output_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    if write_manifest:
        manifest_path = output_dir / "cutover-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")  # fs-policy: ok
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m rgen.cutover",
        description="Dry-run a public snapshot for AgentPilot Orchestrator.",
    )
    parser.add_argument("--root", default=".", help="Repository root to analyze")
    parser.add_argument("--include-internal", action="store_true", help="Include internal assets in the generated manifest")
    parser.add_argument("--output", help="Optional JSON output path")
    parser.add_argument("--export-dir", help="Optional directory where the public snapshot should be materialized")
    parser.add_argument("--clean-output", action="store_true", help="Delete export directory before materializing the snapshot")
    parser.add_argument("--write-export-manifest", action="store_true", help="Write cutover-manifest.json inside the export directory")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if args.export_dir:
        manifest = export_cutover_snapshot(
            root,
            Path(args.export_dir).resolve(),
            include_internal=args.include_internal,
            clean_output=args.clean_output,
            write_manifest=args.write_export_manifest,
        )
    else:
        manifest = build_cutover_manifest(root, include_internal=args.include_internal)
    payload = json.dumps(manifest, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")  # fs-policy: ok
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())