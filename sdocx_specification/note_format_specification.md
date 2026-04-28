# Samsung Notes `note.note` Format Specification

This document describes the supported structure of Samsung Notes `note.note`
files.

## 1. High-Level Layout

`note.note` starts with a short fixed header, followed by note metadata, then two length-prefixed serialized object blobs:

1. Title object
2. Body object

The body object contains the wrapped keyboard text and its rich-text metadata.

## 2. Fixed Header (`0x00..0x0D`)

| Offset | Size | Field | Notes |
| :--- | :--- | :--- | :--- |
| `0x00` | 4 | `integrity_offset` | Absolute file offset of the integrity/hash trailer |
| `0x04` | 1 | constant | Always `0x04` in observed files |
| `0x05` | 4 | `header_flags` | Header flag field |
| `0x09` | 1 | constant | Always `0x04` in observed files |
| `0x0A` | 4 | `property_flags` | Controls optional note-level fields |

The actual note metadata begins at file offset `0x0E` (`14` decimal).

## 3. Note Metadata Block

Starting at `0x0E`, the metadata block stores these fields in order:

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `formatVersion` | `u32` LE | Observed value: `4000` |
| `noteId` | `u16` char count + UTF-16LE | Usually an empty string |
| `fileRevision` | `u32` LE | |
| `createdTime` | `u64` LE | Raw timestamp value |
| `modifiedTime` | `u64` LE | Raw timestamp value |
| `width` | `u32` LE | Logical note width |
| `height` | `u32` LE | Logical note height across all pages |
| `pageHorizontalPadding` | `u32` LE | Logical horizontal padding |
| `pageVerticalPadding` | `u32` LE | Logical vertical padding |
| `minFormatVersion` | `u32` LE | Example: `4000` |
| `titleObjectSize` | `u32` LE | Byte length of serialized title object |
| `titleObject` | byte blob | Serialized object payload |
| `bodyObjectSize` | `u32` LE | Byte length of serialized body object |
| `bodyObject` | byte blob | Serialized object payload containing body text |

## 3.1 `property_flags` Bit Mapping

The optional metadata after the title/body blobs is controlled by `property_flags`.

| Bit | Hex | Meaning |
| :--- | :--- | :--- |
| `1` | `0x000001` | app name |
| `2` | `0x000002` | app major/minor version + patch name |
| `4` | `0x000004` | author info |
| `8` | `0x000008` | geo latitude / longitude |
| `64` | `0x000040` | template URI |
| `128` | `0x000080` | last edited page index |
| `512` | `0x000200` | last edited page image ID + last edited page time |
| `1024` | `0x000400` | string ID list |
| `2048` | `0x000800` | `bodyTextFontSizeDelta` |
| `4096` | `0x001000` | legacy pen info block |
| `8192` | `0x002000` | voice data list |
| `16384` | `0x004000` | attached file list |
| `32768` | `0x008000` | current pen info block |
| `65536` | `0x010000` | last recognized data modified time |
| `131072` | `0x020000` | fixed font |
| `262144` | `0x040000` | fixed text direction |
| `524288` | `0x080000` | fixed background theme |
| `1048576` | `0x100000` | text summarization |
| `2097152` | `0x200000` | stroke group size |
| `4194304` | `0x400000` | app custom data |

### Observed Flag Values

- text-wrapping notes: `0xC0280`
- rich-text notes: `0xC8E80`
- imported-PDF editing notes: `0xC0E80`

In supported rich-text files, these flags are present:

- `0x000400` -> `stringIdList`
- `0x000800` -> `bodyTextFontSizeDelta`
- `0x008000` -> current `penInfo`

No second optional note-level field has been identified for keyboard-text scale.

Imported-PDF editing files show a second useful variant:

- `0x000400` -> `stringIdList`
- `0x000800` -> signed `bodyTextFontSizeDelta`
- no current note-level `penInfo`

### Confirmed Metadata Pattern

For supported text notes:

- `formatVersion = 4000`
- `minFormatVersion = 4000`
- `noteId = ""`
- `width = 961`
- `height = 4119`
- `pageHorizontalPadding = 0`
- `pageVerticalPadding = 21`

### Dietrich Writer Pattern

Dietrich-generated `note.note` files use:

- `formatVersion = 4000`
- `minFormatVersion = 4000`
- `header_flags = 0x00000008`
- `property_flags = 0x000C8E80`
- `width = max(page widths)`
- `height = sum(page heights) + 8`
- `pageHorizontalPadding = 0`
- `pageVerticalPadding = 8`
- a title object built from the neutral note title
- an empty body object
- a string-id block containing the default fountain pen name and advanced
  setting used by generated stroke objects
- current pen info and fixed text/background fields compatible with generated
  pages

## 4. String Encodings Used by `note.note`

Known string encodings:

- short string: `u16` character count + UTF-16LE string
- long string: `u32` character count + UTF-16LE string

So:

- header strings such as `noteId` use the `u16` length form
- rich-text payloads use a `u32` length form

## 4.1 `stringIdList` Binary Block

When `property_flags & 0x000400 != 0`, the title/body blobs are followed by a binary string-id table:

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `stringIdBlockSize` | `u32` LE | Size of the remaining block, excluding this size field |
| `stringIdCount` | `u16` LE | Number of entries |
| repeated entries | `i32` id + `u16` string | UTF-16LE text using the short-string form |

Observed string-id entries:

- `id 0 -> com.samsung.android.sdk.pen.pen.preload.FountainPen`
- `id 1 -> 13;`
- `id 2 -> 14;`

These IDs are referenced from the newer stroke object flexible-data blocks inside `.page` files.

## 4.2 `bodyTextFontSizeDelta`

`bodyTextFontSizeDelta` (`property_flags & 0x000800`) is stored as a signed 32-bit integer.

Confirmed values:

- rich-text notes: `0`
- imported-PDF editing notes: `-5` (`0xFFFFFFFB`)

## 5. Body Object: Confirmed Rich-Text Sub-Block

The outer title/body objects are serialized Samsung text objects. Their rich-text section contains a `TextCommon` block.

Inside the serialized title/body object there is a length-prefixed `TextCommon` block:

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `textCommonSize` | `u32` LE | Byte size of the following `TextCommon` payload |
| `textLength` | `u32` LE | Character count |
| `text` | UTF-16LE | Body text |
| `spanCount` | `u32` LE | Number of span records |
| `spans` | repeated | Rich-text span records |
| `paragraphCount` | `u32` LE | Number of paragraph records |
| `paragraphs` | repeated | Paragraph-format records |
| `leftMargin` | `float32` LE | Logical units |
| `topMargin` | `float32` LE | Logical units |
| `rightMargin` | `float32` LE | Logical units |
| `bottomMargin` | `float32` LE | Logical units |
| `textGravity` | `u8` | Usually `0` in observed files |
| `sectionCount` | `u16` LE | Number of `sectionData` records |
| `sectionData` | repeated `u32,u32` | Text-section records |
| `objectSpanFlags` | `u32` LE | Present when `formatVersion >= 2035` |
| reserved | `u32` LE | Present when `formatVersion >= 2035` |
| optional object-span block | variable | Present when `objectSpanFlags & 1 != 0` |

Important parser rule:

- the ordinary span list explicitly skips span types `15`, `16`, and `18`
- those object-related spans are handled separately from the ordinary span list
- so a parser should not treat the absence of `15/16/18` in the normal span array as evidence that object-span support is missing

### Important Note

The body object is not just plain text data. It is a serialized object made of Samsung object records:

1. object-base record, type `0`
2. shape-base record, type `6`
3. shape/text record, type `7`

The shape/text record has an `ownDataOffset` at record offset `+6`. When its property mask has bit `0x1` set, the first property at that offset is the `TextCommon` size field.

So the deterministic object-local offsets are:

- `shapeTextRecordOffset = objectBaseRecordSize + shapeBaseRecordSize`
- `textCommonSizeOffset = shapeTextRecordOffset + shapeTextRecord.ownDataOffset`
- `textCommonPayloadOffset = textCommonSizeOffset + 4`

In observed rich-text files, both the title object and body object have:

- `objectBaseRecordSize = 113`
- `shapeBaseRecordSize = 66`
- `shapeTextRecord.ownDataOffset = 62`
- `textCommonSizeOffset = 241`

The maintained parser represents this through the Kaitai-backed source loader
and compatibility adapters in `note_pipeline/input/samsung_notes/`.

### `sectionData` Meaning

`sectionData` is not a generic object-reference record. It stores body-text sections such as text-section start and length.

The two stored `u32` values should therefore be interpreted as:

- `start`
- `length`

In the observed notes these records also line up with the logical page text
sections that Samsung uses while laying out body text, so they are useful for
scoping page-local text flow decisions instead of treating the whole note body
as one continuous page.

Observed pattern:

- for a 25-character body section: `(0, 25)`, `(25, 0)`

So the first section covers the whole 25-character body text on page 0, and the second record acts like an empty trailing section.

## 6. Span Record Structure

Each span is stored as:

| Field | Encoding |
| :--- | :--- |
| `payloadSize` | `u16` LE |
| payload | variable |

The payload begins with a common span base:

| Payload Offset | Size | Field |
| :--- | :--- | :--- |
| `+0x00` | 4 | `type` |
| `+0x04` | 4 | `start` |
| `+0x08` | 4 | `end` |
| `+0x0C` | 4 | `expandFlag` |

### Common Sizes

- most spans: `payloadSize = 24` -> `26` bytes total including the leading size
- strikethrough: `payloadSize = 20` -> `22` bytes total
- font name: variable-sized span, longer than `24`

## 7. Confirmed Span Types

| Type | Name | Value Encoding |
| :--- | :--- | :--- |
| `1` | foreground color | `i32` ARGB |
| `3` | font size | `float32` |
| `4` | font name | UTF-16LE string in the span payload |
| `5` | bold | boolean-ish byte |
| `6` | italic | boolean-ish byte |
| `7` | underline | boolean-ish byte plus underline metadata |
| `9` | hyper text | present, exact payload not yet decoded |
| `17` | background color | `i32` ARGB |
| `19` | timestamp | present, exact payload not yet decoded |
| `20` | strikethrough | boolean-ish byte |

The regular rich-text span list only includes the span family above. Object-related span types `15`, `16`, and `18` are not packed into that ordinary span list and instead belong to the separate object-span path described in the `TextCommon` section.

### Background Color Span

Background-color span type `17` is confirmed and must be included.

For underline spans, the trailing `i32` underline color is often serialized as `0`. In the observed files that does **not** mean "transparent underline"; it behaves like "no explicit underline color override", so renderers should fall back to the text color when the underline-color alpha is zero.

### Font Size Note

For rendering, the stored `float32` font size should be used directly.

The only confirmed serialized note-level modifier related to keyboard text size is the optional `bodyTextFontSizeDelta` field (`property_flags & 0x800`):

- text-wrapping notes do not serialize this field
- rich-text notes serialize it explicitly with value `0`

## 8. Paragraph Record Structure

Each paragraph record is stored as:

| Field | Encoding |
| :--- | :--- |
| `payloadSize` | `u16` LE |
| payload | variable |

The payload begins with a common paragraph base:

| Payload Offset | Size | Field |
| :--- | :--- | :--- |
| `+0x00` | 4 | `type` |
| `+0x04` | 4 | `startParagraphIndex` |
| `+0x08` | 4 | `endParagraphIndex` |

Observed paragraph records use `payloadSize = 20` (`22` bytes total including the size field).

Important correction:

- paragraph records are keyed by **paragraph index ranges**, not text-character ranges

This is consistent with paragraph parsing that treats `start` as an index into the split paragraph array.

## 9. Confirmed Paragraph Types

| Type | Name | Value Encoding / Meaning |
| :--- | :--- | :--- |
| `1` | direction | present; exact semantics still limited |
| `2` | indent level | `u32 level`, `u32 direction` |
| `3` | alignment | `0 = left`, `1 = right`, `2 = center`, `3 = justify/both` |
| `4` | line spacing | `u8 type`, `float32 spacing` |
| `5` | bullet | `u32 bulletType`, `u32 extraValue` |
| `6` | parsing state | `u32` bool-ish flag (`0/1`) used by Samsung's paragraph parsing/hypertext pipeline |

### Line Spacing Type

Observed line-spacing type values:

- `0 = pixel`
- `1 = percent`

### Bullet Type

Observed bullet type values:

- `0 = none`
- `1 = arrow`
- `2 = checker`
- `3 = diamond`
- `4 = digit`
- `5 = circled digit`
- `6 = alphabet`
- `7 = roman numeral`
- `8 = solid circle`

## 10. Observed Body Text Patterns

### Rich-Text Pattern

- text length: `35`
- text content: leading newlines, a short body line, then trailing newlines
- span count: `7`
- paragraph count: `16`
- margins: `[16.0, 10.0, 16.0, 10.0]`
- `textGravity = 0`
- `objectCount = 2`

### Leading-Space Pattern

- text length: `52`
- same structure as the rich-text pattern, but with additional leading spaces before the body line
- span count: `7`
- paragraph count: `16`
- margins: `[16.0, 10.0, 16.0, 10.0]`
- `textGravity = 0`
- `objectCount = 2`

### Style Variant Findings

- font-size variant: adds a span type `3` record with value `12.0`
- font-color variant: adds a span type `1` record with a different ARGB value
- text-highlight variant: highlight is represented with normal span records, especially span type `17`

## 11. Page-Flow Relationship to `.page` Files

Observed page-flow relationship:

- note logical width: `961`
- page width from `.page`: `1440`
- scale factor: about `1.5x`

Using the observed values, the logical height per page is:

`(noteHeight - 2 * pageVerticalPadding) / pageCount`

For supported text notes:

- `(4119 - 42) / 3 = 1359`

This matches the `.page` canvas height after applying the same approximate `1.5x` scale.

Dietrich uses this relationship to materialize wrapped keyboard text into page coordinates.

## 12. Text Layout Observations

The file format alone is not the whole text-layout story. Samsung Notes uses
additional layout normalization when measuring or flowing body text:

- the default page width participates in a document-ratio calculation
- body text insertion and movement use that ratio
- text layout uses both document pixel size and `textSizeDelta`
- tablet UX can use a default text-size delta of `-5`, while other layouts can use `0`

### Practical Implication

The `.page` pixel size is therefore not the sole determinant of keyboard-text scale. Samsung also uses:

- a document-width-derived normalization factor (`pageDefaultWidth / 360`)
- a device/display-dependent `bodyTextFontSizeDelta` conversion path

This explains why notes from different internal width families such as `720` and `961` can require different rendering multipliers even when the stored span font size is the same.

## 13. Container Sidecar: `end_tag.bin`

For a dedicated file-level description, see `end_tag_format_specification.md`.

Extracted `.sdocx` folders also contain `end_tag.bin`, a compact document
summary.

The first field is a `u16` payload length. The remaining payload is:

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `formatVersion` | `i32` LE | Example: `4000` |
| `noteId` | `u16` count + UTF-16LE | Short-string encoding |
| `modifiedTime` | `u64` LE | Raw timestamp |
| `propertyFlags` | `i32` LE | End-tag property flags, not the same field position as `note.note` |
| `coverImage` | `u16` count + UTF-16LE | Usually empty |
| `noteWidth` | `i32` LE | Example: `961` |
| `noteHeight` | `float32` LE | Example: `4119.0` |
| `title` | `u16` count + UTF-16LE | Usually empty |
| `thumbnailWidth` | `i32` LE | Often `-1` |
| `thumbnailHeight` | `i32` LE | Often `-1` |
| `appPatchName` | `u16` count + UTF-16LE | |
| `minFormatVersion` | `i32` LE | Example: `4000` |
| `createdTime` | `u64` LE | Raw timestamp |
| `lastViewedPageIndex` | `i32` LE | |
| `pageMode` | `u16` LE | |
| `documentType` | `u16` LE | |
| `ownerId` | `u16` count + UTF-16LE | |
| reserved | `i32`, `i32` | Usually zero |
| `displayCreatedTime` | `u64` LE | Raw timestamp |
| `displayModifiedTime` | `u64` LE | Raw timestamp |
| `lastRecognizedDataModifiedTime` | `u64` LE | |
| `fixedFont` | `u16` count + UTF-16LE | |
| `fixedTextDirection` | `i32` LE | Example: `2` |
| `fixedBackgroundTheme` | `i32` LE | Example: `2` |
| `serverCheckpoint` | `i64` LE | Often `-1` |
| `newOrientation` | `i32` LE | |
| `minUnknownVersion` | `i32` LE | |
| `appCustomData` | `u32` count + UTF-16LE | Long-string encoding; `0xffffffff` means null |
| footer marker | ASCII | Literal `Document for S-Pen SDK` |

Implemented in `note_pipeline/input/samsung_notes/sidecars.py`.

## 14. Container Sidecar: `pageIdInfo.dat`

For a dedicated file-level description, see `page_id_info_format_specification.md`.

`pageIdInfo.dat` stores page order for the extracted note folder.

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `fileHash` | 32 bytes | Hash/check bytes for the sidecar |
| `pageCount` | `u16` LE | Number of page entries |
| repeated page entries | variable | One entry per page |

Each page entry is:

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `pageId` | `u16` count + UTF-16LE | Page UUID without the `.page` suffix |
| `pageHash` | 32 bytes | Per-page hash/check bytes |

Implemented in `note_pipeline/input/samsung_notes/sidecars.py`.
