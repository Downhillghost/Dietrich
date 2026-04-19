from __future__ import annotations

import argparse
import os

from note_pipeline.input import get_importer_class_for_path
from note_pipeline.pipeline import export_note_source


def _default_output_dir(note_source: str, output_format: str) -> str:
    format_name = output_format.lower().strip()
    if os.path.isfile(note_source):
        source_dir = os.path.dirname(note_source)
        source_name = os.path.splitext(os.path.basename(note_source))[0]
        suffix = "rendered_pages" if format_name == "png" else f"{format_name}_export"
        return os.path.join(source_dir, f"{source_name}_{suffix}")

    source_dir = os.path.abspath(note_source)
    suffix = "rendered_pages" if format_name == "png" else f"{format_name}_export"
    return os.path.join(source_dir, suffix)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert supported note files or extracted note folders into open output formats."
    )
    parser.add_argument("note_source", help="Path to a supported note file or extracted note folder")
    parser.add_argument(
        "--output-dir",
        help=(
            "Directory where exported files will be written. Defaults to a format-specific directory "
            "next to the input file or inside the extracted note folder."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("png", "excalidraw"),
        default="png",
        help="Output format to export. Defaults to png.",
    )
    parser.add_argument(
        "--thickness-scale",
        type=float,
        default=0.6,
        help="Scale factor applied only to rendered stroke thickness in PNG export.",
    )
    parser.add_argument(
        "--text-scale",
        type=float,
        help=(
            "Override the auto-estimated keyboard-text scale used for keyboard-text layout. "
            "Larger values make text larger and wrap earlier."
        ),
    )
    parser.add_argument(
        "--output-scale",
        type=float,
        default=1.0,
        help="Scale factor for PNG output resolution without changing note layout.",
    )
    args = parser.parse_args()

    if args.thickness_scale <= 0:
        print(f"Thickness scale must be positive: {args.thickness_scale}")
        return 2
    if args.text_scale is not None and args.text_scale <= 0:
        print(f"Text scale must be positive: {args.text_scale}")
        return 2
    if args.output_scale <= 0:
        print(f"Output scale must be positive: {args.output_scale}")
        return 2

    note_source = os.path.abspath(args.note_source)
    if not os.path.exists(note_source):
        print(f"Input path not found: {note_source}")
        return 2

    importer_cls = get_importer_class_for_path(note_source)
    if importer_cls is None:
        print(f"Unsupported note source: {note_source}")
        return 2

    output_dir = os.path.abspath(args.output_dir or _default_output_dir(note_source, args.format))

    result = export_note_source(
        note_source=note_source,
        output_dir=output_dir,
        output_format=args.format,
        thickness_scale=args.thickness_scale,
        text_scale_override=args.text_scale,
        output_scale=args.output_scale,
    )
    print(f"Export complete ({result.format_name}).")
    for output_path in result.output_paths:
        print(f"  Wrote: {output_path}")
    for warning in result.warnings:
        print(f"  Warning: {warning}")
    return 0
