from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_TOKENS = [
    "routing-generator",
    "routing generator",
    "routing_generator",
    "maironz/routing-generator",
]


def _iter_public_text_files() -> list[Path]:
    files: list[Path] = [
        ROOT / "pyproject.toml",
        ROOT / "README.md",
        ROOT / "README_AGENTPILOT_ORCHESTRATOR_EN.md",
    ]
    files.extend((ROOT / ".github").rglob("*"))
    files.extend((ROOT / "rgen").rglob("*.py"))
    filtered: list[Path] = []
    for p in files:
        if not p.is_file():
            continue
        parts = set(p.parts)
        if "__pycache__" in parts or ".rgen-backups" in parts:
            continue
        if p.suffix == ".pyc":
            continue
        filtered.append(p)
    return filtered


def test_project_metadata_rebranded() -> None:
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'name = "agentpilot-orchestrator"' in content
    assert 'rgen = "rgen.cli:main"' in content
    assert 'agentpilot = "rgen.cli:main"' in content
    assert not (ROOT / "routing-generator.code-workspace").exists()
    assert (ROOT / "agentpilot-orchestrator.code-workspace").exists()


def test_no_legacy_branding_in_public_assets() -> None:
    offenders: list[tuple[Path, str]] = []

    for path in _iter_public_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")
        lowered = text.lower()
        for token in FORBIDDEN_TOKENS:
            if token in lowered:
                offenders.append((path.relative_to(ROOT), token))

    assert not offenders, f"Legacy branding found: {offenders}"
