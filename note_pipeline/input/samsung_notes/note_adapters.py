from __future__ import annotations

from typing import Dict, List, Optional

from note_pipeline.input.samsung_notes.constants import (
    PARAGRAPH_TYPE_ALIGN,
    PARAGRAPH_TYPE_BULLET,
    PARAGRAPH_TYPE_DIRECTION,
    PARAGRAPH_TYPE_INDENT,
    PARAGRAPH_TYPE_LINE_SPACING,
    PARAGRAPH_TYPE_PARSING_STATE,
    SPAN_TYPE_BACKGROUND,
    SPAN_TYPE_BOLD,
    SPAN_TYPE_FONT_NAME,
    SPAN_TYPE_FONT_SIZE,
    SPAN_TYPE_FOREGROUND,
    SPAN_TYPE_ITALIC,
    SPAN_TYPE_STRIKETHROUGH,
    SPAN_TYPE_UNDERLINE,
)
from note_pipeline.input.samsung_notes.generated import SamsungTextCommon
from note_pipeline.input.samsung_notes.source import SamsungBodyTextSource, SamsungNoteSource


def _ks_string(value) -> str:
    return str(getattr(value, "value", "") or "")


def _text_common_score(candidate: Dict[str, object]) -> int:
    text = str(candidate.get("text") or "")
    printable = sum(1 for char in text if not char.isspace())
    score = printable * 8
    score += len(candidate.get("spans", [])) * 20
    score += len(candidate.get("paragraphs", [])) * 10
    if any(char.isalpha() for char in text):
        score += 200
    margins = candidate.get("margins", (0.0, 0.0, 0.0, 0.0))
    if all(0.0 <= float(value) <= 256.0 for value in margins):
        score += 40
    return score


def pen_info_to_dict(pen_info, include_particle_size: bool) -> Dict[str, object]:
    color_int = int(pen_info.color_int)
    info: Dict[str, object] = {
        "name": _ks_string(pen_info.name),
        "size": float(pen_info.size),
        "color_int": color_int,
        "color_argb": f"0x{color_int:08X}",
        "is_curvable": int(pen_info.is_curvable) != 0,
        "advanced_setting": _ks_string(pen_info.advanced_setting),
        "is_eraser_enabled": int(pen_info.is_eraser_enabled) != 0,
        "size_level": int(pen_info.size_level),
        "particle_density": int(pen_info.particle_density),
        "particle_size": None,
        "is_fixed_width": None,
        "hsv": tuple(float(value) for value in pen_info.hsv),
        "color_ui_info": getattr(pen_info, "color_ui_info", None),
    }
    if include_particle_size:
        info["particle_size"] = float(getattr(pen_info, "particle_size", 0.0))
        info["is_fixed_width"] = int(getattr(pen_info, "is_fixed_width", 0)) != 0
    return info


def span_record_to_dict(record, text_length: int) -> Optional[Dict[str, object]]:
    payload_size = int(record.payload_size)
    body = record.body
    span_type = int(body.span_type)
    start = int(body.start)
    end = int(body.end)
    if start > end or end > text_length:
        return None

    extra = body.extra
    span: Dict[str, object] = {
        "type": span_type,
        "start": start,
        "end": end,
        "flag": int(body.expand_flag),
        "payload_size": payload_size,
    }

    if span_type in (SPAN_TYPE_FOREGROUND, SPAN_TYPE_BACKGROUND) and hasattr(extra, "value"):
        span["value"] = int(extra.value)
    elif span_type == SPAN_TYPE_FONT_SIZE and hasattr(extra, "value"):
        span["value"] = float(extra.value)
    elif span_type == SPAN_TYPE_FONT_NAME and hasattr(extra, "value"):
        span["value"] = str(extra.value)
    elif span_type in (SPAN_TYPE_BOLD, SPAN_TYPE_ITALIC, SPAN_TYPE_STRIKETHROUGH) and hasattr(extra, "value"):
        span["value"] = bool(extra.value)
    elif span_type == SPAN_TYPE_UNDERLINE and hasattr(extra, "value"):
        span["value"] = bool(extra.value)
        span["underline_type"] = int(extra.underline_type)
        span["underline_color"] = int(extra.underline_color)

    return span


def paragraph_record_to_dict(record, text_length: int) -> Optional[Dict[str, object]]:
    payload_size = int(record.payload_size)
    body = record.body
    paragraph_type = int(body.paragraph_type)
    start = int(body.start)
    end = int(body.end)
    if start > end or end > text_length + 1:
        return None

    extra = body.extra
    paragraph: Dict[str, object] = {
        "type": paragraph_type,
        "start": start,
        "end": end,
        "payload_size": payload_size,
    }

    if paragraph_type in (PARAGRAPH_TYPE_DIRECTION, PARAGRAPH_TYPE_ALIGN, PARAGRAPH_TYPE_PARSING_STATE) and hasattr(extra, "value"):
        paragraph["value"] = int(extra.value)
    elif paragraph_type == PARAGRAPH_TYPE_INDENT and hasattr(extra, "first"):
        paragraph["level"] = int(extra.first)
        paragraph["direction"] = int(extra.second)
    elif paragraph_type == PARAGRAPH_TYPE_LINE_SPACING and hasattr(extra, "spacing"):
        paragraph["spacing_type"] = int(extra.spacing_type)
        paragraph["spacing"] = float(extra.spacing)
    elif paragraph_type == PARAGRAPH_TYPE_BULLET and hasattr(extra, "first"):
        bullet_type = int(extra.first)
        bullet_value = int(extra.second)
        paragraph["bullet_type"] = bullet_type
        paragraph["bullet_value"] = bullet_value
        paragraph["checked"] = bool(bullet_value) if bullet_type == 2 else False

    return paragraph


def text_common_to_dict(parsed: SamsungTextCommon) -> Optional[Dict[str, object]]:
    text_length = int(parsed.text_length)

    spans: List[Dict[str, object]] = []
    for record in parsed.spans:
        span = span_record_to_dict(record, text_length)
        if span is None:
            return None
        spans.append(span)

    paragraphs: List[Dict[str, object]] = []
    for record in parsed.paragraphs:
        paragraph = paragraph_record_to_dict(record, text_length)
        if paragraph is None:
            return None
        paragraphs.append(paragraph)

    object_refs = [
        {
            "a": int(ref.a),
            "b": int(ref.b),
        }
        for ref in parsed.object_refs
    ]

    object_span_flags = int(getattr(parsed, "object_span_flags", 0) or 0)
    object_spans: List[Dict[str, object]] = []
    if object_span_flags & 1:
        for record in getattr(parsed, "object_spans", []) or []:
            body = record.body
            object_spans.append(
                {
                    "record_size": int(record.record_size),
                    "object_binary_size": int(body.object_binary_size),
                    "object_type": int(body.object_type),
                    "span_target": int(getattr(body, "span_target", 0) or 0),
                }
            )

    if text_length == 0 and not spans and not paragraphs:
        return None

    return {
        "text": str(parsed.text),
        "text_length": text_length,
        "spans": spans,
        "span_count": int(parsed.span_count),
        "paragraphs": paragraphs,
        "paragraph_count": int(parsed.paragraph_count),
        "margins": tuple(float(value) for value in parsed.margins),
        "text_gravity": int(parsed.text_gravity),
        "object_refs": object_refs,
        "object_count": int(parsed.object_count),
        "object_span_flags": object_span_flags,
        "object_spans": object_spans,
    }


def body_text_source_to_dict(source: SamsungBodyTextSource) -> Optional[Dict[str, object]]:
    body_text = text_common_to_dict(source.text_common)
    if body_text is None:
        return None

    body_text["binary_size"] = source.binary_size
    body_text["binary_size_offset"] = source.binary_size_offset
    body_text["binary_payload_offset"] = source.binary_payload_offset
    body_text["score"] = _text_common_score(body_text)
    body_text["offset_source"] = "shape_text_record.own_data_offset"
    return body_text


def note_source_to_metadata(source: SamsungNoteSource) -> Dict[str, object]:
    note: Dict[str, object] = {
        "note_path": source.note_path,
        "file_size": len(source.data),
    }
    parsed = source.note
    if parsed is None:
        if source.parse_error:
            note["parse_error"] = source.parse_error
        return note

    note.update(
        {
            "integrity_offset": int(parsed.integrity_offset),
            "header_constant_1": int(parsed.header_constant_1),
            "header_flags": int(parsed.header_flags),
            "header_constant_2": int(parsed.header_constant_2),
            "property_flags": int(parsed.property_flags),
            "format_version": int(parsed.format_version),
            "note_id": _ks_string(parsed.note_id),
            "file_revision": int(parsed.file_revision),
            "created_time_raw": int(parsed.created_time_raw),
            "modified_time_raw": int(parsed.modified_time_raw),
            "width": int(parsed.width),
            "height": int(parsed.height),
            "page_horizontal_padding": int(parsed.page_horizontal_padding),
            "page_vertical_padding": int(parsed.page_vertical_padding),
            "min_format_version": int(parsed.min_format_version),
            "title_object_size": int(parsed.title_object_size),
            "title_object": parsed.title_object,
            "body_object_size": int(parsed.body_object_size),
            "body_object": parsed.body_object,
        }
    )

    body_object_offset = source.data.find(parsed.body_object)
    if body_object_offset >= 0:
        note["body_object_offset"] = body_object_offset

    if source.body_text is not None:
        body_text = body_text_source_to_dict(source.body_text)
        if body_text is not None:
            note["body_text"] = body_text

    if hasattr(parsed, "app_name"):
        note["app_name"] = _ks_string(parsed.app_name)
    if hasattr(parsed, "app_version"):
        note["app_major_version"] = int(parsed.app_version.major)
        note["app_minor_version"] = int(parsed.app_version.minor)
        note["app_patch_name"] = _ks_string(parsed.app_version.patch_name)
    if hasattr(parsed, "author_info"):
        note["author_info"] = {
            "a": _ks_string(parsed.author_info.a),
            "b": _ks_string(parsed.author_info.b),
            "c": _ks_string(parsed.author_info.c),
            "d": int(parsed.author_info.d),
        }
    if hasattr(parsed, "geo"):
        note["geo_latitude"] = float(parsed.geo.latitude)
        note["geo_longitude"] = float(parsed.geo.longitude)
    if hasattr(parsed, "template_uri"):
        note["template_uri"] = _ks_string(parsed.template_uri)
    if hasattr(parsed, "last_edited_page_index"):
        note["last_edited_page_index"] = int(parsed.last_edited_page_index)
    if hasattr(parsed, "last_edited_page_image"):
        note["last_edited_page_image_id"] = int(parsed.last_edited_page_image.image_id)
        note["last_edited_page_time_raw"] = int(parsed.last_edited_page_image.time_raw)
    if hasattr(parsed, "string_id_block_size"):
        string_id_map: Dict[int, str] = {}
        for entry in parsed.string_id_block.entries:
            string_id_map[int(entry.string_id)] = _ks_string(entry.value)
        note["string_id_block_size"] = int(parsed.string_id_block_size)
        note["string_id_map"] = string_id_map
    if hasattr(parsed, "body_text_font_size_delta"):
        note["body_text_font_size_delta"] = int(parsed.body_text_font_size_delta)
    if hasattr(parsed, "legacy_pen_info"):
        note["legacy_pen_info"] = pen_info_to_dict(parsed.legacy_pen_info, include_particle_size=False)
    if hasattr(parsed, "attached_files"):
        note["attached_files"] = {
            _ks_string(entry.filename): int(entry.bind_id)
            for entry in parsed.attached_files.entries
            if _ks_string(entry.filename)
        }
    if hasattr(parsed, "current_pen_info_block"):
        note["current_pen_info_block_size"] = int(parsed.current_pen_info_block.block_size)
        note["current_pen_info"] = pen_info_to_dict(
            parsed.current_pen_info_block.body,
            include_particle_size=True,
        )
    if hasattr(parsed, "last_recognized_data_modified_time_raw"):
        note["last_recognized_data_modified_time_raw"] = int(parsed.last_recognized_data_modified_time_raw)
    if hasattr(parsed, "fixed_font"):
        note["fixed_font"] = _ks_string(parsed.fixed_font)
    if hasattr(parsed, "fixed_text_direction"):
        note["fixed_text_direction"] = int(parsed.fixed_text_direction)
    if hasattr(parsed, "fixed_background_theme"):
        note["fixed_background_theme"] = int(parsed.fixed_background_theme)
    if hasattr(parsed, "text_summarization"):
        note["text_summarization"] = _ks_string(parsed.text_summarization)
    if hasattr(parsed, "stroke_group_size"):
        note["stroke_group_size"] = int(parsed.stroke_group_size)
    if hasattr(parsed, "app_custom_data"):
        note["app_custom_data"] = _ks_string(parsed.app_custom_data)

    integrity_offset = int(note.get("integrity_offset") or 0)
    note["optional_data_end_offset"] = integrity_offset if 0 <= integrity_offset <= len(source.data) else parsed._io.pos()
    if hasattr(parsed, "unknown_optional_bytes"):
        note["unknown_optional_bytes"] = parsed.unknown_optional_bytes

    try:
        integrity_hash = parsed.integrity_hash
    except Exception:
        integrity_hash = None
    if integrity_hash is not None:
        note["integrity_hash"] = integrity_hash

    return note
