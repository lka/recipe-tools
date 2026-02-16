# -*- coding: utf-8 -*-
"""HTML-Erzeugung aus strukturierten Rezeptdaten."""

import json
import os
import re
import shutil
from pathlib import Path

from recipe_processor.core.utils import (
    create_tmp_dir_if_needed,
    get_working_dir,
)

# -- Transliterations-Tabelle fuer Dateinamen --

_TRANSLITERATION = str.maketrans(
    {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "Ä": "Ae",
        "Ö": "Oe",
        "Ü": "Ue",
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "â": "a",
        "î": "i",
        "ô": "o",
        "û": "u",
        "ç": "c",
    }
)

# -- Einheiten fuer Mengen-Spacing --

_UNITS = (
    "g",
    "kg",
    "mg",
    "l",
    "ml",
    "cl",
    "dl",
    "EL",
    "TL",
    "Stk",
    "Pck",
    "Pkg",
    "Pr",
    "Msp",
    "Bd",
    "Bund",
)

_UNIT_PATTERN = re.compile(r"(\d+[.,]?\d*)\s*(" + "|".join(_UNITS) + r")\b")

# -- Default HTML-Template --

_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_TEMPLATE = (_ASSETS_DIR / "Template.html").read_text(encoding="utf-8")


def _sanitize_filename(name: str, max_length: int = 50) -> str:
    """Erzeugt einen URL-sicheren Dateinamen.

    Args:
        name: Rezeptname im Klartext.
        max_length: Maximale Zeichenlaenge.

    Returns:
        Bereinigter Dateiname ohne Erweiterung.
    """
    safe = name.translate(_TRANSLITERATION)
    safe = re.sub(r"[^a-zA-Z0-9\s-]", "", safe)
    safe = re.sub(r"\s+", "-", safe.strip())
    safe = re.sub(r"-+", "-", safe).strip("-").lower()
    return safe[:max_length]


def _parse_iso_duration(text: str) -> str:
    """Wandelt deutsche Zeitangaben in ISO 8601 Duration.

    Args:
        text: Z.B. "30 Min", "1 Std 15 Min", "2 Stunden".

    Returns:
        ISO-String wie "PT30M", "PT1H15M" oder leerer String.
    """
    if not text:
        return ""
    text_lower = text.lower().strip()
    hours = 0
    minutes = 0

    h_match = re.search(r"(\d+)\s*(?:std|stunde|stunden|h)\b", text_lower)
    if h_match:
        hours = int(h_match.group(1))

    m_match = re.search(r"(\d+)\s*(?:min|minute|minuten|m)\b", text_lower)
    if m_match:
        minutes = int(m_match.group(1))

    if hours == 0 and minutes == 0:
        # Versuch: reine Zahl als Minuten interpretieren
        num_match = re.match(r"^(\d+)$", text_lower)
        if num_match:
            minutes = int(num_match.group(1))

    if hours == 0 and minutes == 0:
        return ""

    parts = "PT"
    if hours:
        parts += f"{hours}H"
    if minutes:
        parts += f"{minutes}M"
    return parts


def _format_ingredient_heading(text: str) -> str:
    """Wandelt Ueberschriften in Zutatenlisten um.

    Erkennt das Muster "--- Text ---" und ersetzt es durch "<b>Text</b>".

    Args:
        text: Zutatzeile, z.B. "--- Fuer den Teig ---".

    Returns:
        Formatierter Text oder unveraenderter Text.
    """
    match = re.match(r"^-{2,}\s+(.+?)\s+-{2,}$", text)
    if match:
        return f"<b>{match.group(1)}</b>"
    return text


def _fix_quantity_spacing(text: str) -> str:
    """Setzt Leerzeichen zwischen Menge und Einheit.

    Args:
        text: Zutatzeile, z.B. "250g Mehl".

    Returns:
        Korrigierter Text, z.B. "250 g Mehl".
    """
    return _UNIT_PATTERN.sub(r"\1 \2", text)


def _clean_source(text: str) -> str:
    """Bereinigt Quellangaben.

    Entfernt fuehrende/abschliessende Seitenzahlen und
    "Bild auf Seite X"-Hinweise.

    Args:
        text: Rohtext der Quellangabe.

    Returns:
        Bereinigte Quellangabe.
    """
    if not text:
        return ""
    cleaned = re.sub(r"[Bb]ild\s+auf\s+[Ss]eite\s+\d+", "", text)
    cleaned = re.sub(r"^\d{1,3}\s+", "", cleaned)
    cleaned = re.sub(r"(?<!/)\s+\d{1,3}$", "", cleaned)
    return cleaned.strip()


def _find_recipe_image(tmp_dir: str) -> str | None:
    """Findet das erste Foto im tmp-Verzeichnis.

    Args:
        tmp_dir: Pfad zum temporaeren Verzeichnis.

    Returns:
        Absoluter Pfad zur Bilddatei oder None.
    """
    if not os.path.isdir(tmp_dir):
        return None
    fotos = sorted(f for f in os.listdir(tmp_dir) if f.endswith("_foto.png"))
    if fotos:
        return os.path.join(tmp_dir, fotos[0])
    return None


def _render_html(template: str, data: dict[str, str]) -> str:
    """Ersetzt Template-Tags durch Rezeptdaten.

    Args:
        template: HTML-Template mit <TAG>-Platzhaltern.
        data: Mapping von Tag-Name zu Wert.

    Returns:
        Befuelltes HTML.
    """
    result = template
    for tag, value in data.items():
        result = result.replace(f"<{tag}>", value)
    return result


def _unique_path(path: str) -> str:
    """Gibt einen eindeutigen Dateipfad zurueck (Suffix _2, _3, ...)."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    counter = 2
    while os.path.exists(f"{base}_{counter}{ext}"):
        counter += 1
    return f"{base}_{counter}{ext}"


def build_recipe_html(
    recipe_name: str,
    subtitle: str = "",
    portions: str = "",
    prep_time: str = "",
    cook_time: str = "",
    wait_time: str = "",
    ingredients: list[str] | None = None,
    instructions: list[str] | None = None,
    tips: str = "",
    nutrition: str = "",
    source: str = "",
    category: str = "",
) -> str:
    """Erstellt HTML aus strukturierten Rezeptdaten.

    Uebernimmt automatisch Dateinamen-Sanitisierung,
    ISO-Zeitformat-Berechnung, Leerzeichen Menge/Einheit,
    Quellen-Bereinigung, Template-Befuellung, Bild-Zuordnung
    und Datei-Speicherung.

    Args:
        recipe_name: Name des Rezepts.
        subtitle: Optionaler Untertitel.
        portions: Portionsangabe, z.B. "4 Personen".
        prep_time: Vorbereitungszeit, z.B. "15 Min".
        cook_time: Zubereitungszeit, z.B. "30 Min".
        wait_time: Wartezeit, z.B. "1 Std".
        ingredients: Liste der Zutaten.
        instructions: Liste der Zubereitungsschritte.
        tips: Tipps und Hinweise.
        nutrition: Naehrwertangaben.
        source: Quellangabe.
        category: Index-Kategorie (optional, wird automatisch vorgeschlagen).

    Returns:
        JSON-String mit html_file, image_file, safe_name und index_result.
    """
    if ingredients is None:
        ingredients = []
    if instructions is None:
        instructions = []

    working_dir = get_working_dir()
    tmp_dir = create_tmp_dir_if_needed()
    output_dir = os.path.join(working_dir, "Ausgang")
    images_dir = os.path.join(output_dir, "Images")
    os.makedirs(images_dir, exist_ok=True)

    # Dateiname
    safe_name = _sanitize_filename(recipe_name)

    # Zeitformate
    prep_iso = _parse_iso_duration(prep_time)
    cook_iso = _parse_iso_duration(cook_time)
    wait_iso = _parse_iso_duration(wait_time)
    total_min = _sum_minutes(prep_time, cook_time, wait_time)
    total_time = f"{total_min} Min" if total_min else ""
    total_iso = f"PT{total_min}M" if total_min else ""

    # Zutaten mit Ueberschriften-Erkennung und Spacing-Fix
    fixed_ingredients = [
        _format_ingredient_heading(z) if re.match(r"^-{2,}\s+", z)
        else _fix_quantity_spacing(z)
        for z in ingredients
    ]
    ingredients_html = (
        "<ul>\n" + "\n".join(f"<li>{z}</li>" for z in fixed_ingredients) + "\n</ul>"
    )

    # Zubereitungsschritte
    instructions_html = (
        "<ol>\n" + "\n".join(f"<li>{s}</li>" for s in instructions) + "\n</ol>"
    )

    # Quellen-Bereinigung
    clean_src = _clean_source(source)

    # Bild zuordnen
    image_file = ""
    image_path_html = ""
    foto = _find_recipe_image(tmp_dir)
    if foto:
        dest = _unique_path(os.path.join(images_dir, f"{safe_name}.png"))
        shutil.copy(foto, dest)
        image_file = dest
        image_path_html = "Images/" + os.path.basename(dest)

    # Template laden
    template_path = os.path.join(output_dir, "Template.html")
    if os.path.isfile(template_path):
        with open(template_path, encoding="utf-8") as f:
            template = f.read()
    else:
        template = DEFAULT_TEMPLATE

    # HTML rendern
    data = {
        "TITLE": recipe_name,
        "RECIPE_NAME": recipe_name,
        "SUBTITLE": subtitle,
        "IMAGE_PATH": image_path_html,
        "PREP_TIME": prep_time,
        "PREP_TIME_ISO": prep_iso,
        "COOK_TIME": cook_time,
        "COOK_TIME_ISO": cook_iso,
        "WAIT_TIME": wait_time,
        "WAIT_TIME_ISO": wait_iso,
        "TOTAL_TIME": total_time,
        "TOTAL_TIME_ISO": total_iso,
        "PORTIONS": portions,
        "INGREDIENTS": ingredients_html,
        "INSTRUCTIONS": instructions_html,
        "TIPS": tips,
        "NUTRITION": nutrition,
        "SOURCE": clean_src,
    }
    html = _render_html(template, data)

    # Datei speichern
    html_path = _unique_path(os.path.join(output_dir, f"{safe_name}.html"))
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Index aktualisieren (ggf. aus Template erzeugen)
    index_result = ""
    index_path = os.path.join(output_dir, "index.html")
    from recipe_processor.core.recipes_index import RecipeIndexManager

    index_mgr = RecipeIndexManager(Path(index_path))
    if not os.path.isfile(index_path):
        index_mgr.create_index()
    index_result = index_mgr.add_recipe(
        recipe_name=recipe_name,
        recipe_file=os.path.basename(html_path),
        category=category or None,
    )

    return json.dumps(
        {
            "html_file": html_path,
            "image_file": image_file,
            "safe_name": safe_name,
            "index_result": index_result,
        },
        ensure_ascii=False,
    )


def _sum_minutes(*times: str) -> int:
    """Summiert Zeitangaben zu Gesamtminuten."""
    total = 0
    for t in times:
        if not t:
            continue
        iso = _parse_iso_duration(t)
        h_match = re.search(r"(\d+)H", iso)
        m_match = re.search(r"(\d+)M", iso)
        if h_match:
            total += int(h_match.group(1)) * 60
        if m_match:
            total += int(m_match.group(1))
    return total


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python -m recipe_processor.tools.html_builder <recipe.json>")
        sys.exit(1)

    recipe_file = sys.argv[1]
    with open(recipe_file, encoding="utf-8") as f:
        data = json.load(f)

    result = build_recipe_html(**data)
    print(result)
