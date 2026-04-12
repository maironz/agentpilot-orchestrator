"""
Unit tests for LanguageDetector — project language detection.

Tests cover:
- Language detection from metadata
- Fallback behavior
- Supported language checks
"""

from __future__ import annotations

import pytest

from rgen.language_detector import LanguageDetector


class TestLanguageDetectorInit:
    """Test detector initialization."""

    def test_init_default_english(self):
        """Test default language is English."""
        detector = LanguageDetector()
        assert detector.default == "en"

    def test_init_custom_default(self):
        """Test custom default language."""
        detector = LanguageDetector(default="it")
        assert detector.default == "it"


class TestLanguageDetection:
    """Test language detection strategies."""

    def test_detect_from_metadata(self):
        """Test detection from metadata dict."""
        detector = LanguageDetector()
        metadata = {"language": "it"}

        lang = detector.detect(metadata=metadata)
        assert lang == "it"

    def test_detect_default_fallback(self):
        """Test fallback to default when no detection source."""
        detector = LanguageDetector()

        lang = detector.detect(project_path=None, metadata=None)
        assert lang == "en"


class TestLanguageConstants:
    """Test language constants and class methods."""

    def test_supported_langs_list(self):
        """Test supported languages list."""
        langs = LanguageDetector.SUPPORTED_LANGS
        assert set(langs) == {"it", "en", "es", "fr"}

    def test_is_supported_true(self):
        """Test is_supported for valid languages."""
        for lang in LanguageDetector.SUPPORTED_LANGS:
            assert LanguageDetector.is_supported(lang)

    def test_is_supported_false(self):
        """Test is_supported for invalid languages."""
        assert not LanguageDetector.is_supported("de")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
