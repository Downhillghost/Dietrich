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

- `.sdocx` files and already extracted Samsung Notes folders
- page dimensions and note metadata
- PDF page backgrounds
- inserted images
- handwriting strokes, including per-point pressure and timing metadata
- keyboard text with rich-text spans
- `.spi` media metadata preservation
- PNG page export
- Excalidraw scene export

Unknown Samsung-specific structures are preserved where possible instead of
being silently discarded.

## Why A Neutral Model?

Dietrich is intentionally built as:

```text
input format -> neutral note model -> output format
```

Samsung Notes is the first supported input format, but the code is organized so
other note formats can be added later without rewriting the exporters. A future
OneNote, GoodNotes, Xournal++, or other importer should only need to convert its
source format into the same internal model. PNG, Excalidraw, and future
exporters can then consume that model without knowing where the note came from.

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
The Samsung Notes importer currently accepts `.sdocx` files and extracted
folders that look like Samsung Notes packages. Future importers can use file
extensions, container signatures, folder structure, or any other reliable check.

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

Show all CLI options:

```powershell
python dietrich.py --help
```

### Text Scale

`--text-scale` controls how Samsung Notes keyboard text is materialized onto
pages. It multiplies the reconstructed font size, line height, line wrapping,
and indentation used for typed text. It does not affect handwriting strokes,
images, PDF backgrounds, or PNG output resolution.

By default, Dietrich does not use a fixed number. If `--text-scale` is omitted,
the Samsung Notes importer auto-estimates the value from the note metadata:

- width `720`: uses about `1.6`
- width `961`: uses about `3.2`
- width `1080`: uses about `2.19`
- widths between those families are interpolated
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

Dietrich is useful, but the Samsung Notes format is not fully documented. Some
fields are still partially understood, especially stroke rendering
details and parts of `.spi` image payloads. The parser keeps unknown data where
possible so support can improve without throwing information away.

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
