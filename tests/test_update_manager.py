from __future__ import annotations

from pathlib import Path

from core import update_manager


def test_get_update_status_flags_behind_default_branch(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    monkeypatch.setattr(update_manager, "_repo_root", lambda: repo)

    def fake_git(args: list[str], cwd: Path, timeout: int = 20):
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "feat/my-work", ""
        if args == ["rev-parse", "--short", "HEAD"]:
            return 0, "abc1234", ""
        if args == ["remote", "show", "origin"]:
            return 0, "  HEAD branch: main", ""
        if args == ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]:
            return 0, "origin/main", ""
        if args == ["rev-list", "--left-right", "--count", "HEAD...origin/feat/my-work"]:
            return 0, "0 0", ""
        if args == ["rev-list", "--left-right", "--count", "HEAD...origin/main"]:
            return 0, "0 2", ""
        if args[:3] == ["fetch", "--quiet", "origin"]:
            return 0, "", ""
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(update_manager, "_git", fake_git)

    status = update_manager.get_update_status(refresh=False)

    assert status["status"] == "outdated"
    assert status["update_available"] is True
    assert status["behind_commits"] == 0
    assert status["behind_default_commits"] == 2
    assert status["default_branch"] == "main"


def test_manual_update_blocks_when_only_default_branch_is_behind(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)

    monkeypatch.setattr(update_manager, "_repo_root", lambda: repo)

    def fake_git(args: list[str], cwd: Path, timeout: int = 20):
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return 0, "feat/my-work", ""
        if args == ["rev-parse", "--short", "HEAD"]:
            return 0, "abc1234", ""
        if args == ["remote", "show", "origin"]:
            return 0, "  HEAD branch: main", ""
        if args == ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"]:
            return 0, "origin/main", ""
        if args[:3] == ["fetch", "--quiet", "origin"]:
            return 0, "", ""
        if args == ["rev-list", "--left-right", "--count", "HEAD...origin/feat/my-work"]:
            return 0, "0 0", ""
        if args == ["rev-list", "--left-right", "--count", "HEAD...origin/main"]:
            return 0, "0 1", ""
        if args == ["status", "--porcelain"]:
            return 0, "", ""
        if args == ["pull", "--ff-only"]:
            raise AssertionError("pull should not run when only default branch is behind")
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(update_manager, "_git", fake_git)

    result = update_manager.manual_update(confirm=True)

    assert result["updated"] is False
    assert result["status"] == "needs_default_branch_sync"
    assert result["details"]["behind_default_commits"] == 1
