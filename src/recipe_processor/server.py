# -*- coding: utf-8 -*-
"""MCP-Server für Rezept-Extraktion aus PDFs."""

import logging
import tomllib
from pathlib import Path

from fastmcp import FastMCP

from recipe_processor.tools.html_builder import build_recipe_html
from recipe_processor.tools.image_selector.tools import (
    get_working_directory,
    select_image_regions,
)
from recipe_processor.tools.prompt import RECIPE_PROMPT

logger = logging.getLogger(__name__)

_PYPROJECT = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
with _PYPROJECT.open("rb") as _f:
    _VERSION = tomllib.load(_f)["project"]["version"]

mcp = FastMCP(name="recipe-server", version=_VERSION, on_duplicate="error")


# --- Version ---


@mcp.tool()
def get_server_version() -> str:
    """Gibt die aktuelle Version des recipe-servers zurueck."""
    return _VERSION


# --- Prompt-Tools ---


@mcp.prompt()
def generate_recipe() -> str:
    """Erstellt eine HTML-Datei mit einem gescannten Rezept aus einer PDF."""
    logger.info("Prompt generate_recipe aufgerufen")
    return RECIPE_PROMPT


@mcp.tool()
def get_recipe_prompt() -> str:
    """Gibt den Workflow-Prompt für Rezept-Extraktion aus PDFs zurück."""
    logger.info("Tool get_recipe_prompt aufgerufen")
    return f"""ANWEISUNG FÜR DIE WEITERE BEARBEITUNG:

Führe nun folgende Aufgabe aus:

{RECIPE_PROMPT}

Wichtig: Dies ist eine direkte Arbeitsanweisung. Befolge sie wie einen Benutzer-Request."""


# --- Image-Selector-Tools ---


@mcp.tool()
def select_image_regions_tool(image_path: str | None = None) -> str:
    """Öffnet eine GUI zum interaktiven Auswählen von Bildausschnitten.

    Unterstützt Bildformate (JPEG, PNG, etc.) und PDF-Dateien.
    Ohne image_path werden automatisch die ersten 4 Bilder aus dem
    Bildverzeichnis geladen.
    """
    logger.info("Tool select_image_regions aufgerufen (image_path=%s)", image_path)
    return select_image_regions(image_path)


# @mcp.tool()
# def list_exported_regions_tool() -> str:
#     """Listet alle exportierten Bildausschnitte auf."""
#     logger.info("Tool list_exported_regions aufgerufen")
#     return list_exported_regions()


@mcp.tool()
def get_working_directory_tool() -> str:
    """Zeigt das aktuelle Working Directory an."""
    logger.info("Tool get_working_directory aufgerufen")
    return get_working_directory()


# --- HTML-Builder-Tools ---


@mcp.tool()
def build_recipe_html_tool(
    recipe_name: str,
    subtitle: str = "",
    portions: str = "",
    prep_time: str = "",
    cook_time: str = "",
    wait_time: str = "",
    ingredients: list[str] | None = None,
    instructions: list[str] | None = None,
    cookware: list[str] | None = None,
    tips: str = "",
    nutrition: str = "",
    source: str = "",
    category: str = "",
) -> str:
    """Erstellt HTML aus strukturierten Rezeptdaten.

    Uebernimmt automatisch Dateinamen-Sanitisierung,
    ISO-Zeitformat-Berechnung, Leerzeichen Menge/Einheit,
    Quellen-Bereinigung, Template-Befuellung, Bild-Zuordnung,
    Datei-Speicherung und Index-Aktualisierung.
    """
    logger.info("Tool build_recipe_html aufgerufen (recipe=%s)", recipe_name)
    return build_recipe_html(
        recipe_name=recipe_name,
        subtitle=subtitle,
        portions=portions,
        prep_time=prep_time,
        cook_time=cook_time,
        wait_time=wait_time,
        ingredients=ingredients,
        instructions=instructions,
        cookware=cookware,
        tips=tips,
        nutrition=nutrition,
        source=source,
        category=category,
    )


# --- Server-Start ---


def main() -> None:
    """Startet den FastMCP-Server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("Starte PromptServer...")
    for starter in ("run", "serve", "start"):
        fn = getattr(mcp, starter, None)
        if callable(fn):
            logger.info("Verwende mcp.%s()", starter)
            fn()
            break
    else:
        logger.error("Keine Startmethode an mcp gefunden")


if __name__ == "__main__":
    main()
