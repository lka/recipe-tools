# -*- coding: utf-8 -*-
"""Tests fuer RecipeIndexManager."""

import pytest

from recipe_processor.core.recipes_index import RecipeIndexManager


MINIMAL_INDEX = """\
<!DOCTYPE html>
<html>
<body>
<section>
<h2>Hauptgerichte</h2>
<ul>
<li><a class="recipe" href="curry.html">Curry</a></li>
<li><a class="recipe" href="pasta.html">Pasta</a></li>
</ul>
</section>
<section>
<h2>Salate</h2>
<ul>
<li><a class="recipe" href="salat.html">Griechischer Salat</a></li>
</ul>
</section>
<section>
<h2>Suppen</h2>
<ul>
</ul>
</section>
</body>
</html>
"""


@pytest.fixture()
def index_file(tmp_path):
    """Erstellt eine minimale index.html."""
    path = tmp_path / "index.html"
    path.write_text(MINIMAL_INDEX, encoding="utf-8")
    return path


@pytest.fixture()
def manager(index_file):
    """Erstellt einen RecipeIndexManager mit der Test-Index-Datei."""
    return RecipeIndexManager(index_file)


# -- suggest_category --


class TestSuggestCategory:

    def test_keyword_match(self, manager):
        assert manager.suggest_category("Tomatensalat") == "Salate"

    def test_keyword_suppe(self, manager):
        assert manager.suggest_category("Gulaschsuppe") == "Suppen"

    def test_keyword_kuchen(self, manager):
        assert manager.suggest_category("Apfelkuchen") == "Desserts & Kuchen"

    def test_keyword_brot(self, manager):
        assert manager.suggest_category("Frankenlaib") == "Brot & Gebäck"

    def test_fallback(self, manager):
        assert manager.suggest_category("Unbekanntes Gericht") == "Hauptgerichte"


# -- _german_sort_key --


class TestGermanSortKey:

    def test_umlaute(self, manager):
        assert manager._german_sort_key("Ärger") == "aerger"

    def test_sz(self, manager):
        assert manager._german_sort_key("Süße") == "suesse"

    def test_lowercase(self, manager):
        assert manager._german_sort_key("ABC") == "abc"


# -- get_categories --


class TestGetCategories:

    def test_returns_all(self, manager):
        cats = manager.get_categories()
        assert "Hauptgerichte" in cats
        assert "Salate" in cats
        assert "Suppen" in cats
        assert len(cats) == 3


# -- count_recipes --


class TestCountRecipes:

    def test_total(self, manager):
        result = manager.count_recipes()
        assert result["total"] == 3

    def test_by_category(self, manager):
        result = manager.count_recipes()
        assert result["by_category"]["Hauptgerichte"] == 2
        assert result["by_category"]["Salate"] == 1


# -- check_duplicate --


class TestCheckDuplicate:

    def test_exists(self, manager):
        is_dup, link = manager.check_duplicate("Curry")
        assert is_dup is True
        assert link == "curry.html"

    def test_case_insensitive(self, manager):
        is_dup, _ = manager.check_duplicate("curry")
        assert is_dup is True

    def test_not_exists(self, manager):
        is_dup, link = manager.check_duplicate("Risotto")
        assert is_dup is False
        assert link is None


# -- add_recipe --


class TestAddRecipe:

    def test_adds_recipe(self, manager):
        result = manager.add_recipe("Risotto", "risotto.html", "Hauptgerichte")
        assert "Risotto" in result
        # Pruefen dass es in der Datei steht
        recipes = manager.list_recipes("Hauptgerichte")
        assert "Risotto" in recipes["Hauptgerichte"]

    def test_alphabetical_order(self, manager):
        manager.add_recipe("Auflauf", "auflauf.html", "Hauptgerichte")
        recipes = manager.list_recipes("Hauptgerichte")
        names = recipes["Hauptgerichte"]
        assert names.index("Auflauf") < names.index("Curry")

    def test_duplicate_rejected(self, manager):
        result = manager.add_recipe("Curry", "curry2.html", "Hauptgerichte")
        assert "existiert bereits" in result

    def test_auto_category(self, manager):
        result = manager.add_recipe("Kartoffelsuppe", "kartoffelsuppe.html")
        assert "Suppen" in result

    def test_unknown_category(self, manager):
        result = manager.add_recipe("Test", "test.html", "Unbekannt")
        assert "nicht gefunden" in result

    def test_empty_category_ul(self, manager):
        result = manager.add_recipe("Tomatensuppe", "tomatensuppe.html", "Suppen")
        assert "Tomatensuppe" in result
        recipes = manager.list_recipes("Suppen")
        assert "Tomatensuppe" in recipes["Suppen"]


# -- remove_recipe --


class TestRemoveRecipe:

    def test_removes_recipe(self, manager):
        result = manager.remove_recipe("Curry")
        assert "entfernt" in result
        is_dup, _ = manager.check_duplicate("Curry")
        assert is_dup is False

    def test_not_found(self, manager):
        result = manager.remove_recipe("Unbekannt")
        assert "nicht gefunden" in result


# -- list_recipes --


class TestListRecipes:

    def test_all(self, manager):
        result = manager.list_recipes()
        assert "Hauptgerichte" in result
        assert "Salate" in result

    def test_filtered(self, manager):
        result = manager.list_recipes("Salate")
        assert "Salate" in result
        assert "Hauptgerichte" not in result

    def test_case_insensitive_filter(self, manager):
        result = manager.list_recipes("salate")
        assert "Salate" in result


# -- create_index --


class TestCreateIndex:

    def test_creates_file(self, tmp_path):
        path = tmp_path / "index.html"
        mgr = RecipeIndexManager(path)
        result = mgr.create_index()
        assert path.exists()
        assert result == str(path)

    def test_contains_all_categories(self, tmp_path):
        path = tmp_path / "index.html"
        mgr = RecipeIndexManager(path)
        mgr.create_index()
        content = path.read_text(encoding="utf-8")
        for category in mgr.category_keywords:
            assert category in content

    def test_has_empty_lists(self, tmp_path):
        path = tmp_path / "index.html"
        mgr = RecipeIndexManager(path)
        mgr.create_index()
        cats = mgr.get_categories()
        assert len(cats) == len(mgr.category_keywords)
        counts = mgr.count_recipes()
        assert counts["total"] == 0

    def test_add_recipe_after_create(self, tmp_path):
        path = tmp_path / "index.html"
        mgr = RecipeIndexManager(path)
        mgr.create_index()
        result = mgr.add_recipe("Tomatensuppe", "tomatensuppe.html", "Suppen")
        assert "Tomatensuppe" in result
        recipes = mgr.list_recipes("Suppen")
        assert "Tomatensuppe" in recipes["Suppen"]
