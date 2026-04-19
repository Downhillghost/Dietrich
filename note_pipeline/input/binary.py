from __future__ import annotations

import struct
from typing import Tuple


def can_read(data: bytes, offset: int, size: int) -> bool:
    return 0 <= offset <= len(data) and offset + size <= len(data)


def u8(data: bytes, offset: int) -> int:
    return data[offset]


def u16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def i32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<i", data, offset)[0]


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def i64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<q", data, offset)[0]


def f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def f64(data: bytes, offset: int) -> float:
    return struct.unpack_from("<d", data, offset)[0]


def rect_i32(data: bytes, offset: int) -> Tuple[int, int, int, int]:
    return (
        i32(data, offset),
        i32(data, offset + 4),
        i32(data, offset + 8),
        i32(data, offset + 12),
    )


def rect_f32(data: bytes, offset: int) -> Tuple[float, float, float, float]:
    return (
        f32(data, offset),
        f32(data, offset + 4),
        f32(data, offset + 8),
        f32(data, offset + 12),
    )


def rect_f64(data: bytes, offset: int) -> Tuple[float, float, float, float]:
    return (
        f64(data, offset),
        f64(data, offset + 8),
        f64(data, offset + 16),
        f64(data, offset + 24),
    )


def read_utf16_u16(data: bytes, offset: int) -> Tuple[str, int]:
    if not can_read(data, offset, 2):
        return "", offset

    char_count = u16(data, offset)
    offset += 2
    if char_count == 0xFFFF:
        return "", offset

    byte_count = char_count * 2
    if not can_read(data, offset, byte_count):
        return "", len(data)

    return data[offset : offset + byte_count].decode("utf-16le", errors="replace"), offset + byte_count


def read_utf16_u32(data: bytes, offset: int) -> Tuple[str, int]:
    if not can_read(data, offset, 4):
        return "", offset

    char_count = u32(data, offset)
    offset += 4
    if char_count == 0xFFFFFFFF:
        return "", offset

    byte_count = char_count * 2
    if not can_read(data, offset, byte_count):
        return "", len(data)

    return data[offset : offset + byte_count].decode("utf-16le", errors="replace"), offset + byte_count


def read_counted_utf8(data: bytes, offset: int) -> Tuple[str, int]:
    if not can_read(data, offset, 4):
        return "", offset

    byte_count = u32(data, offset)
    offset += 4
    if not can_read(data, offset, byte_count):
        return "", len(data)

    return data[offset : offset + byte_count].decode("utf-8", errors="replace"), offset + byte_count


def read_utf8_u16_bytes(
    data: bytes,
    offset: int,
    *,
    trim_at_nul: bool = False,
    max_chars: int | None = None,
) -> Tuple[str, int]:
    if not can_read(data, offset, 2):
        return "", offset

    byte_count = u16(data, offset)
    offset += 2
    if not can_read(data, offset, byte_count):
        return "", len(data)

    raw = data[offset : offset + byte_count]
    if trim_at_nul and (nul_index := raw.find(b"\x00")) != -1:
        raw = raw[:nul_index]

    value = raw.decode("utf-8", errors="replace")
    if max_chars is not None:
        value = value[:max_chars]
    return value, offset + byte_count
