from __future__ import annotations

from pathlib import Path

from rgen.cutover import build_cutover_manifest, classify_repo_path, export_cutover_snapshot


def test_classify_repo_path_returns_expected_scope() -> None:
    assert classify_repo_path("README.md") == "public"
    assert classify_repo_path(".github/ROADMAP.md") == "internal"
    assert classify_repo_path(".github/esperti/esperto_backend.md") == "public"
    assert classify_repo_path("agentpilot-orchestrator.code-workspace") == "public"
    assert classify_repo_path(".github/plans-local/private.plan") == "private"
    assert classify_repo_path("knowledge_base/psm_stack/esperti/esperto_sistemista.md") == "private"


def test_build_cutover_manifest_excludes_private_and_internal_by_default(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "ROADMAP.md").write_text("internal", encoding="utf-8")
    (tmp_path / ".github" / "interventions.db").write_text("private", encoding="utf-8")
    (tmp_path / ".continue").mkdir()
    (tmp_path / ".continue" / "prompt.md").write_text("local", encoding="utf-8")
    (tmp_path / "sample.db").write_text("sqlite", encoding="utf-8")

    manifest = build_cutover_manifest(tmp_path)

    assert manifest["included"] == ["README.md"]
    assert manifest["excluded_internal"] == [".github/ROADMAP.md"]
    assert manifest["excluded_private"] == [".continue/prompt.md", ".github/interventions.db"]


def test_build_cutover_manifest_can_include_internal_assets(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "ROADMAP.md").write_text("internal", encoding="utf-8")

    manifest = build_cutover_manifest(tmp_path, include_internal=True)

    assert ".github/ROADMAP.md" in manifest["included"]
    assert manifest["excluded_internal"] == []


def test_export_cutover_snapshot_materializes_only_included_files(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("ok", encoding="utf-8")
    (root / ".github").mkdir()
    (root / ".github" / "ROADMAP.md").write_text("internal", encoding="utf-8")
    export_dir = tmp_path / "public"

    manifest = export_cutover_snapshot(root, export_dir, clean_output=True)

    assert (export_dir / "README.md").exists()
    assert not (export_dir / ".github" / "ROADMAP.md").exists()
    assert not (export_dir / "cutover-manifest.json").exists()
    assert manifest["included"] == ["README.md"]


def test_export_cutover_snapshot_can_write_manifest_when_requested(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("ok", encoding="utf-8")
    export_dir = tmp_path / "public"

    export_cutover_snapshot(root, export_dir, clean_output=True, write_manifest=True)

    assert (export_dir / "cutover-manifest.json").exists()