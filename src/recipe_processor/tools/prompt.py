# -*- coding: utf-8 -*-
"""Prompt-Template fuer Rezept-Extraktion aus PDFs."""

RECIPE_PROMPT = r"""
# Rezept-Extraktion aus PDF

## Verfuegbare Tools
| Tool | Zweck |
|------|-------|
| `select_image_regions_tool` | GUI zur Bildausschnitt-Selektion mit OCR |
| `get_working_directory_tool` | Zeigt das Arbeitsverzeichnis an |
| `build_recipe_html_tool` | Erzeugt HTML, ordnet Bild zu, aktualisiert Index |

## Verzeichnisse
| Pfad | Zweck |
|------|-------|
| Eingang/ | PDFs und Bilder (koennen mehrere Rezepte enthalten) |
| Ausgang/ | HTML-Dateien, index.html, Template.html |
| Ausgang/Images/ | Rezeptbilder |
| tmp/ | Temporaer (OCR-Ergebnisse, wird automatisch verwaltet) |

---

## Workflow

### 1. Bildauswahl & OCR
1. `select_image_regions_tool` aufrufen (ohne Parameter → laedt automatisch Bilder aus Eingang/)
2. Nutzer markiert Regionen fuer **ein** Rezept:
   - **text**: Rezeptname, Zutaten, Zubereitung, Metadaten, Tipps, Quelle
   - **foto**: Hauptbild des Rezepts
3. Ergebnis: `full_recipe_text` (OCR aller Textregionen) + Foto-Dateien in tmp/

### 2. OCR-Text interpretieren und strukturieren
Die OCR-Erkennungsrate ist oft niedrig. Den Text sorgfaeltig interpretieren
und folgende Felder extrahieren:

| Feld | Hinweise |
|------|----------|
| `recipe_name` | Erste Ueberschrift; Fallback: Nutzer fragen |
| `subtitle` | Kurzbeschreibung unter dem Rezeptnamen |
| `portions` | "fuer X Personen", "X Stueck", "Ergibt:" |
| `prep_time` | "Vorbereitungszeit:", "Vorbereitung:" (z.B. "15 Min") |
| `cook_time` | "Zubereitungszeit:", "Backzeit:", "Kochzeit:" (z.B. "30 Min") |
| `wait_time` | "Wartezeit:", "Ruhezeit:", "Kuehlzeit:" (z.B. "1 Std") |
| `ingredients` | Liste der Zutaten (nach "Zutaten:", "Du brauchst:") |
| `instructions` | Liste der Zubereitungsschritte (nach "Zubereitung:", "So geht's:") |
| `cookware` | Liste der benoetigten Kuechengeraete (z.B. ["Pfanne", "Topf", "Backofen"]) – optional |
| `tips` | "Tipp:", "Hinweis:", "Info:" |
| `nutrition` | "Naehrwerte pro Portion:", "kcal" |
| `source` | Kurze Quellenangabe mit Jahreszahl/Monat (oft am Seitenrand/-fuss) |
| `category` | Eine der folgenden Kategorien: Salate, Suppen, Vorspeisen & Snacks, Hauptgerichte, Brot & Gebaeck, Desserts & Kuchen. Keine eigenen Kategorien erfinden! Wenn leer, wird automatisch vorgeschlagen. |

**OCR-Korrektur** – Haeufige Fehlerkennungen beachten:
- `0` ↔ `O`, `rn` ↔ `m`, `l` ↔ `I` ↔ `1`, `ii` ↔ `ü`
- Zusammengezogene oder getrennte Woerter korrigieren
- Umlaute rekonstruieren (ae→ä, oe→ö, ue→ü, ss→ß wo sinnvoll)

**Zutaten-Ueberschriften**: Gruppen wie "Fuer den Teig", "Fuer die Sauce"
als `--- Ueberschrift ---` in die ingredients-Liste einfuegen.

**Zutaten mit gleicher Menge**: "je 1 TL Kreuzkuemmel und Chilipulver" unveraendert
uebernehmen – das Tool vereinzelt sie automatisch.

**Kuechengeraete** (`cookware`): Wenn im Rezepttext explizit Geraete erwaehnt werden
(z.B. "in einer beschichteten Pfanne", "im vorgeheizten Backofen"), als Liste extrahieren.
Wenn keine Geraete genannt, Feld weglassen.

**Validierung** vor dem Aufruf:
- Rezeptname vorhanden?
- Mindestens 3 Zutaten?
- Mindestens 1 Zubereitungsschritt?
- Bei fehlenden Pflichtfeldern: Nutzer fragen

### 3. HTML erzeugen
`build_recipe_html_tool` mit den strukturierten Daten aufrufen.

Das Tool uebernimmt automatisch:
- Dateinamen-Sanitisierung (Umlaute, Sonderzeichen)
- Leerzeichen zwischen Menge und Einheit ("250g" → "250 g")
- ISO-Zeitformate berechnen
- Quellen-Bereinigung (Seitenzahlen entfernen)
- Template-Befuellung und HTML-Speicherung
- Foto aus tmp/ zuordnen und nach Ausgang/Images/ kopieren
- index.html aktualisieren (oder aus Template erzeugen falls nicht vorhanden)

### 4. Qualitaetspruefung
Erzeugte HTML-Datei im Edge-Browser oeffnen, damit der Nutzer das Ergebnis pruefen kann.
Ergebnis pruefen:
- Rezeptname korrekt? Umlaute richtig?
- Zutaten vollstaendig und plausibel?
- Zubereitungsschritte in richtiger Reihenfolge?
- Quelle erkannt?
- Bei Fehlern: `build_recipe_html_tool` erneut aufrufen

### 5. Weitere Rezepte?
- **Ja**: Zurueck zu Schritt 1. Bei mehreren Rezepten im selben PDF:
  `select_image_regions_tool` erneut aufrufen, andere Regionen markieren.
- **Nein**: Abschlussmeldung mit Zusammenfassung.
"""
