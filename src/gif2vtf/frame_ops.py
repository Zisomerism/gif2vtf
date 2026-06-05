"""Frame-count reductions: decimation and experimental optimization.

The optimization here is inspired by ImageMagick's ``RemoveDups`` and
``RemoveZero`` "-layers" methods. It only removes whole frames; it does NOT
perform GIF sub-frame/disposal optimization, which is meaningless for VTF
output where every frame is a full canvas image.
"""

from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from gif2vtf.gif_loader import GifSequence


@dataclass
class OptimizeStats:
    """Counts of frames removed by each optimization pass."""

    zero_delay_removed: int = 0
    duplicates_removed: int = 0


def decimate_frames(frames: list[Image.Image], factor: int) -> list[Image.Image]:
    """Drop every ``factor``-th frame using 1-based indexing.

    With ``factor=4`` the 4th, 8th, 12th... frames are removed. ``factor`` must
    be at least 2, and the result must retain at least one frame.
    """
    if factor < 2:
        raise ValueError("--decimate must be at least 2.")

    kept = [frame for index, frame in enumerate(frames) if (index + 1) % factor != 0]
    if not kept:
        raise ValueError(
            f"--decimate {factor} would remove every frame from a "
            f"{len(frames)}-frame animation."
        )
    return kept


def _frames_match(a: Image.Image, b: Image.Image, fuzz: int) -> bool:
    """Return whether two frames are visually identical within ``fuzz``."""
    if a.size != b.size:
        return False
    data_a = a.tobytes()
    data_b = b.tobytes()
    if fuzz <= 0:
        return data_a == data_b
    return all(abs(x - y) <= fuzz for x, y in zip(data_a, data_b))


def remove_zero_delay_frames(seq: GifSequence) -> tuple[GifSequence, int]:
    """Drop frames with a zero display duration (intermediate frames).

    At least one frame is always retained; if every frame is zero-delay the
    sequence is returned unchanged.
    """
    keep_indices = [i for i, d in enumerate(seq.durations_ms) if d > 0]
    if not keep_indices:
        return seq, 0

    removed = len(seq.frames) - len(keep_indices)
    if removed == 0:
        return seq, 0

    frames = [seq.frames[i] for i in keep_indices]
    durations = [seq.durations_ms[i] for i in keep_indices]
    return GifSequence(frames=frames, durations_ms=durations), removed


def remove_duplicate_frames(seq: GifSequence, *, fuzz: int = 0) -> tuple[GifSequence, int]:
    """Merge runs of consecutive identical frames into a single frame.

    The dropped frame's duration is folded into the kept frame so the overall
    animation timing is preserved.
    """
    if not seq.frames:
        return seq, 0

    frames = [seq.frames[0]]
    durations = [seq.durations_ms[0]]
    removed = 0
    for frame, duration in zip(seq.frames[1:], seq.durations_ms[1:]):
        if _frames_match(frames[-1], frame, fuzz):
            durations[-1] += duration
            removed += 1
        else:
            frames.append(frame)
            durations.append(duration)

    if removed == 0:
        return seq, 0
    return GifSequence(frames=frames, durations_ms=durations), removed


def optimize_frames(seq: GifSequence, *, fuzz: int = 0) -> tuple[GifSequence, OptimizeStats]:
    """Remove zero-delay intermediate frames, then consecutive duplicates."""
    seq, zero_removed = remove_zero_delay_frames(seq)
    seq, dup_removed = remove_duplicate_frames(seq, fuzz=fuzz)
    return seq, OptimizeStats(zero_delay_removed=zero_removed, duplicates_removed=dup_removed)
