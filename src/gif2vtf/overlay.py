"""Composite a static RGBA overlay image onto every animation frame."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

SUPPORTED_EXTENSIONS = {".png", ".tga"}


def load_overlay(path: Path) -> Image.Image:
    """Load a PNG or TGA overlay and return it as an RGBA image."""
    if not path.is_file():
        raise ValueError(f"Overlay file not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        valid = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported overlay format {suffix!r}. Supported formats: {valid}"
        )

    try:
        with Image.open(path) as img:
            return img.convert("RGBA")
    except OSError as exc:
        raise ValueError(f"Could not read overlay image {path}: {exc}") from exc


def compute_position(
    frame_size: tuple[int, int],
    overlay_size: tuple[int, int],
    *,
    x: int = 0,
    y: int = 0,
    center: bool = False,
) -> tuple[int, int]:
    """Return the top-left paste position for an overlay on a frame."""
    frame_w, frame_h = frame_size
    overlay_w, overlay_h = overlay_size
    if center:
        x += (frame_w - overlay_w) // 2
        y += (frame_h - overlay_h) // 2
    return x, y


def _overlay_fully_outside_frame(
    frame_size: tuple[int, int],
    position: tuple[int, int],
    overlay_size: tuple[int, int],
) -> bool:
    frame_w, frame_h = frame_size
    overlay_w, overlay_h = overlay_size
    x, y = position
    return (
        x >= frame_w
        or y >= frame_h
        or x + overlay_w <= 0
        or y + overlay_h <= 0
    )


def apply_overlay(
    frames: list[Image.Image],
    overlay: Image.Image,
    *,
    x: int = 0,
    y: int = 0,
    center: bool = False,
) -> list[Image.Image]:
    """Alpha-composite ``overlay`` onto every frame at the computed position."""
    if not frames:
        raise ValueError("Cannot apply overlay to an empty frame list.")

    overlay_rgba = overlay if overlay.mode == "RGBA" else overlay.convert("RGBA")
    result: list[Image.Image] = []

    for index, frame in enumerate(frames):
        rgba = frame if frame.mode == "RGBA" else frame.convert("RGBA")
        position = compute_position(rgba.size, overlay_rgba.size, x=x, y=y, center=center)
        if _overlay_fully_outside_frame(rgba.size, position, overlay_rgba.size):
            raise ValueError(
                f"Overlay is entirely outside frame {index} ({rgba.size[0]}x{rgba.size[1]}) "
                f"at position {position}."
            )
        composited = rgba.copy()
        composited.paste(overlay_rgba, position, overlay_rgba)
        result.append(composited)

    return result
