"""Data models for routing-generator."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ProjectProfile:
    """Describes the target project for routing generation."""
    project_name: str
    target_path: Path
    pattern_id: str
    template_vars: dict[str, str] = field(default_factory=dict)
    tech_stack: list[str] = field(default_factory=list)
    domain_keywords: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.target_path = Path(self.target_path)


@dataclass
class GenerationResult:
    """Result of a routing system generation run."""
    success: bool
    files_written: list[Path] = field(default_factory=list)
    files_skipped: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    backup_dir: Path | None = None

    @property
    def total_files(self) -> int:
        return len(self.files_written) + len(self.files_skipped)


@dataclass
class CheckReport:
    """Result of post-generation self-check."""
    passed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def overall(self) -> bool:
        return len(self.errors) == 0
