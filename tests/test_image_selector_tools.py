# -*- coding: utf-8 -*-
"""Tests für die image_selector Tool-Funktionen."""

import os
import tempfile

import pytest

from recipe_processor.tools.image_selector.tools import (
    _build_export_response,
    _resolve_image_path,
    get_working_directory,
    list_exported_regions,
)


class TestResolveImagePath:
    """Tests für _resolve_image_path."""

    def test_none_returns_none(self):
        assert _resolve_image_path(None) is None

    def test_empty_string_returns_none(self):
        assert _resolve_image_path('') is None

    def test_nonexistent_absolute_path_returns_error(self):
        result = _resolve_image_path('/nicht/vorhanden/bild.png')
        assert result.startswith('Fehler')
        assert 'nicht gefunden' in result

    def test_existing_file_returns_path(self, tmp_path):
        img = tmp_path / 'test.png'
        img.write_bytes(b'\x89PNG')
        result = _resolve_image_path(str(img))
        assert result == str(img)

    def test_relative_path_resolved(self, tmp_path, monkeypatch):
        img = tmp_path / 'bild.png'
        img.write_bytes(b'\x89PNG')
        monkeypatch.setenv('IMAGE_SELECTOR_WORKING_DIR', str(tmp_path))
        result = _resolve_image_path('bild.png')
        assert result == str(img)


class TestBuildExportResponse:
    """Tests für _build_export_response."""

    def test_foto_entry(self):
        files = [{'type': 'foto', 'region': 1, 'file': '/tmp/r1_foto.png'}]
        result = _build_export_response(files, 1, '/tmp')
        assert 'FOTO' in result
        assert 'r1_foto.png' in result

    def test_text_entry(self, tmp_path):
        text_file = tmp_path / 'r1_text.txt'
        text_file.write_text('Testzutat', encoding='utf-8')
        files = [
            {
                'type': 'text',
                'region': 1,
                'image_file': str(tmp_path / 'r1_text.png'),
                'text_file': str(text_file),
            }
        ]
        result = _build_export_response(files, 1, str(tmp_path))
        assert 'TEXT' in result
        assert 'full_recipe_text' in result
        assert 'Testzutat' in result

    def test_empty_files(self):
        result = _build_export_response([], 0, '/tmp')
        assert '0 Bereiche' in result


class TestListExportedRegions:
    """Tests für list_exported_regions."""

    def test_empty_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv('IMAGE_SELECTOR_WORKING_DIR', str(tmp_path))
        result = list_exported_regions()
        assert 'keine Dateien gefunden' in result

    def test_lists_png_and_txt(self, tmp_path, monkeypatch):
        monkeypatch.setenv('IMAGE_SELECTOR_WORKING_DIR', str(tmp_path))
        tmp_dir = tmp_path / 'tmp'
        tmp_dir.mkdir()
        (tmp_dir / 'region_1.png').write_bytes(b'\x89PNG')
        (tmp_dir / 'region_1.txt').write_text('text', encoding='utf-8')
        (tmp_dir / 'other.jpg').write_bytes(b'\xff\xd8')  # wird ignoriert

        result = list_exported_regions()
        assert 'region_1.png' in result
        assert 'region_1.txt' in result
        assert 'other.jpg' not in result


class TestGetWorkingDirectory:
    """Tests für get_working_directory."""

    def test_returns_working_directory_prefix(self):
        result = get_working_directory()
        assert result.startswith('Working Directory: ')

    def test_respects_env_variable(self, tmp_path, monkeypatch):
        monkeypatch.setenv('IMAGE_SELECTOR_WORKING_DIR', str(tmp_path))
        result = get_working_directory()
        assert str(tmp_path) in result
