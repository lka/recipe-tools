# -*- coding: utf-8 -*-
"""Tests fuer html_builder."""

import json
import os

import pytest

from recipe_processor.tools.html_builder import (
    _clean_source,
    _expand_je_ingredient,
    _find_recipe_image,
    _fix_quantity_spacing,
    _parse_iso_duration,
    _render_html,
    _sanitize_filename,
    _sum_minutes,
    build_recipe_html,
)

# -- _sanitize_filename --


class TestSanitizeFilename:

    def test_umlaute(self):
        assert _sanitize_filename("Käsekuchen") == "kaesekuchen"

    def test_sz(self):
        assert _sanitize_filename("Süßkartoffel") == "suesskartoffel"

    def test_spaces_to_hyphens(self):
        assert _sanitize_filename("Rote Beete Salat") == "rote-beete-salat"

    def test_special_chars_removed(self):
        result = _sanitize_filename("Crème brûlée (vegan!)")
        assert "(" not in result
        assert "!" not in result

    def test_max_length(self):
        long_name = "A" * 100
        assert len(_sanitize_filename(long_name)) <= 50

    def test_custom_max_length(self):
        assert len(_sanitize_filename("Langer Name", max_length=5)) <= 5

    def test_multiple_spaces(self):
        assert _sanitize_filename("Apfel   Kuchen") == "apfel-kuchen"


# -- _parse_iso_duration --


class TestParseIsoDuration:

    def test_minutes(self):
        assert _parse_iso_duration("30 Min") == "PT30M"

    def test_hours_and_minutes(self):
        assert _parse_iso_duration("1 Std 15 Min") == "PT1H15M"

    def test_hours_only(self):
        assert _parse_iso_duration("2 Stunden") == "PT2H"

    def test_bare_number(self):
        assert _parse_iso_duration("45") == "PT45M"

    def test_empty(self):
        assert _parse_iso_duration("") == ""

    def test_none_like(self):
        assert _parse_iso_duration("keine Angabe") == ""

    def test_minute_singular(self):
        assert _parse_iso_duration("1 Minute") == "PT1M"


# -- _fix_quantity_spacing --


class TestFixQuantitySpacing:

    def test_grams(self):
        assert _fix_quantity_spacing("250g Mehl") == "250 g Mehl"

    def test_already_spaced(self):
        assert _fix_quantity_spacing("250 g Mehl") == "250 g Mehl"

    def test_milliliter(self):
        assert _fix_quantity_spacing("100ml Milch") == "100 ml Milch"

    def test_tablespoon(self):
        assert _fix_quantity_spacing("2EL Oel") == "2 EL Oel"

    def test_decimal(self):
        assert _fix_quantity_spacing("1,5kg Kartoffeln") == "1,5 kg Kartoffeln"

    def test_no_unit(self):
        assert _fix_quantity_spacing("3 Eier") == "3 Eier"


# -- _expand_je_ingredient --


class TestExpandJeIngredient:

    def test_zwei_zutaten_mit_einheit(self):
        result = _expand_je_ingredient("je 1 TL Kreuzkümmel und Chilipulver")
        assert result == ["1 TL Kreuzkümmel", "1 TL Chilipulver"]

    def test_el_einheit(self):
        result = _expand_je_ingredient("je 2 EL Olivenöl und Zitronensaft")
        assert result == ["2 EL Olivenöl", "2 EL Zitronensaft"]

    def test_prise_einheit(self):
        result = _expand_je_ingredient("je 1 Prise Salz und Pfeffer")
        assert result == ["1 Prise Salz", "1 Prise Pfeffer"]

    def test_drei_zutaten_komma_und(self):
        result = _expand_je_ingredient("je 1 TL Salz, Pfeffer und Paprika")
        assert result == ["1 TL Salz", "1 TL Pfeffer", "1 TL Paprika"]

    def test_gramm_ohne_leerzeichen(self):
        result = _expand_je_ingredient("je 100g Karotten und Zucchini")
        assert result == ["100g Karotten", "100g Zucchini"]

    def test_dezimalzahl(self):
        result = _expand_je_ingredient("je 1,5 TL Salz und Kumin")
        assert result == ["1,5 TL Salz", "1,5 TL Kumin"]

    def test_grossbuchstabe_je(self):
        result = _expand_je_ingredient("Je 1 TL Oregano und Thymian")
        assert result == ["1 TL Oregano", "1 TL Thymian"]

    def test_kein_je_unveraendert(self):
        result = _expand_je_ingredient("200 g Mehl")
        assert result == ["200 g Mehl"]

    def test_kein_und_einzel_zutat(self):
        result = _expand_je_ingredient("je 1 TL Paprika")
        assert result == ["1 TL Paprika"]


# -- _clean_source --


class TestCleanSource:

    def test_page_prefix(self):
        assert _clean_source("22 lecker 03/2025") == "lecker 03/2025"

    def test_page_suffix(self):
        assert _clean_source("lecker 03/2025 45") == "lecker 03/2025"

    def test_bild_auf_seite(self):
        result = _clean_source("lecker Bild auf Seite 12 03/2025")
        assert "Bild auf Seite" not in result

    def test_empty(self):
        assert _clean_source("") == ""

    def test_clean_source_already(self):
        assert _clean_source("lecker 03/2025") == "lecker 03/2025"


# -- _find_recipe_image --


class TestFindRecipeImage:

    def test_no_directory(self):
        assert _find_recipe_image("/nicht/vorhanden") is None

    def test_empty_directory(self, tmp_path):
        assert _find_recipe_image(str(tmp_path)) is None

    def test_finds_foto(self, tmp_path):
        foto = tmp_path / "region_1_foto.png"
        foto.write_bytes(b"\x89PNG")
        result = _find_recipe_image(str(tmp_path))
        assert result == str(foto)

    def test_ignores_non_foto(self, tmp_path):
        (tmp_path / "region_1_text.png").write_bytes(b"\x89PNG")
        assert _find_recipe_image(str(tmp_path)) is None

    def test_returns_first_sorted(self, tmp_path):
        (tmp_path / "b_foto.png").write_bytes(b"\x89PNG")
        (tmp_path / "a_foto.png").write_bytes(b"\x89PNG")
        result = _find_recipe_image(str(tmp_path))
        assert "a_foto.png" in result


# -- _render_html --


class TestRenderHtml:

    def test_replaces_tags(self):
        template = "<h1><RECIPE_NAME></h1><p><SUBTITLE></p>"
        result = _render_html(
            template,
            {
                "RECIPE_NAME": "Apfelkuchen",
                "SUBTITLE": "saftig",
            },
        )
        assert result == "<h1>Apfelkuchen</h1><p>saftig</p>"

    def test_missing_tag_unchanged(self):
        template = "<p><UNKNOWN></p>"
        result = _render_html(template, {"RECIPE_NAME": "Test"})
        assert "<UNKNOWN>" in result


# -- _sum_minutes --


class TestSumMinutes:

    def test_simple(self):
        assert _sum_minutes("15 Min", "30 Min") == 45

    def test_with_hours(self):
        assert _sum_minutes("1 Std", "30 Min") == 90

    def test_empty(self):
        assert _sum_minutes("", "", "") == 0


# -- build_recipe_html --


class TestBuildRecipeHtml:

    def test_creates_html_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = json.loads(
            build_recipe_html(
                recipe_name="Testrezept",
                ingredients=["200g Mehl", "3 Eier"],
                instructions=["Mischen", "Backen"],
            )
        )
        assert os.path.isfile(result["html_file"])
        assert result["safe_name"] == "testrezept"

    def test_html_contains_recipe_name(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = json.loads(
            build_recipe_html(
                recipe_name="Apfelkuchen",
            )
        )
        with open(result["html_file"], encoding="utf-8") as f:
            html = f.read()
        assert "Apfelkuchen" in html

    def test_ingredients_spacing_fixed(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = json.loads(
            build_recipe_html(
                recipe_name="Test",
                ingredients=["250g Mehl"],
            )
        )
        with open(result["html_file"], encoding="utf-8") as f:
            html = f.read()
        assert "250 g Mehl" in html

    def test_image_copied(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()
        (tmp_dir / "region_1_foto.png").write_bytes(b"\x89PNG")

        result = json.loads(build_recipe_html(recipe_name="Bildtest"))
        assert result["image_file"]
        assert os.path.isfile(result["image_file"])

    def test_custom_template(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        ausgang = tmp_path / "Ausgang"
        ausgang.mkdir()
        (ausgang / "Template.html").write_text(
            "<h1><RECIPE_NAME></h1>", encoding="utf-8"
        )
        result = json.loads(build_recipe_html(recipe_name="Custom"))
        with open(result["html_file"], encoding="utf-8") as f:
            html = f.read()
        assert html == "<h1>Custom</h1>"

    def test_source_cleaned(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = json.loads(
            build_recipe_html(
                recipe_name="Quelltest",
                source="22 lecker 03/2025",
            )
        )
        with open(result["html_file"], encoding="utf-8") as f:
            html = f.read()
        assert "lecker 03/2025" in html
        # Seitenzahl 22 am Anfang sollte entfernt sein
        assert ">22 lecker" not in html

    def test_index_updated(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        ausgang = tmp_path / "Ausgang"
        ausgang.mkdir()
        index_html = ausgang / "index.html"
        index_html.write_text(
            "<!DOCTYPE html><html><body>"
            "<section><h2>Hauptgerichte</h2><ul></ul></section>"
            "</body></html>",
            encoding="utf-8",
        )
        result = json.loads(build_recipe_html(recipe_name="Testgericht"))
        assert "Testgericht" in result["index_result"]
        # Pruefen dass index.html das Rezept enthaelt
        updated = index_html.read_text(encoding="utf-8")
        assert "Testgericht" in updated

    def test_index_auto_created(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        index_path = tmp_path / "Ausgang" / "index.html"
        assert not index_path.exists()
        result = json.loads(build_recipe_html(recipe_name="Ohne Index"))
        assert index_path.exists()
        assert "Ohne Index" in result["index_result"]

    def test_cookware_in_html(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = json.loads(
            build_recipe_html(
                recipe_name="Geraetetest",
                cookware=["Pfanne", "Topf", "Backofen"],
            )
        )
        with open(result["html_file"], encoding="utf-8") as f:
            html = f.read()
        assert "Pfanne, Topf, Backofen" in html

    def test_cookware_leer(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        result = json.loads(build_recipe_html(recipe_name="Ohnegeraet"))
        with open(result["html_file"], encoding="utf-8") as f:
            html = f.read()
        assert "COOKWARE" not in html
