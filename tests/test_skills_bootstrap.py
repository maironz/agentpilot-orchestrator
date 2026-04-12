from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / ".github" / "skills.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _prepare_workspace(tmp_path: Path) -> tuple[Path, Path]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    github_dir = workspace / ".github"
    github_dir.mkdir()
    shutil.copy2(SCRIPT_PATH, github_dir / "skills.sh")

    fakebin = workspace / ".fakebin"
    fakebin.mkdir()
    return workspace, fakebin


def _run_script(workspace: Path, command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-lc", f'export PATH="$(pwd)/.fakebin:$PATH"; {command}'],
        cwd=workspace,
        text=True,
        capture_output=True,
        check=False,
    )


def test_setup_skips_when_skill_already_present(tmp_path: Path) -> None:
    workspace, fakebin = _prepare_workspace(tmp_path)
    existing_skill = workspace / ".claude" / "skills" / "existing" / "SKILL.md"
    existing_skill.parent.mkdir(parents=True)
    existing_skill.write_text("# existing\n", encoding="utf-8")

    _write_executable(
        fakebin / "npx",
        "#!/usr/bin/env bash\n"
        "touch \"$PWD/.npx_called\"\n"
        "exit 0\n",
    )

    result = _run_script(workspace, "bash .github/skills.sh setup-anthropic-skills")

    assert result.returncode == 0
    assert "already configured" in result.stdout
    assert not (workspace / ".npx_called").exists()


def test_setup_works_when_script_is_sourced(tmp_path: Path) -> None:
    workspace, _ = _prepare_workspace(tmp_path)

    result = _run_script(
        workspace,
        "source .github/skills.sh; type setup-anthropic-skills > /dev/null; echo sourced-ok",
    )

    assert result.returncode == 0
    assert "sourced-ok" in result.stdout


def test_setup_installs_with_npx_when_available(tmp_path: Path) -> None:
    workspace, fakebin = _prepare_workspace(tmp_path)

    _write_executable(
        fakebin / "npx",
        "#!/usr/bin/env bash\n"
        "mkdir -p \"$PWD/.claude/skills/from-npx\"\n"
        "printf '# from npx\\n' > \"$PWD/.claude/skills/from-npx/SKILL.md\"\n"
        "exit 0\n",
    )

    result = _run_script(workspace, "bash .github/skills.sh setup-anthropic-skills")

    assert result.returncode == 0
    assert "installed via skills.sh" in result.stdout
    assert (workspace / ".claude" / "skills" / "from-npx" / "SKILL.md").exists()


def test_setup_falls_back_to_git_when_npx_fails(tmp_path: Path) -> None:
    workspace, fakebin = _prepare_workspace(tmp_path)

    _write_executable(
        fakebin / "npx",
        "#!/usr/bin/env bash\n"
        "exit 1\n",
    )
    _write_executable(
        fakebin / "git",
        "#!/usr/bin/env bash\n"
        "dest=\"${@: -1}\"\n"
        "mkdir -p \"$dest/.claude/skills/from-git\"\n"
        "printf '# from git\\n' > \"$dest/.claude/skills/from-git/SKILL.md\"\n"
        "exit 0\n",
    )

    result = _run_script(
        workspace,
        "GIT_BIN=git NPX_BIN=npx bash .github/skills.sh setup-anthropic-skills",
    )

    assert result.returncode == 0
    assert "falling back to git clone" in result.stdout
    assert "bootstrapped into" in result.stdout
    assert (workspace / ".claude" / "skills" / "from-git" / "SKILL.md").exists()


def test_setup_force_refresh_replaces_existing_content(tmp_path: Path) -> None:
    workspace, fakebin = _prepare_workspace(tmp_path)
    old_skill = workspace / ".claude" / "skills" / "old-skill" / "SKILL.md"
    old_skill.parent.mkdir(parents=True)
    old_skill.write_text("# old\n", encoding="utf-8")

    _write_executable(
        fakebin / "npx",
        "#!/usr/bin/env bash\n"
        "mkdir -p \"$PWD/.claude/skills/new-skill\"\n"
        "printf '# new\\n' > \"$PWD/.claude/skills/new-skill/SKILL.md\"\n"
        "exit 0\n",
    )

    result = _run_script(workspace, "bash .github/skills.sh setup-anthropic-skills --force")

    assert result.returncode == 0
    assert "Force refresh enabled" in result.stdout
    assert not old_skill.exists()
    assert (workspace / ".claude" / "skills" / "new-skill" / "SKILL.md").exists()
