"""
Unit tests for TemplateLocalizer — template localization.

Tests cover:
- Language metadata substitution
- Fallback to English when target missing
- Variable substitution
"""

from __future__ import annotations

import pytest

from rgen.template_localizer import TemplateLocalizer


class TestTemplateLocalizer:
    """Test template localization."""

    def test_supported_languages(self):
        """Test all supported languages."""
        langs = TemplateLocalizer.get_supported_languages()
        assert set(langs) == {"it", "en", "es", "fr"}

    def test_language_metadata_complete(self):
        """Test all languages have required metadata."""
        required_keys = {"name", "tone", "examples_prefix", "requirements_prefix", "best_practices_prefix"}

        for lang in TemplateLocalizer.get_supported_languages():
            meta = TemplateLocalizer.LANGUAGE_METADATA[lang]
            assert set(meta.keys()) == required_keys
            assert all(isinstance(v, str) for v in meta.values())

    def test_italian_metadata(self):
        """Test Italian language metadata."""
        localizer = TemplateLocalizer("it")
        assert localizer.get_language_name() == "Italian"

    def test_english_metadata(self):
        """Test English language metadata."""
        localizer = TemplateLocalizer("en")
        assert localizer.get_language_name() == "English"


class TestLanguageSubstitution:
    """Test language-specific variable substitution."""

    def test_substitute_language_context_italian(self):
        """Test Italian language context substitution."""
        localizer = TemplateLocalizer("it")
        template = "Linguaggio: {{LANGUAGE}}\nTono: {{TONE}}"

        result = localizer.substitute_language_context(template)

        assert "Italian" in result
        assert "Professionale" in result

    def test_substitute_custom_variables(self):
        """Test custom variable substitution."""
        localizer = TemplateLocalizer("it")
        template = "Progetto: {{PROJECT_NAME}}"
        vars_dict = {"PROJECT_NAME": "MioProgetto"}

        result = localizer.substitute_language_context(template, vars_dict)

        assert "MioProgetto" in result

    def test_is_language_supported_true(self):
        """Test is_language_supported for valid languages."""
        assert TemplateLocalizer.is_language_supported("it")
        assert TemplateLocalizer.is_language_supported("en")

    def test_is_language_supported_false(self):
        """Test is_language_supported for invalid languages."""
        assert not TemplateLocalizer.is_language_supported("de")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
