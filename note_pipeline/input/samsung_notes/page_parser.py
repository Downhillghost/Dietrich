from __future__ import annotations

import os
import struct
from io import BytesIO
from typing import Dict, Iterable, List, Optional, Tuple

from kaitaistruct import KaitaiStream

from note_pipeline.input.binary import (
    can_read,
    f32,
    f64,
    i32,
    read_counted_utf8,
    read_utf8_u16_bytes,
    read_utf16_u16,
    rect_f32,
    u8,
    u16,
    u32,
    u64,
)
from note_pipeline.input.samsung_notes.constants import IMAGE_LAYOUT_USE_DEFAULT
from note_pipeline.input.samsung_notes.generated import SamsungPage, SamsungPageLayers
from note_pipeline.input.samsung_notes.sidecars import parse_media_info
from note_pipeline.input.samsung_notes.spi import parse_spi_file
from note_pipeline.model import IntRect, Point, Rect


_NOTE_METADATA_CACHE: Dict[str, Dict[str, object]] = {}
_COMPACT_PRESSURE_DELTA_SCALE = 128.0
_COMPACT_ANGLE_DELTA_SCALE = 32.0


class SpenNotesPageParser:
    def __init__(self, file_path: str, note_root: Optional[str] = None):
        self.file_path = os.path.abspath(file_path)
        self.note_root = os.path.abspath(note_root or os.path.dirname(self.file_path) or os.getcwd())
        with open(self.file_path, "rb") as f:
            self.data = f.read()
        self._media_index: Optional[Dict[int, Dict[str, object]]] = None
        self._note_metadata: Optional[Dict[str, object]] = None
        self._page_metadata: Optional[Dict[str, object]] = None
        self._resolved_layers: Optional[List[Dict[str, object]]] = None

    def _can_read(self, offset: int, size: int) -> bool:
        return can_read(self.data, offset, size)

    def _u8(self, offset: int) -> int:
        return u8(self.data, offset)

    def _u16(self, offset: int) -> int:
        return u16(self.data, offset)

    def _u32(self, offset: int) -> int:
        return u32(self.data, offset)

    def _i32(self, offset: int) -> int:
        return i32(self.data, offset)

    def _u64(self, offset: int) -> int:
        return u64(self.data, offset)

    def _f32(self, offset: int) -> float:
        return f32(self.data, offset)

    def _f64(self, offset: int) -> float:
        return f64(self.data, offset)

    def _rectd(self, offset: int) -> Rect:
        return (
            self._f64(offset),
            self._f64(offset + 8),
            self._f64(offset + 16),
            self._f64(offset + 24),
        )

    def _recti(self, offset: int) -> IntRect:
        return (
            self._i32(offset),
            self._i32(offset + 4),
            self._i32(offset + 8),
            self._i32(offset + 12),
        )

    @staticmethod
    def _read_utf16_string(blob: bytes, offset: int) -> Tuple[str, int]:
        return read_utf16_u16(blob, offset)

    def unpack_coord_delta(self, val: int) -> float:
        sign = (val >> 15) & 1
        integer = (val >> 5) & 0x3FF
        fraction = val & 0x1F
        delta = integer + fraction / 32.0
        return -delta if sign else delta

    def _unpack_scaled_delta(self, val: int, scale: float) -> float:
        return self.unpack_coord_delta(val) / scale

    def _parse_compact_float_series(
        self,
        cursor: int,
        limit: int,
        point_count: int,
        delta_scale: float,
    ) -> Optional[Tuple[List[float], int]]:
        if point_count <= 0:
            return [], cursor

        size = 4 + (max(0, point_count - 1) * 2)
        if cursor + size > limit or not self._can_read(cursor, size):
            return None

        values = [self._f32(cursor)]
        current = values[0]
        delta_cursor = cursor + 4
        for _ in range(point_count - 1):
            current += self._unpack_scaled_delta(self._u16(delta_cursor), delta_scale)
            values.append(current)
            delta_cursor += 2
        return values, cursor + size

    def _parse_compact_timestamp_series(
        self,
        cursor: int,
        limit: int,
        point_count: int,
    ) -> Optional[Tuple[List[int], int]]:
        if point_count <= 0:
            return [], cursor

        size = 4 + (max(0, point_count - 1) * 2)
        if cursor + size > limit or not self._can_read(cursor, size):
            return None

        values = [self._i32(cursor)]
        current = values[0]
        delta_cursor = cursor + 4
        for _ in range(point_count - 1):
            current += self._u16(delta_cursor)
            values.append(current)
            delta_cursor += 2
        return values, cursor + size

    def _parse_raw_float_series(
        self,
        cursor: int,
        limit: int,
        point_count: int,
    ) -> Optional[Tuple[List[float], int]]:
        if point_count <= 0:
            return [], cursor

        size = point_count * 4
        if cursor + size > limit or not self._can_read(cursor, size):
            return None

        return [self._f32(cursor + (index * 4)) for index in range(point_count)], cursor + size

    def _parse_raw_timestamp_series(
        self,
        cursor: int,
        limit: int,
        point_count: int,
    ) -> Optional[Tuple[List[int], int]]:
        if point_count <= 0:
            return [], cursor

        size = point_count * 4
        if cursor + size > limit or not self._can_read(cursor, size):
            return None

        return [self._i32(cursor + (index * 4)) for index in range(point_count)], cursor + size

    def _load_note_metadata(self) -> Dict[str, object]:
        if self._note_metadata is not None:
            return self._note_metadata

        note_path = os.path.abspath(os.path.join(self.note_root, "note.note"))
        cached = _NOTE_METADATA_CACHE.get(note_path)
        if cached is not None:
            self._note_metadata = cached
            return cached

        if not os.path.exists(note_path):
            self._note_metadata = {}
            _NOTE_METADATA_CACHE[note_path] = self._note_metadata
            return self._note_metadata

        from .note_adapters import note_source_to_metadata
        from .source import load_samsung_note_source

        note_metadata = note_source_to_metadata(load_samsung_note_source(note_path))
        _NOTE_METADATA_CACHE[note_path] = note_metadata
        self._note_metadata = note_metadata
        return note_metadata

    def _load_string_id_map(self) -> Dict[int, str]:
        note_metadata = self._load_note_metadata()
        raw_string_map = note_metadata.get("string_id_map")
        if not isinstance(raw_string_map, dict):
            return {}

        string_id_map: Dict[int, str] = {}
        for key, value in raw_string_map.items():
            if isinstance(key, int) and isinstance(value, str):
                string_id_map[int(key)] = value
        return string_id_map

    def _read_var_uint(self, offset: int, size: int, limit: int) -> Optional[int]:
        if size < 0 or size > 4:
            return None
        if size == 0:
            return 0
        if offset < 0 or offset + size > limit or not self._can_read(offset, size):
            return None
        return int.from_bytes(self.data[offset : offset + size], "little", signed=False)

    def _parse_new_stroke_raw_geometry(
        self,
        cursor: int,
        limit: int,
        point_count: int,
        has_optional_axes: bool,
    ) -> Optional[Tuple[List[Point], Dict[str, object], int, int]]:
        if point_count < 0:
            return None

        points: List[Point] = []
        if point_count > 0:
            point_bytes = point_count * 16
            if cursor + point_bytes > limit or not self._can_read(cursor, point_bytes):
                return None

            for point_index in range(point_count):
                point_offset = cursor + (point_index * 16)
                points.append((self._f64(point_offset), self._f64(point_offset + 8)))
            cursor += point_bytes

        parsed_pressures = self._parse_raw_float_series(cursor, limit, point_count)
        if parsed_pressures is None:
            return None
        pressures, cursor = parsed_pressures

        parsed_timestamps = self._parse_raw_timestamp_series(cursor, limit, point_count)
        if parsed_timestamps is None:
            return None
        timestamps, cursor = parsed_timestamps

        tilts: List[float] = []
        orientations: List[float] = []

        if has_optional_axes:
            parsed_tilts = self._parse_raw_float_series(cursor, limit, point_count)
            if parsed_tilts is None:
                return None
            tilts, cursor = parsed_tilts

            parsed_orientations = self._parse_raw_float_series(cursor, limit, point_count)
            if parsed_orientations is None:
                return None
            orientations, cursor = parsed_orientations

        if cursor + 2 > limit or not self._can_read(cursor, 2):
            return None
        tail_value = self._u16(cursor)
        cursor += 2
        dynamics: Dict[str, object] = {
            "pressures": pressures,
            "timestamps": timestamps,
            "tilts": tilts,
            "orientations": orientations,
            "pressure_encoding": "raw_f32",
            "timestamp_encoding": "raw_s32",
            "tilt_encoding": "raw_f32" if has_optional_axes else None,
            "orientation_encoding": "raw_f32" if has_optional_axes else None,
        }
        return points, dynamics, cursor, tail_value

    def _parse_new_stroke_compact_geometry(
        self,
        cursor: int,
        limit: int,
        point_count: int,
        has_optional_axes: bool,
    ) -> Optional[Tuple[List[Point], Dict[str, object], int, int]]:
        if point_count < 0:
            return None

        points: List[Point] = []
        delta_count = max(0, point_count - 1)

        if point_count > 0:
            if cursor + 16 > limit or not self._can_read(cursor, 16):
                return None

            curr_x = self._f64(cursor)
            curr_y = self._f64(cursor + 8)
            points.append((curr_x, curr_y))
            cursor += 16

            delta_bytes = delta_count * 4
            if cursor + delta_bytes > limit or not self._can_read(cursor, delta_bytes):
                return None

            delta_cursor = cursor
            for _ in range(delta_count):
                dx = self.unpack_coord_delta(self._u16(delta_cursor))
                dy = self.unpack_coord_delta(self._u16(delta_cursor + 2))
                curr_x += dx
                curr_y += dy
                points.append((curr_x, curr_y))
                delta_cursor += 4
            cursor += delta_bytes

        parsed_pressures = self._parse_compact_float_series(
            cursor,
            limit,
            point_count,
            _COMPACT_PRESSURE_DELTA_SCALE,
        )
        if parsed_pressures is None:
            return None
        pressures, cursor = parsed_pressures

        parsed_timestamps = self._parse_compact_timestamp_series(cursor, limit, point_count)
        if parsed_timestamps is None:
            return None
        timestamps, cursor = parsed_timestamps

        tilts: List[float] = []
        orientations: List[float] = []
        if has_optional_axes:
            parsed_tilts = self._parse_compact_float_series(
                cursor,
                limit,
                point_count,
                _COMPACT_ANGLE_DELTA_SCALE,
            )
            if parsed_tilts is None:
                return None
            tilts, cursor = parsed_tilts

            parsed_orientations = self._parse_compact_float_series(
                cursor,
                limit,
                point_count,
                _COMPACT_ANGLE_DELTA_SCALE,
            )
            if parsed_orientations is None:
                return None
            orientations, cursor = parsed_orientations

        if cursor + 2 > limit or not self._can_read(cursor, 2):
            return None
        tail_value = self._u16(cursor)
        cursor += 2
        dynamics: Dict[str, object] = {
            "pressures": pressures,
            "timestamps": timestamps,
            "tilts": tilts,
            "orientations": orientations,
            "pressure_encoding": f"compact_f32_delta_scale_{_COMPACT_PRESSURE_DELTA_SCALE:g}",
            "timestamp_encoding": "compact_s32_u16_delta",
            "tilt_encoding": f"compact_f32_delta_scale_{_COMPACT_ANGLE_DELTA_SCALE:g}" if has_optional_axes else None,
            "orientation_encoding": f"compact_f32_delta_scale_{_COMPACT_ANGLE_DELTA_SCALE:g}" if has_optional_axes else None,
        }
        return points, dynamics, cursor, tail_value

    def _parse_new_stroke_flexible_data(
        self,
        subrecord_start: int,
        subrecord_end: int,
        flexible_offset: int,
        flexible_mask: int,
        string_id_map: Dict[int, str],
    ) -> Dict[str, object]:
        info: Dict[str, object] = {
            "flexible_offset": flexible_offset,
            "flexible_mask": flexible_mask,
        }

        cursor = subrecord_start + flexible_offset
        if cursor < subrecord_start or cursor > subrecord_end or not self._can_read(cursor, 0):
            info["flexible_parse_error"] = "invalid flexible offset"
            return info

        info["style_offset"] = cursor

        def read_u32() -> Optional[int]:
            nonlocal cursor
            if cursor + 4 > subrecord_end or not self._can_read(cursor, 4):
                return None
            value = self._u32(cursor)
            cursor += 4
            return value

        def read_u16() -> Optional[int]:
            nonlocal cursor
            if cursor + 2 > subrecord_end or not self._can_read(cursor, 2):
                return None
            value = self._u16(cursor)
            cursor += 2
            return value

        def read_u8() -> Optional[int]:
            nonlocal cursor
            if cursor + 1 > subrecord_end or not self._can_read(cursor, 1):
                return None
            value = self._u8(cursor)
            cursor += 1
            return value

        def read_f32() -> Optional[float]:
            nonlocal cursor
            if cursor + 4 > subrecord_end or not self._can_read(cursor, 4):
                return None
            value = self._f32(cursor)
            cursor += 4
            return value

        # The imported-PDF notes use Samsung's newer object-stroke binary.
        # Its flexible block is flag-ordered and can omit visible attributes like
        # color entirely, so we decode only the confirmed fields and fall back
        # conservatively when a preset still needs higher-level interpretation.
        if flexible_mask & 0x0002:
            advanced_setting_id = read_u32()
            if advanced_setting_id is None:
                info["flexible_parse_error"] = "truncated advanced setting id"
                return info
            info["advanced_setting_id"] = advanced_setting_id
            info["advanced_setting"] = string_id_map.get(advanced_setting_id)

        if flexible_mask & 0x0004:
            color_int = read_u32()
            if color_int is None:
                info["flexible_parse_error"] = "truncated color"
                return info
            info["color_int"] = color_int

        if flexible_mask & 0x0008:
            pen_size = read_f32()
            if pen_size is None:
                info["flexible_parse_error"] = "truncated pen size"
                return info
            info["pen_size"] = pen_size

        if flexible_mask & 0x0010:
            byte_value = read_u8()
            if byte_value is None:
                info["flexible_parse_error"] = "truncated flexible byte"
                return info
            info["flex_byte_0x10"] = byte_value

        if flexible_mask & 0x0020:
            info["has_unsupported_flexible_bit_0x20"] = True
            return info

        if flexible_mask & 0x0080:
            pen_name_id = read_u32()
            if pen_name_id is None:
                info["flexible_parse_error"] = "truncated pen name id"
                return info
            info["pen_name_id"] = pen_name_id
            info["pen_name"] = string_id_map.get(pen_name_id)

        if flexible_mask & 0x0100:
            value = read_f32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x0100 float"
                return info
            info["float_0x0100"] = value

        if flexible_mask & 0x0200:
            value = read_u32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x0200 int"
                return info
            info["int_0x0200"] = value

        if flexible_mask & 0x0400:
            value = read_u32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x0400 int"
                return info
            info["int_0x0400"] = value

        if flexible_mask & 0x0800:
            value = read_u32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x0800 int"
                return info
            info["int_0x0800"] = value

        if flexible_mask & 0x1000:
            value = read_u32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x1000 int"
                return info
            info["int_0x1000"] = value

        if flexible_mask & 0x2000:
            value = read_f32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x2000 float"
                return info
            info["float_0x2000"] = value

        if flexible_mask & 0x4000:
            value = read_u16()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x4000 u16"
                return info
            info["short_0x4000"] = value

        if flexible_mask & 0x8000:
            value = read_f32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x8000 float"
                return info
            info["float_0x8000"] = value

        if flexible_mask & 0x10000:
            value = read_u16()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x10000 u16"
                return info
            info["short_0x10000"] = value

        if flexible_mask & 0x20000:
            value = read_f32()
            if value is None:
                info["flexible_parse_error"] = "truncated 0x20000 float"
                return info
            info["float_0x20000"] = value

        unknown_mask = flexible_mask & ~0x3FFBE
        if unknown_mask:
            info["unknown_flexible_mask_bits"] = unknown_mask

        return info

    def _parse_new_stroke_object(
        self,
        layer: Dict[str, object],
        obj: Dict[str, object],
        string_id_map: Dict[int, str],
    ) -> Optional[Dict[str, object]]:
        stroke_subrecord = next((record for record in obj["subrecords"] if record["type"] == 1), None)
        if stroke_subrecord is None:
            return None

        start = int(stroke_subrecord["start"])
        end = int(stroke_subrecord["end"])
        if start + 20 > end or not self._can_read(start, 20):
            return None

        flexible_offset = self._u32(start + 6)
        property_mask1_length = self._u8(start + 10)
        property_mask1 = self._read_var_uint(start + 11, property_mask1_length, end)
        if property_mask1 is None:
            return None

        mask2_length_offset = start + 11 + property_mask1_length
        if mask2_length_offset + 1 > end or not self._can_read(mask2_length_offset, 1):
            return None
        property_mask2_length = self._u8(mask2_length_offset)
        property_mask2 = self._read_var_uint(mask2_length_offset + 1, property_mask2_length, end)
        if property_mask2 is None:
            return None

        cursor = mask2_length_offset + 1 + property_mask2_length
        if cursor + 2 > end or not self._can_read(cursor, 2):
            return None
        point_count = self._u16(cursor)
        cursor += 2

        geometry: Optional[Tuple[List[Point], Dict[str, object], int, int]]
        if property_mask1 & 0x0001:
            geometry = self._parse_new_stroke_compact_geometry(
                cursor,
                end,
                point_count,
                bool(property_mask1 & 0x0004),
            )
        else:
            geometry = self._parse_new_stroke_raw_geometry(
                cursor,
                end,
                point_count,
                bool(property_mask1 & 0x0004),
            )
        if geometry is None:
            return None

        points, stroke_dynamics, geometry_end, tail_value = geometry
        flexible_info = self._parse_new_stroke_flexible_data(
            start,
            end,
            flexible_offset,
            property_mask2,
            string_id_map,
        )

        direct_color = flexible_info.get("color_int")
        color_int = int(direct_color) if isinstance(direct_color, int) else 0xFF000000
        direct_pen_size = flexible_info.get("pen_size")
        pen_size = float(direct_pen_size) if isinstance(direct_pen_size, (int, float)) else 2.0
        uses_preset_color_fallback = direct_color is None and bool(property_mask2 & 0x0082)

        style: Dict[str, object] = {
            "source": "object-stroke-new",
            "property_mask_1": property_mask1,
            "property_mask_2": property_mask2,
            "pen_name_id": flexible_info.get("pen_name_id"),
            "pen_name": flexible_info.get("pen_name"),
            "advanced_setting_id": flexible_info.get("advanced_setting_id"),
            "advanced_setting": flexible_info.get("advanced_setting"),
        }
        for key in (
            "float_0x0100",
            "int_0x0200",
            "int_0x0400",
            "int_0x0800",
            "int_0x1000",
            "float_0x2000",
            "short_0x4000",
            "float_0x8000",
            "short_0x10000",
            "float_0x20000",
            "has_unsupported_flexible_bit_0x20",
            "unknown_flexible_mask_bits",
            "flexible_parse_error",
        ):
            if key in flexible_info:
                style[key] = flexible_info[key]

        return {
            "start": obj["start"],
            "end": obj["record_end"],
            "object_start": obj["start"],
            "subrecord_start": start,
            "subrecord_end": end,
            "point_count": point_count,
            "points": points,
            "pressures": stroke_dynamics.get("pressures", []),
            "timestamps": stroke_dynamics.get("timestamps", []),
            "tilts": stroke_dynamics.get("tilts", []),
            "orientations": stroke_dynamics.get("orientations", []),
            "stroke_dynamics": stroke_dynamics,
            "style": style,
            "color_int": color_int,
            "color_hex_argb": f"0x{color_int:08X}",
            "rgba": self._argb_to_rgba(color_int),
            "color_source": "direct" if direct_color is not None else "default_black",
            "uses_preset_color_fallback": uses_preset_color_fallback,
            "pen_size": pen_size,
            "pen_size_source": "direct" if direct_pen_size is not None else "default",
            "style_offset": flexible_info.get("style_offset"),
            "layer_number": layer["layer_number"],
            "geometry_end": geometry_end,
            "tail_value": tail_value,
            "pen_name": flexible_info.get("pen_name"),
            "advanced_setting": flexible_info.get("advanced_setting"),
        }

    def _extract_object_stroke_records(self) -> List[Dict[str, object]]:
        string_id_map = self._load_string_id_map()
        records: List[Dict[str, object]] = []
        stroke_object_count = 0

        for layer in self._parse_layers():
            for obj in self._iter_flat_objects(layer["objects"]):
                if obj["object_type"] not in (1, 15):
                    continue
                stroke_object_count += 1
                record = self._parse_new_stroke_object(layer, obj, string_id_map)
                if record is not None:
                    records.append(record)

        if stroke_object_count == 0:
            return []
        if len(records) * 2 < stroke_object_count:
            return []
        return records

    def _looks_like_stroke(self, pos: int) -> bool:
        if pos + 18 > len(self.data):
            return False

        point_count = struct.unpack_from("<H", self.data, pos)[0]
        if not 1 < point_count < 10000:
            return False

        bx, by = struct.unpack_from("<dd", self.data, pos + 2)
        if not (1.0 < bx < 2400 and 1.0 < by < 2400):
            return False

        end_pos = pos + 18 + (point_count - 1) * 4
        return end_pos <= len(self.data)

    def _extract_geometry_records(self) -> List[Dict[str, object]]:
        strokes: List[Dict[str, object]] = []
        if len(self.data) < 128:
            return strokes

        metadata = self.extract_page_metadata()
        start_offset = int(metadata.get("layer_offset") or 0)
        pos = start_offset

        while pos < len(self.data) - 40:
            if not self._looks_like_stroke(pos):
                pos += 2
                continue

            point_count = struct.unpack_from("<H", self.data, pos)[0]
            curr_x, curr_y = struct.unpack_from("<dd", self.data, pos + 2)
            points: List[Point] = [(curr_x, curr_y)]
            delta_pos = pos + 18

            try:
                for _ in range(point_count - 1):
                    dx = self.unpack_coord_delta(struct.unpack_from("<H", self.data, delta_pos)[0])
                    dy = self.unpack_coord_delta(struct.unpack_from("<H", self.data, delta_pos + 2)[0])
                    curr_x += dx
                    curr_y += dy
                    points.append((curr_x, curr_y))
                    delta_pos += 4
            except struct.error:
                pos += 2
                continue

            strokes.append(
                {
                    "start": pos,
                    "end": delta_pos,
                    "point_count": point_count,
                    "points": points,
                }
            )
            pos = delta_pos

        return strokes

    def _argb_to_rgba(self, color_int: int) -> Tuple[float, float, float, float]:
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

    def _normalize_stroke_record(self, stroke: Dict[str, object]) -> Dict[str, object]:
        color_value = stroke.get("color_int")
        color_int = int(color_value) if isinstance(color_value, int) else 0xFF000000
        stroke["color_int"] = color_int
        stroke["color_hex_argb"] = str(stroke.get("color_hex_argb") or f"0x{color_int:08X}")

        rgba = stroke.get("rgba")
        if not isinstance(rgba, tuple) or len(rgba) != 4:
            stroke["rgba"] = self._argb_to_rgba(color_int)

        pen_size = stroke.get("pen_size")
        stroke["pen_size"] = float(pen_size) if isinstance(pen_size, (int, float)) else 2.0
        stroke.setdefault("style", None)
        stroke.setdefault("style_offset", None)
        stroke.setdefault("layer_number", 0)
        for dynamic_key in ("pressures", "timestamps", "tilts", "orientations"):
            if not isinstance(stroke.get(dynamic_key), list):
                stroke[dynamic_key] = []
        stroke.setdefault("stroke_dynamics", {})
        return stroke

    def _scan_style_records(self) -> List[Dict[str, object]]:
        styles: List[Dict[str, object]] = []
        min_size = 2 + 4 + 4 + 4 + 4 + 4 + 4 + 4 + 32

        for pos in range(0, len(self.data) - min_size + 1):
            record_id = struct.unpack_from("<H", self.data, pos)[0]
            if not 0 < record_id < 32:
                continue

            style_variant = struct.unpack_from("<I", self.data, pos + 2)[0]
            if style_variant not in (1, 3, 5):
                continue

            color_int = struct.unpack_from("<I", self.data, pos + 6)[0]
            thickness = struct.unpack_from("<f", self.data, pos + 10)[0]
            reserved = struct.unpack_from("<I", self.data, pos + 14)[0]
            if not 0.01 <= thickness <= 200.0:
                continue

            if style_variant in (1, 5):
                repeated_thickness = struct.unpack_from("<f", self.data, pos + 18)[0]
                repeated_constant = struct.unpack_from("<I", self.data, pos + 22)[0]
                secondary_value = struct.unpack_from("<f", self.data, pos + 26)[0]

                if reserved not in (0, 4) or repeated_constant != 1:
                    continue
                if abs(repeated_thickness - thickness) > 1e-4:
                    continue
                if not 0.0 <= secondary_value <= 200.0:
                    continue

                opaque_blob_start = pos + 30
            elif style_variant == 3:
                repeated_thickness = None
                repeated_constant = struct.unpack_from("<I", self.data, pos + 18)[0]
                secondary_value = struct.unpack_from("<f", self.data, pos + 22)[0]

                if reserved != 2 or repeated_constant != 1:
                    continue
                if not 0.0 <= secondary_value <= 200.0:
                    continue

                opaque_blob_start = pos + 26
            else:
                continue

            styles.append(
                {
                    "pos": pos,
                    "record_id": record_id,
                    "style_variant": style_variant,
                    "color_int": color_int,
                    "color_hex_argb": f"0x{color_int:08X}",
                    "bgra_bytes": self.data[pos + 6 : pos + 10].hex(),
                    "rgba": self._argb_to_rgba(color_int),
                    "thickness": thickness,
                    "reserved": reserved,
                    "repeated_thickness": repeated_thickness,
                    "repeated_constant": repeated_constant,
                    "secondary_value": secondary_value,
                    "opaque_blob": self.data[opaque_blob_start : opaque_blob_start + 32].hex(),
                }
            )

        return styles

    def extract_stroke_records(self) -> List[Dict[str, object]]:
        object_strokes = self._extract_object_stroke_records()
        if object_strokes:
            return [self._normalize_stroke_record(stroke) for stroke in object_strokes]

        strokes = self._extract_geometry_records()
        styles = self._scan_style_records()

        style_index = 0
        for stroke in strokes:
            while style_index < len(styles) and styles[style_index]["pos"] < stroke["end"]:
                style_index += 1

            style = styles[style_index] if style_index < len(styles) else None
            if style is not None:
                style_index += 1

            stroke["style"] = style
            stroke["color_int"] = style["color_int"] if style else 0xFF000000
            stroke["color_hex_argb"] = style["color_hex_argb"] if style else "0xFF000000"
            stroke["rgba"] = style["rgba"] if style else (0.0, 0.0, 0.0, 1.0)
            stroke["pen_size"] = float(style["thickness"]) if style else 2.0
            stroke["style_offset"] = style["pos"] if style else None

        return [self._normalize_stroke_record(stroke) for stroke in strokes]

    def extract_strokes(self) -> List[List[Point]]:
        return [stroke["points"] for stroke in self.extract_stroke_records()]

    def _parse_page_properties(
        self,
        property_offset: int,
        property_mask: int,
        format_version: int = 0,
    ) -> Tuple[Dict[str, object], int]:
        properties: Dict[str, object] = {}
        pos = property_offset

        if not self._can_read(pos, 0):
            return properties, pos

        if property_mask & 0x00000001 and self._can_read(pos, 32):
            properties["drawn_rect"] = self._rectd(pos)
            pos += 32

        if property_mask & 0x00000002 and self._can_read(pos, 2):
            tag_count = self._u16(pos)
            pos += 2
            tags: List[str] = []
            for _ in range(tag_count):
                tag, pos = self._read_utf16_string(self.data, pos)
                if tag:
                    tags.append(tag)
            properties["tags"] = tags

        if property_mask & 0x00000004:
            template_uri, pos = self._read_utf16_string(self.data, pos)
            if template_uri:
                properties["template_uri"] = template_uri

        if property_mask & 0x00000008 and self._can_read(pos, 4):
            properties["bg_image_id"] = self._u32(pos)
            pos += 4

        if property_mask & 0x00000010 and self._can_read(pos, 4):
            properties["bg_image_mode"] = self._u32(pos)
            pos += 4

        if property_mask & 0x00000020 and self._can_read(pos, 4):
            color_int = self._u32(pos)
            properties["background_color_int"] = color_int
            properties["background_color_argb"] = f"0x{color_int:08X}"
            pos += 4

        if property_mask & 0x00000040 and self._can_read(pos, 4):
            properties["bg_width"] = self._u32(pos)
            pos += 4

        if property_mask & 0x00000080 and self._can_read(pos, 4):
            properties["bg_rotation"] = self._u32(pos)
            pos += 4

        if property_mask & 0x00000100 and self._can_read(pos, 2):
            pdf_data_count = self._u16(pos)
            pos += 2
            pdf_data_list: List[Dict[str, object]] = []
            for _ in range(pdf_data_count):
                if not self._can_read(pos, 24):
                    break
                rect_kind = "rectf" if format_version and format_version < 2034 else "recti"
                pdf_data_list.append(
                    {
                        "file_id": self._i32(pos),
                        "page_index": self._i32(pos + 4),
                        "rect": rect_f32(self.data, pos + 8) if rect_kind == "rectf" else self._recti(pos + 8),
                        "rect_kind": rect_kind,
                    }
                )
                pos += 24
            properties["pdf_data_list"] = pdf_data_list
            properties["pdf_data_count"] = len(pdf_data_list)

        if property_mask & 0x00000200 and self._can_read(pos, 4):
            properties["template_type"] = self._u32(pos)
            pos += 4

        if property_mask & 0x00000400 and self._can_read(pos, 6):
            canvas_cache_entry_count = self._u32(pos)
            pos += 4
            canvas_cache_record_size = self._u16(pos)
            pos += 2
            canvas_cache_entries: List[Dict[str, object]] = []
            for _ in range(canvas_cache_entry_count):
                if canvas_cache_record_size < 49 or not self._can_read(pos, canvas_cache_record_size):
                    break
                payload_pos = pos + 4
                canvas_cache_entries.append(
                    {
                        "key": self._u32(pos),
                        "file_id": self._u32(payload_pos),
                        "width": self._u32(payload_pos + 4),
                        "height": self._u32(payload_pos + 8),
                        "is_dark_mode": bool(self._u8(payload_pos + 12)),
                        "background_color_int": self._u32(payload_pos + 13),
                        "version0": self._u32(payload_pos + 17),
                        "version1": self._u32(payload_pos + 21),
                        "version2": self._u32(payload_pos + 25),
                        "cache_version": self._u32(payload_pos + 29),
                        "property": self._u32(payload_pos + 33),
                        "locale_list_id": self._u32(payload_pos + 37),
                        "system_font_path_hash": self._u32(payload_pos + 41),
                    }
                )
                pos += canvas_cache_record_size
            properties["canvas_cache_record_size"] = canvas_cache_record_size
            properties["canvas_cache_entries"] = canvas_cache_entries

        if property_mask & 0x00000800 and self._can_read(pos, 4):
            properties["imported_data_height"] = self._u32(pos)
            pos += 4

        if property_mask & 0x00001000 and self._can_read(pos, 4):
            properties["reserved_0x1000"] = self._u32(pos)
            pos += 4

        if property_mask & 0x00040000 and self._can_read(pos, 4):
            custom_object_count = self._u32(pos)
            pos += 4
            custom_objects: List[Dict[str, object]] = []
            for _ in range(custom_object_count):
                if not self._can_read(pos, 8):
                    break
                object_type = self._u32(pos)
                payload_size = self._u32(pos + 4)
                pos += 8
                payload_end = pos + payload_size
                if payload_end > len(self.data):
                    break

                custom_object = self._parse_custom_object_payload(object_type, pos, payload_end)
                if custom_object is not None:
                    custom_objects.append(custom_object)
                pos = payload_end
            properties["custom_objects"] = custom_objects

        return properties, pos

    def _parse_custom_object_payload(
        self,
        object_type: int,
        payload_start: int,
        payload_end: int,
    ) -> Optional[Dict[str, object]]:
        cursor = payload_start
        if cursor + 9 > payload_end:
            return None

        prefix_u32 = self._u32(cursor)
        cursor += 4
        prefix_bytes = self.data[cursor : cursor + 3]
        cursor += 3
        prefix_short = self._u16(cursor)
        cursor += 2

        uuid, cursor = read_utf8_u16_bytes(self.data, cursor, trim_at_nul=True, max_chars=36)
        if cursor + 4 > payload_end or not self._can_read(cursor, 4):
            return None

        attached_file_count = self._u32(cursor)
        cursor += 4
        attached_files: Dict[str, int] = {}
        for _ in range(attached_file_count):
            key, cursor = read_counted_utf8(self.data, cursor)
            if cursor + 4 > payload_end or not self._can_read(cursor, 4):
                return None
            bind_id = self._u32(cursor)
            cursor += 4
            if key:
                attached_files[key] = bind_id

        if cursor + 4 > payload_end or not self._can_read(cursor, 4):
            return None
        custom_data_count = self._u32(cursor)
        cursor += 4
        custom_data: Dict[str, str] = {}
        for _ in range(custom_data_count):
            key, cursor = read_counted_utf8(self.data, cursor)
            value, cursor = read_counted_utf8(self.data, cursor)
            if cursor > payload_end:
                return None
            if key:
                custom_data[key] = value

        if cursor + 32 > payload_end or not self._can_read(cursor, 32):
            return None
        rect = self._rectd(cursor)

        return {
            "type": object_type,
            "uuid": uuid,
            "attached_files": attached_files,
            "custom_data": custom_data,
            "rect": rect,
            "prefix_u32": prefix_u32,
            "prefix_bytes": prefix_bytes.hex(),
            "prefix_short": prefix_short,
        }

    def extract_page_metadata(self) -> Dict[str, object]:
        if self._page_metadata is not None:
            return self._page_metadata

        raw_layer_offset = self._u32(0) if self._can_read(0, 4) else 0
        metadata: Dict[str, object] = {
            "raw_layer_offset": raw_layer_offset,
            "layer_offset": raw_layer_offset,
            "property_offset": self._u32(4) if self._can_read(4, 4) else 0,
            "text_only_flag": self._u32(9) if self._can_read(9, 4) else 0,
            "page_property_mask": self._u32(0x0E) if self._can_read(0x0E, 4) else 0,
            "file_size": len(self.data),
        }

        if self._can_read(0x12, 20):
            metadata["note_orientation"] = self._u32(0x12)
            metadata["page_width"] = self._u32(0x16)
            metadata["page_height"] = self._u32(0x1A)
            metadata["offset_x"] = self._u32(0x1E)
            metadata["offset_y"] = self._u32(0x22)

        if self._can_read(0x26, 2):
            uuid_length = self._u16(0x26)
            uuid_end = 0x28 + uuid_length * 2
            if uuid_end <= len(self.data):
                metadata["page_uuid_length"] = uuid_length
                metadata["page_uuid"] = self.data[0x28:uuid_end].decode("utf-16le", errors="replace")
                cursor = uuid_end
                if self._can_read(cursor, 8):
                    metadata["modified_time_raw"] = self._u64(cursor)
                    cursor += 8
                if self._can_read(cursor, 4):
                    metadata["format_version"] = self._u32(cursor)
                    cursor += 4
                if self._can_read(cursor, 4):
                    metadata["min_format_version"] = self._u32(cursor)

        properties, property_end_offset = self._parse_page_properties(
            int(metadata["property_offset"]),
            int(metadata["page_property_mask"]),
            int(metadata.get("format_version") or 0),
        )
        metadata.update(properties)
        metadata["property_end_offset"] = property_end_offset
        metadata["layer_offset"], metadata["layer_offset_reason"] = self._resolve_layer_offset(metadata)
        self._page_metadata = metadata
        return metadata

    def _parse_layers_from_offset(self, layer_offset: int) -> Optional[List[Dict[str, object]]]:
        if not self._can_read(layer_offset, 4):
            return None

        layer_count = self._u16(layer_offset)
        current_layer_index = self._u16(layer_offset + 2)
        if not 1 <= layer_count <= 64:
            return None
        if current_layer_index >= layer_count:
            return None

        layers: List[Dict[str, object]] = []
        pos = layer_offset + 4

        for layer_index in range(layer_count):
            if not self._can_read(pos, 16):
                return None

            layer_start = pos
            header_size = self._u32(pos)
            metadata_offset_abs = self._u32(pos + 4)
            flags_1 = self._u8(pos + 9)
            flags_2 = self._u8(pos + 11)
            layer_number = self._u32(pos + 12)
            if header_size < 16 or header_size > 0x4000:
                return None
            if metadata_offset_abs >= len(self.data):
                return None

            object_count_pos = layer_start + header_size
            if not self._can_read(object_count_pos, 4):
                return None

            object_count = self._u32(object_count_pos)
            if object_count > 4096:
                return None

            cursor = object_count_pos + 4
            objects: List[Dict[str, object]] = []
            for _ in range(object_count):
                obj, next_cursor = self._parse_object_record(cursor)
                if obj is None or next_cursor <= cursor:
                    return None
                objects.append(obj)
                cursor = next_cursor

            layer_end = cursor + 32 if self._can_read(cursor, 32) else cursor
            if layer_end <= layer_start:
                return None

            layers.append(
                {
                    "index": layer_index,
                    "current_layer_index": current_layer_index,
                    "start": layer_start,
                    "header_size": header_size,
                    "metadata_offset_abs": metadata_offset_abs,
                    "flags_1": flags_1,
                    "flags_2": flags_2,
                    "layer_number": layer_number,
                    "object_count": object_count,
                    "objects": objects,
                }
            )
            pos = layer_end

        return layers

    def _resolve_layer_offset(self, metadata: Dict[str, object]) -> Tuple[int, str]:
        if self._resolved_layers is not None:
            return int(metadata.get("layer_offset") or 0), str(metadata.get("layer_offset_reason") or "cached")

        raw_layer_offset = int(metadata.get("raw_layer_offset") or 0)
        property_offset = int(metadata.get("property_offset") or 0)
        property_end_offset = int(metadata.get("property_end_offset") or 0)

        candidate_offsets: List[Tuple[int, str]] = []
        if raw_layer_offset > 0:
            candidate_offsets.append((raw_layer_offset, "header field"))
        if property_end_offset > 0:
            # Some synced/exported pages replace the classic footer with an opaque
            # 60-byte trailer and repoint the first header field at that trailer.
            # In those cases the real layer section still begins right after the
            # parsed page-property block, so we keep that as the first fallback.
            candidate_offsets.append((property_end_offset, "after page properties"))

        scan_start = max(property_offset, property_end_offset)
        scan_end = min(len(self.data), scan_start + 1024)
        for candidate in range(scan_start, scan_end, 4):
            candidate_offsets.append((candidate, "scanned after page properties"))

        seen_offsets = set()
        for candidate, reason in candidate_offsets:
            if candidate in seen_offsets or candidate < 0:
                continue
            seen_offsets.add(candidate)
            layers = self._parse_layers_from_offset(candidate)
            if layers is None:
                continue

            self._resolved_layers = layers
            return candidate, reason

        self._resolved_layers = []
        if raw_layer_offset > 0 and self._can_read(raw_layer_offset, 4):
            return raw_layer_offset, "header field (unvalidated)"
        if property_end_offset > 0 and self._can_read(property_end_offset, 4):
            return property_end_offset, "after page properties (unvalidated)"
        return 0, "unresolved"

    def _load_media_index(self) -> Dict[int, Dict[str, object]]:
        if self._media_index is not None:
            return self._media_index

        media_index: Dict[int, Dict[str, object]] = {}
        media_info_path = os.path.join(self.note_root, "media", "mediaInfo.dat")
        if not os.path.exists(media_info_path):
            self._media_index = media_index
            return media_index

        with open(media_info_path, "rb") as f:
            media_data = f.read()

        media_info = parse_media_info(media_data)
        format_version = int(media_info.get("format_version") or 0)
        for entry in media_info.get("entries", []):
            if not isinstance(entry, dict):
                continue
            bind_id = int(entry.get("bind_id") or 0)
            filename = str(entry.get("filename") or "")
            media_path = os.path.join(self.note_root, "media", filename) if filename else None
            media_entry = {
                "bind_id": bind_id,
                "filename": filename,
                "file_hash": str(entry.get("file_hash") or ""),
                "ref_count": int(entry.get("ref_count") or 0),
                "modified_time": int(entry.get("modified_time") or 0),
                "is_file_attached": bool(entry.get("is_file_attached")),
                "path": media_path,
                "format_version": format_version,
            }
            if filename.lower().endswith(".spi") and media_path and os.path.exists(media_path):
                try:
                    media_entry["spi_info"] = parse_spi_file(media_path)
                except OSError as exc:
                    media_entry["spi_info"] = {"parse_error": str(exc)}
            media_index[bind_id] = media_entry

        self._media_index = media_index
        return media_index

    def _parse_subrecords(self, payload_start: int, payload_end: int) -> List[Dict[str, int]]:
        subrecords: List[Dict[str, int]] = []
        pos = payload_start

        while pos + 6 <= payload_end:
            size = self._u32(pos)
            subrecord_type = self._u16(pos + 4)
            if size <= 0 or pos + size > payload_end:
                break

            subrecords.append(
                {
                    "type": subrecord_type,
                    "start": pos,
                    "size": size,
                    "end": pos + size,
                }
            )
            pos += size

        return subrecords

    def _parse_object_record(self, pos: int) -> Tuple[Optional[Dict[str, object]], int]:
        if not self._can_read(pos, 7):
            return None, pos

        object_type = self._u8(pos)
        child_count = self._u16(pos + 1)
        object_size = self._u32(pos + 3)
        if object_size < 32:
            return None, pos

        payload_start = pos + 7
        payload_end = payload_start + object_size - 32
        record_end = payload_start + object_size
        if payload_end < payload_start or record_end > len(self.data):
            return None, pos

        obj: Dict[str, object] = {
            "start": pos,
            "object_type": object_type,
            "child_count": child_count,
            "object_size": object_size,
            "payload_start": payload_start,
            "payload_end": payload_end,
            "record_end": record_end,
            "subrecords": self._parse_subrecords(payload_start, payload_end),
            "children": [],
        }

        cursor = record_end
        children: List[Dict[str, object]] = []
        for _ in range(child_count):
            child, next_cursor = self._parse_object_record(cursor)
            if child is None or next_cursor <= cursor:
                break
            children.append(child)
            cursor = next_cursor

        obj["children"] = children
        return obj, cursor

    def _parse_layers(self) -> List[Dict[str, object]]:
        metadata = self.extract_page_metadata()
        if self._resolved_layers is not None:
            return self._resolved_layers

        layer_offset = int(metadata.get("layer_offset") or 0)
        layers = self._parse_layers_from_offset(layer_offset)
        self._resolved_layers = layers or []
        return self._resolved_layers

    def _iter_flat_objects(self, objects: Iterable[Dict[str, object]]) -> Iterable[Dict[str, object]]:
        for obj in objects:
            yield obj
            yield from self._iter_flat_objects(obj.get("children", []))

    def _parse_shape_image_info(self, subrecord: Dict[str, int]) -> Dict[str, object]:
        start = subrecord["start"]
        end = subrecord["end"]
        if start + 57 > end:
            return {}

        shape_info: Dict[str, object] = {
            "shape_type": self._u32(start + 17) if self._can_read(start + 17, 4) else None,
            "original_rect": self._rectd(start + 21) if self._can_read(start + 21, 32) else None,
            "own_offset": self._u32(start + 6) if self._can_read(start + 6, 4) else 0,
            "shape_property_mask": self._u32(start + 13) if self._can_read(start + 13, 4) else 0,
        }

        own_offset = int(shape_info["own_offset"])
        shape_property_mask = int(shape_info["shape_property_mask"])
        if own_offset <= 0 or start + own_offset >= end or (shape_property_mask & 0x20) == 0:
            return shape_info

        # The known image samples write the fill-image effect first inside the own-data block.
        # There can be optional small fields before it, so skip the simple fixed-width ones.
        cursor = start + own_offset
        if shape_property_mask & 0x01:
            return shape_info
        if shape_property_mask & 0x02:
            cursor += 1
        if shape_property_mask & 0x04:
            cursor += 4
        if shape_property_mask & 0x08:
            cursor += 4
        if shape_property_mask & 0x10:
            cursor += 4

        if cursor + 10 > end:
            return shape_info

        block_size = self._u32(cursor)
        effect_type = self._u8(cursor + 4)
        if block_size < 6 or cursor + 5 + block_size > end or effect_type != 2:
            return shape_info

        shape_info.update(
            {
                "fill_effect_start": cursor,
                "fill_effect_size": block_size,
                "fill_effect_type": effect_type,
                "image_type": self._u8(cursor + 5),
                "image_bind_id": self._u32(cursor + 6),
            }
        )
        return shape_info

    def _parse_image_layout_info(self, subrecord: Dict[str, int]) -> Dict[str, object]:
        start = subrecord["start"]
        end = subrecord["end"]
        if start + 10 > end:
            return {}

        own_offset = self._u32(start + 6) if self._can_read(start + 6, 4) else 0
        if own_offset <= 0:
            return {}

        cursor = start + own_offset
        if cursor + 14 > end:
            return {}

        block_size = self._u32(cursor)
        if block_size < 14 or cursor + 4 + block_size > end:
            return {}

        layout_type = self._u32(cursor + 6)
        if layout_type > IMAGE_LAYOUT_USE_DEFAULT:
            return {
                "own_offset": own_offset,
                "block_size": block_size,
                "raw_layout_type": layout_type,
            }

        # Partial decode: the image object's common type-6 own block stores at
        # least the object layout mode and alpha:
        #   1 = wrap around, 2 = wrap text behind, 3 = follow current default.
        return {
            "own_offset": own_offset,
            "block_size": block_size,
            "layout_type": layout_type,
            "alpha": self._u32(cursor + 10),
        }

    def _parse_image_own_info(self, subrecord: Dict[str, int]) -> Dict[str, object]:
        start = subrecord["start"]
        end = subrecord["end"]
        if start + 17 > end:
            return {}

        group1_flags = self._u8(start + 13) if self._can_read(start + 13, 1) else 0
        group2_flags = self._u8(start + 14) if self._can_read(start + 14, 1) else 0
        group3_flags = self._u8(start + 15) if self._can_read(start + 15, 1) else 0
        info: Dict[str, object] = {
            "group1_flags": group1_flags,
            "group2_flags": group2_flags,
            "group3_flags": group3_flags,
        }

        flexible_payload_present = bool(self._u8(start + 6)) if self._can_read(start + 6, 1) else False
        if not flexible_payload_present:
            return info

        # The image-own payload is a flexible flag-ordered structure. Only decode
        # confirmed field groups that affect rendering; unknown flags keep the
        # payload opaque.
        unsupported_group1 = group1_flags & ~0x3A
        unsupported_group2 = group2_flags & ~0x1E
        unsupported_group3 = group3_flags & ~0x0E
        if unsupported_group1 or unsupported_group2 or unsupported_group3:
            info["has_unsupported_flags"] = True
            return info

        cursor = start + 17

        def skip(size: int) -> bool:
            nonlocal cursor
            if cursor + size > end:
                return False
            cursor += size
            return True

        if group1_flags & 0x02:
            if cursor + 16 > end:
                return info
            info["crop_rect"] = self._recti(cursor)
            cursor += 16
        if group1_flags & 0x08 and not skip(4):
            return info
        if group1_flags & 0x10 and not skip(4):
            return info
        if group1_flags & 0x20 and not skip(2):
            return info

        if group2_flags & 0x02 and not skip(4):
            return info
        if group2_flags & 0x04 and not skip(16):
            return info
        if group2_flags & 0x08 and not skip(16):
            return info
        if group2_flags & 0x10 and not skip(4):
            return info

        if group3_flags & 0x02:
            if cursor + 32 > end:
                return info
            info["original_rect"] = self._rectd(cursor)
            cursor += 32
        if group3_flags & 0x04 and not skip(4):
            return info

        return info

    def extract_image_records(self) -> List[Dict[str, object]]:
        media_index = self._load_media_index()
        image_records: List[Dict[str, object]] = []

        for layer in self._parse_layers():
            for obj in self._iter_flat_objects(layer["objects"]):
                if obj["object_type"] != 3:
                    continue

                subrecords = obj["subrecords"]
                layout_subrecord = next((record for record in subrecords if record["type"] == 6), None)
                shape_subrecord = next((record for record in subrecords if record["type"] == 7), None)
                if shape_subrecord is None:
                    continue
                image_own_subrecord = next((record for record in subrecords if record["type"] == 3), None)

                layout_info = self._parse_image_layout_info(layout_subrecord) if layout_subrecord else {}
                shape_info = self._parse_shape_image_info(shape_subrecord)
                image_own_info = self._parse_image_own_info(image_own_subrecord) if image_own_subrecord else {}
                rect = shape_info.get("original_rect")
                image_bind_id = shape_info.get("image_bind_id")
                if rect is None or image_bind_id is None:
                    continue

                media_entry = media_index.get(int(image_bind_id))
                media_path = media_entry["path"] if media_entry else None
                image_records.append(
                    {
                        "object_start": obj["start"],
                        "layer_number": layer["layer_number"],
                        "shape_type": shape_info.get("shape_type"),
                        "rect": rect,
                        "bind_id": int(image_bind_id),
                        "layout_type": layout_info.get("layout_type"),
                        "layout_alpha": layout_info.get("alpha"),
                        "raw_layout_type": layout_info.get("raw_layout_type"),
                        "crop_rect": image_own_info.get("crop_rect"),
                        "image_own_original_rect": image_own_info.get("original_rect"),
                        "image_own_has_unsupported_flags": bool(image_own_info.get("has_unsupported_flags")),
                        "media_entry": media_entry,
                        "media_path": media_path if media_path and os.path.exists(media_path) else None,
                        "filename": media_entry["filename"] if media_entry else None,
                    }
                )

        return image_records

    def extract_background_records(self) -> List[Dict[str, object]]:
        metadata = self.extract_page_metadata()
        pdf_data_list = list(metadata.get("pdf_data_list") or [])
        if not pdf_data_list:
            return []

        media_index = self._load_media_index()
        canvas_cache_entries = list(metadata.get("canvas_cache_entries") or [])
        background_records: List[Dict[str, object]] = []

        for index, pdf_data in enumerate(pdf_data_list):
            rect = pdf_data.get("rect")
            if not isinstance(rect, tuple) or len(rect) != 4:
                continue

            raw_file_id = pdf_data.get("file_id")
            file_id = int(raw_file_id) if isinstance(raw_file_id, int) else -1
            media_entry = media_index.get(file_id)
            media_path = media_entry["path"] if media_entry else None
            cache_entry = canvas_cache_entries[index] if index < len(canvas_cache_entries) else None
            if isinstance(cache_entry, dict) and isinstance(cache_entry.get("file_id"), int):
                cache_file_id = int(cache_entry["file_id"])
            else:
                cache_file_id = -1
            cache_media_entry = media_index.get(cache_file_id) if cache_file_id >= 0 else None
            cache_media_path = cache_media_entry["path"] if cache_media_entry else None

            background_records.append(
                {
                    "background_type": "pdf",
                    "file_id": file_id,
                    "page_index": int(pdf_data.get("page_index") or 0),
                    "rect": tuple(float(value) for value in rect),
                    "media_entry": media_entry,
                    "media_path": media_path if media_path and os.path.exists(media_path) else None,
                    "filename": media_entry["filename"] if media_entry else None,
                    "cache_entry": cache_entry,
                    "cache_file_id": cache_file_id if cache_file_id >= 0 else None,
                    "cache_media_entry": cache_media_entry,
                    "cache_media_path": cache_media_path if cache_media_path and os.path.exists(cache_media_path) else None,
                    "cache_filename": cache_media_entry["filename"] if cache_media_entry else None,
                }
            )

        return background_records

    @staticmethod
    def _ks_string(value) -> str:
        return str(getattr(value, "value", "") or "")

    @staticmethod
    def _rect_from_generated(rect) -> Tuple[float, float, float, float]:
        return (
            float(rect.left),
            float(rect.top),
            float(rect.right),
            float(rect.bottom),
        )

    def _parse_custom_object_payload_bytes(self, object_type: int, payload: bytes) -> Optional[Dict[str, object]]:
        cursor = 0
        payload_end = len(payload)
        if cursor + 9 > payload_end:
            return None

        prefix_u32 = u32(payload, cursor)
        cursor += 4
        prefix_bytes = payload[cursor : cursor + 3]
        cursor += 3
        prefix_short = u16(payload, cursor)
        cursor += 2

        uuid, cursor = read_utf8_u16_bytes(payload, cursor, trim_at_nul=True, max_chars=36)
        if cursor + 4 > payload_end:
            return None

        attached_file_count = u32(payload, cursor)
        cursor += 4
        attached_files: Dict[str, int] = {}
        for _ in range(attached_file_count):
            key, cursor = read_counted_utf8(payload, cursor)
            if cursor + 4 > payload_end:
                return None
            bind_id = u32(payload, cursor)
            cursor += 4
            if key:
                attached_files[key] = bind_id

        if cursor + 4 > payload_end:
            return None
        custom_data_count = u32(payload, cursor)
        cursor += 4
        custom_data: Dict[str, str] = {}
        for _ in range(custom_data_count):
            key, cursor = read_counted_utf8(payload, cursor)
            value, cursor = read_counted_utf8(payload, cursor)
            if cursor > payload_end:
                return None
            if key:
                custom_data[key] = value

        if cursor + 32 > payload_end:
            return None
        rect = (
            f64(payload, cursor),
            f64(payload, cursor + 8),
            f64(payload, cursor + 16),
            f64(payload, cursor + 24),
        )

        return {
            "type": object_type,
            "uuid": uuid,
            "attached_files": attached_files,
            "custom_data": custom_data,
            "rect": rect,
            "prefix_u32": prefix_u32,
            "prefix_bytes": prefix_bytes.hex(),
            "prefix_short": prefix_short,
        }

    def _parse_page_properties(
        self,
        property_offset: int,
        property_mask: int,
        format_version: int = 0,
    ) -> Tuple[Dict[str, object], int]:
        properties: Dict[str, object] = {}
        if property_offset < 0 or property_offset > len(self.data):
            return properties, property_offset

        stream = KaitaiStream(BytesIO(self.data[property_offset:]))
        try:
            parsed = SamsungPage.PageProperties(int(property_mask), int(format_version), stream)
        except Exception:
            return properties, property_offset

        if hasattr(parsed, "drawn_rect"):
            properties["drawn_rect"] = self._rect_from_generated(parsed.drawn_rect)
        if hasattr(parsed, "tags"):
            tags = [self._ks_string(tag) for tag in parsed.tags.tags if self._ks_string(tag)]
            properties["tags"] = tags
        if hasattr(parsed, "template_uri") and self._ks_string(parsed.template_uri):
            properties["template_uri"] = self._ks_string(parsed.template_uri)
        for key in (
            "bg_image_id",
            "bg_image_mode",
            "bg_width",
            "bg_rotation",
            "template_type",
            "imported_data_height",
            "reserved_0x1000",
        ):
            if hasattr(parsed, key):
                properties[key] = int(getattr(parsed, key))
        if hasattr(parsed, "background_color_int"):
            color_int = int(parsed.background_color_int)
            properties["background_color_int"] = color_int
            properties["background_color_argb"] = f"0x{color_int:08X}"
        if hasattr(parsed, "pdf_data"):
            rect_kind = "rectf" if format_version and format_version < 2034 else "recti"
            pdf_data_list: List[Dict[str, object]] = []
            for entry in parsed.pdf_data.entries:
                rect = entry.rect_as_f32 if rect_kind == "rectf" else entry.rect_as_i32
                pdf_data_list.append(
                    {
                        "file_id": int(entry.file_id),
                        "page_index": int(entry.page_index),
                        "rect": self._rect_from_generated(rect),
                        "rect_kind": rect_kind,
                    }
                )
            properties["pdf_data_list"] = pdf_data_list
            properties["pdf_data_count"] = len(pdf_data_list)
        if hasattr(parsed, "canvas_cache"):
            canvas_cache_entries: List[Dict[str, object]] = []
            for entry in parsed.canvas_cache.entries:
                canvas_cache_entries.append(
                    {
                        "key": int(entry.key),
                        "file_id": int(entry.file_id),
                        "width": int(entry.width),
                        "height": int(entry.height),
                        "is_dark_mode": bool(entry.is_dark_mode),
                        "background_color_int": int(entry.background_color_int),
                        "version0": int(entry.version0),
                        "version1": int(entry.version1),
                        "version2": int(entry.version2),
                        "cache_version": int(entry.cache_version),
                        "property": int(entry.property),
                        "locale_list_id": int(entry.locale_list_id),
                        "system_font_path_hash": int(entry.system_font_path_hash),
                    }
                )
            properties["canvas_cache_record_size"] = int(parsed.canvas_cache.record_size)
            properties["canvas_cache_entries"] = canvas_cache_entries
        if hasattr(parsed, "custom_objects"):
            custom_objects: List[Dict[str, object]] = []
            for entry in parsed.custom_objects.entries:
                custom_object = self._parse_custom_object_payload_bytes(int(entry.object_type), bytes(entry.payload))
                if custom_object is not None:
                    custom_objects.append(custom_object)
            properties["custom_objects"] = custom_objects

        return properties, property_offset + stream.pos()

    def extract_page_metadata(self) -> Dict[str, object]:
        if self._page_metadata is not None:
            return self._page_metadata

        metadata: Dict[str, object] = {
            "file_size": len(self.data),
        }
        try:
            parsed = SamsungPage(KaitaiStream(BytesIO(self.data)))
        except Exception:
            self._page_metadata = metadata
            return metadata

        metadata.update(
            {
                "raw_layer_offset": int(parsed.raw_layer_offset),
                "layer_offset": int(parsed.raw_layer_offset),
                "property_offset": int(parsed.property_offset),
                "text_only_flag": int(parsed.text_only_flag),
                "page_property_mask": int(parsed.page_property_mask),
                "note_orientation": int(parsed.note_orientation),
                "page_width": int(parsed.page_width),
                "page_height": int(parsed.page_height),
                "offset_x": int(parsed.offset_x),
                "offset_y": int(parsed.offset_y),
                "page_uuid_length": int(parsed.page_uuid.len),
                "page_uuid": self._ks_string(parsed.page_uuid),
            }
        )
        if hasattr(parsed, "modified_time_raw"):
            metadata["modified_time_raw"] = int(parsed.modified_time_raw)
        if hasattr(parsed, "format_version"):
            metadata["format_version"] = int(parsed.format_version)
        if hasattr(parsed, "min_format_version"):
            metadata["min_format_version"] = int(parsed.min_format_version)

        properties, property_end_offset = self._parse_page_properties(
            int(metadata["property_offset"]),
            int(metadata["page_property_mask"]),
            int(metadata.get("format_version") or 0),
        )
        metadata.update(properties)
        metadata["property_end_offset"] = property_end_offset
        metadata["layer_offset"], metadata["layer_offset_reason"] = self._resolve_layer_offset(metadata)
        self._page_metadata = metadata
        return metadata

    def _convert_generated_object(self, generated_object, object_start: int) -> Tuple[Dict[str, object], int]:
        object_type = int(generated_object.object_type)
        child_count = int(generated_object.child_count)
        object_size = int(generated_object.object_size)
        payload_start = object_start + 7
        payload_end = payload_start + object_size - 32
        record_end = payload_start + object_size

        subrecords: List[Dict[str, object]] = []
        subrecord_pos = payload_start
        payload_bytes = bytes(generated_object.payload_bytes)
        relative_pos = 0
        while relative_pos + 6 <= len(payload_bytes):
            subrecord_stream = KaitaiStream(BytesIO(payload_bytes[relative_pos:]))
            try:
                subrecord = SamsungPageLayers.Subrecord(subrecord_stream, generated_object, generated_object._root)
            except Exception:
                break
            size = int(subrecord.size)
            if size <= 0 or relative_pos + size > len(payload_bytes):
                break
            subrecords.append(
                {
                    "type": int(subrecord.record_type),
                    "start": subrecord_pos,
                    "size": size,
                    "end": subrecord_pos + size,
                    "body": subrecord.body,
                    "raw_body": getattr(subrecord, "_raw_body", bytes(subrecord.body) if isinstance(subrecord.body, bytes) else b""),
                }
            )
            subrecord_pos += size
            relative_pos += size

        cursor = record_end
        children: List[Dict[str, object]] = []
        for child in generated_object.children:
            child_object, cursor = self._convert_generated_object(child, cursor)
            children.append(child_object)

        return (
            {
                "start": object_start,
                "object_type": object_type,
                "child_count": child_count,
                "object_size": object_size,
                "payload_start": payload_start,
                "payload_end": payload_end,
                "record_end": record_end,
                "subrecords": subrecords,
                "children": children,
            },
            cursor,
        )

    def _parse_layers_from_offset(self, layer_offset: int) -> Optional[List[Dict[str, object]]]:
        if layer_offset < 0 or not self._can_read(layer_offset, 4):
            return None

        try:
            parsed = SamsungPageLayers(KaitaiStream(BytesIO(self.data[layer_offset:])))
        except Exception:
            return None

        layer_count = int(parsed.layer_count)
        current_layer_index = int(parsed.current_layer_index)
        if not 1 <= layer_count <= 64 or current_layer_index >= layer_count:
            return None

        layers: List[Dict[str, object]] = []
        pos = layer_offset + 4
        for layer_index, generated_layer in enumerate(parsed.layers):
            layer_start = pos
            header_size = int(generated_layer.header_size)
            metadata_offset_abs = int(generated_layer.metadata_offset_abs)
            layer_number = int(generated_layer.layer_number)
            object_count = int(generated_layer.object_count)
            if header_size < 16 or header_size > 0x4000:
                return None
            if metadata_offset_abs >= len(self.data):
                return None
            if object_count > 4096:
                return None

            object_start = layer_start + header_size + 4
            objects: List[Dict[str, object]] = []
            cursor = object_start
            for generated_object in generated_layer.objects:
                obj, cursor = self._convert_generated_object(generated_object, cursor)
                objects.append(obj)

            layer_end = cursor + (32 if hasattr(generated_layer, "trailer") else 0)
            if layer_end <= layer_start:
                return None

            layers.append(
                {
                    "index": layer_index,
                    "current_layer_index": current_layer_index,
                    "start": layer_start,
                    "header_size": header_size,
                    "metadata_offset_abs": metadata_offset_abs,
                    "flags_1": int(generated_layer.flags_1),
                    "flags_2": int(generated_layer.flags_2),
                    "layer_number": layer_number,
                    "object_count": object_count,
                    "objects": objects,
                }
            )
            pos = layer_end

        return layers

    def _parse_new_stroke_object(
        self,
        layer: Dict[str, object],
        obj: Dict[str, object],
        string_id_map: Dict[int, str],
    ) -> Optional[Dict[str, object]]:
        stroke_subrecord = next((record for record in obj["subrecords"] if record["type"] == 1), None)
        if stroke_subrecord is None:
            return None

        start = int(stroke_subrecord["start"])
        end = int(stroke_subrecord["end"])
        generated_body = stroke_subrecord.get("body")
        if generated_body is None or not hasattr(generated_body, "flexible_offset"):
            return None

        flexible_offset = int(generated_body.flexible_offset)
        property_mask1_bytes = bytes(generated_body.property_mask1_bytes)
        property_mask2_bytes = bytes(generated_body.property_mask2_bytes)
        property_mask1 = int.from_bytes(property_mask1_bytes, "little", signed=False)
        property_mask2 = int.from_bytes(property_mask2_bytes, "little", signed=False)
        point_count = int(generated_body.point_count)
        cursor = start + 6 + 4 + 1 + len(property_mask1_bytes) + 1 + len(property_mask2_bytes) + 2

        geometry: Optional[Tuple[List[Point], Dict[str, object], int, int]]
        if property_mask1 & 0x0001:
            geometry = self._parse_new_stroke_compact_geometry(
                cursor,
                end,
                point_count,
                bool(property_mask1 & 0x0004),
            )
        else:
            geometry = self._parse_new_stroke_raw_geometry(
                cursor,
                end,
                point_count,
                bool(property_mask1 & 0x0004),
            )
        if geometry is None:
            return None

        points, stroke_dynamics, geometry_end, tail_value = geometry
        flexible_info = self._parse_new_stroke_flexible_data(
            start,
            end,
            flexible_offset,
            property_mask2,
            string_id_map,
        )

        direct_color = flexible_info.get("color_int")
        color_int = int(direct_color) if isinstance(direct_color, int) else 0xFF000000
        direct_pen_size = flexible_info.get("pen_size")
        pen_size = float(direct_pen_size) if isinstance(direct_pen_size, (int, float)) else 2.0
        uses_preset_color_fallback = direct_color is None and bool(property_mask2 & 0x0082)

        style: Dict[str, object] = {
            "source": "object-stroke-new",
            "property_mask_1": property_mask1,
            "property_mask_2": property_mask2,
            "pen_name_id": flexible_info.get("pen_name_id"),
            "pen_name": flexible_info.get("pen_name"),
            "advanced_setting_id": flexible_info.get("advanced_setting_id"),
            "advanced_setting": flexible_info.get("advanced_setting"),
        }
        for key in (
            "float_0x0100",
            "int_0x0200",
            "int_0x0400",
            "int_0x0800",
            "int_0x1000",
            "float_0x2000",
            "short_0x4000",
            "float_0x8000",
            "short_0x10000",
            "float_0x20000",
            "has_unsupported_flexible_bit_0x20",
            "unknown_flexible_mask_bits",
            "flexible_parse_error",
        ):
            if key in flexible_info:
                style[key] = flexible_info[key]

        return {
            "start": obj["start"],
            "end": obj["record_end"],
            "object_start": obj["start"],
            "subrecord_start": start,
            "subrecord_end": end,
            "point_count": point_count,
            "points": points,
            "pressures": stroke_dynamics.get("pressures", []),
            "timestamps": stroke_dynamics.get("timestamps", []),
            "tilts": stroke_dynamics.get("tilts", []),
            "orientations": stroke_dynamics.get("orientations", []),
            "stroke_dynamics": stroke_dynamics,
            "style": style,
            "color_int": color_int,
            "color_hex_argb": f"0x{color_int:08X}",
            "rgba": self._argb_to_rgba(color_int),
            "color_source": "direct" if direct_color is not None else "default_black",
            "uses_preset_color_fallback": uses_preset_color_fallback,
            "pen_size": pen_size,
            "pen_size_source": "direct" if direct_pen_size is not None else "default",
            "style_offset": flexible_info.get("style_offset"),
            "layer_number": layer["layer_number"],
            "geometry_end": geometry_end,
            "tail_value": tail_value,
            "pen_name": flexible_info.get("pen_name"),
            "advanced_setting": flexible_info.get("advanced_setting"),
        }

    def _parse_shape_image_info(self, subrecord: Dict[str, int]) -> Dict[str, object]:
        start = int(subrecord["start"])
        end = int(subrecord["end"])
        body = subrecord.get("body")
        if body is None or not hasattr(body, "shape_type"):
            return {}

        shape_info: Dict[str, object] = {
            "shape_type": int(body.shape_type),
            "original_rect": self._rect_from_generated(body.original_rect),
            "own_offset": int(body.own_offset),
            "shape_property_mask": int(body.shape_property_mask),
        }

        own_offset = int(shape_info["own_offset"])
        shape_property_mask = int(shape_info["shape_property_mask"])
        if own_offset <= 0 or start + own_offset >= end or (shape_property_mask & 0x20) == 0:
            return shape_info

        cursor = start + own_offset
        if shape_property_mask & 0x01:
            return shape_info
        if shape_property_mask & 0x02:
            cursor += 1
        if shape_property_mask & 0x04:
            cursor += 4
        if shape_property_mask & 0x08:
            cursor += 4
        if shape_property_mask & 0x10:
            cursor += 4

        if cursor + 10 > end:
            return shape_info

        block_size = self._u32(cursor)
        effect_type = self._u8(cursor + 4)
        if block_size < 6 or cursor + 5 + block_size > end or effect_type != 2:
            return shape_info

        shape_info.update(
            {
                "fill_effect_start": cursor,
                "fill_effect_size": block_size,
                "fill_effect_type": effect_type,
                "image_type": self._u8(cursor + 5),
                "image_bind_id": self._u32(cursor + 6),
            }
        )
        return shape_info

    def _parse_image_layout_info(self, subrecord: Dict[str, int]) -> Dict[str, object]:
        body = subrecord.get("body")
        if body is None or not hasattr(body, "own_offset"):
            return {}

        own_offset = int(body.own_offset)
        if own_offset <= 0:
            return {}

        try:
            own_block = body.own_block
        except Exception:
            return {}

        block_size = int(own_block.block_size)
        layout_type = int(own_block.layout_type)
        if block_size < 14:
            return {}
        if layout_type > IMAGE_LAYOUT_USE_DEFAULT:
            return {
                "own_offset": own_offset,
                "block_size": block_size,
                "raw_layout_type": layout_type,
            }
        return {
            "own_offset": own_offset,
            "block_size": block_size,
            "layout_type": layout_type,
            "alpha": int(own_block.alpha),
        }

    def _parse_image_own_info(self, subrecord: Dict[str, int]) -> Dict[str, object]:
        start = int(subrecord["start"])
        end = int(subrecord["end"])
        body = subrecord.get("body")
        if body is None or not hasattr(body, "group1_flags"):
            return {}

        group1_flags = int(body.group1_flags)
        group2_flags = int(body.group2_flags)
        group3_flags = int(body.group3_flags)
        info: Dict[str, object] = {
            "group1_flags": group1_flags,
            "group2_flags": group2_flags,
            "group3_flags": group3_flags,
        }

        if not bool(body.flexible_payload_present):
            return info

        unsupported_group1 = group1_flags & ~0x3A
        unsupported_group2 = group2_flags & ~0x1E
        unsupported_group3 = group3_flags & ~0x0E
        if unsupported_group1 or unsupported_group2 or unsupported_group3:
            info["has_unsupported_flags"] = True
            return info

        cursor = start + 17

        def skip(size: int) -> bool:
            nonlocal cursor
            if cursor + size > end:
                return False
            cursor += size
            return True

        if group1_flags & 0x02:
            if cursor + 16 > end:
                return info
            info["crop_rect"] = self._recti(cursor)
            cursor += 16
        if group1_flags & 0x08 and not skip(4):
            return info
        if group1_flags & 0x10 and not skip(4):
            return info
        if group1_flags & 0x20 and not skip(2):
            return info

        if group2_flags & 0x02 and not skip(4):
            return info
        if group2_flags & 0x04 and not skip(16):
            return info
        if group2_flags & 0x08 and not skip(16):
            return info
        if group2_flags & 0x10 and not skip(4):
            return info

        if group3_flags & 0x02:
            if cursor + 32 > end:
                return info
            info["original_rect"] = self._rectd(cursor)
            cursor += 32
        if group3_flags & 0x04 and not skip(4):
            return info

        return info


__all__ = ["SpenNotesPageParser"]

