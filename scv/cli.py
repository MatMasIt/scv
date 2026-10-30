"""Command line entry point: python -m scv.cli or scv command."""

from __future__ import annotations
import argparse
from pathlib import Path
import json
import os
import sys

from .core import ArchiveError, PRESETS, Settings, Job, encode, inspect, VERSION
from .exporter import export_video


def main(argv=None):
    """Parse CLI arguments and run the requested SCV operation."""
    # When no arguments are provided and running in an interactive terminal,
    # launch the SCV Studio GUI if a desktop display exists, otherwise show help.
    raw_args = sys.argv[1:] if argv is None else list(argv)
    if not raw_args:
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or sys.platform in ("win32", "darwin"))
        if has_display:
            try:
                from .studio import main as studio_main
                return studio_main([])
            except Exception:
                pass

    parser = argparse.ArgumentParser(
        prog="scv", description="Slide Compressed Video (SCV) Suite CLI"
    )
    parser.add_argument("--version", action="version", version=VERSION)
    sub = parser.add_subparsers(dest="command")

    # GUI subcommands
    sub.add_parser("studio", help="Launch the SCV Studio desktop application")
    player_cmd = sub.add_parser("player", help="Launch the SCV Player desktop GUI")
    player_cmd.add_argument("file", nargs="?", type=Path, help="SCV lecture to play")

    encoder_cmd = sub.add_parser("encoder", help="Launch the SCV Batch Encoder desktop GUI")
    encoder_cmd.add_argument("videos", nargs="*", type=Path, help="Videos to queue")

    exporter_cmd = sub.add_parser("gui-export", help="Launch the SCV MP4 Exporter desktop GUI")
    exporter_cmd.add_argument("file", nargs="?", type=Path, help="SCV archive to export")

    # Headless CLI subcommands
    convert = sub.add_parser("encode", help="Headless encode video into .scv")
    convert.add_argument("videos", nargs="+", type=Path)
    convert.add_argument("-o", "--output-dir", type=Path, default=Path("."))
    convert.add_argument(
        "--output", type=Path, help="Explicit .scv output path (one input only)"
    )
    convert.add_argument("--preset", choices=PRESETS, default="Balanced")
    convert.add_argument("--bitrate", type=int, help="Opus kbps (6-256)")
    convert.add_argument("--quality", type=int, help="WebP quality (1-100)")
    convert.add_argument("--fps", type=float, help="Slide detection sample rate")
    convert.add_argument("--change", type=float)
    convert.add_argument("--stable", type=float)
    convert.add_argument("--settle", type=int)
    convert.add_argument("--stereo", action="store_true")
    convert.add_argument("--ocr", action="store_true", help="Extract slide text with Tesseract")
    convert.add_argument("--ocr-lang", default="eng", help="Tesseract language code")

    export = sub.add_parser("export", help="Headless export of .scv to MP4 video")
    export.add_argument("file", type=Path)
    export.add_argument("-o", "--output", required=True, type=Path)
    export.add_argument("--crf", type=int, default=20)

    info = sub.add_parser("inspect", help="Print manifest from an SCV archive")
    info.add_argument("file", type=Path)

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "studio":
        from .studio import main as studio_main
        return studio_main([])

    if args.command == "player":
        from .player import main as player_main
        return player_main([str(args.file)] if args.file else [])

    if args.command == "encoder":
        from .encoder import main as encoder_main
        return encoder_main([str(v) for v in args.videos] if args.videos else [])

    if args.command == "gui-export":
        from .export_gui import main as export_gui_main
        return export_gui_main([str(args.file)] if args.file else [])

    if args.command == "export":
        try:
            export_video(args.file, args.output, crf=args.crf)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    if args.command == "inspect":
        try:
            print(json.dumps(inspect(args.file), indent=2, ensure_ascii=False))
        except (ArchiveError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.output and len(args.videos) != 1:
        parser.error("--output requires exactly one input video")

    settings = Settings.from_preset(
        args.preset,
        bitrate=args.bitrate,
        quality=args.quality,
        fps=args.fps,
        change=args.change,
        stable=args.stable,
        settle=args.settle,
        stereo=True if args.stereo else None,
        ocr=args.ocr,
        ocr_lang=args.ocr_lang,
    )
    try:
        settings.validate()
        for source in args.videos:
            dest = (
                args.output if args.output else args.output_dir / (source.stem + ".scv")
            )
            print(f"\n{source} -> {dest}", flush=True)
            encode(
                source,
                dest,
                settings,
                lambda p, msg: print(
                    f"\r{p * 100:5.1f}%  {msg[:70]:<70}", end="", flush=True
                ),
            )
            print()
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
