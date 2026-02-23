# -*- coding: utf-8 -*-
"""Tool-Implementierungen für Bildausschnitt-Selektion."""

import os
import sys

from .export import export_regions
from .web_gui import WebImageSelectorGUI as ImageSelectorGUI
from recipe_processor.core.utils import create_tmp_dir_if_needed, get_working_dir

from .utils import transform_coords


def _resolve_image_path(image_path: str | None) -> str | None:
    """Löst einen relativen Bildpfad auf und validiert die Existenz."""
    if not image_path:
        return None
    if not os.path.isabs(image_path):
        image_path = os.path.join(get_working_dir(), image_path)
    if not os.path.exists(image_path):
        return f"Fehler: Bild nicht gefunden: {image_path}"
    return image_path


def _export_all_regions(images_data: list, export_dir: str) -> tuple[list, int]:
    """Exportiert Regionen aller Bilder und gibt Dateiliste + Anzahl zurück."""
    all_files: list = []
    total = 0
    for img_data in images_data:
        if not img_data["regions"]:
            continue
        for region in img_data["regions"]:
            region["coords"] = transform_coords(
                region["coords"], img_data["scale_factor"]
            )
        result = export_regions(
            img_data["original_path"],
            img_data["regions"],
            export_dir,
            image_object=img_data["original_image"],
        )
        all_files.extend(result["files"])
        total += result["exported_count"]
    return all_files, total


def _build_export_response(
    exported_files: list, image_count: int, export_dir: str
) -> str:
    """Baut die Antwort-Nachricht aus exportierten Dateien zusammen."""
    lines = [
        f"✓ Erfolgreich {len(exported_files)} Bereiche "
        f"von {image_count} Bild(ern) exportiert:\n",
    ]
    for fi in exported_files:
        if fi["type"] == "foto":
            lines.append(
                f"  Region {fi['region']} (FOTO): " f"{os.path.basename(fi['file'])}"
            )
        else:
            lines.append(f"  Region {fi['region']} (TEXT):")
            lines.append(f"    - Bild: {os.path.basename(fi['image_file'])}")
            lines.append(f"    - Text: {os.path.basename(fi['text_file'])}")

    lines.append(f"\nAusgabeverzeichnis: {export_dir}")

    text_files = sorted(
        [fi["text_file"] for fi in exported_files if fi["type"] == "text"],
        key=lambda p: os.path.basename(p),
    )
    parts = []
    for tf in text_files:
        try:
            with open(tf, encoding="utf-8") as f:
                parts.append(f.read().strip())
        except OSError:
            pass
    if parts:
        full_text = "\n\n".join(parts)
        full_text_path = os.path.join(export_dir, "full_recipe_text.txt")
        with open(full_text_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        lines.append(f"\nGesamttext: {os.path.basename(full_text_path)}")
        lines.append("\n--- full_recipe_text ---")
        lines.append(full_text)

    return "\n".join(lines)


def select_image_regions(image_path: str | None = None) -> str:
    """Öffnet eine GUI zum interaktiven Auswählen von Bildausschnitten.

    Unterstützt Bildformate (JPEG, PNG, etc.) und PDF-Dateien.
    Ohne image_path werden automatisch die ersten 4 Bilder aus dem
    Bildverzeichnis geladen.
    """
    export_dir = create_tmp_dir_if_needed()

    resolved = _resolve_image_path(image_path)
    if isinstance(resolved, str) and resolved.startswith("Fehler"):
        return resolved

    gui = ImageSelectorGUI(resolved, export_dir)
    images_data = gui.run()

    if not images_data:
        return "Auswahl abgebrochen - keine Bereiche exportiert"

    exported_files, total = _export_all_regions(images_data, export_dir)

    if total == 0:
        return "Keine Bereiche zum Exportieren ausgewählt"

    return _build_export_response(exported_files, len(images_data), export_dir)


def list_exported_regions() -> str:
    """Listet alle exportierten Bildausschnitte aus dem Working Directory auf."""
    export_dir = create_tmp_dir_if_needed()
    files = sorted(f for f in os.listdir(export_dir) if f.endswith((".png", ".txt")))

    result = f"Exportierte Dateien in {export_dir}:\n\n"
    if files:
        result += "\n".join(f"  - {f}" for f in files)
    else:
        result += "  (keine Dateien gefunden)"
    return result


def get_working_directory() -> str:
    """Zeigt das aktuelle Working Directory an."""
    return f"Working Directory: {get_working_dir()}"


def run_standalone(image_path: str | None = None) -> None:
    """Starte die GUI im Standalone-Modus ohne MCP-Server."""
    from dotenv import load_dotenv

    load_dotenv()
    try:
        result = select_image_regions(image_path)
        print(result)
    except Exception as e:
        print(f"Fehler: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        path = sys.argv[2] if len(sys.argv) > 2 else None
        run_standalone(path)
