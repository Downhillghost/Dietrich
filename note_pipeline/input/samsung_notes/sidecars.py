from __future__ import annotations

from io import BytesIO
from typing import Dict, List

from kaitaistruct import KaitaiStream

from note_pipeline.input.samsung_notes.generated import SamsungEndTag, SamsungMediaInfo, SamsungPageIdInfo


def _ks_string(value) -> str:
    return str(getattr(value, "value", "") or "")


def parse_page_id_info(data: bytes) -> Dict[str, object]:
    result: Dict[str, object] = {
        "file_hash": data[:32] if len(data) >= 32 else b"",
        "entries": [],
    }
    if len(data) < 34:
        return result

    try:
        parsed = SamsungPageIdInfo(KaitaiStream(BytesIO(data)))
    except Exception:
        return result

    entries: List[Dict[str, object]] = []
    for entry in parsed.entries:
        entries.append(
            {
                "page_id": _ks_string(entry.page_id),
                "page_hash": entry.page_hash,
            }
        )

    result["file_hash"] = parsed.file_hash
    result["num_entries"] = parsed.num_entries
    result["entries"] = entries
    return result


def parse_media_info(data: bytes) -> Dict[str, object]:
    result: Dict[str, object] = {
        "format_version": 0,
        "entries": [],
        "footer_marker": b"",
    }
    if len(data) < 6:
        return result

    try:
        parsed = SamsungMediaInfo(KaitaiStream(BytesIO(data)))
    except Exception:
        return result

    entries: List[Dict[str, object]] = []
    entry_start = 6
    for entry in parsed.entries:
        body = entry.body
        entries.append(
            {
                "entry_size": entry.entry_size,
                "entry_start": entry_start,
                "bind_id": body.bind_id,
                "filename": _ks_string(body.filename),
                "file_hash": body.file_hash_raw.decode("ascii", errors="replace").rstrip("\x00"),
                "ref_count": body.ref_count,
                "modified_time": body.modified_time,
                "is_file_attached": bool(body.is_file_attached),
                "extra_bytes": body.extra_bytes,
            }
        )
        entry_start += 4 + int(entry.entry_size)

    result["format_version"] = parsed.format_version
    result["num_entries"] = parsed.num_entries
    result["entries"] = entries
    result["footer_marker"] = parsed.footer_marker[:4]
    return result


def parse_end_tag(data: bytes) -> Dict[str, object]:
    if len(data) < 2:
        return {}

    try:
        parsed = SamsungEndTag(KaitaiStream(BytesIO(data)))
    except Exception:
        return {}

    payload = parsed.payload
    return {
        "payload_size": parsed.payload_size,
        "format_version": payload.format_version,
        "note_id": _ks_string(payload.note_id),
        "modified_time_raw": payload.modified_time_raw,
        "property_flags": payload.property_flags,
        "cover_image": _ks_string(payload.cover_image),
        "note_width": payload.note_width,
        "note_height": payload.note_height,
        "title": _ks_string(payload.title),
        "thumbnail_width": payload.thumbnail_width,
        "thumbnail_height": payload.thumbnail_height,
        "app_patch_name": _ks_string(payload.app_patch_name),
        "min_format_version": payload.min_format_version,
        "created_time_raw": payload.created_time_raw,
        "last_viewed_page_index": payload.last_viewed_page_index,
        "page_mode": payload.page_mode,
        "document_type": payload.document_type,
        "owner_id": _ks_string(payload.owner_id),
        "reserved_zero_1": payload.reserved_zero_1,
        "reserved_zero_2": payload.reserved_zero_2,
        "display_created_time_raw": payload.display_created_time_raw,
        "display_modified_time_raw": payload.display_modified_time_raw,
        "last_recognized_data_modified_time_raw": payload.last_recognized_data_modified_time_raw,
        "fixed_font": _ks_string(payload.fixed_font),
        "fixed_text_direction": payload.fixed_text_direction,
        "fixed_background_theme": payload.fixed_background_theme,
        "server_checkpoint": payload.server_checkpoint,
        "new_orientation": payload.new_orientation,
        "min_unknown_version": payload.min_unknown_version,
        "app_custom_data": _ks_string(payload.app_custom_data),
        "footer_marker": payload.footer_marker,
    }
