from __future__ import annotations

import base64
import hashlib
import math
import mimetypes
import os
import re
import struct
import time
import uuid
import zlib
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import unquote_to_bytes

from note_pipeline.model import (
    Asset,
    ExportResult,
    FrameElement,
    ImageElement,
    NoteDocument,
    PdfBackgroundElement,
    StrokeElement,
    TextElement,
    UnsupportedElement,
)
from note_pipeline.output.base import ExportOptions, NoteExporter


PAGE_FOOTER = b"Page for SAMSUNG S-Pen SDK"
END_TAG_FOOTER = b"Document for S-Pen SDK"
DEFAULT_BACKGROUND_COLOR = 0xFFFCFCFC
DEFAULT_PAGE_WIDTH = 720
DEFAULT_PAGE_HEIGHT = 1018
MAX_STROKE_POINTS = 60000
PRACTICAL_PAGE_LIMIT = 20000
MAX_SIGNED_PAGE_DIMENSION = 0x7FFFFFFF
NOTE_PROPERTY_FLAGS = 0x000C8E80
NOTE_HEADER_FLAGS = 0x00000008
DEFAULT_NOTE_VERTICAL_PADDING = 8
DEFAULT_PEN_NAME = "com.samsung.android.sdk.pen.pen.preload.FountainPen"
DEFAULT_ADVANCED_SETTING = "18;0;100;"
OBJECT_BASE_PAGE_DIMENSION_SCALE = 256
TEXT_FIELD_FONT_SIZE_SCALE = 0.10
TEXT_FIELD_WIDTH_SCALE = 1.0
TEXT_FIELD_HEIGHT_SCALE = 1.0
TEXT_FIELD_VERTICAL_SIZE_SCALE = 1.5
TEXT_FIELD_LINE_HEIGHT_SCALE = 1.35
TEXT_FIELD_AVERAGE_CHAR_WIDTH = 0.72
TEXT_FIELD_MARGIN_LEFT = 8.0
TEXT_FIELD_MARGIN_TOP = 4.0
TEXT_FIELD_MARGIN_RIGHT = 8.0
TEXT_FIELD_MARGIN_BOTTOM = 4.0
TEXT_FIELD_MIN_WIDTH = 360.0
TEXT_FIELD_MIN_HEIGHT = 132.0
TEXT_FIELD_MIN_DIMENSION_FONT_REFERENCE = 52.0
TEXT_FIELD_DIMENSION_SCALE_PER_FONT_POINT = 0.075
TEXT_FIELD_MIN_DIMENSION_MAX_SCALE = 6.0
FRAME_LABEL_FONT_SIZE_PT = 7.0
FRAME_LABEL_SAMSUNG_FONT_SIZE = 5.5
FRAME_LABEL_BOX_MIN_WIDTH = 640.0
FRAME_LABEL_BOX_MIN_HEIGHT = 220.0
FRAME_LABEL_BOX_WIDTH_PER_CHAR = 28.0
FRAME_LABEL_GAP = 8.0
FRAME_OUTLINE_STEP = 8.0
ZIP_GENERAL_PURPOSE_FLAG = 0x0806
ZIP_DOS_DATE_1980_JAN_ZERO = 0x0020
ZIP_DEFLATED = 8
TEXT_FIELD_SHAPE_BASE_TAIL = bytes.fromhex(
    "04000000000000000013000000010002000000ff0000000000000000000000000c000000000000000000000000000000"
)
TEXT_FIELD_TRAILER_SUBRECORD = bytes.fromhex("0f0000000200000000000100020000")
EMPTY_TITLE_OBJECT_TEMPLATE = base64.b64decode(
    "cQAAAAAAaQAAAAK/AQQAQAAAoA8AACQAODVjZGI3ZmMtMWQ5Mi0xMWYxLTg4ZjAtYmI5ODM1ODY0ZDcyJJ95dMZMBgAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0AIAAAAAAABCAAAABgAbAAAAAQABDAAAAAAEAAAAAAAAAAATAAAA"
    "AQACAAAA/wAAAAAAAAAAAAAAAAwAAAAAAAAAAAAAAAAAAACrAAAABwA+AAAAAQQEAQAAAAQAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGkAAAAJAAAAMAAwADAAMAAwADAAMAAwADAAAQAAABgAAQAAAAAAAAAJAAAAAQAA"
    "ACUlJf8AAAAAAQAAABQABgAAAAAAAAABAAAAAAAAAAAAAAAAADRBAAAAAAAANEEAAAAAAAAAAAAAAAAAAAAPAAAAAgAAAAAA"
    "AQACAAA="
)
EMPTY_BODY_OBJECT_TEMPLATE = base64.b64decode(
    "cQAAAAAAaQAAAAK/AQQAQAAAoA8AACQANDA4N2NjOGUtMWYyZi0xMWYxLTk2NTAtMzcxMWM3YmE4MmExMx8buu9MBgAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0AIAAAAAAABCAAAABgAbAAAAAQABDAAAAAAEAAAAAAAAAAATAAAA"
    "AQACAAAA/wAAAAAAAAAAAAAAAAwAAAAAAAAAAAAAAAAAAABqAAAABwA+AAAAAQQEASAAAAQAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACcAAAAAAAAAAAAAAAAAAAAAAIBBAAAgQQAAgEEAACBBAAAAAAAAAAAAAAACDwAA"
    "AAIAAAAAAAEAAgAA"
)
TITLE_OBJECT_PREFIX = base64.b64decode(
    "cQAAAAAAaQAAAAK/AQQAQAAAoA8AACQANDA4N2M3ZDQtMWYyZi0xMWYxLTg1YjktYmIyZWQ1OTM3OTJmWR4buu9M"
    "BgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA0AIAAAAAAABCAAAABgAbAAAAAQABDAAAAAAE"
    "AAAAAAAAAAATAAAAAQACAAAA/wAAAAAAAAAAAAAAAAwAAAAAAAAAAAAAAAAAAACRAAAABwA+AAAAAQQEAQAAAAQA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
)
TITLE_OBJECT_TRAILER = base64.b64decode("DwAAAAIAAAAAAAEAAgAA")
CURRENT_PEN_INFO_TEMPLATE = base64.b64decode(
    "ngAAADMAYwBvAG0ALgBzAGEAbQBzAHUAbgBnAC4AYQBuAGQAcgBvAGkAZAAuAHMAZABrAC4AcABlAG4ALgBwAGUAbgAuAHAA"
    "cgBlAGwAbwBhAGQALgBGAG8AdQBuAHQAYQBpAG4AUABlAG4AMzOjQNLrL/8BAAAAAAAAAAAAHgAAAAEAAAAAAAAAAAAAAHMF"
    "LEPNzEw/7OtrPwAAAAA="
)


@dataclass(frozen=True)
class _PagePayload:
    page_id: str
    data: bytes
    page_hash: bytes
    width: int
    height: int
    stroke_count: int
    omitted_count: int


@dataclass(frozen=True)
class _ZipPayload:
    name: str
    data: bytes


@dataclass(frozen=True)
class _SamsungImage:
    element: ImageElement
    bind_id: int


def _u16(value: int) -> bytes:
    return struct.pack("<H", max(0, min(0xFFFF, int(value))))


def _u32(value: int) -> bytes:
    return struct.pack("<I", max(0, min(0xFFFFFFFF, int(value))))


def _i32(value: int) -> bytes:
    return struct.pack("<i", max(-0x80000000, min(0x7FFFFFFF, int(value))))


def _i64(value: int) -> bytes:
    return struct.pack("<q", max(-0x8000000000000000, min(0x7FFFFFFFFFFFFFFF, int(value))))


def _u64(value: int) -> bytes:
    return struct.pack("<Q", max(0, min(0xFFFFFFFFFFFFFFFF, int(value))))


def _f32(value: float) -> bytes:
    return struct.pack("<f", float(value))


def _f64(value: float) -> bytes:
    return struct.pack("<d", float(value))


def _normalized_text(value: object) -> str:
    text = str(value or "")
    if not text:
        return ""
    try:
        text.encode("utf-16le")
        return text
    except UnicodeEncodeError:
        return text.encode("utf-16le", errors="surrogatepass").decode("utf-16le", errors="replace")


def _utf16le_text(value: object) -> bytes:
    return _normalized_text(value).encode("utf-16le")


def _utf16_u16(value: object) -> bytes:
    encoded = _utf16le_text(value)
    char_count = min(0xFFFF, len(encoded) // 2)
    return _u16(char_count) + encoded[: char_count * 2]


def _utf16_u32_nullable(value: Optional[str]) -> bytes:
    if value is None:
        return _u32(0xFFFFFFFF)
    encoded = _utf16le_text(value)
    char_count = min(0xFFFFFFFF, len(encoded) // 2)
    return _u32(char_count) + encoded[: char_count * 2]


def _finite_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return default


def _argb_to_rgba(color_int: int) -> Tuple[float, float, float, float]:
    alpha = (color_int >> 24) & 0xFF
    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    return (
        red / 255.0,
        green / 255.0,
        blue / 255.0,
        alpha / 255.0,
    )


def _surface_id_to_page_id(note: NoteDocument, surface_id: str, index: int) -> str:
    try:
        parsed = uuid.UUID(str(surface_id))
        if parsed.version == 1:
            return str(parsed)
    except (ValueError, TypeError):
        pass
    return _samsung_like_uuid()


def _stroke_bounds(strokes: Iterable[StrokeElement]) -> Optional[Tuple[float, float, float, float]]:
    rects: List[Tuple[float, float, float, float]] = []
    for stroke in strokes:
        if not stroke.points:
            continue
        xs = [float(point[0]) for point in stroke.points if math.isfinite(float(point[0]))]
        ys = [float(point[1]) for point in stroke.points if math.isfinite(float(point[1]))]
        if xs and ys:
            rects.append((min(xs), min(ys), max(xs), max(ys)))
    if not rects:
        return None
    return (
        min(rect[0] for rect in rects),
        min(rect[1] for rect in rects),
        max(rect[2] for rect in rects),
        max(rect[3] for rect in rects),
    )


def _pack_compact_delta(delta: float) -> Optional[bytes]:
    value = abs(float(delta))
    if not math.isfinite(value) or value >= 1024.0:
        return None
    integer = int(math.floor(value))
    fraction = int(round((value - integer) * 32.0))
    if fraction >= 32:
        integer += 1
        fraction = 0
    if integer >= 1024:
        return None
    encoded = (0x8000 if delta < 0 else 0) | (integer << 5) | fraction
    return _u16(encoded)


def _pack_compact_float_series(values: List[float], scale: float) -> Optional[bytes]:
    if not values:
        return b""
    data = bytearray()
    data.extend(_f32(values[0]))
    current = float(values[0])
    for value in values[1:]:
        delta = (float(value) - current) * scale
        encoded = _pack_compact_delta(delta)
        if encoded is None:
            return None
        data.extend(encoded)
        current = float(value)
    return bytes(data)


def _pack_compact_timestamp_series(values: List[int]) -> Optional[bytes]:
    if not values:
        return b""
    data = bytearray()
    data.extend(_i32(values[0]))
    current = int(values[0])
    for value in values[1:]:
        delta = int(value) - current
        if delta < 0 or delta > 0xFFFF:
            return None
        data.extend(_u16(delta))
        current = int(value)
    return bytes(data)


def _surface_size(surface) -> Tuple[int, int]:
    width = int(surface.width or 0)
    height = int(surface.height or 0)
    if width > 0 and height > 0:
        return width, height

    bounds = _stroke_bounds(element for element in surface.elements if isinstance(element, StrokeElement))
    if bounds is None:
        return DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT
    return (
        max(1, int(math.ceil(bounds[2] + 120.0))),
        max(1, int(math.ceil(bounds[3] + 120.0))),
    )


def _clamp_surface_size(width: int, height: int) -> Tuple[int, int, bool]:
    clamped = width > MAX_SIGNED_PAGE_DIMENSION or height > MAX_SIGNED_PAGE_DIMENSION
    return (
        min(max(1, int(width)), MAX_SIGNED_PAGE_DIMENSION),
        min(max(1, int(height)), MAX_SIGNED_PAGE_DIMENSION),
        clamped,
    )


def _object_base_page_dimension(value: int) -> int:
    return max(1, int(value)) * OBJECT_BASE_PAGE_DIMENSION_SCALE


def _safe_media_filename(value: str) -> str:
    basename = os.path.basename(str(value or "")).strip() or "image"
    return "".join(char if char not in '<>:"/\\|?*' and ord(char) >= 32 else "_" for char in basename)


def _extension_for_media_type(media_type: str) -> str:
    extension = mimetypes.guess_extension(media_type or "")
    if extension == ".jpe":
        return ".jpg"
    return extension or ".bin"


def _asset_data_url(asset: Asset) -> Optional[str]:
    value = asset.vendor_extensions.get("data_url")
    if isinstance(value, str):
        return value
    excalidraw = asset.vendor_extensions.get("excalidraw")
    if isinstance(excalidraw, dict):
        value = excalidraw.get("data_url")
        if isinstance(value, str):
            return value
    return None


def _asset_preferred_filename(asset: Asset) -> str:
    excalidraw = asset.vendor_extensions.get("excalidraw")
    if isinstance(excalidraw, dict):
        filename = excalidraw.get("filename") or excalidraw.get("embedded_ref")
        if isinstance(filename, str) and filename:
            return _safe_media_filename(filename)
    if asset.source_path:
        return _safe_media_filename(asset.source_path)
    if asset.source_ref:
        return _safe_media_filename(asset.source_ref)
    return "image"


def _asset_media_bytes(asset: Asset) -> Optional[Tuple[bytes, str, str]]:
    if asset.source_path and os.path.isfile(asset.source_path):
        with open(asset.source_path, "rb") as handle:
            data = handle.read()
        media_type = mimetypes.guess_type(asset.source_path)[0] or asset.media_type or "application/octet-stream"
        return data, _asset_preferred_filename(asset), media_type

    data_url = _asset_data_url(asset)
    if not data_url:
        return None
    match = re.match(r"^data:([^;,]+)?((?:;[^,]*)?),(.*)$", data_url, re.DOTALL)
    if match is None:
        return None
    media_type = match.group(1) or asset.media_type or "application/octet-stream"
    options = match.group(2) or ""
    payload = match.group(3) or ""
    try:
        data = base64.b64decode(payload, validate=False) if ";base64" in options else unquote_to_bytes(payload)
    except Exception:
        return None
    filename = _asset_preferred_filename(asset)
    if not os.path.splitext(filename)[1]:
        filename = f"{filename}{_extension_for_media_type(media_type)}"
    return data, filename, media_type


def _build_media_info(entries: List[Tuple[int, str, bytes, int]]) -> bytes:
    data = bytearray()
    data.extend(_u32(5304))
    data.extend(_u16(len(entries)))
    for bind_id, filename, content, modified_time in entries:
        body = bytearray()
        body.extend(_u32(bind_id))
        body.extend(_utf16_u16(filename))
        body.extend(hashlib.sha256(content).hexdigest().encode("ascii")[:64].ljust(64, b"0"))
        body.extend(_u16(1))
        body.extend(_u64(modified_time))
        body.extend(b"\x01")
        data.extend(_u32(len(body)))
        data.extend(body)
    data.extend(b"EOFX")
    return bytes(data)


def _text_field_rect(element: TextElement) -> Tuple[float, float, float, float]:
    font_size = max(1.0, _finite_float(element.font_size_pt, element.ascent + element.descent or 20.0))
    samsung_font_size = _text_field_font_size(element)
    text_top = float(element.baseline_y) - max(1.0, float(element.ascent))
    content_width = max(1.0, float(element.width))
    lines = _normalized_text(element.text).splitlines() or [""]
    longest_line = max((len(line) for line in lines), default=0)
    estimated_text_width = longest_line * samsung_font_size * TEXT_FIELD_AVERAGE_CHAR_WIDTH
    line_count = max(1, len(lines))
    estimated_text_height = samsung_font_size * TEXT_FIELD_LINE_HEIGHT_SCALE * line_count
    content_height = max(float(element.ascent) + float(element.descent), font_size * 1.2)
    min_dimension_scale = _text_field_min_dimension_scale(font_size)
    min_width = _text_field_minimum(element, "min_width", TEXT_FIELD_MIN_WIDTH * min_dimension_scale)
    min_height = _text_field_minimum(element, "min_height", TEXT_FIELD_MIN_HEIGHT * min_dimension_scale)
    left = float(element.x) - TEXT_FIELD_MARGIN_LEFT
    top = text_top - TEXT_FIELD_MARGIN_TOP
    right = left + max(
        min_width,
        (content_width * TEXT_FIELD_WIDTH_SCALE) + TEXT_FIELD_MARGIN_LEFT + TEXT_FIELD_MARGIN_RIGHT,
        estimated_text_width + TEXT_FIELD_MARGIN_LEFT + TEXT_FIELD_MARGIN_RIGHT,
    )
    base_height = max(
        min_height,
        (content_height * TEXT_FIELD_HEIGHT_SCALE) + TEXT_FIELD_MARGIN_TOP + TEXT_FIELD_MARGIN_BOTTOM,
        estimated_text_height + TEXT_FIELD_MARGIN_TOP + TEXT_FIELD_MARGIN_BOTTOM,
    )
    bottom = top + (base_height * TEXT_FIELD_VERTICAL_SIZE_SCALE)
    return left, top, right, bottom


def _text_field_font_size(element: TextElement) -> float:
    samsung_notes = element.vendor_extensions.get("samsung_notes")
    if isinstance(samsung_notes, dict):
        value = samsung_notes.get("font_size")
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return max(1.0, float(value))
    font_size = max(1.0, _finite_float(element.font_size_pt, element.ascent + element.descent or 20.0))
    return max(1.0, font_size * TEXT_FIELD_FONT_SIZE_SCALE)


def _text_field_min_dimension_scale(font_size: float) -> float:
    font_points_over_reference = max(0.0, font_size - TEXT_FIELD_MIN_DIMENSION_FONT_REFERENCE)
    return min(
        TEXT_FIELD_MIN_DIMENSION_MAX_SCALE,
        1.0 + (font_points_over_reference * TEXT_FIELD_DIMENSION_SCALE_PER_FONT_POINT),
    )


def _text_field_minimum(element: TextElement, key: str, default: float) -> float:
    samsung_notes = element.vendor_extensions.get("samsung_notes")
    if isinstance(samsung_notes, dict):
        value = samsung_notes.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return max(1.0, float(value))
    return default


def _normal_rect(rect: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    left, top, right, bottom = (float(value) for value in rect)
    return min(left, right), min(top, bottom), max(left, right), max(top, bottom)


def _densify_segment(start: Tuple[float, float], end: Tuple[float, float], step: float) -> List[Tuple[float, float]]:
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    count = max(1, int(math.ceil(length / max(1.0, step))))
    return [
        (
            start[0] + ((end[0] - start[0]) * index / count),
            start[1] + ((end[1] - start[1]) * index / count),
        )
        for index in range(1, count + 1)
    ]


def _frame_outline_points(frame: FrameElement) -> List[Tuple[float, float]]:
    left, top, right, bottom = _normal_rect(frame.rect)
    vertices = [(left, top), (right, top), (right, bottom), (left, bottom), (left, top)]
    points = [vertices[0], vertices[0], vertices[0]]
    for start, end in zip(vertices, vertices[1:]):
        points.extend(_densify_segment(start, end, FRAME_OUTLINE_STEP))
    points.extend(vertices[0] for _ in range(3))
    return points


def _frame_to_stroke(frame: FrameElement) -> StrokeElement:
    points = _frame_outline_points(frame)
    return StrokeElement(
        element_id=f"{frame.element_id}-outline",
        points=points,
        color_int=frame.color_int,
        color_hex_argb=frame.color_hex_argb,
        rgba=frame.rgba,
        pen_size=max(0.5, float(frame.stroke_width) / 0.15),
        style={
            "source": "neutral-frame-outline",
            "stroke_width": frame.stroke_width,
            "child_element_ids": list(frame.child_element_ids),
        },
        layer_number=frame.layer_number,
        source_order=frame.source_order,
        z_index=frame.z_index,
        pressures=[0.5 for _ in points],
        timestamps=[index * 8 for index in range(len(points))],
        vendor_extensions={"source_frame_element_id": frame.element_id},
    )


def _frame_to_label(frame: FrameElement) -> Optional[TextElement]:
    label = str(frame.name or "").strip()
    if not label:
        return None
    left, top, _, _ = _normal_rect(frame.rect)
    font_size = max(1.0, float(frame.label_font_size_pt or FRAME_LABEL_FONT_SIZE_PT))
    min_width = max(FRAME_LABEL_BOX_MIN_WIDTH, len(label) * FRAME_LABEL_SAMSUNG_FONT_SIZE * FRAME_LABEL_BOX_WIDTH_PER_CHAR)
    box_top = top - FRAME_LABEL_GAP - (FRAME_LABEL_BOX_MIN_HEIGHT * TEXT_FIELD_VERTICAL_SIZE_SCALE)
    return TextElement(
        element_id=f"{frame.element_id}-label",
        text=label,
        x=left + TEXT_FIELD_MARGIN_LEFT,
        baseline_y=box_top + TEXT_FIELD_MARGIN_TOP + font_size,
        width=max(1.0, min_width - TEXT_FIELD_MARGIN_LEFT - TEXT_FIELD_MARGIN_RIGHT),
        ascent=font_size,
        descent=max(1.0, font_size * 0.25),
        color_int=frame.color_int,
        layer_number=frame.layer_number,
        source_order=frame.source_order,
        z_index=frame.z_index,
        font_size_pt=font_size,
        font_name=None,
        vendor_extensions={
            "source_frame_element_id": frame.element_id,
            "samsung_notes": {
                "font_size": FRAME_LABEL_SAMSUNG_FONT_SIZE,
                "min_width": min_width,
                "min_height": FRAME_LABEL_BOX_MIN_HEIGHT,
            },
        },
    )


def _rect_union(rects: Iterable[Tuple[float, float, float, float]]) -> Optional[Tuple[float, float, float, float]]:
    items = list(rects)
    if not items:
        return None
    return (
        min(rect[0] for rect in items),
        min(rect[1] for rect in items),
        max(rect[2] for rect in items),
        max(rect[3] for rect in items),
    )


def _safe_timestamp_ms() -> int:
    return int(time.time() * 1000)


def _safe_timestamp_us() -> int:
    return int(time.time() * 1_000_000)


def _identity_hash(identifier: str, modified_time_raw: int) -> bytes:
    return hashlib.sha256(f"{identifier}{int(modified_time_raw)}".encode("utf-8")).digest()


def _samsung_like_uuid() -> str:
    node = int.from_bytes(os.urandom(6), "big") | 0x010000000000
    clock_seq = int.from_bytes(os.urandom(2), "big") & 0x3FFF
    return str(uuid.uuid1(node=node, clock_seq=clock_seq))


def _note_title(note: NoteDocument) -> str:
    return str(note.title or note.source.display_name or "").strip()


def _bounded_text(value: str, max_chars: int = 240) -> str:
    text = _normalized_text(value)
    return text[:max_chars]


def _patch_text_object_base(template: bytes, object_id: str, now: int) -> bytearray:
    data = bytearray(template)
    encoded_id = object_id.encode("ascii", errors="ignore")[:36].ljust(36, b"0")
    data[24:60] = encoded_id
    struct.pack_into("<Q", data, 60, now)
    return data


def _build_title_text_common(title: str) -> bytes:
    text = _bounded_text(title)
    encoded = _utf16le_text(text)
    payload = bytearray()
    payload.extend(_u32(len(encoded) // 2))
    payload.extend(encoded)
    payload.extend(_u32(0))
    if text:
        payload.extend(_u32(1))
        payload.extend(_u16(20))
        payload.extend(_u32(6))
        payload.extend(_u32(0))
        payload.extend(_u32(1))
        payload.extend(_u32(0))
        payload.extend(_u32(0))
    else:
        payload.extend(_u32(0))
    for value in (15.0, 0.0, 15.0, 0.0):
        payload.extend(_f32(value))
    payload.extend(b"\x00")
    payload.extend(_u16(0))
    payload.extend(_u32(0))
    payload.extend(_u32(0))
    return bytes(payload)


def _span_record(span_type: int, start: int, end: int, extra: bytes, payload_size: int = 24) -> bytes:
    payload = bytearray()
    payload.extend(_u32(span_type))
    payload.extend(_u32(start))
    payload.extend(_u32(end))
    payload.extend(_u32(1))
    payload.extend(extra)
    if len(payload) < payload_size:
        payload.extend(b"\x00" * (payload_size - len(payload)))
    return _u16(payload_size) + bytes(payload[:payload_size])


def _paragraph_record(paragraph_type: int, start: int, end: int, extra: bytes, payload_size: int = 20) -> bytes:
    payload = bytearray()
    payload.extend(_u32(paragraph_type))
    payload.extend(_u32(start))
    payload.extend(_u32(end))
    payload.extend(extra)
    if len(payload) < payload_size:
        payload.extend(b"\x00" * (payload_size - len(payload)))
    return _u16(payload_size) + bytes(payload[:payload_size])


def _build_text_field_text_common(element: TextElement) -> bytes:
    text = _normalized_text(element.text)
    encoded = _utf16le_text(text)
    text_length = len(encoded) // 2
    font_size = _text_field_font_size(element)

    spans = [
        _span_record(3, 0, text_length, _f32(font_size)),
        _span_record(1, 0, text_length, _u32(int(element.color_int) & 0xFFFFFFFF)),
    ]
    paragraphs = [
        _paragraph_record(3, 0, 1, _u32(0)),
        _paragraph_record(6, 0, 1, _u32(0)),
    ]

    payload = bytearray()
    payload.extend(_u32(text_length))
    payload.extend(encoded)
    payload.extend(_u32(len(spans)))
    for span in spans:
        payload.extend(span)
    payload.extend(_u32(len(paragraphs)))
    for paragraph in paragraphs:
        payload.extend(paragraph)
    for value in (
        TEXT_FIELD_MARGIN_LEFT,
        TEXT_FIELD_MARGIN_TOP,
        TEXT_FIELD_MARGIN_RIGHT,
        TEXT_FIELD_MARGIN_BOTTOM,
    ):
        payload.extend(_f32(value))
    payload.extend(b"\x00")
    payload.extend(_u16(0))
    payload.extend(_u32(0))
    payload.extend(_u32(0))
    return bytes(payload)


def _build_title_object(title: str, object_id: str, now: int) -> bytes:
    data = _patch_text_object_base(TITLE_OBJECT_PREFIX, object_id, now)
    text_common = _build_title_text_common(title)
    shape_text_start = 113 + 66
    struct.pack_into("<I", data, shape_text_start, 66 + len(text_common))
    data.extend(_u32(len(text_common)))
    data.extend(text_common)
    data.extend(TITLE_OBJECT_TRAILER)
    return bytes(data)


def _build_body_object(object_id: str, now: int) -> bytes:
    return bytes(_patch_text_object_base(EMPTY_BODY_OBJECT_TEMPLATE, object_id, now))


def _build_string_id_block(entries: List[Tuple[int, str]]) -> bytes:
    body = bytearray()
    body.extend(_u16(len(entries)))
    for string_id, value in entries:
        body.extend(_i32(string_id))
        body.extend(_utf16_u16(value))
    return _u32(len(body)) + bytes(body)


def _build_current_pen_info() -> bytes:
    return CURRENT_PEN_INFO_TEMPLATE


def _deflate_raw(data: bytes) -> bytes:
    compressor = zlib.compressobj(level=1, method=zlib.DEFLATED, wbits=-15)
    return compressor.compress(data) + compressor.flush()


def _write_samsung_zip(output_path: str, entries: List[_ZipPayload]) -> None:
    central_directory = bytearray()
    raw_end_tag = next((entry.data for entry in entries if entry.name == "end_tag.bin"), b"")
    with open(output_path, "wb") as target:
        for entry in entries:
            name = entry.name.encode("utf-8")
            data = bytes(entry.data)
            compressed = _deflate_raw(data)
            crc = zlib.crc32(data) & 0xFFFFFFFF
            local_offset = target.tell()

            target.write(
                struct.pack(
                    "<IHHHHHIIIHH",
                    0x04034B50,
                    20,
                    ZIP_GENERAL_PURPOSE_FLAG,
                    ZIP_DEFLATED,
                    0,
                    ZIP_DOS_DATE_1980_JAN_ZERO,
                    crc,
                    len(compressed),
                    len(data),
                    len(name),
                    0,
                )
            )
            target.write(name)
            target.write(compressed)

            central_directory.extend(
                struct.pack(
                    "<IHHHHHHIIIHHHHHII",
                    0x02014B50,
                    0,
                    20,
                    ZIP_GENERAL_PURPOSE_FLAG,
                    ZIP_DEFLATED,
                    0,
                    ZIP_DOS_DATE_1980_JAN_ZERO,
                    crc,
                    len(compressed),
                    len(data),
                    len(name),
                    0,
                    0,
                    0,
                    0,
                    0,
                    local_offset,
                )
            )
            central_directory.extend(name)

        central_offset = target.tell()
        target.write(central_directory)
        target.write(
            struct.pack(
                "<IHHHHIIH",
                0x06054B50,
                0,
                0,
                len(entries),
                len(entries),
                len(central_directory),
                central_offset,
                0,
            )
        )
        # Samsung-written .sdocx files keep end_tag.bin in the zip and append
        # the same raw 148-byte footer after the official ZIP end record.
        if raw_end_tag:
            target.write(raw_end_tag)


class SamsungNotesExporter(NoteExporter):
    format_name = "sdocx"

    def _build_media_payloads(
        self,
        note: NoteDocument,
        now: int,
        warnings: List[str],
    ) -> Tuple[Dict[str, int], List[_ZipPayload], bytes]:
        referenced_asset_ids: Set[str] = {
            str(element.asset_id)
            for surface in note.surfaces
            for element in surface.elements
            if isinstance(element, ImageElement) and element.asset_id
        }
        bind_ids: Dict[str, int] = {}
        media_entries: List[Tuple[int, str, bytes, int]] = []
        zip_entries: List[_ZipPayload] = []
        used_filenames: Set[str] = set()

        for asset_id in sorted(referenced_asset_ids):
            asset = note.assets.get(asset_id)
            if asset is None:
                warnings.append(f"Omitted image asset {asset_id}: asset metadata is missing.")
                continue
            media = _asset_media_bytes(asset)
            if media is None:
                warnings.append(f"Omitted image asset {asset_id}: source bytes could not be resolved.")
                continue
            content, preferred_filename, media_type = media
            if not media_type.startswith("image/"):
                warnings.append(f"Exporting media asset {asset_id} as an inserted image although its media type is {media_type}.")

            bind_id = len(media_entries)
            filename_body = re.sub(r"^\d+@", "", _safe_media_filename(preferred_filename))
            if not os.path.splitext(filename_body)[1]:
                filename_body = f"{filename_body}{_extension_for_media_type(media_type)}"
            filename = f"{bind_id}@{filename_body}"
            suffix = 1
            while filename in used_filenames:
                stem, extension = os.path.splitext(filename_body)
                filename = f"{bind_id}@{stem}_{suffix}{extension}"
                suffix += 1
            used_filenames.add(filename)
            bind_ids[asset_id] = bind_id
            media_entries.append((bind_id, filename, content, now))
            zip_entries.append(_ZipPayload(f"media/{filename}", content))

        return bind_ids, zip_entries, _build_media_info(media_entries)

    def export(self, note: NoteDocument, output_dir: str, options: ExportOptions) -> ExportResult:
        output_path = self._resolve_output_path(note, output_dir)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        warnings: List[str] = []
        page_payloads: List[_PagePayload] = []
        now = _safe_timestamp_us()
        media_bind_ids, media_payloads, media_info = self._build_media_payloads(note, now, warnings)

        for index, surface in enumerate(note.surfaces):
            page_payload = self._build_page_payload(
                note,
                surface,
                index,
                now,
                warnings,
                media_bind_ids=media_bind_ids,
            )
            page_payloads.append(page_payload)

        if not page_payloads:
            synthetic_page = self._build_empty_page(note, 0, now, warnings)
            page_payloads.append(synthetic_page)

        if note.layout_kind == "infinite_canvas":
            for page_payload in page_payloads:
                warnings.append(
                    "Infinite canvas was materialized as one finite Samsung Notes page "
                    f"({page_payload.width}x{page_payload.height})."
                )

        trailing_page = self._build_empty_page(note, len(page_payloads), now, warnings)
        page_payloads.append(trailing_page)
        warnings.append("Added Samsung Notes trailing blank page for import compatibility.")

        note_data, note_hash = self._build_note_file(note, page_payloads, now)
        page_id_info = self._build_page_id_info(note_hash, page_payloads)
        end_tag = self._build_end_tag(note, page_payloads, now)
        _write_samsung_zip(
            output_path,
            [
                _ZipPayload("media/mediaInfo.dat", media_info),
                *media_payloads,
                *[_ZipPayload(f"{page_payload.page_id}.page", page_payload.data) for page_payload in page_payloads],
                _ZipPayload("pageIdInfo.dat", page_id_info),
                _ZipPayload("note.note", note_data),
                _ZipPayload("end_tag.bin", end_tag),
            ],
        )

        return ExportResult(
            format_name=self.format_name,
            output_paths=[output_path],
            warnings=warnings,
            metadata={
                "page_count": len(page_payloads),
                "stroke_count": sum(page.stroke_count for page in page_payloads),
                "omitted_element_count": sum(page.omitted_count for page in page_payloads),
            },
        )

    def _resolve_output_path(self, note: NoteDocument, output_dir: str) -> str:
        absolute = os.path.abspath(output_dir)
        if absolute.lower().endswith(".sdocx"):
            return absolute
        display_name = note.source.display_name or note.title or "converted_note"
        safe_name = "".join(char if char not in '<>:"/\\|?*' else "_" for char in display_name).strip() or "converted_note"
        return os.path.join(absolute, f"{safe_name}.sdocx")

    def _build_empty_page(self, note: NoteDocument, index: int, now: int, warnings: List[str]) -> _PagePayload:
        class _Surface:
            surface_id = f"empty-{index}"
            width = DEFAULT_PAGE_WIDTH
            height = DEFAULT_PAGE_HEIGHT
            elements: List[object] = []
            background = None

        return self._build_page_payload(note, _Surface(), index, now, warnings)

    def _build_page_payload(
        self,
        note: NoteDocument,
        surface,
        index: int,
        now: int,
        warnings: List[str],
        media_bind_ids: Optional[Dict[str, int]] = None,
    ) -> _PagePayload:
        media_bind_ids = media_bind_ids or {}
        page_id = _surface_id_to_page_id(note, str(surface.surface_id), index)
        source_width, source_height = _surface_size(surface)
        width, height, size_clamped = _clamp_surface_size(source_width, source_height)
        if size_clamped:
            warnings.append(
                f"Samsung Notes page {index + 1} dimensions exceeded the signed 32-bit metadata limit; "
                f"clamped from {source_width}x{source_height} "
                f"to {width}x{height}."
            )
        if width > PRACTICAL_PAGE_LIMIT or height > PRACTICAL_PAGE_LIMIT:
            warnings.append(
                f"Samsung Notes page {index + 1} is very large ({width}x{height}); "
                "the file is valid structurally, but Samsung Notes may become slow or refuse it."
            )

        strokes: List[StrokeElement] = []
        text_fields: List[TextElement] = []
        images: List[_SamsungImage] = []
        omitted_count = 0
        text_field_count = 0
        image_count = 0
        frame_count = 0
        for element in surface.elements:
            if isinstance(element, StrokeElement):
                if len(element.points) >= 2:
                    strokes.append(element)
                continue
            if isinstance(element, TextElement):
                if str(element.text or ""):
                    text_fields.append(element)
                    text_field_count += 1
                else:
                    omitted_count += 1
                continue
            if isinstance(element, ImageElement):
                asset_id = str(element.asset_id or "")
                bind_id = media_bind_ids.get(asset_id)
                if bind_id is None:
                    omitted_count += 1
                    continue
                images.append(_SamsungImage(element, bind_id))
                image_count += 1
                continue
            if isinstance(element, FrameElement):
                strokes.append(_frame_to_stroke(element))
                label = _frame_to_label(element)
                if label is not None:
                    text_fields.append(label)
                frame_count += 1
                continue
            if isinstance(element, (PdfBackgroundElement, UnsupportedElement)):
                omitted_count += 1

        if text_field_count:
            warnings.append(
                f"Converted {text_field_count} text element(s) on page {index + 1} to native Samsung Notes text field objects."
            )
        if image_count:
            warnings.append(f"Converted {image_count} image element(s) on page {index + 1} to Samsung Notes image objects.")
        if frame_count:
            warnings.append(f"Converted {frame_count} frame element(s) on page {index + 1} to Samsung Notes outline/text objects.")

        if omitted_count:
            warnings.append(
                f"Omitted {omitted_count} non-stroke element(s) on page {index + 1}; "
                "Samsung Notes export currently supports strokes, stroke-like shape outlines, text fields, frames, and resolved images."
            )

        background_color = DEFAULT_BACKGROUND_COLOR
        background = getattr(surface, "background", None)
        if background is not None and isinstance(getattr(background, "color_int", None), int):
            background_color = int(background.color_int) & 0xFFFFFFFF

        data, page_hash = self._build_page_file(
            page_id=page_id,
            width=width,
            height=height,
            background_color=background_color,
            strokes=strokes,
            text_fields=text_fields,
            images=images,
            now=now,
        )
        return _PagePayload(
            page_id=page_id,
            data=data,
            page_hash=page_hash,
            width=width,
            height=height,
            stroke_count=len(strokes),
            omitted_count=omitted_count,
        )

    def _build_page_file(
        self,
        page_id: str,
        width: int,
        height: int,
        background_color: int,
        strokes: List[StrokeElement],
        text_fields: List[TextElement],
        images: List[_SamsungImage],
        now: int,
    ) -> Tuple[bytes, bytes]:
        property_offset = 0x80
        drawn_rect = _rect_union(
            [
                rect
                for rect in (
                    _stroke_bounds(strokes),
                    _rect_union(_text_field_rect(field) for field in text_fields),
                    _rect_union(image.element.rect for image in images),
                )
                if rect is not None
            ]
        )
        property_mask = 0x70 | (0x01 if drawn_rect is not None else 0)

        page = bytearray()
        page.extend(b"\x00" * 18)
        page.extend(_u32(0))
        page.extend(_u32(width))
        page.extend(_u32(height))
        page.extend(_u32(0))
        page.extend(_u32(0))
        page.extend(_utf16_u16(page_id))
        page.extend(_u64(now))
        page.extend(_u32(4000))
        page.extend(_u32(4000))

        if len(page) > property_offset:
            raise ValueError(f"Page metadata exceeded fixed property offset: {len(page)} bytes")
        page.extend(b"\x00" * (property_offset - len(page)))

        if drawn_rect is not None:
            for value in drawn_rect:
                page.extend(_f64(value))
        page.extend(_u32(2))
        page.extend(struct.pack("<I", background_color & 0xFFFFFFFF))
        page.extend(_u32(width))

        layer_offset = len(page)
        layer_section, layer_hash = self._build_layer_section(
            page_id=page_id,
            strokes=strokes,
            text_fields=text_fields,
            images=images,
            layer_offset=layer_offset,
            page_width=width,
            page_height=height,
            now=now,
        )
        page.extend(layer_section)

        struct.pack_into("<I", page, 0x00, layer_offset)
        struct.pack_into("<I", page, 0x04, property_offset)
        page[0x08] = 0x04
        struct.pack_into("<I", page, 0x09, 0)
        page[0x0D] = 0x04
        struct.pack_into("<I", page, 0x0E, property_mask)

        content = bytes(page)
        page_hash = hashlib.sha256(layer_hash + _identity_hash(page_id, now)).digest()
        return content + page_hash + PAGE_FOOTER, page_hash

    def _build_layer_section(
        self,
        page_id: str,
        strokes: List[StrokeElement],
        text_fields: List[TextElement],
        images: List[_SamsungImage],
        layer_offset: int,
        page_width: int,
        page_height: int,
        now: int,
    ) -> Tuple[bytes, bytes]:
        objects: List[Tuple[int, int, bytes, bytes]] = []
        for stroke in sorted(strokes, key=lambda item: (int(item.z_index), int(item.source_order))):
            for obj, object_hash in self._stroke_objects(stroke, page_id, page_width, page_height, now):
                objects.append((int(stroke.z_index), int(stroke.source_order), obj, object_hash))
        for text_field in sorted(text_fields, key=lambda item: (int(item.z_index), int(item.source_order))):
            obj, object_hash = self._pack_text_field_object(text_field, page_width, page_height, now)
            objects.append((int(text_field.z_index), int(text_field.source_order), obj, object_hash))
        for image in sorted(images, key=lambda item: (int(item.element.z_index), int(item.element.source_order))):
            obj, object_hash = self._pack_image_object(image, page_width, page_height, now)
            objects.append((int(image.element.z_index), int(image.element.source_order), obj, object_hash))
        objects.sort(key=lambda item: (item[0], item[1]))

        section = bytearray()
        section.extend(_u16(1))
        section.extend(_u16(0))

        layer_id = _samsung_like_uuid()
        layer_extra = _utf16_u16(layer_id) + _u64(now)
        layer_start = len(section)
        header_size = 16 + len(layer_extra)
        metadata_offset_abs = layer_offset + layer_start + 16
        layer = bytearray()
        layer.extend(_u32(header_size))
        layer.extend(_u32(metadata_offset_abs))
        layer.extend(b"\x01")
        layer.extend(b"\x02")
        layer.extend(b"\x01")
        layer.extend(b"\x18")
        layer.extend(_u32(0))
        layer.extend(layer_extra)
        layer.extend(_u32(len(objects)))
        object_hashes = bytearray()
        for _, _, obj, object_hash in objects:
            layer.extend(obj)
            object_hashes.extend(object_hash)

        object_hashes.extend(_identity_hash(layer_id, now))
        layer_hash = hashlib.sha256(bytes(object_hashes)).digest()
        layer.extend(layer_hash)
        section.extend(layer)
        return bytes(section), layer_hash

    def _stroke_objects(
        self,
        stroke: StrokeElement,
        page_id: str,
        page_width: int,
        page_height: int,
        now: int,
    ) -> List[Tuple[bytes, bytes]]:
        objects: List[Tuple[bytes, bytes]] = []
        points = [
            (_finite_float(point[0]), _finite_float(point[1]))
            for point in stroke.points
            if math.isfinite(_finite_float(point[0])) and math.isfinite(_finite_float(point[1]))
        ]
        if len(points) < 2:
            return objects

        pressures = list(stroke.pressures) if len(stroke.pressures) == len(stroke.points) else []
        timestamps = list(stroke.timestamps) if len(stroke.timestamps) == len(stroke.points) else []
        for start in range(0, len(points), MAX_STROKE_POINTS):
            point_chunk = points[start : start + MAX_STROKE_POINTS]
            if len(point_chunk) < 2:
                continue
            pressure_chunk = pressures[start : start + len(point_chunk)] if pressures else []
            timestamp_chunk = timestamps[start : start + len(point_chunk)] if timestamps else []
            object_id = _samsung_like_uuid()
            objects.append(
                self._pack_stroke_object(
                    object_id=object_id,
                    stroke=stroke,
                    points=point_chunk,
                    pressures=pressure_chunk,
                    timestamps=timestamp_chunk,
                    page_width=page_width,
                    page_height=page_height,
                    now=now,
                )
            )
        return objects

    def _pack_stroke_object(
        self,
        object_id: str,
        stroke: StrokeElement,
        points: List[Tuple[float, float]],
        pressures: List[float],
        timestamps: List[int],
        page_width: int,
        page_height: int,
        now: int,
    ) -> Tuple[bytes, bytes]:
        if len(pressures) != len(points):
            pressures = [0.5 for _ in points]
        else:
            pressures = [max(0.0, min(1.0, _finite_float(pressure, 0.5))) for pressure in pressures]

        if len(timestamps) != len(points):
            timestamps = [index * 8 for index in range(len(points))]
        else:
            timestamps = [int(timestamp) for timestamp in timestamps]

        compact_geometry = self._build_compact_stroke_geometry(points, pressures, timestamps)
        property_mask1 = 0x0425 if compact_geometry is not None else 0x0000
        property_mask2 = 0x258E
        property_mask1_bytes = property_mask1.to_bytes(2, "little", signed=False)
        property_mask2_bytes = property_mask2.to_bytes(4, "little", signed=False)

        geometry = compact_geometry if compact_geometry is not None else self._build_raw_stroke_geometry(
            points,
            pressures,
            timestamps,
        )

        body_without_flexible_offset = bytearray()
        body_without_flexible_offset.extend(bytes([len(property_mask1_bytes)]))
        body_without_flexible_offset.extend(property_mask1_bytes)
        body_without_flexible_offset.extend(bytes([len(property_mask2_bytes)]))
        body_without_flexible_offset.extend(property_mask2_bytes)
        body_without_flexible_offset.extend(_u16(len(points)))
        body_without_flexible_offset.extend(geometry)

        flexible = bytearray()
        flexible.extend(_u32(1))
        flexible.extend(struct.pack("<I", int(stroke.color_int) & 0xFFFFFFFF))
        pen_size = max(0.5, _finite_float(stroke.pen_size, 2.0))
        flexible.extend(_f32(pen_size))
        flexible.extend(_u32(0))
        flexible.extend(_f32(pen_size))
        flexible.extend(_u32(1))
        flexible.extend(_f32(max(0.1, pen_size - 2.5)))

        flexible_offset = 6 + 4 + len(body_without_flexible_offset)
        body = bytearray()
        body.extend(_u32(flexible_offset))
        body.extend(body_without_flexible_offset)
        body.extend(flexible)

        stroke_subrecord = _u32(len(body) + 6) + _u16(1) + bytes(body)
        base_subrecord = self._pack_object_base_record(object_id, stroke, points, page_width, page_height, now)
        payload = base_subrecord + stroke_subrecord
        object_hash = _identity_hash(object_id, now)
        object_without_hash = bytes([1]) + _u16(0) + _u32(len(payload) + 32) + payload
        return object_without_hash + object_hash, object_hash

    def _build_compact_stroke_geometry(
        self,
        points: List[Tuple[float, float]],
        pressures: List[float],
        timestamps: List[int],
    ) -> Optional[bytes]:
        if not points:
            return b"\x03\x00"

        data = bytearray()
        current_x, current_y = points[0]
        data.extend(_f64(current_x))
        data.extend(_f64(current_y))

        for x, y in points[1:]:
            dx = _pack_compact_delta(float(x) - float(current_x))
            dy = _pack_compact_delta(float(y) - float(current_y))
            if dx is None or dy is None:
                return None
            data.extend(dx)
            data.extend(dy)
            current_x, current_y = x, y

        pressure_data = _pack_compact_float_series(pressures, 128.0)
        timestamp_data = _pack_compact_timestamp_series(timestamps)
        tilt_data = _pack_compact_float_series([0.0 for _ in points], 32.0)
        orientation_data = _pack_compact_float_series([0.0 for _ in points], 32.0)
        if None in (pressure_data, timestamp_data, tilt_data, orientation_data):
            return None

        data.extend(pressure_data or b"")
        data.extend(timestamp_data or b"")
        data.extend(tilt_data or b"")
        data.extend(orientation_data or b"")
        data.extend(_u16(3))
        return bytes(data)

    def _build_raw_stroke_geometry(
        self,
        points: List[Tuple[float, float]],
        pressures: List[float],
        timestamps: List[int],
    ) -> bytes:
        geometry = bytearray()
        for x, y in points:
            geometry.extend(_f32(x))
            geometry.extend(_f32(y))
        for pressure in pressures:
            geometry.extend(_f32(pressure))
        for timestamp in timestamps:
            geometry.extend(_i32(timestamp))
        geometry.extend(_u16(3))
        return bytes(geometry)

    def _pack_text_field_object(
        self,
        element: TextElement,
        page_width: int,
        page_height: int,
        now: int,
    ) -> Tuple[bytes, bytes]:
        object_id = _samsung_like_uuid()
        rect = _text_field_rect(element)
        payload = (
            self._pack_object_base_record_for_rect(
                object_id,
                rect,
                page_width,
                page_height,
                now,
                fixed_point_page_dimensions=False,
            )
            + self._pack_text_field_shape_base_record(rect)
            + self._pack_text_field_shape_text_record(element, rect)
            + TEXT_FIELD_TRAILER_SUBRECORD
        )
        object_hash = _identity_hash(object_id, now)
        object_without_hash = bytes([2]) + _u16(0) + _u32(len(payload) + 32) + payload
        return object_without_hash + object_hash, object_hash

    def _pack_image_object(
        self,
        image: _SamsungImage,
        page_width: int,
        page_height: int,
        now: int,
    ) -> Tuple[bytes, bytes]:
        object_id = _samsung_like_uuid()
        rect = self._normal_image_rect(image.element.rect)
        payload = (
            self._pack_image_base_record(object_id, rect, page_width, page_height, now)
            + self._pack_image_layout_record(rect)
            + self._pack_image_shape_record(rect, image.bind_id, page_width)
            + bytes.fromhex("11 00 00 00 03 00 00 00 00 00 01 00 04 00 00 00 00")
        )
        object_hash = _identity_hash(object_id, now)
        object_without_hash = bytes([3]) + _u16(0) + _u32(len(payload) + 32) + payload
        return object_without_hash + object_hash, object_hash

    def _normal_image_rect(self, rect: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
        left, top, right, bottom = (float(value) for value in rect)
        return min(left, right), min(top, bottom), max(left, right), max(top, bottom)

    def _pack_image_base_record(
        self,
        object_id: str,
        rect: Tuple[float, float, float, float],
        page_width: int,
        page_height: int,
        now: int,
    ) -> bytes:
        record = bytearray()
        record.extend(_u32(122))
        record.extend(_u16(0))
        record.extend(_u32(105))
        record.extend(bytes.fromhex("02 bf 01 04 00 e0 00 00"))
        record.extend(_u32(4000))
        record.extend(_u16(36))
        record.extend(object_id.encode("ascii", errors="ignore")[:36].ljust(36, b"0"))
        record.extend(_u64(now))
        for value in rect:
            record.extend(_f64(value))
        record.extend(_u32(0))
        record.extend(_u64(now))
        record.extend(_u32(_object_base_page_dimension(page_width)))
        record.extend(_u32(_object_base_page_dimension(page_height)))
        record.extend(b"\x00\x02")
        return bytes(record)

    def _pack_image_layout_record(self, rect: Tuple[float, float, float, float]) -> bytes:
        left, top, right, bottom = rect
        mid_x = (left + right) / 2.0
        mid_y = (top + bottom) / 2.0
        record = bytearray()
        record.extend(_u32(130))
        record.extend(_u16(6))
        record.extend(_u32(91))
        record.extend(bytes.fromhex("01 00 01 0c"))
        record.extend(_u32(4))
        for value in (mid_x, top, right, mid_y, mid_x, bottom, left, mid_y):
            record.extend(_f64(value))
        record.extend(_u32(4))
        record.extend(b"\x00" * 5)
        record.extend(bytes.fromhex("13 00 00 00 01 00 02 00 00 00 ff 00 00 00"))
        record.extend(b"\x00" * 9)
        record.extend(_u32(12))
        record.extend(b"\x00" * 12)
        return bytes(record)

    def _pack_image_shape_record(
        self,
        rect: Tuple[float, float, float, float],
        bind_id: int,
        page_width: int,
    ) -> bytes:
        left, top, right, bottom = rect
        path_block = bytearray()
        path_block.extend(_u32(73))
        path_block.extend(_u32(5))
        for command, x, y in (
            (1, left, top),
            (2, right, top),
            (2, right, bottom),
            (2, left, bottom),
        ):
            path_block.extend(bytes([command]))
            path_block.extend(_f64(x))
            path_block.extend(_f64(y))
        path_block.extend(_u16(6))

        fill_effect = bytearray()
        fill_effect.extend(_u32(62))
        fill_effect.extend(b"\x02")
        fill_effect.extend(b"\x00")
        fill_effect.extend(_u32(bind_id))
        fill_effect.extend(b"\x00" * 16)
        fill_effect.extend(b"\x00" * 8)
        fill_effect.extend(_f32(100.0))
        fill_effect.extend(_f32(100.0))
        fill_effect.extend(_f32(0.0))
        fill_effect.extend(b"\x00")
        fill_effect.extend(b"\x00" * 16)
        fill_effect.extend(_u32(max(1, int(page_width))))
        fill_effect.extend(b"\x02")

        record = bytearray()
        record.extend(_u32(203))
        record.extend(_u16(7))
        record.extend(_u32(135))
        record.extend(bytes.fromhex("01 00 04 20 10 00 00"))
        record.extend(_u32(4))
        for value in rect:
            record.extend(_f64(value))
        record.extend(_u32(0))
        record.extend(path_block)
        record.extend(fill_effect)
        return bytes(record)

    def _pack_text_field_shape_base_record(self, rect: Tuple[float, float, float, float]) -> bytes:
        left, top, right, bottom = rect
        mid_x = (left + right) / 2.0
        mid_y = (top + bottom) / 2.0
        record = bytearray()
        record.extend(_u32(130))
        record.extend(_u16(6))
        record.extend(_u32(91))
        record.extend(bytes.fromhex("01 00 01 0c"))
        record.extend(_u32(4))
        for value in (mid_x, top, right, mid_y, mid_x, bottom, left, mid_y):
            record.extend(_f64(value))
        record.extend(TEXT_FIELD_SHAPE_BASE_TAIL)
        return bytes(record)

    def _pack_text_field_shape_text_record(
        self,
        element: TextElement,
        rect: Tuple[float, float, float, float],
    ) -> bytes:
        left, top, right, bottom = rect
        path_block = bytearray()
        path_block.extend(_u32(73))
        path_block.extend(_u32(5))
        for command, x, y in (
            (1, left, top),
            (2, right, top),
            (2, right, bottom),
            (2, left, bottom),
        ):
            path_block.extend(bytes([command]))
            path_block.extend(_f64(x))
            path_block.extend(_f64(y))
        path_block.extend(_u16(6))

        text_common = _build_text_field_text_common(element)
        body = bytearray()
        body.extend(_u32(135))
        body.extend(bytes.fromhex("01 04 04"))
        body.extend(_u32(0x2001))
        body.extend(_u32(4))
        for value in rect:
            body.extend(_f64(value))
        body.extend(_u32(0))
        body.extend(path_block)
        body.extend(_u32(len(text_common)))
        body.extend(text_common)
        body.extend(b"\x02")

        return _u32(len(body) + 6) + _u16(7) + bytes(body)

    def _pack_object_base_record_for_rect(
        self,
        object_id: str,
        rect: Tuple[float, float, float, float],
        page_width: int,
        page_height: int,
        now: int,
        fixed_point_page_dimensions: bool = True,
    ) -> bytes:
        left, top, right, bottom = rect
        embedded_page_width = (
            _object_base_page_dimension(page_width) if fixed_point_page_dimensions else max(1, int(page_width))
        )
        embedded_page_height = (
            _object_base_page_dimension(page_height) if fixed_point_page_dimensions else max(1, int(page_height))
        )
        record = bytearray()
        record.extend(_u32(121))
        record.extend(_u16(0))
        record.extend(_u32(105))
        record.extend(bytes.fromhex("02 bf 01 04 00 60 00 00"))
        record.extend(_u32(4000))
        record.extend(_u16(36))
        record.extend(object_id.encode("ascii", errors="ignore")[:36].ljust(36, b"0"))
        record.extend(_u64(now))
        for value in (left, top, right, bottom):
            record.extend(_f64(value))
        record.extend(_u32(0))
        if fixed_point_page_dimensions:
            record.extend(_u64(now))
            record.extend(_u32(embedded_page_width))
            record.extend(_u32(embedded_page_height))
            record.extend(b"\x00")
        else:
            record.extend(b"\x00")
            record.extend(_u64(now))
            record.extend(_u32(embedded_page_width))
            record.extend(_u32(embedded_page_height))
        return bytes(record)

    def _pack_object_base_record(
        self,
        object_id: str,
        stroke: StrokeElement,
        points: List[Tuple[float, float]],
        page_width: int,
        page_height: int,
        now: int,
    ) -> bytes:
        pad = max(1.0, _finite_float(stroke.pen_size, 2.0))
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        left = min(xs) - pad
        top = min(ys) - pad
        right = max(xs) + pad
        bottom = max(ys) + pad
        return self._pack_object_base_record_for_rect(object_id, (left, top, right, bottom), page_width, page_height, now)

    def _build_note_file(
        self,
        note: NoteDocument,
        pages: List[_PagePayload],
        now: int,
    ) -> Tuple[bytes, bytes]:
        width = max((page.width for page in pages), default=DEFAULT_PAGE_WIDTH)
        height = sum(page.height for page in pages) + DEFAULT_NOTE_VERTICAL_PADDING
        title_object = _build_title_object(
            _note_title(note),
            _samsung_like_uuid(),
            now,
        )
        body_object = _build_body_object(
            _samsung_like_uuid(),
            now,
        )

        data = bytearray()
        data.extend(b"\x00" * 4)
        data.extend(b"\x04")
        data.extend(_u32(NOTE_HEADER_FLAGS))
        data.extend(b"\x04")
        data.extend(_u32(NOTE_PROPERTY_FLAGS))
        data.extend(_u32(4000))
        data.extend(_utf16_u16(""))
        data.extend(_u32(5))
        data.extend(_u64(now))
        data.extend(_u64(now))
        data.extend(_u32(width))
        data.extend(_u32(height))
        data.extend(_u32(0))
        data.extend(_u32(DEFAULT_NOTE_VERTICAL_PADDING))
        data.extend(_u32(4000))
        data.extend(_u32(len(title_object)))
        data.extend(title_object)
        data.extend(_u32(len(body_object)))
        data.extend(body_object)

        optional_offset = len(data)
        struct.pack_into("<I", data, 0, optional_offset)
        data.extend(_i32(0))
        data.extend(_i32(-1))
        data.extend(_u64(0))
        data.extend(
            _build_string_id_block(
                [
                    (0, DEFAULT_PEN_NAME),
                    (1, DEFAULT_ADVANCED_SETTING),
                ]
            )
        )
        data.extend(_i32(0))
        data.extend(_build_current_pen_info())
        data.extend(_i32(2))
        data.extend(_i32(2))

        note_hash = hashlib.sha256(bytes(data)).digest()
        data.extend(note_hash)
        return bytes(data), note_hash

    def _build_page_id_info(self, note_hash: bytes, pages: List[_PagePayload]) -> bytes:
        data = bytearray()
        data.extend(note_hash[:32].ljust(32, b"\x00"))
        data.extend(_u16(len(pages)))
        for page in pages:
            data.extend(_utf16_u16(page.page_id))
            data.extend(page.page_hash[:32].ljust(32, b"\x00"))
        return bytes(data)

    def _build_end_tag(self, note: NoteDocument, pages: List[_PagePayload], now: int) -> bytes:
        width = max((page.width for page in pages), default=DEFAULT_PAGE_WIDTH)
        height = float(sum(page.height for page in pages) + DEFAULT_NOTE_VERTICAL_PADDING)
        display_created_time = now
        display_modified_time = now // 1000

        payload = bytearray()
        payload.extend(_i32(4000))
        payload.extend(_utf16_u16(""))
        payload.extend(_u64(now))
        payload.extend(_i32(0))
        payload.extend(_utf16_u16(""))
        payload.extend(_i32(width))
        payload.extend(_f32(height))
        payload.extend(_utf16_u16(""))
        payload.extend(_i32(-1))
        payload.extend(_i32(-1))
        payload.extend(_utf16_u16(""))
        payload.extend(_i32(4000))
        payload.extend(_u64(now))
        payload.extend(_i32(0))
        payload.extend(_u16(0))
        payload.extend(_u16(0))
        payload.extend(_utf16_u16(""))
        payload.extend(_i32(0))
        payload.extend(_i32(0))
        payload.extend(_u64(display_created_time))
        payload.extend(_u64(display_modified_time))
        payload.extend(_u64(0))
        payload.extend(_utf16_u16(""))
        payload.extend(_i32(2))
        payload.extend(_i32(2))
        payload.extend(_i64(-1))
        payload.extend(_i32(0))
        payload.extend(_i32(0))
        payload.extend(_utf16_u32_nullable(""))
        payload.extend(END_TAG_FOOTER)

        return _u16(len(payload)) + bytes(payload)
