"""Decode an animated GIF into a list of fully-composited RGBA frames."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image, ImageSequence


@dataclass
class GifSequence:
    """A decoded animation: RGBA frames plus their per-frame durations.

    ``frames`` and ``durations_ms`` are always the same length and ordered for
    playback. Durations come straight from the source file; a frame with no
    recorded delay (common for non-animated inputs) gets ``0``.
    """

    frames: list[Image.Image] = field(default_factory=list)
    durations_ms: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.frames) != len(self.durations_ms):
            raise ValueError(
                "frames and durations_ms must have the same length "
                f"({len(self.frames)} != {len(self.durations_ms)})."
            )

    def __len__(self) -> int:
        return len(self.frames)


def load_gif_sequence(
    path: Path,
    *,
    skip: int = 0,
    max_frames: Optional[int] = None,
) -> GifSequence:
    """Load an animated (or static) image into a :class:`GifSequence`.

    Each frame is fully composited against the preceding frames, which undoes
    the GIF "optimization" where frames only store changed pixels (the manual
    "Unoptimize" step in the VTFEdit spray guide). Frames are returned in
    playback order as ``RGBA`` :class:`PIL.Image.Image` objects.

    :param skip: Number of leading frames to discard.
    :param max_frames: Maximum number of frames to keep after skipping.
    """
    if skip < 0:
        raise ValueError("--skip must not be negative.")
    if max_frames is not None and max_frames < 1:
        raise ValueError("--max-frames must be at least 1.")

    frames: list[Image.Image] = []
    durations_ms: list[int] = []
    with Image.open(path) as img:
        # ImageSequence composites disposal methods so each yielded frame is the
        # full visible image at that point in the animation.
        for index, frame in enumerate(ImageSequence.Iterator(img)):
            if index < skip:
                continue
            frames.append(frame.convert("RGBA"))
            # ``duration`` is per-frame metadata Pillow stores on each frame.
            durations_ms.append(int(frame.info.get("duration", 0) or 0))
            if max_frames is not None and len(frames) >= max_frames:
                break

    if not frames:
        raise ValueError(
            f"No frames decoded from {path} (skip={skip}, max_frames={max_frames})."
        )
    return GifSequence(frames=frames, durations_ms=durations_ms)


def load_gif_frames(
    path: Path,
    *,
    skip: int = 0,
    max_frames: Optional[int] = None,
) -> list[Image.Image]:
    """Load just the RGBA frames of an animation (compatibility wrapper)."""
    return load_gif_sequence(path, skip=skip, max_frames=max_frames).frames
