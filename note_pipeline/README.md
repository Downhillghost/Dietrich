# Dietrich Internals

`note_pipeline` is the maintained conversion library in this repository. It
imports Samsung Notes files, converts them into a neutral note model, and
exports that model to output formats such as PNG and Excalidraw.

## Layers

- `input/`: source-format importers
- `model/`: source-neutral document, page, element, asset, and result classes
- `output/`: exporters that consume only the neutral model

The Samsung Notes importer uses Kaitai-generated Python for deterministic binary
structures. Samsung-specific interpretation stays inside
`input/samsung_notes/`; output code does not depend on Samsung parser objects.

## Samsung Notes Input

Important modules:

- `input/samsung_notes/source.py`: loads `note.note` into Kaitai-backed source objects
- `input/samsung_notes/generated/`: committed Python generated from `schema/samsung_notes/`
- `input/samsung_notes/note_adapters.py`: compatibility conversion for dict-returning parser APIs
- `input/samsung_notes/page_parser.py`: page metadata, backgrounds, strokes, and images
- `input/samsung_notes/importer.py`: converts Samsung Notes input into `NoteDocument`
- `input/samsung_notes/runtime.py`: compatibility helpers for existing scripts

## Public Entry Points

Library use:

```python
from note_pipeline.pipeline import export_note_source

export_note_source("path/to/note.sdocx", output_format="png")
```

CLI wrapper:

```powershell
python dietrich.py path\to\note.sdocx --format png
python dietrich.py path\to\note.sdocx --format excalidraw
```

The CLI detects input formats through `input/registry.py`. Add future note
formats by registering another `NoteImporter` implementation with its own
`supports_path()` method.

## Kaitai Regeneration

The project requires the `kaitaistruct` Python package. The Kaitai compiler is
only needed when editing files in `schema/samsung_notes/`.

```powershell
powershell -ExecutionPolicy Bypass -File tools/generate_kaitai.ps1
```

Generated parser files are committed so users do not need the compiler.
