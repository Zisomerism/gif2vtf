"""Command-line interface for converting GIFs into animated VTF files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from srctools.vtf import VTFFlags

from gif2vtf import formats, presets
from gif2vtf.frame_ops import decimate_frames, optimize_frames
from gif2vtf.gif_loader import load_gif_sequence
from gif2vtf.overlay import apply_overlay, load_overlay
from gif2vtf.resize import (
    RESIZE_METHODS,
    resize_frames,
    target_dimensions,
    validate_dimensions,
)
from gif2vtf.vtf_builder import build_vtf, estimate_size, frames_have_alpha


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gif2vtf",
        description="Convert an animated GIF into an animated Valve Texture Format (.vtf) file.",
    )
    parser.add_argument("input", type=Path, help="Path to the source GIF (or other animated image).")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output .vtf path (defaults to the input name with a .vtf extension).",
    )
    parser.add_argument(
        "--preset", choices=sorted(presets.PRESETS), default=presets.DEFAULT_PRESET,
        help="Default option set to start from (default: %(default)s).",
    )

    fmt = parser.add_argument_group("format")
    fmt.add_argument("--format", default=None, help="Image format for frames without alpha.")
    fmt.add_argument("--alpha-format", default=None, help="Image format for frames with alpha.")
    fmt.add_argument(
        "--alpha-threshold", type=int, default=None,
        help="Cutoff (0-255) for one-bit-alpha formats.",
    )

    rsz = parser.add_argument_group("resize")
    rsz.add_argument(
        "--resize", action=argparse.BooleanOptionalAction, default=None,
        help="Resize frames to a valid VTF size.",
    )
    rsz.add_argument("--resize-method", choices=RESIZE_METHODS, default=None, help="How to pick the target size.")
    rsz.add_argument("--width", type=int, default=None, help="Explicit target width (implies 'set' method).")
    rsz.add_argument("--height", type=int, default=None, help="Explicit target height (implies 'set' method).")
    rsz.add_argument(
        "--clamp", action=argparse.BooleanOptionalAction, default=None,
        help="Cap dimensions to the clamp size.",
    )
    rsz.add_argument("--clamp-width", type=int, default=None, help="Maximum width when clamping.")
    rsz.add_argument("--clamp-height", type=int, default=None, help="Maximum height when clamping.")
    rsz.add_argument(
        "--resize-filter", choices=("nearest", "bilinear", "bicubic", "lanczos"), default=None,
        help="Resampling filter used when resizing.",
    )

    mip = parser.add_argument_group("mipmaps")
    mip.add_argument(
        "--mipmaps", action=argparse.BooleanOptionalAction, default=None,
        help="Generate a mipmap chain.",
    )
    mip.add_argument("--mip-filter", choices=sorted(formats.MIP_FILTERS), default=None, help="Mipmap downscale filter.")

    flg = parser.add_argument_group("flags")
    flg.add_argument("--flag", action="append", default=[], metavar="NAME", help="Add a VTFFlags flag (repeatable).")
    flg.add_argument("--no-flag", action="append", default=[], metavar="NAME", help="Remove a preset flag (repeatable).")

    frm = parser.add_argument_group("frames")
    frm.add_argument("--max-frames", type=int, default=None, help="Keep at most this many frames.")
    frm.add_argument("--skip", type=int, default=0, help="Skip this many leading frames.")
    frm.add_argument(
        "--decimate", type=int, default=None, metavar="N",
        help="Drop every Nth frame (1-based). N must be at least 2.",
    )
    frm.add_argument(
        "--optimize-frames", action="store_true",
        help="EXPERIMENTAL: remove duplicate and zero-delay frames.",
    )
    frm.add_argument(
        "--optimize-fuzz", type=int, default=0, metavar="N",
        help="Max per-channel RGBA difference for duplicate detection (default: 0 = exact). "
        "Only valid with --optimize-frames.",
    )

    ovr = parser.add_argument_group("overlay")
    ovr.add_argument(
        "--overlay", type=Path, default=None,
        help="PNG/TGA image composited onto every frame.",
    )
    ovr.add_argument(
        "--overlay-x", type=int, default=0,
        help="Horizontal overlay offset in pixels (default: 0).",
    )
    ovr.add_argument(
        "--overlay-y", type=int, default=0,
        help="Vertical overlay offset in pixels (default: 0).",
    )
    ovr.add_argument(
        "--overlay-center", action="store_true",
        help="Center the overlay on each frame, then apply overlay-x/y as a nudge.",
    )
    ovr.add_argument(
        "--overlay-after-resize", action="store_true",
        help="Apply overlay after resize, in final VTF pixel space "
        "(default: before resize, overlay scales with frames).",
    )

    other = parser.add_argument_group("other")
    other.add_argument(
        "--version", dest="vtf_version", default="7.5",
        help="VTF version to write (7.2-7.5, default: %(default)s).",
    )
    other.add_argument(
        "--strict-size", action="store_true",
        help="Fail (instead of warn) when the output exceeds the spray size limit.",
    )
    other.add_argument("-v", "--verbose", action="store_true", help="Print details about the conversion.")
    return parser


def _resolved(value: object, default: object) -> object:
    """Return ``value`` if the user supplied it, otherwise the preset default."""
    return default if value is None else value


def _parse_version(text: str) -> tuple[int, int]:
    try:
        major_s, minor_s = text.split(".")
        version = (int(major_s), int(minor_s))
    except ValueError:
        raise SystemExit(f"gif2vtf: invalid --version {text!r}; expected something like 7.5")
    if not ((7, 2) <= version <= (7, 5)):
        raise SystemExit(f"gif2vtf: --version must be between 7.2 and 7.5, got {text}")
    return version


def _resolve_flags(preset_flags: Sequence[str], add: Sequence[str], remove: Sequence[str]) -> VTFFlags:
    names = {name.upper() for name in preset_flags}
    names.update(name.upper() for name in add)
    names.difference_update(name.upper() for name in remove)
    flags = VTFFlags.EMPTY
    for name in names:
        flags |= formats.resolve_flag(name)
    return flags


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    preset = presets.PRESETS[args.preset]

    def opt(name: str) -> object:
        return _resolved(getattr(args, name), preset[name])

    try:
        version = _parse_version(args.vtf_version)

        if args.optimize_fuzz and not args.optimize_frames:
            raise ValueError("--optimize-fuzz requires --optimize-frames.")
        if args.optimize_fuzz < 0:
            raise ValueError("--optimize-fuzz must not be negative.")

        overlay_options = (
            args.overlay_x != 0
            or args.overlay_y != 0
            or args.overlay_center
            or args.overlay_after_resize
        )
        if args.overlay is None and overlay_options:
            raise ValueError("--overlay is required when using overlay options.")

        overlay_image = load_overlay(args.overlay) if args.overlay is not None else None

        sequence = load_gif_sequence(args.input, skip=args.skip, max_frames=args.max_frames)
        decoded_count = len(sequence)

        optimize_stats = None
        if args.optimize_frames:
            print("gif2vtf: warning: --optimize-frames is experimental", file=sys.stderr)
            sequence, optimize_stats = optimize_frames(sequence, fuzz=args.optimize_fuzz)
        optimized_count = len(sequence)

        frames = sequence.frames
        if args.decimate is not None:
            frames = decimate_frames(frames, args.decimate)
        decimated_count = len(frames)

        def _apply_overlay_to_frames(frame_list: list) -> list:
            assert overlay_image is not None
            return apply_overlay(
                frame_list,
                overlay_image,
                x=args.overlay_x,
                y=args.overlay_y,
                center=args.overlay_center,
            )

        if overlay_image is not None and not args.overlay_after_resize:
            frames = _apply_overlay_to_frames(frames)

        resize_enabled = bool(opt("resize"))
        # Explicit width/height force the 'set' method.
        if args.width is not None or args.height is not None:
            method = "set"
            resize_enabled = True
        else:
            method = str(opt("resize_method"))

        if resize_enabled:
            width, height = target_dimensions(
                frames[0].width, frames[0].height,
                method=method,
                set_width=args.width,
                set_height=args.height,
                clamp=bool(opt("clamp")),
                clamp_width=int(opt("clamp_width")),
                clamp_height=int(opt("clamp_height")),
            )
            frames = resize_frames(frames, (width, height), resample=str(opt("resize_filter")))
        else:
            sizes = {frame.size for frame in frames}
            if len(sizes) != 1:
                raise ValueError(
                    "Frames have differing sizes; enable resizing to normalise them."
                )
            width, height = frames[0].size

        if overlay_image is not None and args.overlay_after_resize:
            frames = _apply_overlay_to_frames(frames)

        validate_dimensions(width, height)

        has_alpha = frames_have_alpha(frames)
        format_name = str(opt("alpha_format") if has_alpha else opt("format"))
        image_format = formats.resolve_format(format_name)

        flags = _resolve_flags(preset["flags"], args.flag, args.no_flag)
        mipmaps = bool(opt("mipmaps"))
        mip_filter = formats.resolve_mip_filter(str(opt("mip_filter")))

        estimated = estimate_size(image_format, width, height, len(frames), mipmaps=mipmaps)

        result = build_vtf(
            frames,
            image_format=image_format,
            has_alpha=has_alpha,
            width=width,
            height=height,
            flags=flags,
            mipmaps=mipmaps,
            mip_filter=mip_filter,
            version=version,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"gif2vtf: {exc}", file=sys.stderr)
        return 1

    over_limit = len(result.data) > presets.SPRAY_SIZE_LIMIT
    if over_limit and bool(preset["warn_spray_size"]):
        message = (
            f"output is {len(result.data) / 1024:.1f} KB, over the "
            f"{presets.SPRAY_SIZE_LIMIT // 1024} KB spray limit. Reduce the "
            "resolution or frame count, or pick a more compressed format."
        )
        if args.strict_size:
            print(f"gif2vtf: {message}", file=sys.stderr)
            return 1
        print(f"gif2vtf: warning: {message}", file=sys.stderr)

    output = args.output or args.input.with_suffix(".vtf")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(result.data)
    except OSError as exc:
        print(f"gif2vtf: {exc}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Input:       {args.input}")
        print(f"Output:      {output}")
        stages = f"Frames:      {result.frame_count}"
        if args.optimize_frames or args.decimate is not None:
            parts = [f"decoded {decoded_count}"]
            if args.optimize_frames:
                parts.append(f"optimized {optimized_count}")
            if args.decimate is not None:
                parts.append(f"decimated {decimated_count}")
            stages += f" ({' -> '.join(parts)})"
        print(stages)
        if optimize_stats is not None:
            print(
                f"Optimized:   removed {optimize_stats.zero_delay_removed} zero-delay, "
                f"{optimize_stats.duplicates_removed} duplicate frame(s)"
            )
        if overlay_image is not None:
            timing = "after resize" if args.overlay_after_resize else "before resize"
            position = "centered" if args.overlay_center else "top-left"
            print(f"Overlay:     {args.overlay} ({timing}, {position}, x={args.overlay_x}, y={args.overlay_y})")
        print(f"Dimensions:  {result.width}x{result.height}")
        print(f"Format:      {result.image_format.name} ({'alpha' if has_alpha else 'no alpha'})")
        print(f"Mipmaps:     {'yes' if mipmaps else 'no'} ({result.mipmap_count} level(s))")
        print(f"Flags:       {flags!r}")
        print(f"Size:        {len(result.data) / 1024:.1f} KB (estimate {estimated / 1024:.1f} KB)")
    else:
        print(f"Wrote {output} ({result.frame_count} frames, {len(result.data) / 1024:.1f} KB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
