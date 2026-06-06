import io

from PIL import Image
from srctools.vtf import VTF, VTFFlags, ImageFormats

from gif2vtf.cli import main


def _write_gif(path, frame_colors, size=(100, 100), duration=100):
    frames = [Image.new("RGB", size, color) for color in frame_colors]
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
    )


def test_cli_end_to_end(tmp_path):
    gif = tmp_path / "anim.gif"
    out = tmp_path / "anim.vtf"
    _write_gif(gif, [(255, 0, 0), (0, 255, 0), (0, 0, 255)])

    rc = main([str(gif), "-o", str(out), "--format", "RGBA8888"])
    assert rc == 0
    assert out.exists()

    parsed = VTF.read(io.BytesIO(out.read_bytes()))
    assert parsed.frame_count == 3
    # 100x100 rounds to nearest power of two (128) under the default preset.
    assert parsed.width == 128 and parsed.height == 128


def test_cli_spray_preset_applies_flags(tmp_path):
    gif = tmp_path / "spray.gif"
    out = tmp_path / "spray.vtf"
    _write_gif(gif, [(10, 20, 30), (30, 20, 10)])

    rc = main([
        str(gif), "-o", str(out),
        "--preset", "spray",
        "--width", "64", "--height", "64",
        "--format", "RGBA8888",
    ])
    assert rc == 0

    parsed = VTF.read(io.BytesIO(out.read_bytes()))
    assert parsed.width == 64 and parsed.height == 64
    assert VTFFlags.NO_MIP in parsed.flags
    assert VTFFlags.CLAMP_S in parsed.flags
    assert VTFFlags.CLAMP_T in parsed.flags
    assert VTFFlags.POINT_SAMPLE in parsed.flags


def test_cli_decimate_halves_frames(tmp_path):
    gif = tmp_path / "anim.gif"
    out = tmp_path / "anim.vtf"
    # 6 distinct frames; --decimate 2 should keep 3 (drops frames 2, 4, 6).
    _write_gif(gif, [(i * 30, 0, 0) for i in range(6)])

    rc = main([str(gif), "-o", str(out), "--format", "RGBA8888", "--decimate", "2"])
    assert rc == 0

    parsed = VTF.read(io.BytesIO(out.read_bytes()))
    assert parsed.frame_count == 3


def test_cli_optimize_frames_removes_duplicates(tmp_path, capsys):
    gif = tmp_path / "dup.gif"
    out = tmp_path / "dup.vtf"
    # Two identical leading frames, then a distinct one.
    _write_gif(gif, [(10, 20, 30), (10, 20, 30), (200, 100, 50)])

    rc = main([str(gif), "-o", str(out), "--format", "RGBA8888", "--optimize-frames"])
    assert rc == 0

    parsed = VTF.read(io.BytesIO(out.read_bytes()))
    assert parsed.frame_count == 2
    assert "experimental" in capsys.readouterr().err


def test_cli_optimize_fuzz_requires_optimize_frames(tmp_path, capsys):
    gif = tmp_path / "f.gif"
    out = tmp_path / "f.vtf"
    _write_gif(gif, [(0, 0, 0), (255, 255, 255)])

    rc = main([str(gif), "-o", str(out), "--format", "RGBA8888", "--optimize-fuzz", "5"])
    assert rc == 1
    assert not out.exists()
    assert "--optimize-fuzz requires --optimize-frames" in capsys.readouterr().err


def test_cli_strict_size_fails_when_over_limit(tmp_path, capsys):
    gif = tmp_path / "big.gif"
    out = tmp_path / "big.vtf"
    # Uncompressed 512x512 RGBA single frame = 1 MB, well over the 512 KB limit.
    _write_gif(gif, [(255, 255, 255)], size=(512, 512))

    rc = main([
        str(gif), "-o", str(out),
        "--preset", "spray",
        "--width", "512", "--height", "512",
        "--format", "RGBA8888",
        "--strict-size",
    ])
    assert rc == 1
    assert not out.exists()
    assert "spray limit" in capsys.readouterr().err


def test_cli_overlay_applies_before_resize_by_default(tmp_path):
    gif = tmp_path / "anim.gif"
    overlay = tmp_path / "overlay.png"
    out = tmp_path / "anim.vtf"
    _write_gif(gif, [(255, 0, 0), (0, 255, 0)], size=(64, 64))
    Image.new("RGBA", (64, 64), (0, 0, 255, 128)).save(overlay)

    rc = main([
        str(gif), "-o", str(out),
        "--format", "RGBA8888",
        "--alpha-format", "RGBA8888",
        "--width", "64", "--height", "64",
        "--overlay", str(overlay),
    ])
    assert rc == 0

    parsed = VTF.read(io.BytesIO(out.read_bytes()))
    assert parsed.frame_count == 2
    assert parsed.format is ImageFormats.RGBA8888
    assert VTFFlags.EIGHTBITALPHA in parsed.flags


def test_cli_overlay_applies_after_resize(tmp_path):
    gif = tmp_path / "anim.gif"
    overlay = tmp_path / "overlay.png"
    out = tmp_path / "anim.vtf"
    _write_gif(gif, [(255, 0, 0), (0, 255, 0)], size=(64, 64))
    Image.new("RGBA", (64, 64), (0, 0, 255, 128)).save(overlay)

    rc = main([
        str(gif), "-o", str(out),
        "--format", "RGBA8888",
        "--alpha-format", "RGBA8888",
        "--width", "64", "--height", "64",
        "--overlay", str(overlay),
        "--overlay-after-resize",
    ])
    assert rc == 0

    parsed = VTF.read(io.BytesIO(out.read_bytes()))
    assert parsed.frame_count == 2


def test_cli_overlay_option_requires_overlay_path(tmp_path, capsys):
    gif = tmp_path / "anim.gif"
    out = tmp_path / "anim.vtf"
    _write_gif(gif, [(255, 0, 0)])

    rc = main([str(gif), "-o", str(out), "--format", "RGBA8888", "--overlay-x", "4"])
    assert rc == 1
    assert not out.exists()
    assert "--overlay is required" in capsys.readouterr().err
