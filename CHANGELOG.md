# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-06

### Added

- Composite static PNG or TGA images with transparency onto every frame of the GIF (before resize by default): `--overlay`, `--overlay-x`, `--overlay-y`, `--overlay-center`, and `--overlay-after-resize`.

[1.1.0]: https://github.com/Zisomerism/gif2vtf/releases/tag/v1.1.0

## [1.0.0] - 2026-06-05

Initial public release.

### Added

- Convert animated GIFs (and other animated images) into multi-frame animated
  VTF files via the `gif2vtf` command.
- Presets: `general` (default) and `spray` (512 KB-aware defaults with point
  sample and clamp flags).
- Frame selection options: `--skip`, `--max-frames`, `--decimate`, and the
  experimental `--optimize-frames` / `--optimize-fuzz` (removes zero-delay and
  duplicate frames).
- Resize and clamp options: `--resize`, `--resize-method`, `--width`,
  `--height`, `--clamp`, `--clamp-width`, `--clamp-height`, `--resize-filter`.
- Image format control: `--format`, `--alpha-format`, `--alpha-threshold`, with
  automatic alpha detection.
- Mipmap control: `--mipmaps` / `--no-mipmaps` and `--mip-filter`.
- VTF flag control: `--flag` and `--no-flag`, plus `--version` and
  `--strict-size`.

[1.0.0]: https://github.com/Zisomerism/gif2vtf/releases/tag/v1.0.0
