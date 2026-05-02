"""Pattern marketplace utilities (local-first MVP)."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


class PatternRegistry:
    """Local-first pattern discovery and installation."""

    def __init__(self, registry_path: Path | None = None, kb_dir: Path | None = None) -> None:
        project_root = Path(__file__).resolve().parent.parent
        self._registry_path = registry_path or (project_root / "artifacts" / "pattern-registry.json")
        self._kb_dir = kb_dir or (project_root / "knowledge_base")

    def search(self, query: str) -> list[dict[str, object]]:
        """Search installed patterns and optional registry entries."""
        query_l = (query or "").strip().lower()
        results: list[dict[str, object]] = []

        if self._kb_dir.exists():
            for pattern_dir in sorted(self._kb_dir.iterdir()):
                if not pattern_dir.is_dir():
                    continue
                metadata_path = pattern_dir / "metadata.json"
                if not metadata_path.exists():
                    continue
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                haystack = " ".join(
                    [
                        str(metadata.get("id", pattern_dir.name)),
                        str(metadata.get("name", "")),
                        " ".join(metadata.get("tech_stack", [])),
                    ]
                ).lower()
                if not query_l or query_l in haystack:
                    results.append(
                        {
                            "id": metadata.get("id", pattern_dir.name),
                            "name": metadata.get("name", pattern_dir.name),
                            "tags": metadata.get("tech_stack", []),
                            "source": "installed",
                        }
                    )

        for entry in self._load_registry_entries():
            tags = self._to_str_list(entry.get("tags", []))  # <-- qui
            haystack = " ".join(
                [
                    str(entry.get("id", "")),
                    str(entry.get("name", "")),
                    " ".join(tags),
                ]
            ).lower()
            if not query_l or query_l in haystack:
                results.append(entry)

        dedup: dict[str, dict[str, object]] = {}
        for item in results:
            dedup[str(item.get("id", ""))] = item
        return sorted(dedup.values(), key=lambda item: str(item.get("id", "")))

    def install(self, spec: str, install_dir: Path) -> dict[str, str]:
        """Install a pattern pack from local path, URL, GitHub shorthand, or registry id."""
        source_kind, source_value = self._resolve_source(spec)
        if source_kind == "path":
            return self._install_from_pack(Path(source_value), install_dir)

        if source_kind == "url":
            with tempfile.TemporaryDirectory(prefix="rgen-pattern-") as temp_dir:
                extracted = self._download_and_extract_zip(str(source_value), Path(temp_dir))
                pack_dir = self._resolve_pack_dir(extracted)
                return self._install_from_pack(pack_dir, install_dir)

        raise ValueError(f"Unsupported pattern source kind: {source_kind}")

    def _resolve_source(self, spec: str) -> tuple[str, str | Path]:
        candidate = Path(spec)
        if candidate.exists():
            return ("path", candidate)

        if self._looks_like_url(spec):
            return ("url", spec)

        github_url = self._github_spec_to_zip_url(spec)
        if github_url:
            return ("url", github_url)

        for entry in self._load_registry_entries():
            if entry.get("id") == spec:
                source_raw = str(entry.get("source", "")).strip()
                if not source_raw:
                    raise FileNotFoundError(f"Registry source not configured for '{spec}'")
                source_path = Path(source_raw)
                if source_path.exists():
                    return ("path", source_path)
                if self._looks_like_url(source_raw):
                    return ("url", source_raw)
                raise FileNotFoundError(
                    f"Registry source not found for '{spec}': {source_raw}"
                )

        raise FileNotFoundError(f"Pattern source not found: {spec}")

    @staticmethod
    def _looks_like_url(value: str) -> bool:
        parsed = urllib.parse.urlparse(value)
        return parsed.scheme in {"http", "https", "file"}

    @staticmethod
    def _github_spec_to_zip_url(spec: str) -> str | None:
        # Accepts owner/repo or owner/repo:tag
        match = re.fullmatch(
            r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)(?::(?P<ref>[A-Za-z0-9_.\-/]+))?",
            spec.strip(),
        )
        if not match:
            return None
        owner = match.group("owner")
        repo = match.group("repo")
        ref = match.group("ref") or "main"
        return f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{ref}" if ref == "main" else f"https://codeload.github.com/{owner}/{repo}/zip/refs/tags/{ref}"

    @staticmethod
    def _download_and_extract_zip(url: str, temp_dir: Path) -> Path:
        zip_path = temp_dir / "pattern-pack.zip"
        with urllib.request.urlopen(url, timeout=30) as response:
            zip_path.write_bytes(response.read())  # fs-policy: ok

        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(extract_dir)
        return extract_dir

    @staticmethod
    def _resolve_pack_dir(extracted_root: Path) -> Path:
        if (extracted_root / "manifest.json").exists() and (extracted_root / "knowledge_base").exists():
            return extracted_root

        children = [child for child in extracted_root.iterdir() if child.is_dir()]
        for child in children:
            if (child / "manifest.json").exists() and (child / "knowledge_base").exists():
                return child

        raise FileNotFoundError(
            f"No valid pattern pack found in archive: {extracted_root}"
        )

    def _install_from_pack(self, pack_dir: Path, install_dir: Path) -> dict[str, str]:
        manifest = self._load_manifest(pack_dir)
        self._validate_checksums(pack_dir)

        kb_root = pack_dir / "knowledge_base"
        pattern_id = str(manifest["id"])
        source_pattern_dir = kb_root / pattern_id
        if not source_pattern_dir.exists():
            raise FileNotFoundError(
                f"Pattern directory missing in pack: {source_pattern_dir}"
            )

        install_dir = Path(install_dir)
        install_dir.mkdir(parents=True, exist_ok=True)
        destination = install_dir / pattern_id
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source_pattern_dir, destination)

        return {
            "id": pattern_id,
            "version": str(manifest.get("version", "latest")),
            "installed_path": str(destination),
        }

    @staticmethod
    def _load_manifest(pack_dir: Path) -> dict[str, object]:
        manifest_path = pack_dir / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid manifest JSON: {manifest_path}") from exc

        for key in ("id", "version", "name"):
            if key not in manifest:
                raise ValueError(f"Manifest missing required field: {key}")
        return manifest

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _validate_checksums(self, pack_dir: Path) -> None:
        checksums = pack_dir / "checksums.txt"
        if not checksums.exists():
            return

        for raw in checksums.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line:
                continue
            expected, rel_path = line.split("  ", 1)
            file_path = pack_dir / rel_path
            if not file_path.exists():
                raise FileNotFoundError(f"Checksum file missing target: {rel_path}")
            actual = self._file_sha256(file_path)
            if actual != expected:
                raise ValueError(f"Checksum mismatch: {rel_path}")

    def _load_registry_entries(self) -> list[dict[str, object]]:
        if not self._registry_path.exists():
            return []
        try:
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            entries = data.get("patterns", [])
        else:
            entries = data
        if not isinstance(entries, list):
            return []
        return [entry for entry in entries if isinstance(entry, dict)]

    @staticmethod
    def _to_str_list(value: object) -> list[str]:
        if isinstance(value, (list, tuple, set)):
            return [str(v) for v in value]
        return []
