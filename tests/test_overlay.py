import pytest
from PIL import Image

from gif2vtf.overlay import apply_overlay, compute_position, load_overlay


def _solid(color, size=(16, 16)):
    return Image.new("RGBA", size, color)


def test_compute_position_top_left():
    assert compute_position((100, 80), (20, 10), x=5, y=7) == (5, 7)


def test_compute_position_centered():
    assert compute_position((100, 80), (20, 10), center=True) == (40, 35)


def test_compute_position_centered_with_nudge():
    assert compute_position((100, 80), (20, 10), x=2, y=-3, center=True) == (42, 32)


def test_apply_overlay_adds_transparency():
    base = _solid((255, 0, 0, 255))
    overlay = _solid((0, 0, 255, 128), size=(8, 8))
    result = apply_overlay([base], overlay, x=4, y=4)[0]
    assert result.getpixel((4, 4))[3] < 255
    assert result.getpixel((0, 0)) == (255, 0, 0, 255)


def test_apply_overlay_rejects_fully_outside_frame():
    base = _solid((255, 255, 255, 255), size=(8, 8))
    overlay = _solid((0, 0, 0, 255), size=(4, 4))
    with pytest.raises(ValueError, match="entirely outside"):
        apply_overlay([base], overlay, x=20, y=20)


def test_load_overlay_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        load_overlay(tmp_path / "missing.png")


def test_load_overlay_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "overlay.jpg"
    path.write_bytes(b"fake")
    with pytest.raises(ValueError, match="Unsupported overlay format"):
        load_overlay(path)


def test_load_overlay_reads_png(tmp_path):
    path = tmp_path / "overlay.png"
    _solid((0, 255, 0, 200)).save(path)
    overlay = load_overlay(path)
    assert overlay.mode == "RGBA"
    assert overlay.size == (16, 16)
