# i18n Guide

## Goal

Define a predictable layout for localized knowledge base assets used by the generation pipeline.

## Directory Layout

For each pattern under `knowledge_base/`, store localized content under an `i18n/` folder:

- `knowledge_base/<pattern>/i18n/en/`
- `knowledge_base/<pattern>/i18n/it/`
- Optional future languages: `es`, `fr`, others.

Current patterns in this repository:

- `knowledge_base/node_ts/i18n/`
- `knowledge_base/psm_stack/i18n/`
- `knowledge_base/python_api/i18n/`

## Recommended Conventions

- Keep English (`en`) as the default fallback language.
- Keep identical file names across languages when content is equivalent.
- Preserve placeholders and template variables exactly across translations.
- Avoid hardcoding locale-specific operational data.

## Migration Notes

This repository still supports the legacy non-i18n layout for backward compatibility.
During migration:

1. Add localized files under `i18n/<lang>/`.
2. Keep legacy files unchanged until all consumers are updated.
3. Validate generated output for each language before removing legacy paths.

## Validation Checklist

- `i18n/` directory exists for each pattern.
- `en/` and `it/` folders are present.
- Localization placeholders are preserved.
- Fallback to `en` works when target language is missing.

## Related Files

- `rgen/language_detector.py`
- `rgen/template_localizer.py`
- `tests/test_language_detector.py`
- `tests/test_template_localizer.py`
- `tests/test_cli_language_integration.py`
