"""Tests for marketplace local registry utilities."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from rgen.pattern_registry import PatternRegistry


def _build_pack(root: Path, pattern_id: str = "demo_pack") -> Path:
    pack = root / "pack"
    kb = pack / "knowledge_base" / pattern_id
    kb.mkdir(parents=True)
    manifest = {"id": pattern_id, "name": "Demo", "version": "1.0.0"}
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (kb / "metadata.json").write_text(json.dumps({"id": pattern_id, "name": "Demo"}), encoding="utf-8")
    return pack


def _zip_dir(source: Path, zip_path: Path, prefix: str = "") -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in source.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(source).as_posix()
            arcname = f"{prefix}{rel}" if prefix else rel
            archive.write(file_path, arcname=arcname)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_search_finds_installed_patterns() -> None:
    registry = PatternRegistry()
    results = registry.search("python")
    ids = {item["id"] for item in results}
    assert "python_api" in ids


def test_install_local_pack_success(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path)

    registry = PatternRegistry()
    result = registry.install(str(pack), install_dir=tmp_path / "installed")

    assert result["id"] == "demo_pack"
    assert (tmp_path / "installed" / "demo_pack" / "metadata.json").exists()


def test_install_validates_checksums(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path)
    kb = pack / "knowledge_base" / "demo_pack"
    file_path = kb / "metadata.json"

    checksum_line = f"{_sha256(file_path)}  knowledge_base/demo_pack/metadata.json\n"
    (pack / "checksums.txt").write_text(checksum_line, encoding="utf-8")

    registry = PatternRegistry()
    registry.install(str(pack), install_dir=tmp_path / "installed")

    file_path.write_text("tampered", encoding="utf-8")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        registry.install(str(pack), install_dir=tmp_path / "installed")


def test_install_zip_url_success(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path / "src", pattern_id="remote_pack")
    zip_path = tmp_path / "remote_pack.zip"
    _zip_dir(pack, zip_path, prefix="remote_pack/")

    registry = PatternRegistry()
    result = registry.install(zip_path.as_uri(), install_dir=tmp_path / "installed")

    assert result["id"] == "remote_pack"
    assert (tmp_path / "installed" / "remote_pack" / "metadata.json").exists()


def test_install_registry_entry_with_url_source(tmp_path: Path) -> None:
    pack = _build_pack(tmp_path / "src", pattern_id="registry_remote")
    zip_path = tmp_path / "registry_remote.zip"
    _zip_dir(pack, zip_path, prefix="registry_remote/")

    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps(
            {
                "patterns": [
                    {
                        "id": "registry_remote",
                        "name": "Registry Remote",
                        "tags": ["python"],
                        "source": zip_path.as_uri(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    registry = PatternRegistry(registry_path=registry_file)
    result = registry.install("registry_remote", install_dir=tmp_path / "installed")

    assert result["id"] == "registry_remote"
    assert (tmp_path / "installed" / "registry_remote" / "metadata.json").exists()
