"""Tests for rgen/config.py — AgentPilot workspace configuration."""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

from rgen.config import AgentPilotConfig, load, save, _CONFIG_REL


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------


def test_load_defaults_no_file(tmp_path):
    """No config.yaml → all defaults returned."""
    cfg = load(project_root=tmp_path)
    assert cfg == AgentPilotConfig()
    assert cfg.fs_strict is False
    assert cfg.allow_github_write is False
    assert cfg.track_artifacts is False
    assert cfg.cleanup_on_exit is False


def test_load_overrides_keys(tmp_path):
    """Keys present in file override defaults."""
    pytest.importorskip("yaml")
    import yaml

    cfg_path = tmp_path / _CONFIG_REL
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(
        yaml.dump({"fs_strict": True, "allow_github_write": True}), encoding="utf-8"
    )

    cfg = load(project_root=tmp_path)
    assert cfg.fs_strict is True
    assert cfg.allow_github_write is True
    # Unset keys keep defaults
    assert cfg.track_artifacts is False
    assert cfg.cleanup_on_exit is False


def test_load_unknown_keys_ignored(tmp_path):
    """Unknown keys in config file are silently ignored."""
    pytest.importorskip("yaml")
    import yaml

    cfg_path = tmp_path / _CONFIG_REL
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml.dump({"unknown_future_key": 42}), encoding="utf-8")

    cfg = load(project_root=tmp_path)
    assert cfg == AgentPilotConfig()


def test_load_invalid_yaml_warns_and_defaults(tmp_path):
    """Invalid YAML content → warning emitted + defaults returned."""
    pytest.importorskip("yaml")

    cfg_path = tmp_path / _CONFIG_REL
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text("{{ not: valid: yaml: [", encoding="utf-8")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        cfg = load(project_root=tmp_path)

    assert cfg == AgentPilotConfig()
    assert any("could not read" in str(x.message) for x in w)


def test_load_non_bool_value_uses_default(tmp_path):
    """Non-bool values for known keys are ignored (default kept)."""
    pytest.importorskip("yaml")
    import yaml

    cfg_path = tmp_path / _CONFIG_REL
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml.dump({"fs_strict": "yes_please"}), encoding="utf-8")

    cfg = load(project_root=tmp_path)
    assert cfg.fs_strict is False  # "yes_please" is str, not bool → skip


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------


def test_save_creates_file(tmp_path):
    """save() creates .agentpilot/config.yaml."""
    pytest.importorskip("yaml")

    cfg = AgentPilotConfig(fs_strict=True, cleanup_on_exit=True)
    save(cfg, project_root=tmp_path)

    cfg_path = tmp_path / _CONFIG_REL
    assert cfg_path.is_file()


def test_save_and_reload_roundtrip(tmp_path):
    """save() + load() round-trips all four fields."""
    pytest.importorskip("yaml")

    original = AgentPilotConfig(
        fs_strict=True,
        allow_github_write=True,
        track_artifacts=True,
        cleanup_on_exit=True,
    )
    save(original, project_root=tmp_path)
    reloaded = load(project_root=tmp_path)
    assert reloaded == original


def test_save_creates_parent_dirs(tmp_path):
    """save() creates .agentpilot/ even if it doesn't exist yet."""
    pytest.importorskip("yaml")

    assert not (tmp_path / ".agentpilot").exists()
    save(AgentPilotConfig(), project_root=tmp_path)
    assert (tmp_path / _CONFIG_REL).is_file()
