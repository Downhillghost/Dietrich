# Samsung Notes `.page` Format Specification

This document describes the supported structure of Samsung Notes page files.

Scope:

1. The binary page container layout
2. The page-level property mask and optional sections
3. The layer/object framing
4. How inserted images are referenced
5. Confirmed stroke geometry and stroke-style fields

The maintained parser in `note_pipeline/input/samsung_notes/page_parser.py` recovers confirmed stroke geometry and image-reference data.

> [!IMPORTANT]
> Confidence labels used below:
> - **Confirmed**: verified against supported files
> - **Strongly inferred**: supported by observed file behavior, but one detail is still indirect
> - **Partial / Unknown**: visible in the file, but not fully decoded yet

---

## 1. High-Level Page Layout

| Section | Offset | Description | Confidence |
| :--- | :--- | :--- | :--- |
| Patched header | `0x000..0x011` | Two section offsets, a text-only flag, and the page property mask. Written last, after the rest of the file has been serialized. | Confirmed |
| Core page metadata | `0x012..property_offset-1` | Orientation, page size, offsets, UUID, modified time, format versions. | Confirmed |
| Optional page-property block | `property_offset..actual_layer_offset-1` | Drawn rect, background settings, template data, cache maps, and other optional page-level data gated by the property mask. | Confirmed |
| Layer/object section | `actual_layer_offset..EOF-trailer` | Layers, objects, object payloads, and layer/object hashes. | Confirmed |
| Integrity trailer | File tail | Classic pages end with a 32-byte digest plus ASCII footer `Page for SAMSUNG S-Pen SDK`; another supported variant replaces this with a 60-byte opaque trailer. | Confirmed |

For an observed image-reference page:

- `layer_offset   = 0x000000E3`
- `property_offset = 0x00000080`

For the empty counterpart of the same page:

- `layer_offset   = 0x0000008C`
- `property_offset = 0x00000080`

---

## 2. Patched Header

The page header is an 18-byte block at file offset `0x000`.

### Exact Header Layout

| Offset | Size | Name | Description | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `0x00` | 4 | `layer_offset` | In classic pages: absolute file offset of the layer/object section. In the 60-byte trailer variant: points to the opaque EOF trailer instead. | Confirmed |
| `0x04` | 4 | `property_offset` | Absolute file offset of the optional page-property block. | Confirmed |
| `0x08` | 1 | constant | Always `0x04` in observed files. | Confirmed |
| `0x09` | 4 | `text_only_flag` | `0` or `1`. | Confirmed |
| `0x0D` | 1 | constant | Always `0x04` in observed files. | Confirmed |
| `0x0E` | 4 | `page_property_mask` | Bitmask controlling which optional page-property payloads are present at `property_offset`. | Confirmed |

### Observed Header Pair

Empty page:

```text
8C 00 00 00 80 00 00 00 04 00 00 00 00 04 70 00 00 00
```

With inserted image:

```text
E3 00 00 00 80 00 00 00 04 00 00 00 00 04 71 04 00 00
```

So:

- empty page mask = `0x00000070`
- image page mask = `0x00000471`

### Alternate Trailer Variant

The supported alternate-trailer page variant differs from the classic page form in:

1. the first header field at `0x00`
2. the final 60 bytes of the file

For example, one page stores:

- `0x000000AC` in the classic form
- `EOF - 60` (`0x00006F78`) in the alternate-trailer form

The bytes between those regions are otherwise identical, including the layer/object payload.  
So for this variant:

- the actual layer/object section still begins immediately after the parsed page-property block
- the first header field no longer directly identifies that section
- the classic ASCII footer is replaced by an opaque 60-byte trailer

This is a confirmed file variant, but its exact purpose is still unknown.

---

## 3. Core Page Metadata

Immediately after the 18-byte header, the page stores fixed metadata in this order:

| Offset | Size | Field | Description | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `0x12` | 4 | `noteOrientation` | Page/note orientation enum stored as `u32`. | Confirmed |
| `0x16` | 4 | `pageWidth` | Canvas width. | Confirmed |
| `0x1A` | 4 | `pageHeight` | Canvas height. | Confirmed |
| `0x1E` | 4 | `offsetX` | Page offset X. | Confirmed |
| `0x22` | 4 | `offsetY` | Page offset Y. | Confirmed |
| `0x26` | 2 | `uuid_length` | UTF-16 character count of the page UUID. | Confirmed |
| `0x28` | variable | `page_uuid` | UTF-16LE UUID string. | Confirmed |
| `after uuid` | 8 | `modifiedTime` | 64-bit little-endian modified timestamp. | Confirmed |
| `after modifiedTime` | 4 | `formatVersion` | Page format version. | Confirmed |
| `after formatVersion` | 4 | `minFormatVersion` | Minimum reader format version. | Confirmed |

### Observed Values

In observed image-reference files:

- `pageWidth  = 1440` (`0x000005A0`)
- `pageHeight = 2037` (`0x000007F5`)

In observed style-only files:

- `pageWidth  = 720`
- `pageHeight = 1018`

So these are real page/canvas dimensions, not fixed constants.

---

## 4. Optional Page-Property Block

The `page_property_mask` at header offset `0x0E` controls which payloads are written at `property_offset`.

### Confirmed Property Bits

| Bit | Name | Encoding | Confidence |
| :--- | :--- | :--- | :--- |
| `0x00000001` | `drawnRect` | Four `float64` values: left, top, right, bottom | Confirmed |
| `0x00000002` | `tagList` | `u16 count`, then UTF-16LE strings | Confirmed |
| `0x00000004` | `templateUri` | Length-prefixed UTF-16LE string | Confirmed |
| `0x00000008` | `bgImageId` | `u32` media bind id | Confirmed |
| `0x00000010` | `bgImageMode` | `u32` | Confirmed |
| `0x00000020` | `bgColor` | `u32` ARGB color | Confirmed |
| `0x00000040` | `bgWidth` | `u32` | Confirmed |
| `0x00000080` | `bgRotation` | `u32` | Confirmed |
| `0x00000100` | `pdfDataList` | `u16 count`, then repeated `fileId, pageIndex`, and a version-dependent 16-byte rect payload | Confirmed |
| `0x00000200` | `templateType` | `u32` | Confirmed |
| `0x00000400` | `canvasCacheDataMap` | `u32 count`, `u16 record_size`, fixed-size records | Confirmed |
| `0x00000800` | `importedDataHeight` | `u32` | Confirmed |
| `0x00001000` | reserved / unknown | Load path skips 4 bytes when present | Partial |
| `0x00040000` | `customObjectList` | Counted custom-object payloads placed after the normal page-property fields and before the layer section | Confirmed |

### Drawn-Rect Encoding

The drawn-rect payload is **not** four `float32` values.  
It is stored as four little-endian `float64` values.

### Observed Property Blocks

Empty page, mask `0x70`:

- `bgImageMode = 2`
- `bgColor = 0xFFFCFCFC`
- `bgWidth = 1440`

Image page, mask `0x471`:

- `drawnRect = [64.0, 224.600021..., 904.0, 974.165222...]`
- `bgImageMode = 2`
- `bgColor = 0xFFFCFCFC`
- `bgWidth = 1440`
- `canvasCacheDataMap` present with one record

Imported-PDF page-property examples:

- mask `0x160`: PDF background only
- mask `0x561`: PDF background plus one canvas cache entry
- mask `0x761`: PDF background plus `templateType = 16` and one canvas cache entry

Observed PDF background records include:

- `pdfDataList = [(fileId=0, pageIndex=0, rect=(0,0,720,458))]`
- `pdfDataList = [(fileId=0, pageIndex=3, rect=(0,0,1440,916))]`
- `pdfDataList = [(fileId=1, pageIndex=0, rect=(0,0,1440,1018))]`, with `templateType = 16`

So imported PDF backgrounds are page-level properties, not normal object records.

### `pdfDataList`

When bit `0x100` is set, the block layout is:

| Field | Size | Confidence |
| :--- | :--- | :--- |
| `entry_count` | `u16` | Confirmed |
| repeated `fileId` | `i32` | Confirmed |
| repeated `pageIndex` | `i32` | Confirmed |
| repeated `pdfRect` | 16 bytes | Confirmed |

The repeated record size is always 24 bytes, but the final 16 bytes are versioned:

```text
i32 fileId
i32 pageIndex
pdfRect payload (16 bytes)
```

Version split:

- for `formatVersion >= 2034`, `pdfRect` is `left, top, right, bottom` as `4 x i32`
- for `formatVersion < 2034`, `pdfRect` is `RectF` as `4 x float32`

`fileId` resolves through `mediaInfo.dat` and, in imported-PDF notes, points directly to the backing PDF file:

- `fileId = 0` -> imported PDF media entry 0
- `fileId = 1` -> imported PDF media entry 1

### `canvasCacheDataMap`

When bit `0x400` is set, the block layout is:

| Field | Size | Confidence |
| :--- | :--- | :--- |
| `entry_count` | `u32` | Confirmed |
| `record_size` | `u16` | Confirmed |
| repeated record key | `u32` | Confirmed |
| repeated record payload | 49 bytes in the supported format | Confirmed |

Each 49-byte record decodes as:

```text
u32 key
u32 fileId
u32 width
u32 height
u8  isDarkMode
u32 backgroundColor
u32 version0
u32 version1
u32 version2
u32 cacheVersion
u32 property
u32 localeListId
u32 systemFontPathHash
```

In imported-PDF notes, `canvasCacheDataMap.fileId` can point to `.spi` cache media entries:

- `fileId = 2` -> `.spi` cache media entry
- `fileId = 3` -> `.spi` cache media entry
- `fileId = 4` -> `.spi` cache media entry

So `canvasCacheDataMap` appears to describe optional rendered-page caches, while `pdfDataList` identifies the actual PDF source page.
For the `.spi` file structure, see [`spi_format_specification.md`](spi_format_specification.md).

### `customObjectList`

When bit `0x40000` is set, the custom-object block appears after the normal page-property payloads and before the layer section.

Current confirmed outer layout:

| Field | Size | Confidence |
| :--- | :--- | :--- |
| `customObjectCount` | `u32` | Confirmed |
| repeated `customObjectType` | `u32` | Confirmed |
| repeated `customObjectBinarySize` | `u32` | Confirmed |
| repeated `customObjectBinary` | variable | Confirmed |

For the decoded binary payload, the reliable fields are:

1. a small fixed prefix (`u32`, then bytes `1,0,2`, then `u16 0` in observed writes)
2. a fixed-width custom-object UUID block
3. an attached-file map: counted `string -> media bind id`
4. a custom-data map: counted `string -> string`
5. a `RectD` / 4 x `float64` object rect

The detailed semantic meaning of the prefix bytes is still not fully named, but the block placement and the decoded payload structure are now confirmed.

### Samsung-Exported PDF Overlays

In imported-PDF notes, the page metadata can reference a PDF background (`0@..._NoTag.pdf`), while the `.page` files also contain the editable stroke data needed to render the note.

Samsung-generated PDF overlays use page-mode tag strings such as:

- `SPenSDK_PAGE_LIST`
- `SPenSDK_PAGE_SINGLE`
- `SPenSDK_HIGHLIGHT_PAGE_LIST`
- `SPenSDK_HIGHLIGHT_PAGE_SINGLE`
- `SPenSDK`

Strong inference:

- Samsung-exported PDFs can contain note overlay content inside PDF marked-content regions tagged with those Samsung names.
- During import / rendering, Samsung removes or ignores those tagged overlay regions to recover the underlying PDF background.
- The editable `.page` objects are then rendered on top of that cleaned background.

The parser mirrors that behavior at visualization time for Samsung-generated PDFs by stripping those known Samsung marked-content tags from the PDF content stream before rasterization. The exact PDF writer behavior is still not fully documented.

---

## 5. Layer/Object Section

The layer/object section begins at `layer_offset`.

### Section Prefix

| Offset from `layer_offset` | Size | Field | Confidence |
| :--- | :--- | :--- | :--- |
| `+0x00` | 2 | `layer_count` | Confirmed |
| `+0x02` | 2 | `current_layer_index` | Confirmed |

Then `layer_count` serialized layer records follow.

### Layer Record

Each layer begins with this fixed 16-byte prefix:

| Offset from layer start | Size | Field | Description | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `+0x00` | 4 | `layer_header_size` | Total byte length from layer start to `object_count`. | Confirmed |
| `+0x04` | 4 | `metadata_offset_abs` | Absolute file offset where optional layer metadata begins. | Confirmed |
| `+0x08` | 1 | constant | Always `0x01` in the save path. | Confirmed |
| `+0x09` | 1 | `layer_flags_1` | Visibility / lock / forwardable flags. | Confirmed |
| `+0x0A` | 1 | constant | Always `0x01` in the save path. | Confirmed |
| `+0x0B` | 1 | `layer_flags_2` | Optional metadata mask. | Confirmed |
| `+0x0C` | 4 | `layerNumber` | Logical layer number. | Confirmed |

For visualization, ascending `layerNumber` matches the observed stacking order:
lower-numbered layers should be drawn first, with higher-numbered layers on top.

`layer_flags_1` bits:

- `0x01`: layer is hidden (`visible == false`)
- `0x02`: `flagEventForwardable == true`
- `0x04`: layer is locked

`layer_flags_2` bits:

- `0x01`: transparency `u32`
- `0x02`: background color `u32`
- `0x04`: layer name string
- `0x08`: layer UUID string
- `0x10`: modified time `u64`
- `0x20`: thumbnail media id `u32`

After the fixed prefix, the optional metadata fields appear in the order above, according to `layer_flags_2`.

At `layer_start + layer_header_size`:

| Field | Size | Confidence |
| :--- | :--- | :--- |
| `object_count` | `u32` | Confirmed |
| repeated object records | variable | Confirmed |
| layer hash | 32 bytes | Confirmed |

### Example: Image Layer

In an observed image page:

- layer starts at `0x00E7`
- `layer_header_size = 0x62`
- `metadata_offset_abs = 0x00F7`
- `layer_flags_1 = 0x02`
- `layer_flags_2 = 0x18` (`uuid` + `modifiedTime`)
- `object_count = 1` at `0x0149`

---

## 6. Object Records

Within a layer, each object begins with:

| Field | Size | Description | Confidence |
| :--- | :--- | :--- | :--- |
| `object_type` | `u8` | Samsung object type id | Confirmed |
| `child_count` | `u16` | Number of child objects for container objects, otherwise `0` | Confirmed |
| `object_size` | `u32` | Size of the serialized object payload **plus** the trailing 32-byte object hash | Confirmed |
| `object_payload` | `object_size - 32` bytes | Concatenated binary subrecords | Confirmed |
| `object_hash` | 32 bytes | Per-object hash | Confirmed |

If `child_count > 0`, the child object records follow immediately after the parent record.

### Object Payload Subrecords

The object payload itself is a chain of typed binary subrecords.

Each subrecord starts with:

| Field | Size | Confidence |
| :--- | :--- | :--- |
| `subrecord_size` | `u32` | Confirmed |
| `subrecord_type` | `u16` | Confirmed |

Object-subrecord bodies are versioned and object-type-specific. The maintained
parser first reads the stable subrecord frame (`subrecord_size`,
`subrecord_type`, raw body bytes), then applies semantic decoding for stroke
geometry, shape fill effects, image layout, and image-own flexible fields in
normal Python code.

For an observed inserted-image object, the payload contains:

1. type `0` base-object subrecord
2. type `6` shape-base subrecord
3. type `7` shape subrecord
4. type `3` image-own subrecord

The image object itself starts at `0x014D`:

- `object_type = 3`
- `child_count = 0`
- `object_size = 0x01F8`

---

## 7. `mediaInfo.dat`

For a dedicated file-level description, see `media_info_format_specification.md`.

Inserted images are not referenced by filename directly inside the page.  
They are referenced by a numeric media bind id, which is resolved through `media/mediaInfo.dat`.

### File Layout

For `formatVersion = 5304`, `mediaInfo.dat` uses:

| Field | Size | Confidence |
| :--- | :--- | :--- |
| `format_version` | `u32` | Confirmed |
| `entry_count` | `u16` | Confirmed |
| repeated entries | variable | Confirmed |
| footer | 4 bytes ASCII `EOFX` | Confirmed |

Each entry is:

| Field | Size | Description | Confidence |
| :--- | :--- | :--- | :--- |
| `entry_size` | `u32` | Size of the remaining entry bytes, excluding this field | Confirmed |
| `bind_id` | `u32` | Media bind id used from page/object records | Confirmed |
| `name_length` | `u16` | UTF-16 char count | Confirmed |
| `name` | variable | UTF-16LE filename | Confirmed |
| `file_hash` | 64 bytes | ASCII hex string, no separate length field | Confirmed |
| `ref_count` | `u16` | Reference count | Confirmed |
| `modifiedTime` | `u64` | Last modified time | Confirmed |
| `isFileAttached` | `u8` | Attachment flag | Confirmed |

### Inserted-Image Example

An inserted-image note can contain two media entries:

| bind id | filename | ref_count |
| :--- | :--- | :--- |
| `0` | visible image file | `1` |
| `1` | `.spi` companion file | `1` |

So bind id `0` resolves to the visible JPG, and bind id `1` resolves to the SPI companion file.

---

## 8. How Inserted Images Are Referenced

### Main Result

A normal inserted image is **not** referenced through the page-level `bgImageId` property in observed inserted-image files.  
Instead, it is referenced from the image object's **shape fill-effect block**.

In other words:

```text
page -> layer -> object(type 3 image) -> shape subrecord(type 7)
     -> fillImageEffect(type 2) -> imageId(bind id) -> mediaInfo.dat -> filename
```

### The Confirmed Image-Fill Block

The shape fill-image effect is serialized as:

| Field | Size | Confidence |
| :--- | :--- | :--- |
| `size` | `u32` | Confirmed |
| `fill_effect_type` | `u8` | `2 = image` | Confirmed |
| `imageType` | `u8` | Confirmed |
| `imageId` | `u32` | Media bind id | Confirmed |
| `stretchOffset` | 16 bytes | `RectF` | Confirmed |
| `tilingOffset` | 8 bytes | `PointF` | Confirmed |
| `tilingScaleX` | `float32` | Confirmed |
| `tilingScaleY` | `float32` | Confirmed |
| `transparency` | `float32` | Confirmed |
| `rotatable` | `u8` | Confirmed |
| `ninePatchRect` | 16 bytes | `Rect` | Confirmed |
| `ninePatchWidth` | `u32` | Confirmed |

Total serialized size: 67 bytes including the `size` and `fill_effect_type` prefix.

### Where It Appears In An Image Page

In an observed inserted-image page:

1. The image object's shape subrecord starts at `0x0250`.
2. Its header says:
   - `subrecord_type = 7`
   - `own_offset = 0x87`
   - `shape_property_mask = 0x00001020`
3. Bit `0x20` means a fill-effect block is present.
4. `0x0250 + 0x87 = 0x02D7`, so the fill-effect block starts at `0x02D7`.

Bytes at `0x02D7`:

```text
3E 00 00 00 02 00 00 00 00 ...
```

This decodes as:

- `size = 62`
- `fill_effect_type = 2` (image)
- `imageType = 0`
- `imageId = 0`

The page references the inserted image by storing the media bind id in the fill-image effect block.

### Why the Final Image Subrecord Looked Empty

The image object can also have a trailing type-`3` image-own subrecord. In the simplest observed case it is only 17 bytes long and contains no optional image data.

This matches the field split used by the page format:

- the fill-image effect stores the displayed image media id
- the image-own block stores optional extras such as crop/original-image/border/nine-patch-style data when present

So for this simple case:

- the **displayed JPG** is referenced by the shape fill-effect block
- the trailing image-own block is effectively empty

### Image Layout Mode

The image object also carries a type-`6` subrecord with a small own-data block.

In observed inserted-image files, that own block starts at relative offset `0x5B` and begins with:

```text
13 00 00 00 01 00 02 00 00 00 FF 00 00 00 ...
```

Observed interpretation:

- `u32 size = 0x13`
- `u32 layoutType @ +0x06 = 2`
- `u32 alpha @ +0x0A = 255`

Known image layout constants:

- `0 = normal`
- `1 = wrap text around`
- `2 = wrap text behind`
- `3 = use default`

For rendering:

- `layoutType != 1` behaves like a **top/bottom block obstacle** for keyboard text in observed files
- `layoutType == 1` is the only mode that appears to allow text to flow around the image instead

The exact meaning of the remaining bytes in this type-`6` own block is still not fully decoded.

### Cropped-Image Variant

The cropped-image variant shows that the trailing type-`3` image-own subrecord is still important even when the displayed bitmap itself is resolved through `fillImageEffect.imageId`.

For a cropped-image page, the trailing type-`3` block can be `0x41` bytes long and carry optional flexible image data:

- group-1 flag `0x02`: `cropRect` as 4 little-endian `int32` values
- group-3 flag `0x02`: `originalRect` as 4 little-endian `float64` values

Observed decoded values:

- `cropRect = (365, 420, 819, 777)`
- `originalRect = (32.0, 112.0, 452.0, 488.0)`

The supported rendering order is:

1. load the bitmap referenced by `fillImageEffect.imageId`
2. if `cropRect` is present and within the bitmap bounds, crop the **source bitmap**
3. scale the cropped bitmap into the object's `drawnRect`

So the correct interpretation is:

- `fillImageEffect.imageId` chooses **which bitmap file** is displayed
- the trailing type-`3` image-own block can modify **how that bitmap is displayed**, including cropping

### What About the `.spi` File?

The same media table can also contain a `.spi` companion file with a separate bind id.

Current parser behavior:

- it is **not** the primary displayed-image reference in this case
- it is parsed and preserved as a `samsung_spi` asset
- its confirmed header exposes width, height, format family, and primary chunk size

That conclusion is based on the page bytes: the shape fill-effect points to the visible image bind id, not the `.spi` companion bind id.
For the `.spi` layout itself, see [`spi_format_specification.md`](spi_format_specification.md).

### Important Distinction

Inserted images use `fillImageEffect.imageId` for the primary bitmap reference, not:

- page-level `bgImageId`
- direct filename strings inside the `.page`

But for faithful rendering, also check the trailing image-own subrecord for optional display metadata such as `cropRect`.

---

## 9. Stroke Object Binary

Simple handwritten notes can still be recognized with a raw-byte geometry scan, but imported/editable PDF notes use a stricter object-scoped stroke format:

```text
layer -> object(type 1 or 15) -> subrecord(type 1 stroke-own)
```

For object-scoped stroke pages, scanning the whole layer blob produces false positives and random scribble.  
The parser has to stay inside each stroke-own subrecord.

### 9.1 Stroke-Own Header

At the start of the type-`1` stroke-own subrecord:

| Offset from subrecord start | Size | Field | Description | Confidence |
| :--- | :--- | :--- | :--- | :--- |
| `+0x00` | 4 | `subrecordSize` | Total size of the stroke-own subrecord | Confirmed |
| `+0x04` | 2 | `subrecordType` | Always `1` for stroke-own | Confirmed |
| `+0x06` | 4 | `flexibleOffset` | Relative offset of the flexible property block | Confirmed |
| `+0x0A` | 1 | `propertyMask1Size` | Usually `2` in supported files | Confirmed |
| `+0x0B` | variable | `propertyMask1` | Compact stroke flags, little-endian | Confirmed |
| next | 1 | `flexibleMaskSize` | Usually `4` in supported files | Confirmed |
| next | variable | `flexibleMask` | Flexible property mask, little-endian | Confirmed |
| next | 2 | `pointCount` | Number of points in the stroke | Confirmed |
| next | variable | geometry payload | Raw or compact, depending on `propertyMask1` | Confirmed |

In an observed imported-PDF stroke object, a typical stroke-own header is:

- `subrecordSize = 0x0516`
- `flexibleOffset = 0x04FE`
- `propertyMask1 = 0x0025`
- `flexibleMask = 0x258A`
- `pointCount = 103`

### 9.2 Geometry Payload Modes

`propertyMask1` controls how the point data is stored.

- bit `0x0001`: compact/reduced geometry
- bit `0x0004`: two extra optional axis arrays are present

#### Compact geometry (`propertyMask1 & 0x0001 != 0`)

Layout after `pointCount`:

| Field | Size |
| :--- | :--- |
| first point (`x`,`y`) as `float64,float64` | 16 bytes |
| `dx,dy` packed deltas for remaining points | `4 * (pointCount - 1)` bytes |
| first pressure value as `float32` | 4 bytes |
| packed pressure deltas | `2 * (pointCount - 1)` bytes |
| first timestamp value as `int32` | 4 bytes |
| packed timestamp deltas | `2 * (pointCount - 1)` bytes |
| optional tilt values | `4 + 2 * (pointCount - 1)` bytes |
| optional orientation values | `4 + 2 * (pointCount - 1)` bytes |
| tail value | 2 bytes |

The `dx,dy` deltas use the already-confirmed packed coordinate format:

- bit `15`: sign
- bits `14..5`: integer part
- bits `4..0`: fractional part in steps of `1/32`

So:

```text
delta = integer + fraction / 32.0
if sign == 1:
    delta = -delta
```

The point arrays match the stroke data exposed by the object model:
`points`, `pressures`, `timestamps`, `tilts`, and `orientations`.
The compact pressure, tilt, and orientation arrays use the same "first full value,
then per-point packed deltas" pattern as coordinates. In the current parser,
pressure deltas are scaled by `1/128`; tilt and orientation deltas are scaled by
`1/32`. Timestamp deltas are unsigned 16-bit cumulative increments.

Samsung's renderer does not use `penSize` alone. It receives the point,
pressure, timestamp, pen size, curve flag, and advanced pen setting values, and
pen-specific rendering can also depend on velocity and direction. The exact
stroke width/material algorithm is still not fully specified.

#### Raw geometry (`propertyMask1 & 0x0001 == 0`)

Layout after `pointCount`:

| Field | Size |
| :--- | :--- |
| repeated points as `float64,float64` | `16 * pointCount` bytes |
| pressures as `float32` | `4 * pointCount` bytes |
| timestamps as `int32` | `4 * pointCount` bytes |
| optional tilts as `float32` | `4 * pointCount` bytes |
| optional orientations as `float32` | `4 * pointCount` bytes |
| tail value | 2 bytes |

---

## 10. Flexible Stroke Properties

The newer stroke-own subrecord stores color, pen size, and pen metadata in the flexible block at `subrecordStart + flexibleOffset`.

### 10.1 Confirmed `flexibleMask` Bits

| Bit | Hex | Meaning | Confidence |
| :--- | :--- | :--- | :--- |
| `2` | `0x0002` | advanced-setting string id / string | Confirmed |
| `4` | `0x0004` | direct ARGB color | Confirmed |
| `8` | `0x0008` | direct pen size (`float32`) | Confirmed |
| `16` | `0x0010` | one-byte property | Confirmed |
| `32` | `0x0020` | variable skip area tied to document/base data | Confirmed but still opaque |
| `128` | `0x0080` | pen-name string id / string | Confirmed |
| `256` | `0x0100` | `float32` property | Confirmed |
| `1024` | `0x0400` | `u32` property | Confirmed |
| `8192` | `0x2000` | `float32` property | Confirmed |

Imported-PDF pages mainly use:

- `0x258A`: preset-based stroke, no direct color
- `0x258E`: same, but with explicit ARGB color

### 10.2 Imported-PDF Result

For imported-PDF editing notes:

- most strokes resolve `penName -> com.samsung.android.sdk.pen.pen.preload.FountainPen`
- most strokes resolve `advancedSetting -> 13;`
- only a minority of strokes carry explicit direct color (`flexibleMask & 0x0004`)

So the object-scoped stroke format explains why:

- geometry can be decoded from the object-scoped subrecord
- some notes still need a higher-level pen-preset lookup to recover the final visible color when no direct ARGB value is present

### 10.3 Simple-Note Style Heuristic

A repeated "style record after each stroke" heuristic is still useful for simple handwritten notes.

However, it is **not** authoritative for the imported/editable PDF pages, where the real stroke style data lives in the object-scoped flexible block described above.

---

## 11. Integrity Trailer

The final 58 bytes of a `.page` file are:

| Part | Size | Description |
| :--- | :--- | :--- |
| digest | 32 bytes | Digest of the page content before the trailer |
| footer | 26 bytes | ASCII `Page for SAMSUNG S-Pen SDK` |

So:

```text
stored_hash  = data[-58:-26]
footer_text  = data[-26:]
hashed_bytes = data[:-58]
```

---

## 12. Open Questions

Still not fully decoded:

1. The `.spi` payload-to-raster encoding and when it is required instead of direct PDF rasterization
2. The full meaning of all object subrecord fields outside the already-decoded stroke/image pieces
3. The detailed optional fields inside image objects when crop/original-image/border data is present
4. The opaque 32-byte stroke-style tail
5. The exact stroke material and dynamic-width rendering algorithm
6. The exact rule for trailing placeholder pages in imported-PDF notes

---

## 13. Practical Parsing Rules

These rules are reliable:

1. Read `u32le @ 0x00` to find the layer/object section.
2. Read `u32le @ 0x04` to find the optional page-property block.
3. Treat the page header as 18 bytes, not 15 bytes.
4. Parse the core page metadata starting at `0x12` in the order:
   `orientation, width, height, offsetX, offsetY, uuid, modifiedTime, formatVersion, minFormatVersion`.
5. Interpret page-property bit `0x1` as four `float64` drawn-rect values.
6. Parse the layer section as:
   `u16 layer_count, u16 current_layer_index, repeated layers`.
7. Parse each object as:
   `u8 object_type, u16 child_count, u32 object_size, payload, 32-byte object hash`.
8. Resolve inserted images through:
   `shape fillImageEffect.imageId -> mediaInfo.dat bind id -> media filename`.
9. Resolve imported PDF backgrounds through:
   `page property bit 0x100 -> fileId/pageIndex/pdfRect -> mediaInfo.dat bind id -> PDF file`.
10. Interpret `pdfRect` by page format version:
   `RectF` (`4 x float32`) before `2034`, `Rect` (`4 x i32`) from `2034` onward.
11. Parse `customObjectList` after the standard page-property payload and before the layer section when bit `0x40000` is set.
12. Treat `canvasCacheDataMap.fileId` as an optional cache reference; it is not the authoritative PDF-page mapping.
13. Do not assume the trailing image-own subrecord contains the displayed image id.
14. Keep the handwriting parser logic as-is unless a specific unsupported pen/object type is found.
