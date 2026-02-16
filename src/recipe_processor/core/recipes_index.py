# -*- coding: utf-8 -*-
"""Verwaltung des Rezept-Index mit HTML-Manipulation."""

import locale
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
_INDEX_TEMPLATE = (_ASSETS_DIR / "index_template.html").read_text(encoding="utf-8")

# Locale fuer deutsche Sortierung setzen
try:
    locale.setlocale(locale.LC_COLLATE, "de_DE.UTF-8")
except locale.Error:
    try:
        locale.setlocale(locale.LC_COLLATE, "German_Germany.1252")
    except locale.Error:
        logger.warning(
            "Deutsche Locale nicht verfuegbar, verwende Standard-Sortierung"
        )


class RecipeIndexManager:
    """Verwaltet den Rezept-Index mit HTML-Manipulation."""

    def __init__(self, index_path: Path):
        """Initialisiert den Index-Manager.

        Args:
            index_path: Pfad zur index.html Datei.
        """
        self.index_path = index_path
        self.category_keywords = {
            "Salate": ["salat", "bowl", "carpaccio"],
            "Suppen": ["suppe", "eintopf", "brühe", "soup", "brodo"],
            "Vorspeisen & Snacks": [
                "dip",
                "tapenade",
                "mayo",
                "terrine",
                "tatar",
                "hörnchen",
                "creme",
                "pesto",
                "sauce",
            ],
            "Hauptgerichte": [
                "pfanne",
                "curry",
                "pasta",
                "nudeln",
                "risotto",
                "auflauf",
                "gratin",
                "schnitzel",
                "hähnchen",
                "pute",
                "rouladen",
                "wok",
                "fondue",
                "geschnetzeltes",
                "involtini",
                "gnocchi",
                "spaghetti",
                "linguine",
            ],
            "Brot & Gebäck": [
                "brot",
                "brötchen",
                "laib",
                "gebäck",
                "stangen",
                "focaccia",
            ],
            "Desserts & Kuchen": [
                "kuchen",
                "torte",
                "dessert",
                "törtchen",
                "cupcakes",
                "pfannkuchen",
                "panettone",
                "samosas",
            ],
        }

    def create_index(self) -> str:
        """Erzeugt eine neue index.html aus dem Template.

        Erstellt fuer jede Kategorie aus category_keywords eine leere
        Section mit Ueberschrift und leerer UL-Liste.

        Returns:
            Pfad zur erzeugten index.html.
        """
        sections = []
        for category in self.category_keywords:
            sections.append(
                f"<section>\n<h2>{category}</h2>\n<ul>\n</ul>\n</section>"
            )
        categories_html = "\n".join(sections)
        html = _INDEX_TEMPLATE.replace("<CATEGORIES>", categories_html)

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info("Index erstellt: %s", self.index_path)
        return str(self.index_path)

    def _load_index(self) -> BeautifulSoup:
        """Laedt die index.html Datei."""
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index nicht gefunden: {self.index_path}")

        with open(self.index_path, "r", encoding="utf-8") as f:
            return BeautifulSoup(f.read(), "lxml")

    def _save_index(self, soup: BeautifulSoup) -> None:
        """Speichert die index.html Datei."""
        with open(self.index_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

    def _german_sort_key(self, text: str) -> str:
        """Erstellt einen Sortier-Key fuer deutsche Umlaute."""
        replacements = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "ß": "ss",
            "Ä": "Ae",
            "Ö": "Oe",
            "Ü": "Ue",
        }
        result = text.lower()
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    def get_categories(self) -> list[str]:
        """Gibt alle Kategorien aus dem Index zurueck.

        Returns:
            Liste der Kategorien.
        """
        soup = self._load_index()
        categories = []

        for section in soup.find_all("section"):
            h2 = section.find("h2")
            if h2:
                categories.append(h2.get_text(strip=True))

        return categories

    def count_recipes(self) -> dict[str, object]:
        """Zaehlt alle Rezepte im Index.

        Returns:
            Dictionary mit Gesamtanzahl und Anzahl pro Kategorie.
        """
        soup = self._load_index()
        counts: dict[str, int] = defaultdict(int)
        total = 0

        for section in soup.find_all("section"):
            h2 = section.find("h2")
            if h2:
                category = h2.get_text(strip=True)
                recipe_count = len(section.find_all("li"))
                counts[category] = recipe_count
                total += recipe_count

        return {"total": total, "by_category": dict(counts)}

    def check_duplicate(self, recipe_name: str) -> tuple[bool, str | None]:
        """Prueft ob ein Rezept bereits existiert.

        Args:
            recipe_name: Name des Rezepts.

        Returns:
            Tuple (existiert, gefundener_link).
        """
        soup = self._load_index()

        for link in soup.find_all("a", class_="recipe"):
            if link.get_text(strip=True).lower() == recipe_name.lower():
                href = link.get("href")
                return True, str(href) if href else None

        return False, None

    def suggest_category(self, recipe_name: str) -> str:
        """Schlaegt eine Kategorie basierend auf Keywords vor.

        Args:
            recipe_name: Name des Rezepts.

        Returns:
            Vorgeschlagene Kategorie.
        """
        recipe_lower = recipe_name.lower()

        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in recipe_lower:
                    return category

        return "Hauptgerichte"

    def _insert_sorted(self, soup, ul, recipe_name, recipe_file):
        """Fuegt ein Rezept alphabetisch sortiert in eine UL-Liste ein."""
        recipes = []
        for li in ul.find_all("li", recursive=False):
            link = li.find("a", class_="recipe")
            if link:
                recipes.append((link.get_text(strip=True), li))

        new_li = soup.new_tag("li")
        new_link = soup.new_tag("a", **{"class": "recipe", "href": recipe_file})
        new_link.string = recipe_name
        new_li.append("\n\t\t\t\t\t\t")
        new_li.append(new_link)
        new_li.append("\n\t\t\t\t\t")

        recipes.append((recipe_name, new_li))
        recipes.sort(key=lambda x: self._german_sort_key(x[0]))

        ul.clear()
        ul.append("\n\t\t\t\t\t")
        for _, li in recipes:
            ul.append(li)
            ul.append("\n\t\t\t\t\t")

    def add_recipe(
        self,
        recipe_name: str,
        recipe_file: str,
        category: str | None = None,
        date: str | None = None,
    ) -> str:
        """Fuegt ein Rezept zum Index hinzu.

        Args:
            recipe_name: Name des Rezepts.
            recipe_file: Dateiname der HTML-Datei.
            category: Kategorie (optional, wird vorgeschlagen).
            date: Datum (optional, heute wenn nicht angegeben).

        Returns:
            Erfolgs-/Fehlermeldung.
        """
        is_duplicate, existing_link = self.check_duplicate(recipe_name)
        if is_duplicate:
            return f"Rezept existiert bereits: {existing_link}"

        if not category:
            category = self.suggest_category(recipe_name)
            logger.info("Auto-detect Kategorie: %s", category)

        if not date:
            date = datetime.now().strftime("%d.%m.%Y")

        soup = self._load_index()

        # Kategorie-Section finden
        section = None
        for s in soup.find_all("section"):
            h2 = s.find("h2")
            if h2 and h2.get_text(strip=True) == category:
                section = s
                break

        if not section:
            categories = ", ".join(self.get_categories())
            return f"Kategorie nicht gefunden: {category}. Verfuegbar: {categories}"

        ul = section.find("ul")
        if not ul:
            return f"Keine UL-Liste in Kategorie {category} gefunden"

        self._insert_sorted(soup, ul, recipe_name, recipe_file)
        self._save_index(soup)

        return (
            f"Rezept hinzugefuegt: {recipe_name} "
            f"in {category} ({recipe_file})"
        )

    def remove_recipe(self, recipe_name: str) -> str:
        """Entfernt ein Rezept aus dem Index.

        Args:
            recipe_name: Name des Rezepts.

        Returns:
            Erfolgs-/Fehlermeldung.
        """
        soup = self._load_index()

        found = False
        for link in soup.find_all("a", class_="recipe"):
            if link.get_text(strip=True).lower() == recipe_name.lower():
                li = link.find_parent("li")
                if li:
                    li.decompose()
                    found = True
                    break

        if not found:
            return f"Rezept nicht gefunden: {recipe_name}"

        self._save_index(soup)
        return f"Rezept entfernt: {recipe_name}"

    def list_recipes(self, category: str | None = None) -> dict[str, list[str]]:
        """Listet alle Rezepte auf (optional gefiltert nach Kategorie).

        Args:
            category: Kategorie zum Filtern (optional).

        Returns:
            Dictionary mit Kategorien und Rezeptnamen.
        """
        soup = self._load_index()
        result: dict[str, list[str]] = defaultdict(list)

        for section in soup.find_all("section"):
            h2 = section.find("h2")
            if h2:
                cat_name = h2.get_text(strip=True)

                if category and cat_name.lower() != category.lower():
                    continue

                for link in section.find_all("a", class_="recipe"):
                    result[cat_name].append(link.get_text(strip=True))

        return dict(result)
