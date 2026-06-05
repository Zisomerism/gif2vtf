"""Resize and clamp frame dimensions to values a VTF accepts.

srctools requires every VTF dimension to be a power of two, so the resize
methods here all converge on power-of-two sizes. The behaviour mirrors
VTFEdit's ``SVTFCreateOptions`` resize handling (nearest/biggest/smallest
power of two, plus an explicit "set" size and a post-rounding clamp).
"""

from __future__ import annotations

from PIL import Image

RESIZE_METHODS = (
    "nearest-power2",
    "biggest-power2",
    "smallest-power2",
    "set",
)

RESAMPLE_FILTERS = {
    "nearest": Image.Resampling.NEAREST,
    "bilinear": Image.Resampling.BILINEAR,
    "bicubic": Image.Resampling.BICUBIC,
    "lanczos": Image.Resampling.LANCZOS,
}


def is_power_of_two(value: int) -> bool:
    return value >= 1 and (value & (value - 1)) == 0


def _nearest_power_of_two(value: int) -> int:
    if value < 1:
        return 1
    lower = 1 << (value.bit_length() - 1)
    upper = lower << 1
    # Tie goes to the larger size, matching VTFEdit's rounding.
    return upper if (value - lower) >= (upper - value) else lower


def _biggest_power_of_two(value: int) -> int:
    if value < 1:
        return 1
    return value if is_power_of_two(value) else 1 << value.bit_length()


def _smallest_power_of_two(value: int) -> int:
    if value < 1:
        return 1
    return value if is_power_of_two(value) else 1 << (value.bit_length() - 1)


def target_dimensions(
    width: int,
    height: int,
    *,
    method: str,
    set_width: int | None = None,
    set_height: int | None = None,
    clamp: bool = True,
    clamp_width: int = 4096,
    clamp_height: int = 4096,
) -> tuple[int, int]:
    """Compute the output dimensions for the given resize method."""
    if method == "set":
        if set_width is None or set_height is None:
            raise ValueError("Resize method 'set' requires both --width and --height.")
        new_w, new_h = set_width, set_height
    elif method == "nearest-power2":
        new_w, new_h = _nearest_power_of_two(width), _nearest_power_of_two(height)
    elif method == "biggest-power2":
        new_w, new_h = _biggest_power_of_two(width), _biggest_power_of_two(height)
    elif method == "smallest-power2":
        new_w, new_h = _smallest_power_of_two(width), _smallest_power_of_two(height)
    else:
        raise ValueError(f"Unknown resize method {method!r}. Valid: {', '.join(RESIZE_METHODS)}")

    if clamp:
        # Clamp only reduces size, then re-snaps to a power of two (downwards).
        if new_w > clamp_width:
            new_w = _smallest_power_of_two(clamp_width)
        if new_h > clamp_height:
            new_h = _smallest_power_of_two(clamp_height)

    return new_w, new_h


def resize_frames(
    frames: list[Image.Image],
    size: tuple[int, int],
    *,
    resample: str = "bilinear",
) -> list[Image.Image]:
    """Resize every frame to ``size`` using the named resampling filter."""
    try:
        resampling = RESAMPLE_FILTERS[resample.strip().lower()]
    except KeyError:
        valid = ", ".join(sorted(RESAMPLE_FILTERS))
        raise ValueError(f"Unknown resize filter {resample!r}. Valid: {valid}") from None
    return [frame.resize(size, resampling) for frame in frames]


def validate_dimensions(width: int, height: int) -> None:
    """Ensure dimensions are writable by srctools (powers of two)."""
    if not is_power_of_two(width) or not is_power_of_two(height):
        raise ValueError(
            f"VTF dimensions must both be powers of two, got {width}x{height}. "
            "Enable resizing or pick power-of-two --width/--height values."
        )
