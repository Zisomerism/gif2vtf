"""Decode an animated GIF into a list of fully-composited RGBA frames."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image, ImageSequence


def load_gif_frames(
    path: Path,
    *,
    skip: int = 0,
    max_frames: Optional[int] = None,
) -> list[Image.Image]:
    """Load an animated (or static) image as a list of RGBA frames.

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
    with Image.open(path) as img:
        # ImageSequence composites disposal methods so each yielded frame is the
        # full visible image at that point in the animation.
        for index, frame in enumerate(ImageSequence.Iterator(img)):
            if index < skip:
                continue
            frames.append(frame.convert("RGBA"))
            if max_frames is not None and len(frames) >= max_frames:
                break

    if not frames:
        raise ValueError(
            f"No frames decoded from {path} (skip={skip}, max_frames={max_frames})."
        )
    return frames
