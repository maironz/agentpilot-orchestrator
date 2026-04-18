from __future__ import annotations

from pathlib import Path

import tomllib


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    pyproject_path = repo_root / "pyproject.toml"
    version_path = repo_root / "VERSION"

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data["project"]["version"]

    version_path.write_text(f"{version}\n", encoding="utf-8")
    print(f"Synced VERSION={version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
