# Samsung Notes `.spi` Media Format Specification

This document describes the confirmed structure of `.spi` files stored in the
`media/` directory of Samsung Notes containers.

Scope:

1. how `.spi` files are referenced from the container
2. the confirmed packet framing and packet headers
3. how the parser exposes `.spi` metadata
4. what remains opaque

> [!IMPORTANT]
> The current parser reads the confirmed binary structure and preserves the
> original `.spi` file as a `samsung_spi` asset. It does not yet convert the
> opaque payload into pixels.

---

## 1. Role in the Container

`.spi` files are media assets stored under:

```text
<note-root>/media/<bind-id>@page_<number>.spi
```

They are listed in `media/mediaInfo.dat` like other media files, with a numeric
bind id and filename.

Known roles:

- page cache / painting data referenced by `canvasCacheDataMap.fileId`
- companion data next to inserted images
- S Pen painting/cache assets in handwritten notes

Files with bytes `AA 01` at offsets `0x04` and `0x05` use the packetized
`.spi` structure described below instead of a standard image-file structure.

The bind id is still resolved through `mediaInfo.dat`; the numeric prefix in
the filename should not be treated as authoritative by itself.

---

## 2. High-Level Layout

The supported `.spi` files are a pair of length-prefixed packets. The first
packet carries image/cache metadata. The second packet carries the encoded
payload.

```text
0x00  uint32le header_packet_size
0x04  header packet bytes
      uint32le image_packet_size
      image packet bytes
```

A parser can follow this framing directly: read the first little-endian size,
consume that many bytes starting at offset `0x04`, then read the next
little-endian size and consume that many bytes.

### Header Packet

For known files, `header_packet_size` is `20`, so the header packet occupies
`0x04..0x17`.

| Offset | Size | Endian | Field | Observed value / meaning | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x00` | 4 | little | `header_packet_size` | `20` | Confirmed |
| `0x04` | 2 | big | `header_tag` | `0xAA01` | Confirmed |
| `0x06` | 2 | big | `header_reserved` | `0` in supported files | Confirmed |
| `0x08` | 2 | big | `header_record_size` | `20` | Confirmed |
| `0x0A` | 2 | big | `header_record_reserved` | `0` in supported files | Confirmed |
| `0x0C` | 4 | big | `format_family` | observed `4` or `5` | Confirmed |
| `0x10` | 2 | little | `width` | raster/canvas width | Confirmed |
| `0x12` | 2 | little | `height` | raster/canvas height | Confirmed |
| `0x14` | 2 | big | `texture_width_units` | width bucket in 256-pixel units | Confirmed |
| `0x16` | 2 | big | `fixed_00e0` | `0x00E0` in supported files | Confirmed |

Derived field:

```text
texture_width = texture_width_units * 256
```

The current parser treats a file as SPI-like when:

1. `header_packet_size == 20`
2. `header_tag == 0xAA01`
3. `header_record_size == 20`
4. the image packet tag is `0xAA02`
5. `image_packet_size == file_size - 8 - header_packet_size`

When `header_tag == 0xAA01`, the parser treats the file as packetized `.spi`
data.

---

## 3. Image Packet

For known files, the second length field starts at `0x18`. With the observed
20-byte header packet, the image packet starts at `0x1C`.

| Offset | Size | Endian | Field | Observed value / meaning | Confidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x18` | 4 | little | `image_packet_size` | bytes from `0x1C` to EOF in known files | Confirmed |
| `0x1C` | 2 | big | `image_packet_tag` | `0xAA02` | Confirmed |
| `0x1E` | 2 | big | `image_packet_reserved` | `0` in supported files | Confirmed |
| `0x20` | 4 | little | `image_packet_size_hint` | payload-specific size hint; not safe to use as stored byte length in all files | Confirmed |
| `0x24` | variable | raw | `image_payload` | encoded image/cache bytes | Partial |

The `image_packet_size` field is the stored packet length. The
`image_packet_size_hint` field is payload-specific. In one handwritten file it
is smaller than the stored payload bytes after `0x24`. In several cache files
it is larger than the stored payload bytes. For that reason, parsers should
expose the hint but should use `image_packet_size` for packet framing.

Many observed files share this image-payload prefix:

```text
00 00 43 02 E0 A0 2C 00 00 00 3F FF
```

That prefix is useful for diagnostics, but the payload itself is not decoded
well enough to be used as a renderer input.

---

## 4. Observed Handwritten File Values

For one handwritten `.spi` file, the confirmed values are:

| Field | Value |
| :--- | :--- |
| file size | `19749` |
| `header_packet_size` | `20` |
| `header_tag` | `0xAA01` |
| `format_family` | `5` |
| `width` | `1952` |
| `height` | `1268` |
| `texture_width_units` | `32` |
| `texture_width` | `8192` |
| `image_packet_size` | `19721` |
| `image_packet_tag` | `0xAA02` |
| `image_packet_size_hint` | `0x4925` |

The image packet size matches `file_size - 8 - header_packet_size`.

---

## 5. Parser Behavior

The parser exposes `.spi` files in two places:

1. media entries that resolve to `.spi` include a `spi_info` dictionary
2. the importer registers every discovered `.spi` file as an asset with
   `media_type = "samsung_spi"`

The asset preserves:

- bind id and filename from `mediaInfo.dat`
- media path
- parsed header fields
- image packet size, payload size hint, stored payload size, and diagnostic prefixes
- parse errors, if the file cannot be parsed as the supported structure

Exporters do not currently render `.spi` assets directly. They remain available
in the neutral model so future output backends can use them once the payload is
decoded.

---

## 6. Open Questions

Still not fully decoded:

1. the image payload's internal painting/cache encoding
2. the exact semantic meaning of `image_packet_size_hint`
3. whether `format_family = 4` and `format_family = 5` differ only in payload
   encoding or also in rendering behavior
4. the exact relationship between the cached `.spi` payload and any separately
   stored page strokes or image/PDF sources
5. the payload algorithm used to turn the encoded bytes into pixels
