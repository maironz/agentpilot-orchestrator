"""AgentPilot workspace configuration loader/saver.

Reads and writes ``.agentpilot/config.yaml`` (created on first use with
default values).  Writes go directly to the whitelisted ``.agentpilot/``
root, so no :class:`~rgen.fs_policy.FSPolicy` indirection is required here.

Schema
------
fs_strict: false
allow_github_write: false
track_artifacts: false
cleanup_on_exit: false
"""

from __future__ import annotations

import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Union

try:
    import yaml  # PyYAML — optional runtime dependency

    _HAS_YAML = True
except ImportError:  # pragma: no cover
    _HAS_YAML = False

_CONFIG_REL = Path(".agentpilot") / "config.yaml"

_DEFAULTS: dict[str, bool] = {
    "fs_strict": False,
    "allow_github_write": False,
    "track_artifacts": False,
    "cleanup_on_exit": False,
}


@dataclass
class AgentPilotConfig:
    """Validated workspace configuration."""

    fs_strict: bool = False
    allow_github_write: bool = False
    track_artifacts: bool = False
    cleanup_on_exit: bool = False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load(project_root: Union[Path, str, None] = None) -> AgentPilotConfig:
    """Load config from ``.agentpilot/config.yaml``.

    Falls back to defaults when the file is absent, unreadable, or PyYAML is
    not installed.  Unknown keys in the file are silently ignored.
    """
    root = Path(project_root).resolve() if project_root else Path(".").resolve()
    cfg_path = root / _CONFIG_REL
    data: dict = dict(_DEFAULTS)

    if cfg_path.is_file():
        if not _HAS_YAML:
            warnings.warn(
                "agentpilot config: PyYAML not installed — using defaults. "
                "Run: pip install pyyaml",
                stacklevel=2,
            )
        else:
            try:
                with cfg_path.open("r", encoding="utf-8") as fh:
                    loaded = yaml.safe_load(fh) or {}
                if isinstance(loaded, dict):
                    for k in _DEFAULTS:
                        if k in loaded and isinstance(loaded[k], bool):
                            data[k] = loaded[k]
            except Exception as exc:  # noqa: BLE001
                warnings.warn(
                    f"agentpilot config: could not read {cfg_path} — {exc}",
                    stacklevel=2,
                )

    return AgentPilotConfig(**data)


def save(config: AgentPilotConfig, project_root: Union[Path, str, None] = None) -> None:
    """Persist *config* to ``.agentpilot/config.yaml``.

    Creates the ``.agentpilot/`` directory if absent.
    """
    root = Path(project_root).resolve() if project_root else Path(".").resolve()
    cfg_path = root / _CONFIG_REL
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    raw = asdict(config)
    if _HAS_YAML:
        content = yaml.dump(raw, default_flow_style=False, sort_keys=True)
    else:
        # Minimal fallback — produces valid YAML subset
        content = "".join(f"{k}: {str(v).lower()}\n" for k, v in sorted(raw.items()))

    cfg_path.write_text(content, encoding="utf-8")  # fs-policy: ok
