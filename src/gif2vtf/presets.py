"""Default option sets for the supported presets.

A preset only supplies *defaults*. Any value the user passes explicitly on the
command line overrides the matching preset value (handled in ``cli.py``).
"""

from __future__ import annotations

# Maximum file size for Source sprays, in bytes.
SPRAY_SIZE_LIMIT = 512 * 1024

PRESETS: dict[str, dict[str, object]] = {
    "general": {
        "format": "DXT1",
        "alpha_format": "DXT5",
        "alpha_threshold": 128,
        "resize": True,
        "resize_method": "nearest-power2",
        "resize_filter": "bilinear",
        "clamp": True,
        "clamp_width": 4096,
        "clamp_height": 4096,
        "mipmaps": True,
        "mip_filter": "bilinear",
        # Flags applied on top of any auto-detected alpha flags.
        "flags": (),
        # Whether to warn when the output exceeds the spray size limit.
        "warn_spray_size": False,
    },
    "spray": {
        "format": "DXT1",
        "alpha_format": "DXT5",
        "alpha_threshold": 128,
        "resize": True,
        "resize_method": "nearest-power2",
        "resize_filter": "bilinear",
        "clamp": True,
        "clamp_width": 512,
        "clamp_height": 512,
        "mipmaps": False,
        "mip_filter": "bilinear",
        "flags": ("POINT_SAMPLE", "CLAMP_S", "CLAMP_T", "NO_LOD"),
        "warn_spray_size": True,
    },
}

DEFAULT_PRESET = "general"
