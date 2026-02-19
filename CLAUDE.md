# CLAUDE.md

Projektstruktur, Installation und Befehle stehen in der README.md.
Hier nur Architektur-Wissen und Konventionen fuer die Entwicklung.

## Architektur-Pattern

- **Zentrale Server-Registrierung**: `server.py` importiert reine Funktionen aus `tools/`
  und wrapped sie mit `@mcp.tool()` + Logging. Tool-Module haben keine FastMCP-Abhaengigkeit.
- **FastMCP-Internals in Tests** (FastMCP >= 3.0): `asyncio.run(mcp.list_tools())` liefert
  Liste mit `.name`; `asyncio.run(mcp.get_tool("name"))` liefert Tool-Objekt mit `.fn()`;
  analog `mcp.list_prompts()` / `mcp.get_prompt("name")` fuer Prompts.
- **Shared Utils in `core/`**: Gemeinsam genutzte Funktionen (`get_working_dir`,
  `create_tmp_dir_if_needed`, `cleanup_tmp_dir`, `get_image_subdirectory`) leben in
  `core/utils.py`. Image-selector-spezifisches (`transform_coords`) bleibt in
  `image_selector/utils.py`.
- **Working Directory**: Wird ueber `IMAGE_SELECTOR_WORKING_DIR` Env-Var gesteuert
  (Fallback: `os.getcwd()`). Tests nutzen `monkeypatch.setenv()` mit `tmp_path`.

## Code-Stil

- **Formatter**: black (bestimmt Quote-Style → double quotes)
- **Linter**: flake8 (Konfiguration in `.flake8`)
  - max-line-length = 88 (kompatibel mit black)
  - max-complexity = 10 (McCabe)
  - extend-ignore: E203, E501, W503, E402
  - Docstrings: Google-Style
- **Kein flake8-quotes** – bewusst entfernt, black steuert Quotes
- Sprache in Code/Docstrings: Deutsch (Umlaute in Docstrings vermieden, z.B. "ue" statt "ue")

## Implementierungs-Details

- Build-System: hatchling (`build-backend = "hatchling.build"`)
- Python >= 3.11 (verwendet `str | None` Union-Syntax)
- gui.py-Methoden haben `# pragma: no cover` (Tkinter nicht testbar in CI)
- `_UNIT_PATTERN` in html_builder.py: Case-sensitive (EL, TL sind Grossbuchstaben)
- `_clean_source` Regex: `(?<!/)` Negative Lookbehind verhindert,
  dass Jahreszahlen nach "/" entfernt werden (z.B. "03/2025")
