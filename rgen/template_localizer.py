"""
Template localizer for AgentPilot Orchestrator projects.

Loads and localizes agent templates in target language with fallback to English.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TemplateLocalizer:
    """
    Localize templates to target language with intelligent fallback.

    Supports: Italian (it), English (en), Spanish (es), French (fr).
    Falls back to English if target language template missing.
    """

    # Language-specific metadata for template substitution
    LANGUAGE_METADATA = {
        "it": {
            "name": "Italian",
            "tone": "Professionale, formale e con attenzione ai dettagli",
            "examples_prefix": "Esempi:",
            "requirements_prefix": "Requisiti:",
            "best_practices_prefix": "Best practice:",
        },
        "en": {
            "name": "English",
            "tone": "Professional, concise, and detail-oriented",
            "examples_prefix": "Examples:",
            "requirements_prefix": "Requirements:",
            "best_practices_prefix": "Best practices:",
        },
        "es": {
            "name": "Spanish",
            "tone": "Profesional, formal y atento a los detalles",
            "examples_prefix": "Ejemplos:",
            "requirements_prefix": "Requisitos:",
            "best_practices_prefix": "Mejores prácticas:",
        },
        "fr": {
            "name": "French",
            "tone": "Professionnel, formel et attentif aux détails",
            "examples_prefix": "Exemples:",
            "requirements_prefix": "Exigences:",
            "best_practices_prefix": "Bonnes pratiques:",
        },
    }

    def __init__(self, language: str, fallback: str = "en"):
        """
        Initialize template localizer.

        Args:
            language: Target language (it/en/es/fr)
            fallback: Fallback language if target missing (default: en)
        """
        self.language = language if language in self.LANGUAGE_METADATA else fallback
        self.fallback = fallback

    def load_template(
        self,
        pattern: str,
        agent_role: str,
        kb_root: str | Path | None = None,
    ) -> str:
        """
        Load agent template in target language.

        Falls back to fallback language if target language template missing.

        Args:
            pattern: Knowledge base pattern (e.g., "psm_stack", "python_api")
            agent_role: Agent role (e.g., "backend", "database")
            kb_root: Knowledge base root directory (default: ./knowledge_base)

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template not found in target or fallback languages
        """
        if kb_root is None:
            kb_root = Path("knowledge_base")
        else:
            kb_root = Path(kb_root)

        # Build paths
        target_path = (
            kb_root / pattern / "i18n" / self.language / "esperti" / f"esperto_{agent_role}.template.md"
        )
        fallback_path = (
            kb_root / pattern / "i18n" / self.fallback / "esperti" / f"esperto_{agent_role}.template.md"
        )

        # Try target language first
        if target_path.exists():
            return target_path.read_text(encoding="utf-8")

        # Fallback to EN if different from target
        if self.language != self.fallback and fallback_path.exists():
            return fallback_path.read_text(encoding="utf-8")

        # Not found anywhere
        raise FileNotFoundError(
            f"Template not found for agent '{agent_role}' in pattern '{pattern}'. "
            f"Tried: {target_path}, {fallback_path}"
        )

    def substitute_language_context(
        self,
        template: str,
        vars: dict[str, Any] | None = None,
    ) -> str:
        """
        Substitute language-specific variables in template.

        Replaces placeholders:
        - {{LANGUAGE}} → language name ("Italian", "English", etc.)
        - {{TONE}} → communication tone
        - {{EXAMPLES_PREFIX}} → "Examples:" or equivalent
        - {{REQUIREMENTS_PREFIX}} → "Requirements:" or equivalent
        - {{BEST_PRACTICES_PREFIX}} → "Best practices:" or equivalent
        - Other {{VAR}} from vars dict

        Args:
            template: Template string with placeholders
            vars: Optional additional variables to substitute

        Returns:
            Substituted template string
        """
        metadata = self.LANGUAGE_METADATA.get(self.language, self.LANGUAGE_METADATA[self.fallback])

        # Build complete substitution dict
        localized_vars = {
            "LANGUAGE": metadata["name"],
            "TONE": metadata["tone"],
            "EXAMPLES_PREFIX": metadata["examples_prefix"],
            "REQUIREMENTS_PREFIX": metadata["requirements_prefix"],
            "BEST_PRACTICES_PREFIX": metadata["best_practices_prefix"],
        }

        # Add custom vars (they override language metadata)
        if vars:
            localized_vars.update(vars)

        # Perform substitutions
        result = template
        for var_name, var_value in localized_vars.items():
            placeholder = f"{{{{{var_name}}}}}"
            result = result.replace(placeholder, str(var_value))

        return result

    def localize_template(
        self,
        pattern: str,
        agent_role: str,
        vars: dict[str, Any] | None = None,
        kb_root: str | Path | None = None,
    ) -> str:
        """
        Load and localize a template in one call.

        Combines load_template() and substitute_language_context().

        Args:
            pattern: Knowledge base pattern
            agent_role: Agent role
            vars: Optional additional variables to substitute
            kb_root: Knowledge base root directory

        Returns:
            Fully localized template string

        Raises:
            FileNotFoundError: If template not found
        """
        template = self.load_template(pattern, agent_role, kb_root)
        return self.substitute_language_context(template, vars)

    def get_language_name(self) -> str:
        """Get human-readable name of current language."""
        return self.LANGUAGE_METADATA[self.language]["name"]

    @classmethod
    def is_language_supported(cls, language: str) -> bool:
        """
        Check if language is supported.

        Args:
            language: Language code

        Returns:
            True if supported, False otherwise
        """
        return language in cls.LANGUAGE_METADATA

    @classmethod
    def get_supported_languages(cls) -> list[str]:
        """Get list of supported language codes."""
        return sorted(cls.LANGUAGE_METADATA.keys())

    @classmethod
    def get_language_display_name(cls, language: str) -> str:
        """Get human-readable name for language code."""
        if language in cls.LANGUAGE_METADATA:
            return cls.LANGUAGE_METADATA[language]["name"]
        return "Unknown"
