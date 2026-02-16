# -*- coding: utf-8 -*-
"""Tests für das Prompt-Template."""

from recipe_processor.tools.prompt import RECIPE_PROMPT


class TestRecipePrompt:
    """Tests für RECIPE_PROMPT."""

    def test_prompt_is_string(self):
        assert isinstance(RECIPE_PROMPT, str)

    def test_prompt_not_empty(self):
        assert len(RECIPE_PROMPT.strip()) > 0

    def test_prompt_contains_workflow_sections(self):
        for section in (
            '## Verzeichnisse',
            '## Konnektoren',
            '## Workflow',
            '### 0. Vorbereitung',
            '### 1. PDF-Analyse',
            '### 2. Text strukturieren',
            '### 3. Bild verarbeiten',
            '### 4. HTML generieren',
            '### 5. Index aktualisieren',
            '### 6. Qualitätsprüfung',
            '### 7. Protokollierung',
            '### 8. Weitere Rezepte?',
        ):
            assert section in RECIPE_PROMPT, f'Abschnitt fehlt: {section}'

    def test_prompt_contains_required_connectors(self):
        for connector in (
            'filesystem',
            'image-selector',
            'recipe-index',
            'windows-launcher',
            'tesseract',
        ):
            assert connector in RECIPE_PROMPT, f'Konnektor fehlt: {connector}'

    def test_prompt_contains_template_tags(self):
        for tag in (
            '<RECIPE_NAME>',
            '<INGREDIENTS>',
            '<INSTRUCTIONS>',
            '<IMAGE_PATH>',
            '<SOURCE>',
        ):
            assert tag in RECIPE_PROMPT, f'Template-Tag fehlt: {tag}'
