"""Static enforcement test: no direct filesystem writes in rgen/ or core/.

This test scans all .py files in ``rgen/`` and ``core/`` for direct write
patterns (``open(`` in write mode, ``write_text(``, ``write_bytes(``) and
fails if any are found outside of ``fs_policy.py``.

This is a best-effort static check, not a sandbox.  False positives are
possible for read-only ``open(`` calls; maintainers must annotate those
with ``# fs-policy: ok`` to suppress the violation.

Allowed exceptions:
- ``rgen/fs_policy.py`` — the policy layer itself is excluded from the check.
- Lines containing the annotation ``# fs-policy: ok``.
"""

from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

# Directories to scan (relative to ROOT)
SCAN_DIRS = ["rgen", "core"]

# Files excluded from the check (relative to ROOT)
EXCLUDED_FILES = {
    "rgen/fs_policy.py",
}

# Patterns that indicate a write operation.
# ``open(`` is matched only when followed by a write-mode string to reduce
# false positives (e.g. ``open(f, "w")``, ``open(f, "wb")``, ``open(f, "a")``).
WRITE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r'\bopen\s*\([^)]*["\'](?:w|wb|a|ab|x|xb)["\']'),
    re.compile(r'\bwrite_text\s*\('),
    re.compile(r'\bwrite_bytes\s*\('),
]

SUPPRESS_ANNOTATION = "# fs-policy: ok"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_py_files() -> list[Path]:
    files: list[Path] = []
    for scan_dir in SCAN_DIRS:
        for p in (ROOT / scan_dir).rglob("*.py"):
            rel = p.relative_to(ROOT).as_posix()
            if rel not in EXCLUDED_FILES:
                files.append(p)
    return sorted(files)


def _check_file(path: Path) -> list[tuple[int, str]]:
    """Return list of (line_no, line) with unsuppressed write patterns."""
    violations: list[tuple[int, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return violations

    for lineno, line in enumerate(lines, start=1):
        if SUPPRESS_ANNOTATION in line:
            continue
        for pattern in WRITE_PATTERNS:
            if pattern.search(line):
                violations.append((lineno, line.rstrip()))
                break  # one violation per line is enough
    return violations


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_no_direct_writes_in_rgen_and_core() -> None:
    """Fail if any rgen/ or core/ module writes files without fs_policy."""
    py_files = _collect_py_files()
    assert py_files, "No Python files found in rgen/ or core/ — check SCAN_DIRS."

    all_violations: dict[str, list[tuple[int, str]]] = {}
    for path in py_files:
        hits = _check_file(path)
        if hits:
            rel = path.relative_to(ROOT).as_posix()
            all_violations[rel] = hits

    if not all_violations:
        return  # all good

    lines = ["Direct write patterns found outside fs_policy — use FSPolicy API instead."]
    lines.append("To suppress a legitimate exception add  # fs-policy: ok  to the line.\n")
    for rel_path, hits in sorted(all_violations.items()):
        lines.append(f"  {rel_path}:")
        for lineno, text in hits:
            lines.append(f"    L{lineno}: {text}")
    raise AssertionError("\n".join(lines))
