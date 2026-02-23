"""Web-basierte GUI-Komponente fuer die Bildausschnitt-Selektion.

Stellt eine FastAPI-basierte Web-GUI bereit, die im Standard-Browser geoeffnet
wird. Bilder werden als Base64-kodierte PNG-Daten an den Browser uebertragen;
Benutzerinteraktion erfolgt ueber einen HTML Canvas mit Maus-Drag. Die Methode
run() blockiert synchron bis der Benutzer auf 'Fertig & Exportieren' klickt.
"""

import base64
import io
import os
import socket
import threading
import time
import webbrowser

from PIL import Image

_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Bildausschnitt-Selector</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; display: flex; flex-direction: column; height: 100vh; overflow: hidden; background: #fff; }
    #toolbar { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f0f0f0; border-bottom: 2px solid #ccc; flex-shrink: 0; flex-wrap: wrap; }
    #toolbar label { font-size: 13px; cursor: pointer; }
    #toolbar button { padding: 6px 12px; cursor: pointer; border: none; border-radius: 4px; font-size: 13px; font-weight: bold; }
    #btn-save { background: #4CAF50; color: white; }
    #btn-finish { background: #2196F3; color: white; }
    #btn-clear { background: #f44336; color: white; }
    #btn-menu { background: #ddd; font-size: 18px; padding: 4px 10px; }
    .sep { width: 1px; height: 24px; background: #ccc; }
    #main { display: flex; flex: 1; overflow: hidden; }
    #canvas-container { flex: 1; overflow: auto; background: #888; padding: 8px; }
    #mainCanvas { cursor: crosshair; display: block; user-select: none; }
    #sidebar { width: 210px; flex-shrink: 0; display: flex; flex-direction: column; border-left: 1px solid #ccc; background: #fafafa; overflow: hidden; }
    .sidebar-section { padding: 8px; border-bottom: 1px solid #eee; flex: 1; display: flex; flex-direction: column; overflow: hidden; min-height: 80px; }
    .sidebar-section h4 { font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #333; }
    .sidebar-list { list-style: none; overflow-y: auto; flex: 1; }
    .sidebar-list li { padding: 4px 6px; font-size: 12px; cursor: pointer; border-radius: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .sidebar-list li:hover { background: #e8e8e8; }
    .sidebar-list li.active { background: #d0e8ff; font-weight: bold; }
    #status { padding: 5px 10px; font-size: 12px; background: #f5f5f5; border-top: 1px solid #ccc; flex-shrink: 0; }
    #menu-container { position: relative; }
    #dropdown { display: none; position: absolute; top: 100%; left: 0; z-index: 100; background: white; border: 1px solid #ccc; border-radius: 4px; box-shadow: 2px 2px 8px rgba(0,0,0,.2); min-width: 190px; }
    #dropdown.open { display: block; }
    .menu-item { padding: 8px 16px; cursor: pointer; font-size: 13px; }
    .menu-item:hover { background: #f0f0f0; }
    .menu-sep { border-top: 1px solid #eee; margin: 4px 0; }
    .menu-hdr { padding: 6px 16px; font-size: 11px; color: #999; }
    #modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.4); z-index: 200; align-items: center; justify-content: center; }
    #modal-overlay.open { display: flex; }
    #modal-box { background: white; padding: 24px; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,.3); min-width: 420px; }
    #modal-box h3 { margin-bottom: 12px; }
    #modal-path { width: 100%; padding: 8px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 12px; }
    .modal-btns { display: flex; gap: 8px; justify-content: flex-end; }
    .modal-btns button { padding: 6px 16px; cursor: pointer; border: none; border-radius: 4px; font-size: 13px; }
    #modal-ok { background: #2196F3; color: white; font-weight: bold; }
    #modal-cancel2 { background: #eee; }
    #finish-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.5); z-index: 300; align-items: center; justify-content: center; }
    #finish-overlay.open { display: flex; }
    #finish-box { background: white; padding: 48px 56px; border-radius: 8px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,.3); }
    #finish-box h2 { color: #2196F3; margin-bottom: 10px; }
  </style>
</head>
<body>
<div id="toolbar">
  <div id="menu-container">
    <button id="btn-menu" onclick="toggleMenu()">&#9776;</button>
    <div id="dropdown">
      <div class="menu-hdr">Bild drehen</div>
      <div class="menu-item" onclick="rotateImage(-90);closeMenu();">&#8634; 90&deg; links</div>
      <div class="menu-item" onclick="rotateImage(90);closeMenu();">&#8635; 90&deg; rechts</div>
      <div class="menu-item" onclick="rotateImage(180);closeMenu();">&#8635; 180&deg;</div>
      <div class="menu-sep"></div>
      <div class="menu-item" onclick="showAddModal();closeMenu();">&#10133; Bild hinzuf&uuml;gen</div>
    </div>
  </div>
  <div class="sep"></div>
  <span style="font-size:13px">Modus:</span>
  <label><input type="radio" name="mode" value="foto" checked onchange="st.mode=this.value"> Foto</label>
  <label><input type="radio" name="mode" value="text" onchange="st.mode=this.value"> Text</label>
  <div class="sep"></div>
  <button id="btn-save" onclick="saveSelection()">Auswahl speichern</button>
  <button id="btn-finish" onclick="finishSelection()">&check; Fertig &amp; Exportieren</button>
  <button id="btn-clear" onclick="clearRegions()">Bereiche l&ouml;schen</button>
</div>
<div id="main">
  <div id="canvas-container">
    <canvas id="mainCanvas"></canvas>
  </div>
  <div id="sidebar">
    <div class="sidebar-section">
      <h4>Geladene Bilder:</h4>
      <ul class="sidebar-list" id="img-list"></ul>
    </div>
    <div class="sidebar-section">
      <h4>Gespeicherte Bereiche:</h4>
      <ul class="sidebar-list" id="reg-list"></ul>
    </div>
  </div>
</div>
<div id="status">Lade...</div>
<div id="modal-overlay">
  <div id="modal-box">
    <h3>Bild hinzuf&uuml;gen</h3>
    <input type="text" id="modal-path" placeholder="Absoluter Dateipfad, z.B. C:\\Bilder\\scan.jpg">
    <div class="modal-btns">
      <button id="modal-cancel2" onclick="closeModal()">Abbrechen</button>
      <button id="modal-ok" onclick="submitAdd()">Hinzuf&uuml;gen</button>
    </div>
  </div>
</div>
<div id="finish-overlay">
  <div id="finish-box">
    <h2>&#10003; Fertig!</h2>
    <p>Dieses Fenster kann jetzt geschlossen werden.</p>
  </div>
</div>
<script>
const canvas = document.getElementById("mainCanvas");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");
const st = { mode: "foto", dragging: false, dragStart: null, dragEnd: null, pending: null, srv: null, img: new Image() };

function setStatus(m) { statusEl.textContent = m; }

function getPos(e) {
  const r = canvas.getBoundingClientRect();
  return { x: (e.clientX - r.left) * (canvas.width / r.width), y: (e.clientY - r.top) * (canvas.height / r.height) };
}

function redraw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (st.img.complete && st.img.naturalWidth > 0) ctx.drawImage(st.img, 0, 0);
  if (st.srv) {
    for (const r of st.srv.regions) {
      const [x1, y1, x2, y2] = r.coords;
      const c = r.mode === "foto" ? "#0055ff" : "#008800";
      ctx.strokeStyle = c; ctx.lineWidth = 3; ctx.setLineDash([]);
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      ctx.fillStyle = r.mode === "foto" ? "rgba(0,85,255,0.08)" : "rgba(0,136,0,0.08)";
      ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
      ctx.fillStyle = c; ctx.font = "bold 13px Arial";
      ctx.fillText(r.label, x1 + 4, y1 + 16);
    }
  }
  if (st.pending) {
    const {x1, y1, x2, y2} = st.pending;
    ctx.strokeStyle = st.mode === "foto" ? "#0055ff" : "#008800";
    ctx.lineWidth = 3; ctx.setLineDash([8, 4]);
    ctx.strokeRect(x1, y1, x2 - x1, y2 - y1); ctx.setLineDash([]);
  }
  if (st.dragging && st.dragStart && st.dragEnd) {
    ctx.strokeStyle = st.mode === "foto" ? "#0055ff" : "#008800";
    ctx.lineWidth = 2; ctx.setLineDash([5, 5]);
    ctx.strokeRect(st.dragStart.x, st.dragStart.y, st.dragEnd.x - st.dragStart.x, st.dragEnd.y - st.dragStart.y);
    ctx.setLineDash([]);
  }
}

canvas.addEventListener("mousedown", e => { const p = getPos(e); st.dragging = true; st.dragStart = p; st.dragEnd = p; st.pending = null; redraw(); });
canvas.addEventListener("mousemove", e => { if (!st.dragging) return; st.dragEnd = getPos(e); redraw(); });
canvas.addEventListener("mouseup", e => {
  if (!st.dragging) return;
  st.dragging = false;
  const p = getPos(e);
  const x1 = Math.min(st.dragStart.x, p.x), y1 = Math.min(st.dragStart.y, p.y);
  const x2 = Math.max(st.dragStart.x, p.x), y2 = Math.max(st.dragStart.y, p.y);
  if (Math.abs(x2 - x1) > 5 && Math.abs(y2 - y1) > 5) {
    st.pending = {x1, y1, x2, y2};
    setStatus("Auswahl: " + Math.round(x2-x1) + " x " + Math.round(y2-y1) + " px - Klicken Sie 'Auswahl speichern'");
  }
  redraw();
});

async function post(path, body) {
  const r = await fetch(path, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body || {}) });
  return r.json();
}

async function loadImg(dataUrl, w, h) {
  return new Promise(res => {
    canvas.width = w; canvas.height = h;
    st.img = new Image();
    st.img.onload = () => { redraw(); res(); };
    st.img.src = dataUrl;
  });
}

async function switchImage(idx) {
  await post("/api/select_image/" + idx);
  const d = await (await fetch("/api/image/" + idx)).json();
  await loadImg(d.data_url, d.width, d.height);
  st.pending = null;
  const s = await (await fetch("/api/state")).json();
  st.srv = s;
  updateSidebars();
}

async function saveSelection() {
  if (!st.pending) { setStatus("Kein Bereich ausgewaehlt - bitte zuerst einen Bereich aufziehen"); return; }
  const {x1, y1, x2, y2} = st.pending;
  const r = await post("/api/save_region", {x1, y1, x2, y2, mode: st.mode});
  if (r.ok) { st.pending = null; st.srv = r.state; updateSidebars(); setStatus("\\u2713 Bereich " + r.state.regions.length + " gespeichert (" + st.mode + ")"); redraw(); }
  else setStatus("Fehler: " + r.error);
}

async function finishSelection() {
  const r = await post("/api/finish");
  if (r.ok) document.getElementById("finish-overlay").classList.add("open");
  else setStatus("Fehler: " + (r.error || "Bitte mindestens einen Bereich auswaehlen"));
}

async function clearRegions() {
  if (!st.srv || !st.srv.regions.length) { setStatus("Keine Bereiche zum Loeschen"); return; }
  if (!confirm("Alle Bereiche loeschen?")) return;
  await post("/api/clear_regions");
  st.pending = null;
  const s = await (await fetch("/api/state")).json();
  st.srv = s; updateSidebars(); redraw();
  setStatus("Alle Bereiche geloescht");
}

async function rotateImage(angle) {
  const r = await post("/api/rotate", {angle});
  if (r.ok) {
    await loadImg(r.image.data_url, r.image.width, r.image.height);
    st.srv = r.state; st.pending = null;
    updateSidebars();
    const lbl = {90: "90\\u00b0 rechts", "-90": "90\\u00b0 links", 180: "180\\u00b0"}["" + angle] || angle + "\\u00b0";
    setStatus("Bild um " + lbl + " gedreht - Bereiche zurueckgesetzt");
    redraw();
  }
}

function updateSidebars() {
  const il = document.getElementById("img-list"), rl = document.getElementById("reg-list");
  il.innerHTML = ""; rl.innerHTML = "";
  if (!st.srv) return;
  for (const img of st.srv.images) {
    const li = document.createElement("li");
    li.textContent = (img.is_current ? "\\u25b6 " : "  ") + img.name + " [" + img.region_count + "]";
    if (img.is_current) li.classList.add("active");
    li.onclick = () => switchImage(img.index);
    il.appendChild(li);
  }
  for (const r of st.srv.regions) {
    const li = document.createElement("li"); li.textContent = r.label; rl.appendChild(li);
  }
}

function toggleMenu() { document.getElementById("dropdown").classList.toggle("open"); }
function closeMenu() { document.getElementById("dropdown").classList.remove("open"); }
document.addEventListener("click", e => { if (!document.getElementById("menu-container").contains(e.target)) closeMenu(); });

function showAddModal() { document.getElementById("modal-path").value = ""; document.getElementById("modal-overlay").classList.add("open"); setTimeout(() => document.getElementById("modal-path").focus(), 50); }
function closeModal() { document.getElementById("modal-overlay").classList.remove("open"); }
async function submitAdd() {
  const path = document.getElementById("modal-path").value.trim();
  if (!path) return;
  const r = await post("/api/add_image", {path});
  closeModal();
  if (r.ok) { await switchImage(r.new_index); setStatus("\\u2713 Bild hinzugef\\u00fcgt: " + path.split(/[\\\\/]/).pop()); }
  else setStatus("Fehler: " + r.error);
}
document.getElementById("modal-path").addEventListener("keydown", e => { if (e.key === "Enter") submitAdd(); if (e.key === "Escape") closeModal(); });

window.addEventListener("load", async () => {
  const s = await (await fetch("/api/state")).json();
  st.srv = s;
  if (s.images.length > 0) { await switchImage(0); setStatus("Bereit - Ziehen Sie mit der Maus einen Bereich auf"); }
  else setStatus("Keine Bilder geladen");
});
</script>
</body>
</html>"""


class WebImageSelectorGUI:
    """Web-basierte GUI fuer die interaktive Bildauswahl und Region-Selektion.

    Startet einen lokalen FastAPI-Server und oeffnet den Browser automatisch.
    Unterstuetzt mehrere Bilder gleichzeitig (Multi-Image), PDF-Extraktion,
    Bilddrehung sowie den Export markierter Bereiche als Foto- oder
    Text-Regionen.

    Attributes:
        IMAGE_EXTENSIONS: Tuple der unterstuetzten Bilddatei-Endungen.
        working_dir: Arbeitsverzeichnis fuer den Export.
        create_ui: Ob der Web-Server gestartet wird (False fuer Tests).
        images_data: Liste aller geladenen Bilder mit Metadaten und Regionen.
        current_image_index: Index des aktuell angezeigten Bildes.
        result_ready: True wenn der Benutzer den Export bestaetigt hat.
    """

    IMAGE_EXTENSIONS = (".pdf", ".jpeg", ".jpg", ".png", ".bmp", ".gif")

    def __init__(
        self,
        image_path: str | None = None,
        working_dir: str | None = None,
        create_ui: bool = True,
    ):
        """Initialisiert die Web-GUI und laedt Bilder.

        Args:
            image_path: Pfad zum initialen Bild oder PDF. Wenn None, werden
                die ersten 4 Bilddateien aus dem Arbeitsverzeichnis geladen.
            working_dir: Verzeichnis fuer den Export. Wenn None, wird
                get_working_dir() verwendet.
            create_ui: Wenn True, wird der Web-Server gestartet und der Browser
                geoeffnet. Bei False werden nur die Bilddaten geladen (Tests).
        """
        from recipe_processor.core.utils import cleanup_tmp_dir, get_working_dir

        self.working_dir = working_dir or get_working_dir()
        self.create_ui = create_ui
        self.result_ready = False

        cleanup_tmp_dir()

        self.images_data: list = []
        self.current_image_index = 0
        self.image = None

        # Threading-Event zum Blockieren von run() bis der User fertig ist
        self._done_event = threading.Event()
        self._server = None
        self._server_thread = None
        self._port: int | None = None

        # Aktuelle Selektion (Canvas-Koordinaten)
        self.current_selection: tuple | None = None

        if image_path:
            self._add_image(image_path)
        else:
            self._auto_load_images()

        if self.images_data:
            self._load_current_image()

        if self.create_ui:
            self._app = self._build_app()

    # ------------------------------------------------------------------
    # Properties (Rueckwaertskompatibilitaet mit ImageSelectorGUI)
    # ------------------------------------------------------------------

    @property
    def original_image_path(self) -> str | None:
        """Gibt den originalen Dateipfad des aktuell ausgewaehlten Bildes zurueck."""
        if self.images_data:
            return self.images_data[self.current_image_index]["original_path"]
        return None

    @property
    def image_path(self) -> str | None:
        """Gibt den tatsaechlichen Bildpfad zurueck (bei PDFs der extrahierte Pfad)."""
        if self.images_data:
            return self.images_data[self.current_image_index]["image_path"]
        return None

    @property
    def is_pdf(self) -> bool:
        """Gibt True zurueck, wenn das aktuelle Bild aus einem PDF stammt."""
        if self.images_data:
            return self.images_data[self.current_image_index]["is_pdf"]
        return False

    @property
    def extracted_image_path(self) -> str | None:
        """Gibt den Pfad des aus einem PDF extrahierten Bildes zurueck, oder None."""
        if self.images_data:
            return self.images_data[self.current_image_index]["extracted_path"]
        return None

    @property
    def original_image(self):
        """Gibt das unskalierte PIL.Image des aktuellen Bildes zurueck."""
        if self.images_data:
            return self.images_data[self.current_image_index]["original_image"]
        return None

    @original_image.setter
    def original_image(self, value):
        """Setzt das unskalierte PIL.Image fuer das aktuelle Bild."""
        if self.images_data:
            self.images_data[self.current_image_index]["original_image"] = value

    @property
    def scale_factor(self) -> float:
        """Gibt den aktuellen Skalierungsfaktor (Original -> Canvas) zurueck."""
        if self.images_data:
            return self.images_data[self.current_image_index]["scale_factor"]
        return 1.0

    @scale_factor.setter
    def scale_factor(self, value: float):
        """Setzt den Skalierungsfaktor fuer das aktuelle Bild."""
        if self.images_data:
            self.images_data[self.current_image_index]["scale_factor"] = value

    @property
    def regions(self) -> list:
        """Gibt die Liste der markierten Regionen des aktuellen Bildes zurueck."""
        if self.images_data:
            return self.images_data[self.current_image_index]["regions"]
        return []

    @regions.setter
    def regions(self, value: list):
        """Setzt die Liste der markierten Regionen fuer das aktuelle Bild."""
        if self.images_data:
            self.images_data[self.current_image_index]["regions"] = value

    # ------------------------------------------------------------------
    # Bild-Laden (identische Logik zu gui.py)
    # ------------------------------------------------------------------

    @staticmethod
    def compute_scale(
        img_width: int, img_height: int, canvas_width: int, canvas_height: int
    ) -> float:
        """Berechnet den Skalierungsfaktor, um ein Bild in den Canvas einzupassen.

        Args:
            img_width: Breite des Originalbildes in Pixeln.
            img_height: Hoehe des Originalbildes in Pixeln.
            canvas_width: Verfuegbare Breite des Canvas in Pixeln.
            canvas_height: Verfuegbare Hoehe des Canvas in Pixeln.

        Returns:
            Skalierungsfaktor als float (max. 1.25).
        """
        if img_width <= 0 or img_height <= 0:
            return 1.0
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        return min(scale_x, scale_y, 1.25)

    def _auto_load_images(self):
        """Laedt automatisch die ersten 4 Bilddateien aus dem Bildverzeichnis."""
        from recipe_processor.core.utils import get_image_subdirectory

        scan_dir = get_image_subdirectory()
        try:
            files = sorted(os.listdir(scan_dir))
        except OSError:
            return

        loaded = 0
        for filename in files:
            if loaded >= 4:
                break
            if filename.lower().endswith(self.IMAGE_EXTENSIONS):
                full_path = os.path.join(scan_dir, filename)
                if os.path.isfile(full_path):
                    try:
                        self._add_image(full_path)
                        loaded += 1
                    except Exception:
                        pass

    def _add_image(self, image_path: str):
        """Fuegt ein neues Bild oder PDF zur internen Bildliste hinzu.

        Args:
            image_path: Absoluter oder relativer Pfad zum Bild oder PDF.

        Raises:
            ValueError: Wenn aus einem PDF kein Bild extrahiert werden konnte.
        """
        from pathlib import Path

        from .pdf_utils import extract_image_from_pdf

        is_pdf = image_path.lower().endswith(".pdf")
        extracted_path = None

        if is_pdf:
            if Path(image_path).is_absolute():
                extracted_path = extract_image_from_pdf(image_path)
            else:
                extracted_path = extract_image_from_pdf(
                    os.path.join(self.working_dir, image_path)
                )
            if extracted_path is None:
                raise ValueError(
                    f"Konnte kein Bild aus PDF extrahieren: {image_path}"
                )
            actual_image_path = extracted_path
        else:
            actual_image_path = image_path

        image_data = {
            "original_path": image_path,
            "image_path": actual_image_path,
            "is_pdf": is_pdf,
            "extracted_path": extracted_path,
            "original_image": None,
            "scale_factor": 1.0,
            "regions": [],
        }
        self.images_data.append(image_data)

    def _load_current_image(self):
        """Laedt das aktuell ausgewaehlte Bild in den Speicher."""
        try:
            if self.original_image is None:
                img = Image.open(self.image_path)
                self.original_image = img

            canvas_width = 1600
            canvas_height = 1280
            img_width, img_height = self.original_image.size
            self.scale_factor = self.compute_scale(
                img_width, img_height, canvas_width, canvas_height
            )
            new_width = int(img_width * self.scale_factor)
            new_height = int(img_height * self.scale_factor)
            self.image = self.original_image.resize(
                (new_width, new_height), Image.Resampling.LANCZOS
            )
        except Exception:
            if not self.create_ui:
                raise

    # ------------------------------------------------------------------
    # Business-Logic-Methoden (testbar, keine UI-Abhaengigkeit)
    # ------------------------------------------------------------------

    def rotate_image(self, angle: int):
        """Dreht das aktuelle Bild und setzt alle Bereiche zurueck.

        Args:
            angle: Drehwinkel in Grad (90 = rechts, -90 = links, 180).
        """
        if not self.original_image:
            return

        pil_angle = {90: -90, -90: 90}.get(angle, angle)
        self.original_image = self.original_image.rotate(pil_angle, expand=True)

        self.current_selection = None
        self.regions = []

        canvas_width = 1600
        canvas_height = 1280
        img_width, img_height = self.original_image.size
        self.scale_factor = self.compute_scale(
            img_width, img_height, canvas_width, canvas_height
        )
        new_width = int(img_width * self.scale_factor)
        new_height = int(img_height * self.scale_factor)
        self.image = self.original_image.resize(
            (new_width, new_height), Image.Resampling.LANCZOS
        )

    # ------------------------------------------------------------------
    # API-Handler (plain Python, direkt testbar ohne Server)
    # ------------------------------------------------------------------

    def _get_state_response(self) -> dict:
        """Gibt den aktuellen GUI-Zustand als Dict zurueck."""
        images_list = []
        for i, img in enumerate(self.images_data):
            images_list.append(
                {
                    "index": i,
                    "name": os.path.basename(img["original_path"]),
                    "is_pdf": img["is_pdf"],
                    "region_count": len(img["regions"]),
                    "is_current": i == self.current_image_index,
                }
            )
        regions_list = []
        for i, r in enumerate(self.regions):
            x1, y1, x2, y2 = r["coords"]
            regions_list.append(
                {
                    "index": i,
                    "mode": r["mode"],
                    "coords": list(r["coords"]),
                    "width": int(x2 - x1),
                    "height": int(y2 - y1),
                    "label": (
                        f"{i + 1}. {r['mode'].upper()} "
                        f"({int(x2 - x1)}x{int(y2 - y1)})"
                    ),
                }
            )
        w, h = (self.image.size if self.image else (0, 0))
        return {
            "current_index": self.current_image_index,
            "images": images_list,
            "regions": regions_list,
            "scale_factor": self.scale_factor,
            "image_width": w,
            "image_height": h,
        }

    def _get_image_data(self, index: int) -> dict:
        """Gibt Bilddaten fuer images_data[index] als Base64-PNG-Dict zurueck.

        Args:
            index: Index in self.images_data.

        Returns:
            Dict mit data_url, width und height, oder error-Schluessel.
        """
        if index < 0 or index >= len(self.images_data):
            return {"error": "Index ausserhalb des gueltigen Bereichs"}

        img_data = self.images_data[index]
        if img_data["original_image"] is None:
            saved_index = self.current_image_index
            self.current_image_index = index
            self._load_current_image()
            self.current_image_index = saved_index

        orig = img_data["original_image"]
        sf = img_data["scale_factor"]
        w = int(orig.size[0] * sf)
        h = int(orig.size[1] * sf)
        scaled = orig.resize((w, h), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        scaled.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return {"data_url": f"data:image/png;base64,{b64}", "width": w, "height": h}

    def _select_image_api(self, index: int) -> dict:
        """Wechselt zum Bild mit dem angegebenen Index.

        Args:
            index: Zielindex in images_data.

        Returns:
            Aktualisierter GUI-Zustand als Dict.
        """
        if 0 <= index < len(self.images_data):
            self.current_image_index = index
            if self.images_data[index]["original_image"] is None:
                self._load_current_image()
            self.current_selection = None
        return self._get_state_response()

    def _save_region_api(self, body: dict) -> dict:
        """Speichert eine Region aus Canvas-Koordinaten.

        Args:
            body: Dict mit x1, y1, x2, y2 (Canvas-Koordinaten) und mode.

        Returns:
            Dict mit ok, region_count und state, oder ok=False und error.
        """
        x1 = float(body["x1"])
        y1 = float(body["y1"])
        x2 = float(body["x2"])
        y2 = float(body["y2"])
        mode = body.get("mode", "foto")

        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            return {"ok": False, "error": "Auswahl zu klein (mindestens 5px)"}

        region = {
            "coords": (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)),
            "mode": mode,
            "rect_id": None,
        }
        self.regions.append(region)
        return {
            "ok": True,
            "region_count": len(self.regions),
            "state": self._get_state_response(),
        }

    def _clear_regions_api(self) -> dict:
        """Loescht alle Regionen des aktuellen Bildes.

        Returns:
            Dict mit ok und state.
        """
        self.regions = []
        self.current_selection = None
        return {"ok": True, "state": self._get_state_response()}

    def _rotate_api(self, body: dict) -> dict:
        """Dreht das aktuelle Bild und gibt neues Bild und Zustand zurueck.

        Args:
            body: Dict mit angle (90, -90 oder 180).

        Returns:
            Dict mit ok, image (data_url, width, height) und state.
        """
        angle = int(body.get("angle", 90))
        self.rotate_image(angle)
        image_data = self._get_image_data(self.current_image_index)
        return {"ok": True, "image": image_data, "state": self._get_state_response()}

    def _add_image_api(self, body: dict) -> dict:
        """Fuegt ein Bild per Dateipfad hinzu.

        Args:
            body: Dict mit path (absoluter Dateipfad).

        Returns:
            Dict mit ok und new_index, oder ok=False und error.
        """
        path = body.get("path", "").strip()
        if not path:
            return {"ok": False, "error": "Kein Pfad angegeben"}
        try:
            self._add_image(path)
            new_index = len(self.images_data) - 1
            self.current_image_index = new_index
            self._load_current_image()
            return {"ok": True, "new_index": new_index}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _finish_api(self) -> dict:
        """Beendet die Auswahl und signalisiert run() den Abschluss.

        Returns:
            Dict mit ok=True oder ok=False und error wenn keine Regionen.
        """
        total = sum(len(d["regions"]) for d in self.images_data)
        if total == 0:
            return {"ok": False, "error": "Bitte mindestens einen Bereich auswaehlen"}
        self.result_ready = True
        self._done_event.set()
        return {"ok": True}

    def _cancel_api(self) -> dict:
        """Bricht die Auswahl ab und signalisiert run() den Abbruch.

        Returns:
            Dict mit ok=True.
        """
        self.result_ready = False
        self._done_event.set()
        return {"ok": True}

    # ------------------------------------------------------------------
    # FastAPI-App und Server-Lifecycle
    # ------------------------------------------------------------------

    def _build_app(self):
        """Erstellt und konfiguriert die FastAPI-Applikation.

        Returns:
            Konfigurierte FastAPI-Instanz mit allen Routen.
        """
        from fastapi import FastAPI, Request
        from fastapi.responses import HTMLResponse, JSONResponse

        app = FastAPI(title="Image Selector")
        gui = self

        @app.get("/", response_class=HTMLResponse)
        def index():
            return HTMLResponse(content=_HTML_TEMPLATE)

        @app.get("/api/state")
        def get_state():
            return JSONResponse(gui._get_state_response())

        @app.get("/api/image/{index}")
        def get_image(index: int):
            return JSONResponse(gui._get_image_data(index))

        @app.post("/api/select_image/{index}")
        def select_image(index: int):
            return JSONResponse(gui._select_image_api(index))

        @app.post("/api/save_region")
        async def save_region(request: Request):
            body = await request.json()
            return JSONResponse(gui._save_region_api(body))

        @app.post("/api/clear_regions")
        def clear_regions():
            return JSONResponse(gui._clear_regions_api())

        @app.post("/api/rotate")
        async def rotate(request: Request):
            body = await request.json()
            return JSONResponse(gui._rotate_api(body))

        @app.post("/api/add_image")
        async def add_image(request: Request):
            body = await request.json()
            return JSONResponse(gui._add_image_api(body))

        @app.post("/api/finish")
        def finish():
            return JSONResponse(gui._finish_api())

        @app.post("/api/cancel")
        def cancel():
            return JSONResponse(gui._cancel_api())

        return app

    def _find_free_port(self) -> int:
        """Findet einen freien TCP-Port auf localhost.

        Returns:
            Verfuegbare Port-Nummer.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _start_server(self):  # pragma: no cover
        """Startet den uvicorn-Server im Hintergrund-Thread."""
        import uvicorn

        self._port = self._find_free_port()
        config = uvicorn.Config(
            self._app,
            host="127.0.0.1",
            port=self._port,
            log_level="error",
        )
        self._server = uvicorn.Server(config)
        self._server_thread = threading.Thread(
            target=self._server.run, daemon=True, name="web-gui-server"
        )
        self._server_thread.start()

        deadline = time.time() + 10.0
        while not self._server.started and time.time() < deadline:
            time.sleep(0.05)

        if not self._server.started:
            raise RuntimeError("Web-GUI-Server konnte nicht gestartet werden")

    def _stop_server(self):  # pragma: no cover
        """Stoppt den uvicorn-Server."""
        if self._server is not None:
            self._server.should_exit = True
        if self._server_thread is not None:
            self._server_thread.join(timeout=3.0)

    def _run_web_mode(self):  # pragma: no cover
        """Startet Server, oeffnet Browser und wartet auf Benutzer-Eingabe."""
        self._start_server()
        webbrowser.open(f"http://127.0.0.1:{self._port}/")
        self._done_event.wait()
        time.sleep(0.2)
        self._stop_server()

    def run(self) -> list | None:
        """Startet die Web-GUI und blockiert bis der Benutzer fertig ist.

        Returns:
            Liste der images_data-Dicts bei erfolgreichem Export, sonst None.
        """
        if not self.create_ui:
            if self.result_ready:
                return self.images_data
            return None
        self._run_web_mode()  # pragma: no cover
        if self.result_ready:  # pragma: no cover
            return self.images_data  # pragma: no cover
        return None  # pragma: no cover
