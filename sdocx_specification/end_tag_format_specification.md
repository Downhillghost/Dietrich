# Samsung Notes `end_tag.bin` Format Specification

This document describes the compact note-summary sidecar `end_tag.bin`.

## 1. Purpose

`end_tag.bin` stores a compact summary of note-level metadata. Many values
mirror fields that also exist in `note.note`, but this sidecar is shorter and
easier to scan.

## 2. High-Level Layout

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `payloadSize` | `u16` LE | Byte size of the remaining payload |
| `payload` | variable | Summary block |

## 3. Payload Layout

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `formatVersion` | `i32` LE | Example: `4000` |
| `noteId` | `u16` count + UTF-16LE | Short-string encoding |
| `modifiedTime` | `u64` LE | Raw timestamp |
| `propertyFlags` | `i32` LE | Summary property flags |
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
| `reservedZero1` | `i32` LE | Usually `0` |
| `reservedZero2` | `i32` LE | Usually `0` |
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
| `footerMarker` | ASCII | Observed as `Document for S-Pen SDK` |

## 4. String Encodings

`end_tag.bin` uses two string forms:

- short string: `u16` character count + UTF-16LE
- long string: `u32` character count + UTF-16LE

`appCustomData` uses the long-string form. Most other strings in this file use
the short-string form.

## 5. Notes on Specific Fields

### `noteHeight`

Unlike `note.note`, which stores logical height as an integer, `end_tag.bin`
stores `noteHeight` as `float32`.

### `propertyFlags`

This is a summary-sidecar property field. It should not be confused with the
position of `property_flags` inside `note.note`, even when the bit meanings
overlap.

### `footerMarker`

The payload ends with the ASCII marker:

```text
Document for S-Pen SDK
```

## 6. Practical Parsing Rules

These rules are reliable:

1. read `payloadSize`
2. read exactly `payloadSize` bytes of payload
3. parse the fields in order
4. preserve the trailing footer marker
5. treat unknown enum-like fields such as `pageMode` and `documentType` as raw values until named semantics are confirmed
