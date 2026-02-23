# recipe-tools

MCP-Server zur Rezept-Extraktion aus PDFs oder JPG-Dateien. Stellt Prompts und Tools bereit, mit denen
ein LLM-Client (Claude Desktop, Cursor, etc.) gescannte Rezepte interaktiv in strukturierte
HTML-Dateien umwandeln kann.

## Funktionsweise

Der `FastMCP`-Server in `server.py` registriert alle Endpunkte zentral:

- **Prompt** `generate_recipe` -- Rezept-Workflow fuer MCP-Clients mit Prompt-Unterstuetzung
- **Tool** `get_recipe_prompt` -- Rezept-Workflow fuer Clients die nur Tools unterstuetzen
- **Tool** `select_image_regions_tool` -- Web-GUI zur Bildausschnitt-Selektion mit OCR (oeffnet Browser automatisch)
- **Tool** `get_working_directory_tool` -- Zeigt das Arbeitsverzeichnis an
- **Tool** `build_recipe_html_tool` -- Erzeugt HTML aus strukturierten Rezeptdaten und aktualisiert den Index (erzeugt `index.html` automatisch aus Template, falls nicht vorhanden)
- **Tool** `get_server_version` -- Gibt die aktuelle Versionsnummer des Servers zurueck

## Projektstruktur

```
recipe-tools/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── .flake8
├── src/
│   └── recipe_processor/
│       ├── __init__.py
│       ├── server.py                  # Zentraler MCP-Server (FastMCP)
│       ├── assets/
│       │   ├── Template.html          # HTML-Template fuer einzelne Rezepte
│       │   └── index_template.html    # HTML-Template fuer die Rezeptuebersicht
│       ├── core/
│       │   ├── __init__.py
│       │   ├── utils.py              # Gemeinsame Utils (Pfade, Verzeichnisse)
│       │   └── recipes_index.py      # Rezept-Index-Verwaltung (HTML-Manipulation)
│       └── tools/
│           ├── __init__.py
│           ├── prompt.py              # RECIPE_PROMPT Konstante
│           ├── html_builder.py        # HTML-Erzeugung aus Rezeptdaten
│           └── image_selector/
│               ├── __init__.py
│               ├── tools.py           # Tool-Funktionen (select, list, get_dir)
│               ├── web_gui.py         # Browser-GUI (FastAPI + HTML Canvas)
│               ├── gui.py             # Tkinter-GUI (inaktiv, Backup)
│               ├── export.py          # Region-Export + OCR
│               ├── pdf_utils.py       # PDF-Bildextraktion (PyMuPDF)
│               └── utils.py           # transform_coords (image_selector-spezifisch)
└── tests/
    ├── __init__.py
    ├── test_prompt.py
    ├── test_server.py
    ├── test_html_builder.py
    ├── test_image_selector_tools.py
    ├── test_web_gui.py
    └── test_recipes_index.py
```

## Installation

### uv installieren (einmalig)

```powershell
# Option 1: winget
winget install astral-sh.uv

# Option 2: pip
pip install uv
```

Danach Terminal neu starten, damit `uv` im PATH ist.

### Umgebungsvariable setzen (einmalig, damit uv `venv/` statt `.venv/` verwendet)

```powershell
[System.Environment]::SetEnvironmentVariable("UV_PROJECT_ENVIRONMENT", "venv", "User")
```

Danach Terminal neu starten.

### Projekt einrichten

```bash
uv sync --extra dev
git config core.hooksPath .githooks
```

uv legt `venv/` an, installiert alle Abhaengigkeiten und sperrt die genauen
Versionen in `uv.lock`. Der zweite Befehl aktiviert den pre-push Hook (laeuft
einmalig nach dem Klonen).

### Voraussetzung

[Tesseract OCR](https://github.com/tesseract-ocr/tesseract) muss installiert und im PATH sein.

## MCP-Server konfigurieren

Beispielkonfiguration fuer Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "recipe-server": {
      "command": "path/to/venv/Scripts/recipe-server",
      "env": {
        "IMAGE_SELECTOR_WORKING_DIR": "C:/Rezepte",
        "IMAGE_SUBDIRECTORY": "Eingang"
      }
    }
  }
}
```

### Server manuell starten

```bash
uv run recipe-server
```

Oder als Modul:

```bash
uv run python -m recipe_processor.server
```

## Tests und Linting

```bash
uv run pytest
uv run flake8 src/ tests/
uv run black src/ tests/
```

Der pre-push Hook (`.githooks/pre-push`) fuehrt diese drei Schritte automatisch
vor jedem `git push` aus: black formatiert den Code, flake8 prueft auf Fehler,
pytest fuehrt die Tests aus. Hat black Aenderungen vorgenommen, wird der Push
abgebrochen -- die Formatierungen muessen dann noch committet werden.

## CI/CD

Die GitHub Actions Workflows (`.github/workflows/`) verwenden ebenfalls `uv`:

- **CI** (`ci.yml`): laeuft bei jedem Push und PR -- Linting, Formatierung, Tests
- **Release** (`release.yml`): erstellt bei Pushes auf `main` automatisch ein neues
  Release per `python-semantic-release`, wenn konventionelle Commits vorhanden sind
  (`feat:`, `fix:`, etc.). Nach einem Release wird `uv.lock` automatisch
  aktualisiert und mit `[skip ci]` committed.

`uv.lock` ist Teil des Repositories und sichert reproduzierbare Installs. Nach
einem `git pull` genuegt `uv sync --extra dev`, um die Umgebung zu aktualisieren.

## Standalone-Modi (ohne MCP-Server)

### Image Selector (Web-GUI)

```bash
uv run python -m recipe_processor.tools.image_selector.tools --standalone
```

Oeffnet die Browser-GUI automatisch. Laedt die `.env`-Datei automatisch (via `python-dotenv`).
Ohne Argumente werden Bilder aus `IMAGE_SUBDIRECTORY` geladen.
Optional kann ein Bildpfad direkt uebergeben werden:

```bash
uv run python -m recipe_processor.tools.image_selector.tools --standalone pfad/zum/bild.jpg
```

### HTML Builder

```bash
uv run python -m recipe_processor.tools.html_builder rezept.json
```

Erzeugt eine HTML-Datei aus einer JSON-Datei mit Rezeptdaten. Die JSON-Datei
enthaelt die gleichen Felder wie die `build_recipe_html`-Funktion (`recipe_name`,
`ingredients`, `instructions`, etc.). Laedt die `.env`-Datei automatisch.

### Umgebungsvariablen (.env)

| Variable | Beschreibung | Default |
|----------|-------------|---------|
| `IMAGE_SELECTOR_WORKING_DIR` | Arbeitsverzeichnis | `os.getcwd()` |
| `IMAGE_SUBDIRECTORY` | Unterverzeichnis fuer Bilder (relativ zum Working Dir) | `""` (Working Dir selbst) |

## Templates

Im Verzeichnis `src/recipe_processor/assets/` liegen zwei HTML-Templates:

- **Template.html** -- Vorlage fuer einzelne Rezept-HTML-Dateien. Platzhalter werden beim Erzeugen ersetzt:

  | Platzhalter | Inhalt |
  |-------------|--------|
  | `<RECIPE_NAME>`, `<TITLE>` | Rezeptname |
  | `<SUBTITLE>` | Kurzbeschreibung |
  | `<IMAGE_PATH>` | Relativer Bildpfad |
  | `<PREP_TIME>`, `<COOK_TIME>`, `<WAIT_TIME>`, `<TOTAL_TIME>` | Zeitangaben (Text) |
  | `<PREP_TIME_ISO>`, `<COOK_TIME_ISO>`, `<WAIT_TIME_ISO>`, `<TOTAL_TIME_ISO>` | Zeitangaben (ISO 8601) |
  | `<PORTIONS>` | Portionsangabe |
  | `<COOKWARE>` | Benoetigte Kuechengeraete (kommagetrennt) |
  | `<INGREDIENTS>` | Zutatenliste als `<ul>` |
  | `<INSTRUCTIONS>` | Zubereitungsschritte als `<ol>` |
  | `<TIPS>` | Tipps und Hinweise |
  | `<NUTRITION>` | Naehrwertangaben |
  | `<SOURCE>` | Quellangabe |

- **index_template.html** -- Vorlage fuer die Rezeptuebersicht (`index.html`). Enthaelt den Platzhalter `<CATEGORIES>`, der durch die Kategorie-Sections ersetzt wird. Wird automatisch verwendet, wenn im Ausgangsverzeichnis noch keine `index.html` existiert.

### Zutaten-Ueberschriften

Innerhalb der Zutatenliste koennen Ueberschriften mit dem Muster `--- Text ---` markiert werden. Diese werden automatisch in `<b>Text</b>` umgewandelt.

### Zutaten mit gleicher Menge ("je"-Syntax)

Zutaten der Form `je 1 TL Kreuzkuemmel und Chilipulver` werden automatisch in
einzelne Eintraege mit gleicher Menge aufgesplittet:

```
je 1 TL Kreuzkümmel und Chilipulver  →  1 TL Kreuzkümmel
                                         1 TL Chilipulver
je 1 TL Salz, Pfeffer und Paprika    →  1 TL Salz
                                         1 TL Pfeffer
                                         1 TL Paprika
```

Bekannte Einheiten: `g`, `kg`, `mg`, `l`, `ml`, `cl`, `dl`, `EL`, `TL`, `Stk`, `Pck`, `Pkg`, `Pr`, `Prise`, `Msp`, `Bd`, `Bund`.

### Kuechengeraete (`cookware`)

Das optionale Feld `cookware` nimmt eine Liste von Geraeten entgegen und gibt sie
kommagetrennt im HTML-Abschnitt "Kuechengeraete" aus. Fehlt das Feld oder ist es leer,
wird der Abschnitt komplett ausgeblendet.

### Optionale Felder und bedingte HTML-Bloecke

Die Felder `prep_time`, `cook_time`, `wait_time`, `cookware`, `tips`, `nutrition`
und `source` sind optional. Ist ein Feld leer, wird der zugehoerige HTML-Block
vollstaendig weggelassen (keine leere Ueberschrift im Output).

## Abhaengigkeiten

| Paket | Zweck |
|-------|-------|
| fastmcp | MCP-Server-Framework |
| Pillow | Bildverarbeitung |
| PyMuPDF | PDF-Bildextraktion |
| pytesseract | OCR-Texterkennung |
| beautifulsoup4 | HTML-Parsing (Rezept-Index) |
| lxml | HTML-Parser-Backend fuer BeautifulSoup |
| python-dotenv | .env-Datei laden (Standalone-Modus) |
| fastapi | Web-Framework fuer Browser-GUI |
| uvicorn | ASGI-Server fuer Browser-GUI |
