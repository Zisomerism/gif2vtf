import pytest

from gif2vtf.resize import (
    is_power_of_two,
    target_dimensions,
    validate_dimensions,
)


@pytest.mark.parametrize(
    "size, expected",
    [
        ((100, 100), (128, 128)),  # 100 is closer to 128 than 64
        ((96, 96), (128, 128)),    # tie rounds up
        ((70, 70), (64, 64)),      # 70 closer to 64
        ((512, 512), (512, 512)),  # already power of two
    ],
)
def test_nearest_power2(size, expected):
    assert target_dimensions(*size, method="nearest-power2", clamp=False) == expected


def test_biggest_and_smallest_power2():
    assert target_dimensions(100, 100, method="biggest-power2", clamp=False) == (128, 128)
    assert target_dimensions(100, 100, method="smallest-power2", clamp=False) == (64, 64)


def test_set_method_requires_dimensions():
    with pytest.raises(ValueError):
        target_dimensions(100, 100, method="set")
    assert target_dimensions(0, 0, method="set", set_width=128, set_height=64) == (128, 64)


def test_clamp_reduces_to_power_of_two():
    # 1000 -> nearest power of two is 1024, clamped to 512.
    assert target_dimensions(
        1000, 1000, method="nearest-power2", clamp=True, clamp_width=512, clamp_height=512
    ) == (512, 512)
    # Clamp at a non-power-of-two value snaps downward.
    assert target_dimensions(
        1000, 1000, method="biggest-power2", clamp=True, clamp_width=300, clamp_height=300
    ) == (256, 256)


def test_clamp_does_not_upscale():
    assert target_dimensions(
        100, 100, method="nearest-power2", clamp=True, clamp_width=4096, clamp_height=4096
    ) == (128, 128)


def test_is_power_of_two():
    assert is_power_of_two(1)
    assert is_power_of_two(256)
    assert not is_power_of_two(0)
    assert not is_power_of_two(96)


def test_validate_dimensions_rejects_non_power_of_two():
    validate_dimensions(128, 64)
    with pytest.raises(ValueError):
        validate_dimensions(96, 64)
