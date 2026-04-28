# Samsung Notes `pageIdInfo.dat` Format Specification

This document describes the `pageIdInfo.dat` sidecar stored in extracted
Samsung Notes containers.

## 1. Purpose

`pageIdInfo.dat` defines the intended page order for the note.

Each entry stores:

- the page UUID
- a 32-byte per-page hash/check block

The page UUID matches the stem of a corresponding `*.page` filename.

## 2. File Layout

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `fileHash` | 32 bytes | File-level hash/check bytes |
| `pageCount` | `u16` LE | Number of page entries |
| repeated page entries | variable | One entry per page |

There is no footer marker.

## 3. Page Entry Layout

| Field | Encoding | Notes |
| :--- | :--- | :--- |
| `pageId` | `u16` char count + UTF-16LE | Page UUID without the `.page` suffix |
| `pageHash` | 32 bytes | Per-page hash/check bytes |

## 4. Semantics

### `pageId`

`pageId` is the logical page identifier used to order the note.

To resolve a page entry to a file:

```text
page file path = <note-root>/<pageId>.page
```

### `fileHash` and `pageHash`

The 32-byte hash/check fields are preserved by the parser but are not yet fully
named. They should currently be treated as opaque integrity bytes.

## 5. String Encoding

`pageId` uses:

- `u16` character count
- UTF-16LE payload

So the entry does not store a byte length; it stores a UTF-16 code-unit count.

## 6. Parser Behavior

Reliable behavior:

1. read `pageCount`
2. read that many page entries in order
3. use `pageId` to order the `*.page` files
4. if a listed page file is missing, skip it and continue
5. if `pageIdInfo.dat` itself is missing, fall back to filename ordering

## 6.1 Dietrich Writer Behavior

Dietrich writes page entries in exported page order and includes the trailing
blank compatibility page. The file-level hash/check block is derived from the
generated `note.note` hash, and each page entry carries the hash/check block
from the corresponding generated `.page` file.

## 7. Example Interpretation

If the entry list is:

```text
pageId = A
pageId = B
pageId = C
```

then the intended page order is:

```text
A.page
B.page
C.page
```
