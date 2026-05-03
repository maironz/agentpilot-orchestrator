"""T3 — strict mode subprocess exit-code test.

Verifies that a rgen process running in strict mode exits with a non-zero
code (and raises PolicyViolation) when a write outside the whitelist is
attempted, rather than silently continuing.

The test spawns a child Python process so the exit code is observable via
subprocess.returncode without affecting the test runner's own process.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers — small Python snippets run in child processes
# ---------------------------------------------------------------------------

_WRITE_OUTSIDE_WHITELIST = """\
import sys, pathlib
sys.path.insert(0, r"{root}")
from rgen.fs_policy import FSPolicy, PolicyViolation
policy = FSPolicy(project_root=r"{root}", strict=True)
try:
    policy.write_file(pathlib.Path(r"{bad_path}"), "oops")
except PolicyViolation:
    sys.exit(1)
sys.exit(0)
"""

_WRITE_INSIDE_WHITELIST = """\
import sys, pathlib
sys.path.insert(0, r"{root}")
from rgen.fs_policy import FSPolicy
policy = FSPolicy(project_root=r"{root}", strict=True)
target = pathlib.Path(r"{good_path}")
target.parent.mkdir(parents=True, exist_ok=True)
policy.write_file(target, "ok")
sys.exit(0)
"""

_GITHUB_WRITE_NOT_ALLOWED_STRICT = """\
import sys, pathlib
sys.path.insert(0, r"{root}")
from rgen.fs_policy import FSPolicy, PolicyViolation
gh = pathlib.Path(r"{root}") / ".github"
gh.mkdir(exist_ok=True)
policy = FSPolicy(project_root=r"{root}", strict=True, allow_github_write=False)
try:
    policy.write_file(gh / "bad.txt", "oops")
except PolicyViolation:
    sys.exit(1)
sys.exit(0)
"""

_GITHUB_WRITE_ALLOWED_STRICT = """\
import sys, pathlib
sys.path.insert(0, r"{root}")
from rgen.fs_policy import FSPolicy
gh = pathlib.Path(r"{root}") / ".github"
gh.mkdir(exist_ok=True)
policy = FSPolicy(project_root=r"{root}", strict=True, allow_github_write=True)
policy.write_file(gh / "ok.txt", "ok")
sys.exit(0)
"""


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# T3 tests
# ---------------------------------------------------------------------------


def test_strict_write_outside_whitelist_exits_nonzero(tmp_path):
    """In strict mode, writing outside .agentpilot/ exits with code 1."""
    bad = tmp_path / "outside_dir" / "evil.txt"
    code = _WRITE_OUTSIDE_WHITELIST.format(
        root=str(tmp_path).replace("\\", "\\\\"),
        bad_path=str(bad).replace("\\", "\\\\"),
    )
    result = _run(code)
    assert result.returncode != 0, (
        f"Expected non-zero exit, got 0.\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_strict_write_inside_whitelist_exits_zero(tmp_path):
    """In strict mode, writing inside .agentpilot/ exits cleanly."""
    good = tmp_path / ".agentpilot" / "state" / "run.json"
    code = _WRITE_INSIDE_WHITELIST.format(
        root=str(tmp_path).replace("\\", "\\\\"),
        good_path=str(good).replace("\\", "\\\\"),
    )
    result = _run(code)
    assert result.returncode == 0, (
        f"Expected 0 exit, got {result.returncode}.\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_strict_github_write_not_allowed_exits_nonzero(tmp_path):
    """In strict mode with allow_github_write=False, .github/ write exits non-zero."""
    code = _GITHUB_WRITE_NOT_ALLOWED_STRICT.format(
        root=str(tmp_path).replace("\\", "\\\\"),
    )
    result = _run(code)
    assert result.returncode != 0, (
        f"Expected non-zero exit.\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_strict_github_write_allowed_exits_zero(tmp_path):
    """In strict mode with allow_github_write=True, .github/ write succeeds."""
    code = _GITHUB_WRITE_ALLOWED_STRICT.format(
        root=str(tmp_path).replace("\\", "\\\\"),
    )
    result = _run(code)
    assert result.returncode == 0, (
        f"Expected 0 exit.\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_strict_mode_policy_violation_is_runtime_error(tmp_path):
    """PolicyViolation must be a RuntimeError subclass (contract check)."""
    from rgen.fs_policy import PolicyViolation
    assert issubclass(PolicyViolation, RuntimeError)


def test_non_strict_write_outside_whitelist_does_not_raise(tmp_path):
    """Non-strict mode must NOT raise — only warn."""
    import warnings
    from rgen.fs_policy import FSPolicy
    policy = FSPolicy(project_root=tmp_path, strict=False)
    bad = tmp_path / "outside" / "file.txt"
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        policy.write_file(bad, "x")
    assert any("whitelist" in str(x.message) for x in w)
