from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _run_without_site(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-S", str(script)],
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_github_mcp_server_shows_actionable_error_without_mcp_dependency() -> None:
    script = Path(__file__).parent.parent / ".github" / "mcp_server.py"
    result = _run_without_site(script)

    assert result.returncode == 1
    assert "Missing dependency: mcp" in result.stderr
    assert 'pip install "mcp[cli]>=1.0.0"' in result.stderr


def test_core_mcp_server_shows_actionable_error_without_mcp_dependency() -> None:
    script = Path(__file__).parent.parent / "core" / "mcp_server.py"
    result = _run_without_site(script)

    assert result.returncode == 1
    assert "Missing dependency: mcp" in result.stderr
    assert 'pip install "mcp[cli]>=1.0.0"' in result.stderr
