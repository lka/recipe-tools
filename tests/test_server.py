# -*- coding: utf-8 -*-
"""Tests für den MCP-Server."""

from recipe_processor.server import mcp
from recipe_processor.tools.prompt import RECIPE_PROMPT


class TestMcpServerSetup:
    """Tests für die MCP-Server-Konfiguration."""

    def test_server_name(self):
        assert mcp.name == 'PromptServer'

    def test_server_has_tools(self):
        tool_names = list(mcp._tool_manager._tools)
        assert 'get_recipe_prompt' in tool_names
        assert 'select_image_regions_tool' in tool_names
        assert 'list_exported_regions_tool' in tool_names
        assert 'get_working_directory_tool' in tool_names

    def test_server_has_prompts(self):
        prompt_names = list(mcp._prompt_manager._prompts)
        assert 'generate_recipe' in prompt_names


class TestGenerateRecipe:
    """Tests für den generate_recipe Prompt."""

    def test_returns_recipe_prompt(self):
        prompt = mcp._prompt_manager._prompts['generate_recipe']
        result = prompt.fn()
        assert result == RECIPE_PROMPT

    def test_return_type_is_string(self):
        prompt = mcp._prompt_manager._prompts['generate_recipe']
        assert isinstance(prompt.fn(), str)


class TestGetRecipePrompt:
    """Tests für das get_recipe_prompt Tool."""

    def test_contains_recipe_prompt(self):
        tool = mcp._tool_manager._tools['get_recipe_prompt']
        result = tool.fn()
        assert RECIPE_PROMPT in result

    def test_contains_instruction_wrapper(self):
        tool = mcp._tool_manager._tools['get_recipe_prompt']
        result = tool.fn()
        assert 'ANWEISUNG FÜR DIE WEITERE BEARBEITUNG' in result
        assert 'direkte Arbeitsanweisung' in result
