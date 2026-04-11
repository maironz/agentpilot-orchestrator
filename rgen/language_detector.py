"""
Language detector for AgentPilot Orchestrator projects.

Auto-detects project documentation language from README, package metadata,
or defaults to English.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class LanguageDetector:
    """
    Detect project documentation language for agent template localization.

    Supports: Italian (it), English (en), Spanish (es), French (fr).
    Falls back to English if detection is uncertain.
    """

    SUPPORTED_LANGS = ["it", "en", "es", "fr"]

    # Language detection patterns (keywords in README, metadata, etc.)
    DETECTION_PATTERNS = {
        "it": ["italiano", "ingegneria", "progetto", "documentazione", "configurazione", "readme.it"],
        "es": ["español", "ingeniería", "proyecto", "documentación", "configuración", "readme.es"],
        "fr": ["français", "ingénierie", "projet", "documentation", "configuration", "readme.fr"],
        "en": ["english", "engineering", "project", "documentation", "configuration", "readme.en"],
    }

    def __init__(self, default: str = "en"):
        """
        Initialize language detector.

        Args:
            default: Default language if detection fails (default: "en")
        """
        self.default = default if default in self.SUPPORTED_LANGS else "en"

    def detect(
        self,
        project_path: str | Path | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Detect project language from multiple sources.

        Detection strategy (in order):
        1. Metadata dict (if provided with language key)
        2. Project README.md or README.it.md, etc. (file presence)
        3. Project README content (keyword analysis)
        4. Default to English

        Args:
            project_path: Path to project directory
            metadata: Optional metadata dict that may contain "language" key

        Returns:
            Language code: "it", "en", "es", or "fr"
        """
        # Strategy 1: Check metadata dict
        if metadata:
            if isinstance(metadata, dict):
                if "language" in metadata:
                    lang = metadata["language"]
                    if lang in self.SUPPORTED_LANGS:
                        return lang

        # Strategy 2: Check for language-specific README files
        if project_path:
            project_path = Path(project_path)
            for lang in self.SUPPORTED_LANGS:
                readme_path = project_path / f"README.{lang}.md"
                if readme_path.exists():
                    return lang

        # Strategy 3: Analyze README.md content
        if project_path:
            project_path = Path(project_path)
            readme_path = project_path / "README.md"
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding="utf-8").lower()
                    for lang, patterns in self.DETECTION_PATTERNS.items():
                        matches = sum(1 for pattern in patterns if pattern.lower() in content)
                        if matches > 0:
                            return lang
                except Exception:
                    pass

        # Fallback: return default
        return self.default

    def get_language_name(self, language: str) -> str:
        """Get human-readable name for language code."""
        names = {
            "it": "Italian",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
        }
        return names.get(language, "Unknown")

    @classmethod
    def is_supported(cls, language: str) -> bool:
        """Check if language is supported."""
        return language in cls.SUPPORTED_LANGS

    @classmethod
    def get_supported(cls) -> list[str]:
        """Get list of supported language codes."""
        return cls.SUPPORTED_LANGS.copy()
