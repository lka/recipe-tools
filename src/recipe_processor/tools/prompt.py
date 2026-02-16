# -*- coding: utf-8 -*-
"""Prompt-Template für Rezept-Extraktion aus PDFs."""

RECIPE_PROMPT = r"""
# Rezept-Extraktion aus PDF (v3 – optimiert)

## Verzeichnisse
| Pfad | Zweck |
|------|-------|
| tmp/ | Temporär (wird von image-selector automatisch geleert) |
| Eingang/ | PDFs (können mehrere Rezepte enthalten) |
| Ausgang/ | HTML-Dateien + Template.html |
| Ausgang/Images/ | Rezeptbilder |

## Konnektoren
- **filesystem**: Datei-Operationen (list, read, save, append, delete, move, edit)
- **image-selector**: Region-Auswahl mit automatischem OCR → liefert `full_recipe_text` + Foto-Dateien
- **recipe-index**: Index-Verwaltung (add, remove, check_duplicate, suggest_category, list_categories, count, list_all)
- **windows-launcher**: Dateien in Edge öffnen
- **tesseract**: OCR-Fallback

---

## Workflow

### 0. Vorbereitung
1. `filesystem:list_directory` → Verzeichnisse prüfen (tmp/, Eingang/, Ausgang/, Ausgang/Images/)
2. `recipe-index:count_recipes` → Status ausgeben (Template vorhanden? Anzahl Rezepte/Kategorien?)
3. Falls `Ausgang/Template.html` fehlt → Basis-Template erstellen

### 1. PDF-Analyse
1. `image-selector:select_image_regions` (ohne Parameter → wählt automatisch erstes PDF/PNG)
2. Nutzer markiert alle Regionen für **ein** Rezept:
   - **text**: Rezeptname, Zutaten, Zubereitung, Metadaten, Tipps, Quelle
   - **foto**: Hauptbild
   - Quelle: Meist am Rand/Fuß der Seite, z.B. "22 köstlich vegetarisch 02/2026"
3. Ergebnis: `full_recipe_text` (alle Texte konkateniert) + Foto-Dateien in tmp/
4. `image-selector:list_exported_regions` → Validierung

### 2. Text strukturieren
Aus `full_recipe_text` folgende Felder extrahieren:

| Feld | Suchbegriffe | Variable |
|------|-------------|----------|
| Rezeptname | Erste Überschrift; Fallback: Nutzer fragen | `recipe_name` |
| Untertitel | Kurzbeschreibung unter Rezeptname | `subtitle` |
| Portionen | "für X Personen", "Portionen:", "Ergibt:", "X Stück" | `portions` |
| Vorbereitungszeit | "Vorbereitungszeit:", "Vorbereitung:" | `prep_time` |
| Zubereitungszeit | "Zubereitungszeit:", "Backzeit:", "Kochzeit:" | `cook_time` |
| Wartezeit | "Wartezeit:", "Ruhezeit:", "Kühlzeit:" | `wait_time` |
| Gesamtzeit | Summe oder "Gesamtzeit:" | `total_time` |
| Zutaten | Nach "Zutaten:", "Für den Teig:", "Du brauchst:" – Zeilen mit Mengenangaben | `ingredients` |
| Zubereitung | Nach "Zubereitung:", "So geht's:" – Nummerierte Schritte/Absätze | `instructions` |
| Tipps | "Tipp:", "Hinweis:", "Info:" | `tips` |
| Nährwerte | "Nährwerte pro Portion:", "kcal" | `nutrition` |
| Quelle | Kurze Textregion (<100 Zeichen) mit Jahreszahl/Monatsangabe, keine Rezept-Keywords | `source` |

**Regeln**:
- Leerzeichen zwischen Menge und Einheit sicherstellen ("250g" → "250 g")
- Zeitangaben zusätzlich als ISO 8601 Duration speichern (`_iso`-Varianten)
- Quelle bereinigen: Seitenzahlen am Anfang/Ende entfernen, "Bild auf Seite X" entfernen
- Validierung: Rezeptname, mindestens 3 Zutaten, Zubereitungsschritte vorhanden?

### 3. Bild verarbeiten
1. `filesystem:list_directory` in tmp/ → `*_foto.png` filtern
2. **Erstes** Foto automatisch verwenden (keine Rückfrage). Bei 0 Fotos: `image_available = false`
3. URL-sicheren Dateinamen aus `recipe_name` erstellen (Umlaute transliterieren, Sonderzeichen entfernen, Leerzeichen → Bindestrich, max 50 Zeichen) → `safe_image_name`
4. `filesystem:move_file` nach `Ausgang/Images/<safe_image_name>.png` (bei Konflikt: Suffix _2, _3)

### 4. HTML generieren
1. `filesystem:read_file` von `Ausgang/Template.html`
2. Tags ersetzen:

| Tag | Wert |
|-----|------|
| `<TITLE>`, `<RECIPE_NAME>` | recipe_name |
| `<SUBTITLE>` | subtitle |
| `<IMAGE_PATH>` | "Images/" + safe_image_name (oder Platzhalter/hidden) |
| `<PREP_TIME>`, `<PREP_TIME_ISO>` | prep_time, prep_time_iso |
| `<COOK_TIME>`, `<COOK_TIME_ISO>` | cook_time, cook_time_iso |
| `<WAIT_TIME>`, `<WAIT_TIME_ISO>` | wait_time, wait_time_iso |
| `<TOTAL_TIME>`, `<TOTAL_TIME_ISO>` | total_time, total_time_iso |
| `<PORTIONS>` | portions |
| `<INGREDIENTS>` | Als `<ul><li>` Liste |
| `<INSTRUCTIONS>` | Als `<ol><li>` Liste |
| `<TIPS>` | tips |
| `<NUTRITION>` | nutrition |
| `<SOURCE>` | source |

3. `filesystem:save_file` → `Ausgang/<safe_recipe_name>.html`

### 5. Index aktualisieren
1. `recipe-index:check_duplicate_recipe` → Bei Duplikat: Nutzer fragen (Überschreiben/Suffix/Abbrechen)
2. `recipe-index:suggest_recipe_category` → Nutzer bestätigen lassen
   - Kategorien: Salate, Suppen, Vorspeisen & Snacks, Hauptgerichte, Brot & Gebäck, Desserts & Kuchen, Sonstiges
3. `recipe-index:add_recipe_to_index` (recipe_file, recipe_name, category)
4. `recipe-index:count_recipes` → Validierung

### 6. Qualitätsprüfung
1. `windows-launcher:open_in_edge` → HTML öffnen
2. Prüfen: Rezeptname, Zutaten, Schritte, Bild, Umlaute, OCR-Fehler (0↔O, rn↔m, l↔I), Formatierung
3. Bei Fehlern: `filesystem:edit_file` korrigieren; bei Namensänderung: Index remove + add

### 7. Protokollierung
`filesystem:append_file` → `Ausgang/processing_log.txt`:
```
[Datum Zeit] ✓ ERFOLG | PDF: X | Rezept: X | HTML: X | Bild: X | Quelle: X | Kategorie: X | Zutaten: X | Schritte: X | Index: X Rezepte gesamt
```

### 8. Weitere Rezepte?
- **Ja**: Zurück zu Schritt 1. Bei mehreren Rezepten im selben PDF: gleiche Datei erneut öffnen, andere Regionen markieren.
- **Nein**: Abschlussmeldung mit Zusammenfassung (erstellte Dateien, Index-Statistik).
"""
