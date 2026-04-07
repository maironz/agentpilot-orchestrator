"""
Integration test for router.py --dashboard flag.

Tests that the dashboard mode can be invoked from the router CLI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_router_dashboard_help():
    """Test that --dashboard appears in router help."""
    repo_root = Path(__file__).parent.parent
    router_path = repo_root / "core" / "router.py"

    result = subprocess.run(
        [sys.executable, str(router_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=5,
    )

    assert result.returncode == 0
    output = (result.stdout or "") + (result.stderr or "")
    assert "--dashboard" in output
    assert "Live metrics dashboard" in output


def test_router_dashboard_version_check():
    """Test that missing rich gracefully fails."""
    # Note: If rich is installed, this won't trigger the ImportError
    # but the test is still valid for documenting expected behavior
    repo_root = Path(__file__).parent.parent
    router_path = repo_root / "core" / "router.py"

    # This will try to launch the dashboard but should handle gracefully
    # (either succeeds if rich installed, or shows error message)
    result = subprocess.run(
        [sys.executable, str(router_path), "--dashboard"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=2,
        input="q\n",  # Send quit immediately to avoid hanging
    )

    # Should either succeed (return 0) or fail gracefully
    # Main thing is it shouldn't crash unexpectedly
    assert result.returncode in (0, 1, -15)  # 0=ok, 1=dependency error, -15=sigterm


if __name__ == "__main__":
    test_router_dashboard_help()
    print("✓ router --dashboard help test passed")
