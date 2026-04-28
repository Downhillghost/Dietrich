# Dietrich Internals

`note_pipeline` is the maintained conversion library in this repository. It
imports supported note files, converts them into a neutral note model, and
exports that model to output formats such as PNG, Excalidraw, and Samsung Notes
`.sdocx`.

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
- `input/samsung_notes/page_parser.py`: page metadata, backgrounds, strokes, images, and text fields
- `input/samsung_notes/importer.py`: converts Samsung Notes input into `NoteDocument`
- `input/samsung_notes/runtime.py`: compatibility helpers for existing scripts

## Excalidraw Input

- `input/excalidraw.py`: converts an Excalidraw infinite canvas to one finite
  neutral canvas sized to its content bounds. It supports raw `.excalidraw` JSON
  and Obsidian `.excalidraw.md` drawing blocks, including `compressed-json`.
  Common Excalidraw shapes are imported as stroke outlines. Freedraw, text,
  images, lines, arrows, rectangles, diamonds, ellipses, and frames are mapped
  into neutral elements. Image references in Obsidian markdown are resolved
  relative to the source drawing and common asset folders. Frame membership is
  preserved in `FrameElement.child_element_ids` when Excalidraw provides
  `frameId` links or when elements are contained inside a frame.

## Neutral Model

The neutral model currently includes:

- `StrokeElement`: handwriting and stroke-like shape outlines
- `TextElement`: positioned text with font and style metadata
- `ImageElement`: positioned image assets with optional crop metadata
- `FrameElement`: frame rectangle, heading, and grouped child element ids
- `PdfBackgroundElement`: page-level PDF background references
- `UnsupportedElement`: preserved source metadata for objects without a target mapping

## Samsung Notes Output

- `output/samsung_notes.py`: writes a `.sdocx` package with Samsung page files,
  Samsung-style object/layer/page hashes, handwriting strokes, stroke-like shape
  outlines, native Samsung text field objects, native Samsung image objects, and
  frame outlines with heading text fields. PDF backgrounds and unsupported
  objects are omitted with export warnings when there is no Samsung output
  mapping. Archives are written with Samsung-compatible ZIP metadata, include
  `note.note`, `pageIdInfo.dat`, `end_tag.bin`, `media/mediaInfo.dat`, and a
  trailing blank page for import compatibility. Excalidraw infinite-canvas input
  is materialized as one finite Samsung Notes page using Samsung's native
  page-coordinate stroke units.

Samsung text fields use output-specific sizing constants, including a generous
vertical field scale, so the neutral text model does not need Samsung-specific
layout inflation. Text is normalized before UTF-16LE encoding so Unicode
characters from JSON/markdown sources do not stop export.

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
python dietrich.py path\to\scene.excalidraw --format sdocx
python dietrich.py path\to\scene.excalidraw.md --format sdocx
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
