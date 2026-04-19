from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Private package references are allowed only in boundary loaders and their tests.
ALLOWED_PRIVATE_IMPORT_PATHS = {
    Path("rgen/premium_pricing_loader.py"),
    Path("rgen/premium_runtime_loader.py"),
    Path("rgen/premium_policy_loader.py"),
    Path("tests/test_private_boundary_guard.py"),
    Path("tests/test_premium_pricing_loader.py"),
    Path("tests/test_premium_runtime_loader.py"),
    Path("tests/test_premium_policy_loader.py"),
}


def _git_tracked_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git ls-files failed")
    return [Path(line.strip()) for line in proc.stdout.splitlines() if line.strip()]


def test_private_packages_are_not_tracked() -> None:
    tracked = _git_tracked_files()
    private_tracked = [str(p) for p in tracked if p.parts and p.parts[0] == ".private-packages"]

    assert not private_tracked, f"Tracked private files detected: {private_tracked}"


def test_private_imports_are_confined_to_boundary_loaders() -> None:
    tracked = _git_tracked_files()
    offenders: list[str] = []

    for rel in tracked:
        if rel.suffix != ".py":
            continue
        if rel in ALLOWED_PRIVATE_IMPORT_PATHS:
            continue

        abs_path = ROOT / rel
        try:
            text = abs_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = abs_path.read_text(encoding="latin-1")

        if "agentpilot_intelligence" in text:
            offenders.append(str(rel).replace("\\", "/"))

    assert not offenders, (
        "Private package references found outside approved boundaries: "
        + ", ".join(sorted(offenders))
    )
