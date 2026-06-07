# gif2vtf

Convert animated GIFs into animated [Valve Texture Format](https://developer.valvesoftware.com/wiki/Valve_Texture_Format) (`.vtf`) files from the command line.

This automates the manual workflow described in this [Steam Team Fortress 2 animated sprays guide](https://steamcommunity.com/sharedfiles/filedetails/?id=1288408087): split a GIF into frames, normalise their size, and pack them into a single multi-frame VTF. Instead of GIMP plus VTFEdit, you run one command.

There are some basic options for trimming and decimating GIFs, basic GIF optimization, and applying PNG or TGA images as overlays to the GIFs.


## Installation

gif2vtf is on pypi, you can install it from pypi using:

```bash
pip install gif2vtf
```


To install from a source checkout instead:

```bash
pip install .
```

To run the tests as well:

```bash
pip install .[dev]
pytest
```


## Usage

```bash
gif2vtf input.gif                 # writes input.vtf with the "general" preset
gif2vtf input.gif -o out.vtf
gif2vtf input.gif --preset spray --width 128 --height 128
```

### Presets

A preset only supplies defaults; any explicit flag overrides it.

| Preset | Defaults |
| --- | --- |
| `general` (default) | mipmaps on, resize to nearest power of two, clamp 4096, `DXT1` / `DXT5` for alpha |
| `spray` | mipmaps off, clamp 512, point sample + clamp S/T + no LOD flags, warns if over 512 KB |

### Options

```
--format FORMAT          Format for frames without alpha (default DXT1)
--alpha-format FORMAT    Format for frames with alpha (default DXT5)
--alpha-threshold N      One-bit-alpha cutoff (0-255)

--resize / --no-resize   Resize frames to a valid VTF size
--resize-method METHOD   nearest-power2 | biggest-power2 | smallest-power2 | set
--width W --height H     Explicit target size (implies the 'set' method)
--clamp / --no-clamp     Cap dimensions to the clamp size
--clamp-width W          Maximum width when clamping
--clamp-height H         Maximum height when clamping
--resize-filter FILTER   nearest | bilinear | bicubic | lanczos

--mipmaps / --no-mipmaps Generate a mipmap chain
--mip-filter FILTER      nearest | bilinear

--flag NAME              Add a VTF flag, e.g. CLAMP_S (repeatable)
--no-flag NAME           Remove a preset flag (repeatable)

--max-frames N           Keep at most N frames
--skip N                 Skip the first N frames
--decimate N             Drop every Nth frame (1-based); N must be >= 2
--optimize-frames        EXPERIMENTAL: remove duplicate and zero-delay frames
--optimize-fuzz N        Max per-channel RGBA difference for duplicate detection

--overlay PATH           PNG/TGA image composited onto every frame
--overlay-x N            Horizontal overlay offset in pixels (default: 0)
--overlay-y N            Vertical overlay offset in pixels (default: 0)
--overlay-center         Center overlay on each frame, then apply x/y nudge
--overlay-after-resize   Apply overlay after resize (default: before resize)

--version 7.5            VTF version (7.2-7.5)
--strict-size            Fail instead of warning when over the spray limit
-v / --verbose           Print conversion details
```

### Reducing frame count

Sprays have a tight size budget, so trimming frames is often necessary.

- `--decimate N` drops every Nth frame using 1-based counting. `--decimate 2` on a 10-frame GIF removes frames 2, 4, 6, 8, 10 and keeps 5; `--decimate 4` removes every 4th frame and keeps roughly three quarters.
- `--optimize-frames` is experimental. It removes whole frames that add nothing to the visible animation: zero-delay intermediate frames and runs of consecutive identical frames (the spirit of ImageMagick's [`RemoveZero` and `RemoveDups`](https://usage.imagemagick.org/anim_opt/#frame_opt) layer methods). Duplicate detection is exact by default; raise the tolerance with `--optimize-fuzz N`, where `N` is the maximum allowed per-channel difference. This does not perform GIF sub-frame or disposal optimization, which is irrelevant to VTF because every VTF frame stores a full image.

Optimization runs before decimation, and both run after `--skip` / `--max-frames`.

### Overlay

Composite a static PNG or TGA (with alpha) on top of every frame. By default the overlay is applied **before resize**, so it should match the source GIF dimensions and will scale with the animation. Use `--overlay-after-resize` when the overlay is already sized for the final VTF output (e.g. a 128x128 logo on a 128x128 spray).

```bash
# Full-size overlay that scales with the GIF (default)
gif2vtf anim.gif --overlay watermark.png

# Centered logo on a 128x128 spray (overlay must be 128x128)
gif2vtf anim.gif -o spray.vtf --preset spray --width 128 --height 128 \
  --overlay logo.png --overlay-center --overlay-after-resize

# Watermark at a fixed offset in final pixel space
gif2vtf anim.gif -o out.vtf --overlay stamp.png --overlay-x 8 --overlay-y 8 \
  --overlay-after-resize
```

Positioning defaults to the top-left corner (`--overlay-x 0 --overlay-y 0`). With `--overlay-center`, the overlay is centered first and `--overlay-x` / `--overlay-y` nudge it from there.

Supported format names: `DXT1`, `DXT3`, `DXT5`, `DXT1_ONEBITALPHA`, `BGR888`, `RGB888`, `BGRA8888`, `RGBA8888`, `BGR565`, `RGB565`, `ATI2N`.

## Notes and limitations

- **Dimensions must be powers of two.** srctools only writes power-of-two VTFs, so all resize methods converge on power-of-two sizes. With `--no-resize`, every frame must already be a valid power-of-two size.
- **Frame rate is not stored in the VTF.** Source controls animation timing through the material (`.vmt`) and engine, not the texture. In-game sprays play at roughly 5 FPS regardless of the source GIF.
- **Disabling mipmaps** writes only the base image (and sets the `NO_MIP` flag), which keeps sprays under the 512 KB limit as the guide recommends.
- **Mipmap filters** are limited to `nearest` and `bilinear` (all srctools supports).
- This tool outputs `.vtf` only; it does not generate a companion `.vmt` material file.

## License

This project is licensed under the GNU General Public License, version 3 or later (GPL-3.0-or-later). See [LICENSE](LICENSE) for the full text.
