import pytest
from PIL import Image

from gif2vtf.frame_ops import (
    decimate_frames,
    optimize_frames,
    remove_duplicate_frames,
    remove_zero_delay_frames,
)
from gif2vtf.gif_loader import GifSequence


def _solid(color, size=(8, 8)):
    return Image.new("RGBA", size, color)


def _seq(colors, durations):
    return GifSequence(
        frames=[_solid(c) for c in colors],
        durations_ms=list(durations),
    )


def test_decimate_factor_2():
    frames = [_solid((i, 0, 0, 255)) for i in range(10)]
    kept = decimate_frames(frames, 2)
    # 1-based: drops frames 2,4,6,8,10 -> keeps indices 0,2,4,6,8
    assert len(kept) == 5
    assert [f.getpixel((0, 0))[0] for f in kept] == [0, 2, 4, 6, 8]


def test_decimate_factor_4():
    frames = [_solid((i, 0, 0, 255)) for i in range(8)]
    kept = decimate_frames(frames, 4)
    # drops frames 4 and 8 -> indices 3 and 7
    assert [f.getpixel((0, 0))[0] for f in kept] == [0, 1, 2, 4, 5, 6]


def test_decimate_rejects_factor_below_2():
    with pytest.raises(ValueError):
        decimate_frames([_solid((0, 0, 0, 255))], 1)


def test_remove_zero_delay_frames():
    seq = _seq(
        [(0, 0, 0, 255), (1, 0, 0, 255), (2, 0, 0, 255)],
        [100, 0, 100],
    )
    result, removed = remove_zero_delay_frames(seq)
    assert removed == 1
    assert [f.getpixel((0, 0))[0] for f in result.frames] == [0, 2]


def test_remove_zero_delay_keeps_all_when_all_zero():
    seq = _seq([(0, 0, 0, 255), (1, 0, 0, 255)], [0, 0])
    result, removed = remove_zero_delay_frames(seq)
    assert removed == 0
    assert len(result.frames) == 2


def test_remove_duplicate_frames_exact():
    seq = _seq(
        [(5, 5, 5, 255), (5, 5, 5, 255), (9, 9, 9, 255)],
        [100, 100, 100],
    )
    result, removed = remove_duplicate_frames(seq)
    assert removed == 1
    assert [f.getpixel((0, 0))[0] for f in result.frames] == [5, 9]
    # Dropped frame's duration is folded into the kept frame.
    assert result.durations_ms[0] == 200


def test_remove_duplicate_frames_fuzz():
    seq = _seq([(10, 10, 10, 255), (12, 12, 12, 255)], [100, 100])
    # Exact: not duplicates.
    _, removed_exact = remove_duplicate_frames(seq, fuzz=0)
    assert removed_exact == 0
    # Fuzz of 2 treats them as duplicates.
    result, removed_fuzz = remove_duplicate_frames(seq, fuzz=2)
    assert removed_fuzz == 1
    assert len(result.frames) == 1


def test_optimize_frames_combined():
    seq = _seq(
        [(0, 0, 0, 255), (0, 0, 0, 255), (1, 0, 0, 255), (2, 0, 0, 255)],
        [100, 100, 0, 100],
    )
    result, stats = optimize_frames(seq)
    # Zero-delay frame (index 2) removed first, then the leading duplicate pair.
    assert stats.zero_delay_removed == 1
    assert stats.duplicates_removed == 1
    assert [f.getpixel((0, 0))[0] for f in result.frames] == [0, 2]
