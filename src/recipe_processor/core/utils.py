"""Gemeinsame Utility-Funktionen fuer Dateioperationen und Verzeichnisverwaltung."""

import os
import sys


def get_working_dir() -> str:
    """Ermittle das Working Directory."""
    working_dir = os.environ.get("IMAGE_SELECTOR_WORKING_DIR", os.getcwd())
    os.makedirs(working_dir, exist_ok=True)
    return working_dir


def get_image_subdirectory() -> str:
    """Ermittle das Unterverzeichnis fuer Bilder, falls definiert."""
    subdir = os.environ.get("IMAGE_SUBDIRECTORY", "")
    if subdir:
        full_path = os.path.join(get_working_dir(), subdir)
        os.makedirs(full_path, exist_ok=True)
        return full_path
    return get_working_dir()


def create_tmp_dir_if_needed() -> str:
    """Erstelle ein temporaeres Verzeichnis, falls noetig."""
    tmp_dir = os.path.join(get_working_dir(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    return tmp_dir


def cleanup_tmp_dir():
    """Loesche alle Dateien im temporaeren Verzeichnis."""
    tmp_dir = create_tmp_dir_if_needed()
    if os.path.exists(tmp_dir):
        for file in os.listdir(tmp_dir):
            file_path = os.path.join(tmp_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(
                    f"Fehler beim Löschen der Datei {file_path}: {e}", file=sys.stderr
                )
