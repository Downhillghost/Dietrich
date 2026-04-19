# Samsung Notes `.sdocx` Container Specification

This document describes the high-level container structure of Samsung Notes
`.sdocx` files.

## 1. Overview

A `.sdocx` file is a ZIP archive. After extraction, the note content is stored
as a note root directory containing:

```text
<note-root>/
  note.note
  pageIdInfo.dat
  end_tag.bin
  <page-uuid>.page
  <page-uuid>.page
  ...
  media/
    mediaInfo.dat
    <bind-id>@<filename>
    <bind-id>@<filename>
    ...
```

The importer also accepts an already extracted note root.

## 2. Top-Level Files

| Path | Purpose |
| :--- | :--- |
| `note.note` | Main note-level metadata and keyboard-text object data |
| `pageIdInfo.dat` | Page order sidecar |
| `end_tag.bin` | Compact note summary sidecar |
| `*.page` | Individual page/layer/object payloads |
| `media/mediaInfo.dat` | Media bind-id table |
| `media/*` | Referenced assets such as PDFs, images, and `.spi` painting/cache files |

Dedicated format documents:

- `note.note`: [`note_format_specification.md`](note_format_specification.md)
- `.page`: [`page_format_specification.md`](page_format_specification.md)
- `.spi`: [`spi_format_specification.md`](spi_format_specification.md)
- `pageIdInfo.dat`: [`page_id_info_format_specification.md`](page_id_info_format_specification.md)
- `mediaInfo.dat`: [`media_info_format_specification.md`](media_info_format_specification.md)
- `end_tag.bin`: [`end_tag_format_specification.md`](end_tag_format_specification.md)

## 3. Page Files

Each page is stored as its own `<page-uuid>.page` file.

Important points:

- the filename stem is the page UUID
- `pageIdInfo.dat` defines the intended page order

## 4. Media Directory

The `media/` directory contains:

1. `mediaInfo.dat`, which maps numeric media bind ids to filenames
2. the actual asset files referenced by page properties or objects

Known media roles:

- imported PDF backgrounds
- inserted image bitmaps
- `.spi` painting/cache files

The bind id is authoritative. The filename usually starts with the same bind id,
but parsers should resolve media through `mediaInfo.dat` rather than relying on
filename text alone.

## 5. Practical Resolution Rules

These rules are reliable:

1. open the `.sdocx` as a ZIP archive
2. locate the note root directory
3. read `pageIdInfo.dat` for page order
4. read `note.note` for note-level metadata and body text
5. parse each `*.page` file for page geometry and drawable objects
6. resolve image/PDF references through `media/mediaInfo.dat`
7. load referenced files from `media/`

## 6. Optional and Generated Files

Rendered preview folders are not part of the `.sdocx` container format. They
are local export artifacts and should not be treated as authoritative note data.
