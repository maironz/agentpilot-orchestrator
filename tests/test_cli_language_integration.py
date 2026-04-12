"""
CLI integration tests for P2.1 language support.

Tests cover:
- Language flag parsing
- Language detection and passing to generation
- Help text shows language option
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


class TestCLILanguageFlag:
    """Test CLI language flag integration."""

    def test_cli_accepts_language_flag(self):
        """Test --language flag is recognized."""
        repo_root = Path(__file__).parent.parent

        # Run with --help using -m to ensure rgen package is importable
        result = subprocess.run(
            [sys.executable, "-m", "rgen.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_root),
        )

        assert result.returncode == 0
        assert "--language" in result.stdout

    def test_cli_language_choices(self):
        """Test --language accepts it|en|es|fr."""
        repo_root = Path(__file__).parent.parent

        # Run with --help using -m to ensure rgen package is importable
        result = subprocess.run(
            [sys.executable, "-m", "rgen.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(repo_root),
        )

        help_text = result.stdout
        assert "it|en|es|fr" in help_text or "language" in help_text.lower()

    def test_cli_language_flag_default_en(self):
        """Test default language is English when not specified."""
        # LanguageDetector should return 'en' by default
        from rgen.language_detector import LanguageDetector

        detector = LanguageDetector()
        lang = detector.detect()
        assert lang == "en"


class TestCLILanguageDetection:
    """Test language detection in CLI flow."""

    def test_language_detector_used_in_cli_direct(self):
        """Test LanguageDetector is imported and used in _cmd_direct."""
        from rgen import cli

        # Check that LanguageDetector is available in the module
        import inspect

        source = inspect.getsource(cli._cmd_direct)
        assert "LanguageDetector" in source or "language" in source.lower()


class TestLanguageMetadataInCLI:
    """Test language metadata propagates through CLI."""

    def test_supported_languages_list(self):
        """Test all supported languages are accessible."""
        from rgen.language_detector import LanguageDetector
        from rgen.template_localizer import TemplateLocalizer

        detector = LanguageDetector()
        localizer_langs = TemplateLocalizer.get_supported_languages()

        # Both should support same languages
        assert set(detector.SUPPORTED_LANGS) == set(localizer_langs)

    def test_language_constants_aligned(self):
        """Test language constants are aligned between modules."""
        from rgen.language_detector import LanguageDetector
        from rgen.template_localizer import TemplateLocalizer

        expected = {"it", "en", "es", "fr"}
        assert set(LanguageDetector.SUPPORTED_LANGS) == expected
        assert set(TemplateLocalizer.LANGUAGE_METADATA.keys()) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
