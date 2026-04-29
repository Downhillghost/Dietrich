# Dietrich

Dietrich helps you open Samsung Notes files and export their content into open,
portable formats.

The name is German for a lockpick: a small tool used to open locks. Here it is a
metaphor for unlocking your own notes from a closed file format, so they can be
read, archived, converted, and reused outside the original app.

## What It Does

Samsung Notes files with the `.sdocx` extension are ZIP archives containing
binary note metadata, page files, media sidecars, and embedded assets. Dietrich
parses those structures, converts them into a neutral internal note model, and
exports that model to other formats.

Supported today:

Samsung Notes input:

- `.sdocx` files and already extracted Samsung Notes folders
- page dimensions, page order, note metadata, background color, and note summary
  sidecars
- handwriting strokes, including per-point pressure and timing metadata
- keyboard body text with rich-text spans
- native Samsung Notes text fields
- inserted images and PDF page backgrounds
- media tables and `.spi` media metadata preservation

Samsung Notes output:

- `.sdocx` export for neutral pages and Excalidraw infinite-canvas materialized
  as a finite page
- handwriting strokes and stroke-like shape outlines
- native Samsung Notes text-field objects for neutral text elements
- native Samsung Notes image objects for resolved image assets
- frame outlines with positioned heading text fields

Excalidraw input:

- `.excalidraw` JSON files
- Obsidian Excalidraw `.excalidraw.md` files with drawing blocks
- freedraw, lines, arrows, rectangles, diamonds, ellipses, images, text, and
  frames
- image assets embedded in the scene or referenced from nearby markdown assets
- frame-child grouping in the neutral model

Excalidraw output:

- `.excalidraw` scene export from the neutral model
- handwriting strokes, images, text, and frames
- frame child assignment when neutral frame relationships are available

PNG output:

- rendered note pages or materialized canvases
- Samsung Notes PDF backgrounds, images, strokes, shapes, and text elements

Target-specific structures are preserved where possible instead of being
silently discarded.

## Why A Neutral Model?

Dietrich is intentionally built as:

```text
input format -> neutral note model -> output format
```

Samsung Notes and Excalidraw are both supported input formats, and the code is
organized so other note formats can be added later without rewriting the
exporters. A future OneNote, GoodNotes, Xournal++, or other importer should only
need to convert its source format into the same internal model. PNG,
Excalidraw, Samsung Notes, and future exporters can then consume that model
without knowing where the note came from.

The main layers are:

- `note_pipeline/input/`: importers for source formats
- `note_pipeline/model/`: source-neutral document, page, element, and asset classes
- `note_pipeline/output/`: exporters for target formats

For Samsung Notes, deterministic binary structure parsing is generated from
Kaitai Struct specifications in `schema/samsung_notes/`. Samsung-specific
semantic interpretation stays in `note_pipeline/input/samsung_notes/`. Output
code consumes only the neutral model.

Input format detection is handled by the importer registry in
`note_pipeline/input/registry.py`. Each importer implements `supports_path()`.
The Samsung Notes importer accepts `.sdocx` files and extracted folders that
look like Samsung Notes packages. The Excalidraw importer accepts raw
`.excalidraw` JSON files and Obsidian `.excalidraw.md` files with drawing
blocks. Future importers can use file extensions, container signatures, folder
structure, or any other reliable check.

## Install

Use Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The generated Kaitai Python files are committed, so normal users do not need the
Kaitai compiler.

## Usage

Export a `.sdocx` file to PNG pages:

```powershell
python dietrich.py path\to\note.sdocx
```

Choose an output directory:

```powershell
python dietrich.py path\to\note.sdocx --output-dir exported_pages
```

Export to Excalidraw:

```powershell
python dietrich.py path\to\note.sdocx --format excalidraw --output-dir exported_scene
```

Tune keyboard-text layout when the automatic estimate is slightly off:

```powershell
python dietrich.py path\to\note.sdocx --text-scale 2.19
```

You can also pass an already extracted Samsung Notes folder instead of a
`.sdocx` archive.

```powershell
python dietrich.py path\to\extracted_note_folder --format png
```

Export Excalidraw content to Samsung Notes:

```powershell
python dietrich.py path\to\scene.excalidraw --format sdocx --output-dir samsung_export
```

For Excalidraw files, including Obsidian Excalidraw markdown files with
`compressed-json` drawing blocks, Dietrich materializes the infinite canvas as
one finite Samsung Notes page sized to the content bounds plus margin.
Excalidraw frames remain frame elements in the neutral model; Samsung Notes
export renders them as an outline plus a positioned heading text field above the
frame. Very large canvases are written structurally, but Samsung Notes may
become slow or reject them depending on the device/app version.

Handwriting and common Excalidraw shapes are written as Samsung stroke objects.
Lines and arrows are densified into stroke paths, with arrow heads written as
additional strokes. Excalidraw text is written as positioned Samsung Notes text
field objects with Samsung-specific minimum dimensions and vertical padding.
Resolvable Excalidraw images are written as native Samsung image objects and
registered in `media/mediaInfo.dat`. The `.sdocx` exporter writes the document
end tag and appends the trailing blank page used for import compatibility.

Show all CLI options:

```powershell
python dietrich.py --help
```

### Text Scale

`--text-scale` controls how Samsung Notes keyboard body text is materialized
onto pages. It multiplies the reconstructed font size, line height, line
wrapping, and indentation used for that typed-text layout. It does not affect
handwriting strokes, images, PDF backgrounds, native Samsung Notes text-field
objects, Excalidraw text elements, or PNG output resolution.

By default, Dietrich does not use a fixed number. If `--text-scale` is omitted,
the Samsung Notes importer auto-estimates the value from the note metadata:

- width `720`: uses about `1.6`
- width `961`: uses about `3.2`
- width `1080`: uses about `2.19`
- widths between those families are interpolated
- widths below or above those families are scaled from the nearest family and
  clamped to the supported range `0.5` through `8.0`
- missing or unsupported metadata falls back to `1.0`

These presets are empirical and are not strictly monotonic: different Samsung
Notes page families appear to need different text reconstruction scales even
when the page width is larger.

If typed text appears too small or wraps too late, increase `--text-scale`. If
typed text appears too large or wraps too early, decrease it.

## Library Use

```python
from note_pipeline.pipeline import export_note_source

export_note_source(
    "path/to/note.sdocx",
    output_format="excalidraw",
    output_dir="exported_scene",
)
```

## Important Files

- `dietrich.py`: command-line entrypoint
- `note_pipeline/`: parser, model, and exporter implementation
- `schema/samsung_notes/`: Kaitai specifications
- `note_pipeline/input/samsung_notes/generated/`: committed generated Python
- `sdocx_specification`: current understanding of the sdocx format

## Regenerating Kaitai Parsers

Only needed when editing files in `schema/samsung_notes/`.

Install `kaitai-struct-compiler` and run:

```powershell
powershell -ExecutionPolicy Bypass -File tools/generate_kaitai.ps1
```

Generated parser files are committed so users do not need the compiler.

## Status

Dietrich currently covers the main note structures needed for practical
conversion between Samsung Notes, Excalidraw, and PNG: page metadata, strokes,
native text fields, images, PDF backgrounds for rendering, frames, media tables,
page ordering, note summaries, and end-tag data. Some vendor-specific payloads,
especially `.spi` painting/cache payloads and exact pen-material rendering, are
preserved as structured metadata until they have a stable cross-format mapping.

## Contributing

Good contributions include:

- adding sanitized example files
- improving format documentation
- adding input support for another note format
- adding another exporter
- improving Samsung Notes coverage for unsupported objects
- reducing format-specific assumptions in the neutral model

Please avoid committing private notes, extracted `.sdocx` contents and generated
images unless they are intentionally part of the public documentation set.

## License And Legal

Samsung Notes and S Pen are trademarks of Samsung. This project is independent
and is not affiliated with or endorsed by Samsung.

Dietrich is intended for interoperability with notes you are allowed to access.
It is not intended to bypass encryption, authentication, or access controls.

Dietrich is released under the MIT License. See `LICENSE` for details.
