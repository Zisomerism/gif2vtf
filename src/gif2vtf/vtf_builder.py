"""Assemble a multi-frame VTF from RGBA frames using srctools."""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Iterable, Optional

from PIL import Image
from srctools.vtf import VTF, FilterMode, ImageFormats, VTFFlags

# Alpha hint flags srctools does not set automatically on save.
_ONE_BIT_ALPHA_FORMATS = {ImageFormats.DXT1_ONEBITALPHA}
_EIGHT_BIT_ALPHA_FORMATS = {
    ImageFormats.DXT3,
    ImageFormats.DXT5,
    ImageFormats.BGRA8888,
    ImageFormats.RGBA8888,
}


@dataclass
class BuildResult:
    """The outcome of building (and serialising) a VTF."""

    data: bytes
    width: int
    height: int
    frame_count: int
    image_format: ImageFormats
    has_alpha: bool
    mipmap_count: int


def frames_have_alpha(frames: Iterable[Image.Image]) -> bool:
    """Return whether any frame contains a partially transparent pixel."""
    for frame in frames:
        rgba = frame if frame.mode == "RGBA" else frame.convert("RGBA")
        alpha = rgba.getchannel("A")
        if alpha.getextrema()[0] < 255:
            return True
    return False


def _alpha_flags(fmt: ImageFormats) -> VTFFlags:
    if fmt in _ONE_BIT_ALPHA_FORMATS:
        return VTFFlags.ONEBITALPHA
    if fmt in _EIGHT_BIT_ALPHA_FORMATS:
        return VTFFlags.EIGHTBITALPHA
    return VTFFlags.EMPTY


def estimate_size(
    fmt: ImageFormats,
    width: int,
    height: int,
    frame_count: int,
    *,
    mipmaps: bool,
) -> int:
    """Estimate the high-res image payload size in bytes (excluding header)."""
    total = 0
    w, h = width, height
    while True:
        total += fmt.frame_size(w, h) * frame_count
        if not mipmaps or (w <= 1 and h <= 1):
            break
        w = max(1, w >> 1)
        h = max(1, h >> 1)
    return total


def build_vtf(
    frames: list[Image.Image],
    *,
    image_format: ImageFormats,
    has_alpha: bool,
    width: int,
    height: int,
    flags: VTFFlags = VTFFlags.EMPTY,
    mipmaps: bool = True,
    mip_filter: FilterMode = FilterMode.BILINEAR,
    version: tuple[int, int] = (7, 5),
    thumb_fmt: Optional[ImageFormats] = None,
) -> BuildResult:
    """Build an animated VTF and return its serialised bytes.

    Frames must already be sized to ``width`` x ``height``. The VTF is written
    to an in-memory buffer first so a failure (for example, a compressed format
    on a srctools build without libsquish) never leaves a half-written file.
    """
    if not frames:
        raise ValueError("Cannot build a VTF with no frames.")

    full_flags = flags | _alpha_flags(image_format)
    if not mipmaps:
        full_flags |= VTFFlags.NO_MIP

    if thumb_fmt is None:
        thumb_fmt = ImageFormats.DXT1 if has_alpha is False else ImageFormats.DXT5

    vtf = VTF(
        width,
        height,
        version,
        frames=len(frames),
        flags=full_flags,
        fmt=image_format,
        thumb_fmt=thumb_fmt,
    )

    # Disabling mipmaps means only mip 0 is stored, matching the spray guide's
    # advice to omit mipmaps so the file stays under the size limit.
    if not mipmaps:
        vtf.mipmap_count = 1

    for index, frame in enumerate(frames):
        rgba = frame if frame.mode == "RGBA" else frame.convert("RGBA")
        if rgba.size != (width, height):
            raise ValueError(
                f"Frame {index} is {rgba.size[0]}x{rgba.size[1]}, expected {width}x{height}."
            )
        vtf.get(frame=index).copy_from(rgba.tobytes())

    buffer = io.BytesIO()
    try:
        vtf.save(buffer, mip_filter=mip_filter)
    except NotImplementedError as exc:
        raise RuntimeError(
            f"This srctools build cannot write the {image_format.name} format "
            "(the libsquish-backed Cython extension is missing). Reinstall "
            "srctools with the compiled extension, or pick an uncompressed "
            "format such as RGBA8888 or BGRA8888."
        ) from exc

    return BuildResult(
        data=buffer.getvalue(),
        width=width,
        height=height,
        frame_count=len(frames),
        image_format=image_format,
        has_alpha=has_alpha,
        mipmap_count=vtf.mipmap_count,
    )
