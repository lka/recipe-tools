# -*- coding: utf-8 -*-
"""Tests für die image_selector Tool-Funktionen."""

import os
import tempfile

import pytest
from PIL import Image

from recipe_processor.tools.image_selector import tools
from recipe_processor.tools.image_selector.tools import (
    _build_export_response,
    _resolve_image_path,
    get_selection_result,
    get_working_directory,
    list_exported_regions,
    select_image_regions,
)
from recipe_processor.tools.image_selector.web_gui import WebImageSelectorGUI


def _make_image(tmp_path, name="test.png", size=(400, 300), color="red"):
    """Hilfsfunktion: erstellt ein Testbild und gibt den Pfad zurueck."""
    path = tmp_path / name
    Image.new("RGB", size, color=color).save(str(path))
    return str(path)


class TestResolveImagePath:
    """Tests für _resolve_image_path."""

    def test_none_returns_none(self):
        assert _resolve_image_path(None) is None

    def test_empty_string_returns_none(self):
        assert _resolve_image_path("") is None

    def test_nonexistent_absolute_path_returns_error(self):
        result = _resolve_image_path("/nicht/vorhanden/bild.png")
        assert result.startswith("Fehler")
        assert "nicht gefunden" in result

    def test_existing_file_returns_path(self, tmp_path):
        img = tmp_path / "test.png"
        img.write_bytes(b"\x89PNG")
        result = _resolve_image_path(str(img))
        assert result == str(img)

    def test_relative_path_resolved(self, tmp_path, monkeypatch):
        img = tmp_path / "bild.png"
        img.write_bytes(b"\x89PNG")
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = _resolve_image_path("bild.png")
        assert result == str(img)


class TestBuildExportResponse:
    """Tests für _build_export_response."""

    def test_foto_entry(self):
        files = [{"type": "foto", "region": 1, "file": "/tmp/r1_foto.png"}]
        result = _build_export_response(files, 1, "/tmp")
        assert "FOTO" in result
        assert "r1_foto.png" in result

    def test_text_entry(self, tmp_path):
        text_file = tmp_path / "r1_text.txt"
        text_file.write_text("Testzutat", encoding="utf-8")
        files = [
            {
                "type": "text",
                "region": 1,
                "image_file": str(tmp_path / "r1_text.png"),
                "text_file": str(text_file),
            }
        ]
        result = _build_export_response(files, 1, str(tmp_path))
        assert "TEXT" in result
        assert "full_recipe_text" in result
        assert "Testzutat" in result

    def test_empty_files(self):
        result = _build_export_response([], 0, "/tmp")
        assert "0 Bereiche" in result


class TestListExportedRegions:
    """Tests für list_exported_regions."""

    def test_empty_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = list_exported_regions()
        assert "keine Dateien gefunden" in result

    def test_lists_png_and_txt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        (tmp_dir / "region_1.png").write_bytes(b"\x89PNG")
        (tmp_dir / "region_1.txt").write_text("text", encoding="utf-8")
        (tmp_dir / "other.jpg").write_bytes(b"\xff\xd8")  # wird ignoriert

        result = list_exported_regions()
        assert "region_1.png" in result
        assert "region_1.txt" in result
        assert "other.jpg" not in result


class TestGetWorkingDirectory:
    """Tests für get_working_directory."""

    def test_returns_working_directory_prefix(self):
        result = get_working_directory()
        assert result.startswith("Working Directory: ")

    def test_respects_env_variable(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = get_working_directory()
        assert str(tmp_path) in result


class TestSelectImageRegions:
    """Tests für select_image_regions (nicht-blockierender Start)."""

    def test_returns_error_for_missing_image(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = select_image_regions(str(tmp_path / "nope.png"))
        assert result.startswith("Fehler")
        assert tools._active_selection is None

    def test_starts_selection_without_blocking(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        monkeypatch.setattr(tools, "_active_selection", None)
        img_path = _make_image(tmp_path)

        class _NoUiGUI(WebImageSelectorGUI):
            def __init__(self, image_path=None, working_dir=None, create_ui=True):
                super().__init__(image_path, working_dir, create_ui=False)

        monkeypatch.setattr(tools, "ImageSelectorGUI", _NoUiGUI)

        result = select_image_regions(img_path)

        assert "get_selection_result" in result
        assert tools._active_selection is not None
        assert tools._active_selection.images_data[0]["original_path"] == img_path


class TestGetSelectionResult:
    """Tests für get_selection_result."""

    def test_no_active_selection(self, monkeypatch):
        monkeypatch.setattr(tools, "_active_selection", None)
        result = get_selection_result()
        assert "Keine laufende Auswahl" in result

    def test_pending_selection(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        monkeypatch.setattr(tools, "_active_selection", gui)

        result = get_selection_result()

        assert "noch nicht abgeschlossen" in result
        assert tools._active_selection is gui

    def test_cancelled_selection(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._cancel_api()
        monkeypatch.setattr(tools, "_active_selection", gui)

        result = get_selection_result()

        assert "abgebrochen" in result
        assert tools._active_selection is None

    def test_completed_selection_exports_regions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._save_region_api(
            {"x1": 10.0, "y1": 10.0, "x2": 200.0, "y2": 150.0, "mode": "foto"}
        )
        gui._finish_api()
        monkeypatch.setattr(tools, "_active_selection", gui)

        result = get_selection_result()

        assert "Erfolgreich" in result
        assert tools._active_selection is None
