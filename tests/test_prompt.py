# -*- coding: utf-8 -*-
"""Tests fuer das Prompt-Template."""

from recipe_processor.tools.prompt import RECIPE_PROMPT


class TestRecipePrompt:
    """Tests fuer RECIPE_PROMPT."""

    def test_prompt_is_string(self):
        assert isinstance(RECIPE_PROMPT, str)

    def test_prompt_not_empty(self):
        assert len(RECIPE_PROMPT.strip()) > 0

    def test_prompt_contains_workflow_sections(self):
        for section in (
            "## Verfuegbare Tools",
            "## Verzeichnisse",
            "## Workflow",
            "### 1. Bildauswahl & OCR",
            "### 2. OCR-Text interpretieren und strukturieren",
            "### 3. HTML erzeugen",
            "### 4. Qualitaetspruefung",
            "### 5. Weitere Rezepte?",
        ):
            assert section in RECIPE_PROMPT, f"Abschnitt fehlt: {section}"

    def test_prompt_contains_available_tools(self):
        for tool in (
            "select_image_regions_tool",
            "get_working_directory_tool",
            "build_recipe_html_tool",
        ):
            assert tool in RECIPE_PROMPT, f"Tool fehlt: {tool}"

    def test_prompt_contains_recipe_fields(self):
        for field in (
            "recipe_name",
            "ingredients",
            "instructions",
            "source",
            "category",
        ):
            assert field in RECIPE_PROMPT, f"Feld fehlt: {field}"

    def test_prompt_contains_ocr_hints(self):
        assert "OCR" in RECIPE_PROMPT
