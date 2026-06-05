import io

from PIL import Image
from srctools.vtf import VTF, ImageFormats, VTFFlags

from gif2vtf.vtf_builder import build_vtf, estimate_size, frames_have_alpha


def _solid(color, size=(32, 32)):
    return Image.new("RGBA", size, color)


def test_frames_have_alpha_detects_transparency():
    opaque = [_solid((255, 0, 0, 255)), _solid((0, 255, 0, 255))]
    assert frames_have_alpha(opaque) is False

    with_alpha = opaque + [_solid((0, 0, 255, 128))]
    assert frames_have_alpha(with_alpha) is True


def test_build_vtf_roundtrip_multiframe():
    frames = [_solid((255, 0, 0, 255)), _solid((0, 255, 0, 255)), _solid((0, 0, 255, 255))]
    result = build_vtf(
        frames,
        image_format=ImageFormats.RGBA8888,
        has_alpha=False,
        width=32,
        height=32,
        mipmaps=True,
    )

    assert result.frame_count == 3
    parsed = VTF.read(io.BytesIO(result.data))
    assert parsed.frame_count == 3
    assert parsed.width == 32 and parsed.height == 32
    assert parsed.format is ImageFormats.RGBA8888


def test_no_mipmaps_sets_flag_and_single_level():
    frames = [_solid((255, 255, 255, 255), size=(64, 64))]
    result = build_vtf(
        frames,
        image_format=ImageFormats.RGBA8888,
        has_alpha=False,
        width=64,
        height=64,
        mipmaps=False,
    )
    assert result.mipmap_count == 1
    parsed = VTF.read(io.BytesIO(result.data))
    assert VTFFlags.NO_MIP in parsed.flags
    assert parsed.mipmap_count == 1


def test_dxt5_alpha_roundtrip_sets_alpha_flag():
    frames = [_solid((255, 0, 0, 128)), _solid((0, 255, 0, 200))]
    result = build_vtf(
        frames,
        image_format=ImageFormats.DXT5,
        has_alpha=True,
        width=32,
        height=32,
        mipmaps=True,
    )
    parsed = VTF.read(io.BytesIO(result.data))
    assert parsed.format is ImageFormats.DXT5
    assert parsed.frame_count == 2
    assert VTFFlags.EIGHTBITALPHA in parsed.flags


def test_estimate_size_matches_uncompressed_payload():
    # 32x32 RGBA8888, 2 frames, no mipmaps -> 32*32*4*2 bytes.
    assert estimate_size(ImageFormats.RGBA8888, 32, 32, 2, mipmaps=False) == 32 * 32 * 4 * 2
