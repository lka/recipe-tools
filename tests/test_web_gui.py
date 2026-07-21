"""Tests fuer WebImageSelectorGUI (create_ui=False, kein Browser/Server)."""

import pytest
from PIL import Image

from recipe_processor.tools.image_selector.web_gui import WebImageSelectorGUI


def _make_image(tmp_path, name="test.png", size=(400, 300), color="red"):
    """Hilfsfunktion: erstellt ein Testbild und gibt den Pfad zurueck."""
    path = tmp_path / name
    Image.new("RGB", size, color=color).save(str(path))
    return str(path)


class TestInitAndImageLoading:
    """Tests fuer Initialisierung und Bildladen."""

    def test_init_with_image(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert len(gui.images_data) == 1
        assert gui.image_path == img_path
        assert gui.original_image is not None

    def test_init_auto_load_from_dir(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        for name in ("a.png", "b.png"):
            _make_image(tmp_path, name=name)
        gui = WebImageSelectorGUI(create_ui=False)
        assert len(gui.images_data) == 2

    def test_init_auto_load_max_four(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        for i in range(6):
            _make_image(tmp_path, name=f"img{i}.png")
        gui = WebImageSelectorGUI(create_ui=False)
        assert len(gui.images_data) == 4

    def test_scale_factor_small_image(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path, size=(100, 80))
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert gui.scale_factor == 1.25

    def test_scale_factor_large_image(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path, size=(3200, 2400))
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert gui.scale_factor < 1.0

    def test_no_app_created_in_test_mode(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert not hasattr(gui, "_app")


class TestComputeScale:
    """Tests fuer den statischen compute_scale-Helfer."""

    def test_max_scale_125(self):
        s = WebImageSelectorGUI.compute_scale(100, 100, 1600, 1280)
        assert s == 1.25

    def test_scale_down_landscape(self):
        s = WebImageSelectorGUI.compute_scale(3200, 800, 1600, 1280)
        assert s == pytest.approx(0.5)

    def test_scale_zero_width_returns_one(self):
        s = WebImageSelectorGUI.compute_scale(0, 100, 1600, 1280)
        assert s == 1.0


class TestProperties:
    """Tests fuer die Kompatibilitaets-Properties."""

    def test_is_pdf_false_for_png(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert gui.is_pdf is False

    def test_extracted_image_path_none_for_png(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert gui.extracted_image_path is None

    def test_original_image_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert gui.original_image_path == img_path

    def test_scale_factor_setter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui.scale_factor = 0.5
        assert gui.scale_factor == 0.5

    def test_regions_setter(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui.regions = [{"coords": (1, 2, 3, 4), "mode": "foto", "rect_id": None}]
        assert len(gui.regions) == 1


class TestRotateImage:
    """Tests fuer rotate_image."""

    def test_rotate_clears_regions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui.regions = [{"coords": (10, 10, 100, 100), "mode": "foto", "rect_id": None}]
        gui.rotate_image(90)
        assert len(gui.regions) == 0

    def test_rotate_90_swaps_dimensions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path, size=(400, 200))
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        orig_w, orig_h = gui.original_image.size
        gui.rotate_image(90)
        new_w, new_h = gui.original_image.size
        assert new_w == orig_h
        assert new_h == orig_w

    def test_rotate_noop_without_image(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        gui = WebImageSelectorGUI(create_ui=False)
        gui.rotate_image(90)  # Kein Fehler, kein Bild geladen


class TestSaveRegionApi:
    """Tests fuer _save_region_api."""

    def test_saves_region_correctly(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._save_region_api(
            {"x1": 10.0, "y1": 20.0, "x2": 110.0, "y2": 120.0, "mode": "foto"}
        )
        assert result["ok"] is True
        assert len(gui.regions) == 1
        assert gui.regions[0]["mode"] == "foto"
        assert gui.regions[0]["rect_id"] is None

    def test_normalizes_coords(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        # x2 < x1 soll normalisiert werden
        gui._save_region_api(
            {"x1": 200.0, "y1": 200.0, "x2": 10.0, "y2": 10.0, "mode": "text"}
        )
        x1, y1, x2, y2 = gui.regions[0]["coords"]
        assert x1 < x2
        assert y1 < y2

    def test_rejects_too_small(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._save_region_api(
            {"x1": 10.0, "y1": 10.0, "x2": 12.0, "y2": 12.0, "mode": "foto"}
        )
        assert result["ok"] is False
        assert len(gui.regions) == 0

    def test_state_in_response(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._save_region_api(
            {"x1": 10.0, "y1": 20.0, "x2": 110.0, "y2": 120.0, "mode": "text"}
        )
        assert "state" in result
        assert result["state"]["regions"][0]["mode"] == "text"


class TestClearRegionsApi:
    """Tests fuer _clear_regions_api."""

    def test_clears_all_regions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._save_region_api(
            {"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 100.0, "mode": "foto"}
        )
        assert len(gui.regions) == 1
        result = gui._clear_regions_api()
        assert result["ok"] is True
        assert len(gui.regions) == 0


class TestGetStateResponse:
    """Tests fuer _get_state_response."""

    def test_structure(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        s = gui._get_state_response()
        assert "current_index" in s
        assert "images" in s
        assert "regions" in s
        assert "scale_factor" in s
        assert "image_width" in s
        assert "image_height" in s

    def test_images_list(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path, name="mein_bild.png")
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        s = gui._get_state_response()
        assert len(s["images"]) == 1
        assert s["images"][0]["name"] == "mein_bild.png"
        assert s["images"][0]["is_current"] is True

    def test_region_label_format(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._save_region_api(
            {"x1": 0.0, "y1": 0.0, "x2": 100.0, "y2": 50.0, "mode": "foto"}
        )
        s = gui._get_state_response()
        assert s["regions"][0]["label"].startswith("1. FOTO")


class TestGetImageData:
    """Tests fuer _get_image_data."""

    def test_returns_data_url(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        d = gui._get_image_data(0)
        assert d["data_url"].startswith("data:image/png;base64,")
        assert d["width"] > 0
        assert d["height"] > 0

    def test_invalid_index_returns_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        d = gui._get_image_data(99)
        assert "error" in d


class TestSelectImageApi:
    """Tests fuer _select_image_api."""

    def test_switch_image(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        p1 = _make_image(tmp_path, name="a.png", color="red")
        p2 = _make_image(tmp_path, name="b.png", color="blue")
        gui = WebImageSelectorGUI(p1, create_ui=False)
        gui._add_image(p2)
        gui._select_image_api(1)
        assert gui.current_image_index == 1

    def test_invalid_index_ignored(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._select_image_api(99)
        assert gui.current_image_index == 0


class TestRotateApi:
    """Tests fuer _rotate_api."""

    def test_returns_image_and_state(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._rotate_api({"angle": 90})
        assert result["ok"] is True
        assert "image" in result
        assert "state" in result
        assert result["image"]["data_url"].startswith("data:image/png;base64,")


class TestAddImageApi:
    """Tests fuer _add_image_api."""

    def test_adds_valid_image(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        p1 = _make_image(tmp_path, name="a.png")
        p2 = _make_image(tmp_path, name="b.png")
        gui = WebImageSelectorGUI(p1, create_ui=False)
        result = gui._add_image_api({"path": p2})
        assert result["ok"] is True
        assert result["new_index"] == 1
        assert len(gui.images_data) == 2

    def test_rejects_empty_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._add_image_api({"path": ""})
        assert result["ok"] is False

    def test_rejects_nonexistent_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._add_image_api({"path": str(tmp_path / "nope.png")})
        assert result["ok"] is False


class TestFinishAndCancelApi:
    """Tests fuer _finish_api und _cancel_api."""

    def test_finish_sets_result_ready(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._save_region_api(
            {"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 100.0, "mode": "foto"}
        )
        result = gui._finish_api()
        assert result["ok"] is True
        assert gui.result_ready is True
        assert gui._done_event.is_set()

    def test_finish_fails_without_regions(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._finish_api()
        assert result["ok"] is False
        assert gui.result_ready is False
        assert not gui._done_event.is_set()

    def test_cancel_does_not_set_result_ready(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        result = gui._cancel_api()
        assert result["ok"] is True
        assert gui.result_ready is False
        assert gui._done_event.is_set()


class TestPollResult:
    """Tests fuer poll_result() im Test-Modus (create_ui=False)."""

    def test_pending_before_finish(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert gui.poll_result() == "pending"

    def test_done_after_finish(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._save_region_api(
            {"x1": 10.0, "y1": 10.0, "x2": 100.0, "y2": 100.0, "mode": "foto"}
        )
        gui._finish_api()
        assert gui.poll_result() == "done"

    def test_cancelled_after_cancel(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._cancel_api()
        assert gui.poll_result() == "cancelled"

    def test_repeated_calls_stay_consistent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui._cancel_api()
        assert gui.poll_result() == "cancelled"
        assert gui.poll_result() == "cancelled"


class TestStart:
    """Tests fuer start() im Test-Modus (create_ui=False)."""

    def test_noop_without_ui(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui.start()  # darf keinen Server starten/Browser oeffnen
        assert gui._server is None


class TestRun:
    """Tests fuer run() im Test-Modus (create_ui=False)."""

    def test_returns_none_when_not_ready(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        assert gui.run() is None

    def test_returns_images_data_when_ready(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IMAGE_SELECTOR_WORKING_DIR", str(tmp_path))
        img_path = _make_image(tmp_path)
        gui = WebImageSelectorGUI(img_path, create_ui=False)
        gui.result_ready = True
        result = gui.run()
        assert result is gui.images_data
