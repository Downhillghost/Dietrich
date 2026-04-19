# Samsung Notes `mediaInfo.dat` Format Specification

This document describes `media/mediaInfo.dat`, the media bind-id table used by
Samsung Notes containers.

## 1. Purpose

`mediaInfo.dat` maps numeric media bind ids to filenames and associated file
metadata.

Page properties and page objects usually reference media by numeric bind id, not
by filename.

## 2. High-Level Layout

For the supported format (`formatVersion = 5304`), the file layout is:

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `formatVersion` | `u32` LE | Example: `5304` |
| `entryCount` | `u16` LE | Number of media entries |
| repeated entries | variable | One entry per bind id |
| `footerMarker` | ASCII | Observed as `EOFX` |

## 3. Entry Layout

Each entry is stored as:

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `entrySize` | `u32` LE | Size of the remaining entry body, excluding this field |
| `bindId` | `u32` LE | Media bind id |
| `filename` | `u16` char count + UTF-16LE | Stored filename |
| `fileHash` | 64 ASCII bytes | Hex text, no separate length field |
| `refCount` | `u16` LE | Reference count |
| `modifiedTime` | `u64` LE | Raw timestamp |
| `isFileAttached` | `u8` | Attachment flag |
| `extraBytes` | remaining bytes | Optional trailing entry data |

## 4. Semantics

### `bindId`

`bindId` is the authoritative media identifier used by page and object records.

### `filename`

The filename usually appears in the `media/` directory. In observed files it
often starts with the same bind id:

```text
0@something.pdf
1@something.jpg
2@page_<number>.spi
```

That filename convention is useful, but parsers should still trust the explicit
`bindId` field first.

### `fileHash`

`fileHash` is stored as 64 ASCII hex characters. The exact hash algorithm is not
yet fully named, so this field should currently be treated as opaque metadata.

### `extraBytes`

Some entries may include trailing bytes beyond the commonly decoded fields. The
parser preserves them but does not currently assign semantics to them.

## 5. Media Roles

Known file types referenced through `mediaInfo.dat`:

- PDF background files
- inserted image files
- `.spi` painting/cache files; see [`spi_format_specification.md`](spi_format_specification.md)

## 6. Resolution Rule

To resolve a media reference:

```text
bind id -> mediaInfo.dat entry -> filename -> <note-root>/media/<filename>
```

## 7. Example Interpretation

If an entry contains:

```text
bindId = 3
filename = 3@page_<number>.spi
```

then media bind id `3` resolves to:

```text
<note-root>/media/3@page_<number>.spi
```

## 8. Practical Parsing Rules

These rules are reliable:

1. read `formatVersion`
2. read `entryCount`
3. for each entry, read `entrySize` and then exactly that many bytes
4. parse the fixed fields inside the entry body
5. preserve any remaining `extraBytes`
6. read the trailing footer and expect `EOFX`
