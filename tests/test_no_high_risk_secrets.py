from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# High-confidence patterns only to avoid noisy false positives.
HIGH_RISK_PATTERNS: dict[str, re.Pattern[str]] = {
    "github_pat": re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
    "github_fine_grained": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}


EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "build",
    "dist",
    "routing_generator.egg-info",
}


EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".db-shm", ".db-wal"}


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in EXCLUDE_SUFFIXES:
            continue
        files.append(p)
    return files


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def test_no_high_risk_secrets_in_repo() -> None:
    hits: list[tuple[str, str]] = []

    for path in _iter_files():
        text = _read_text(path)
        for label, pattern in HIGH_RISK_PATTERNS.items():
            if pattern.search(text):
                hits.append((str(path.relative_to(ROOT)), label))

    assert not hits, f"High-risk secret patterns found: {hits}"
