"""Mapping between user-facing format/filter names and srctools enums."""

from __future__ import annotations

from srctools.vtf import FilterMode, ImageFormats, VTFFlags

# The subset of image formats that make sense for animated sprites/sprays.
# Names are upper-cased on lookup so the CLI accepts any case.
IMAGE_FORMATS: dict[str, ImageFormats] = {
    "DXT1": ImageFormats.DXT1,
    "DXT3": ImageFormats.DXT3,
    "DXT5": ImageFormats.DXT5,
    "DXT1_ONEBITALPHA": ImageFormats.DXT1_ONEBITALPHA,
    "BGR888": ImageFormats.BGR888,
    "RGB888": ImageFormats.RGB888,
    "BGRA8888": ImageFormats.BGRA8888,
    "RGBA8888": ImageFormats.RGBA8888,
    "BGR565": ImageFormats.BGR565,
    "RGB565": ImageFormats.RGB565,
    "ATI2N": ImageFormats.ATI2N,
}

# Formats which cannot be written without the Cython/libsquish build of srctools.
_COMPRESSED_NAMES = {"DXT1", "DXT3", "DXT5", "DXT1_ONEBITALPHA", "ATI2N"}

# Mipmap filters srctools actually supports (it only ships nearest + bilinear).
MIP_FILTERS: dict[str, FilterMode] = {
    "nearest": FilterMode.NEAREST,
    "bilinear": FilterMode.BILINEAR,
}


def resolve_format(name: str) -> ImageFormats:
    """Look up an :class:`ImageFormats` member from a user-supplied name."""
    key = name.strip().upper()
    try:
        return IMAGE_FORMATS[key]
    except KeyError:
        valid = ", ".join(sorted(IMAGE_FORMATS))
        raise ValueError(f"Unknown image format {name!r}. Valid formats: {valid}") from None


def is_compressed_name(name: str) -> bool:
    """Return whether the named format needs the libsquish-backed srctools build."""
    return name.strip().upper() in _COMPRESSED_NAMES


def resolve_mip_filter(name: str) -> FilterMode:
    """Look up a :class:`FilterMode` member from a user-supplied name."""
    key = name.strip().lower()
    try:
        return MIP_FILTERS[key]
    except KeyError:
        valid = ", ".join(sorted(MIP_FILTERS))
        raise ValueError(f"Unknown mip filter {name!r}. Valid filters: {valid}") from None


def resolve_flag(name: str) -> VTFFlags:
    """Look up a :class:`VTFFlags` member from a user-supplied name."""
    key = name.strip().upper()
    try:
        flag = VTFFlags[key]
    except KeyError:
        raise ValueError(f"Unknown VTF flag {name!r}.") from None
    return flag
