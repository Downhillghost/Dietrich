from __future__ import annotations

import os
from io import BytesIO
from typing import Dict, List

from kaitaistruct import KaitaiStream

from note_pipeline.input.samsung_notes.generated import SamsungSpi
from note_pipeline.input.samsung_notes.sidecars import parse_media_info


def _hex(value: int, width: int = 4) -> str:
    return f"0x{value:0{width}X}"


def _count_ff_bytes_before_last_byte(data: bytes) -> int:
    if len(data) < 2:
        return 0

    count = 0
    for value in reversed(data[:-1]):
        if value != 0xFF:
            break
        count += 1
    return count


def parse_spi_bytes(data: bytes) -> Dict[str, object]:
    result: Dict[str, object] = {
        "file_size": len(data),
        "is_spi_like": False,
        "last_byte_hex": _hex(data[-1], 2) if data else None,
        "ff_bytes_before_last_byte": _count_ff_bytes_before_last_byte(data),
    }
    if len(data) < 36:
        result["parse_error"] = "file too small for SPI header"
        return result

    try:
        parsed = SamsungSpi(KaitaiStream(BytesIO(data)))
    except Exception as exc:
        result["parse_error"] = str(exc)
        result["header_prefix_hex"] = data[:36].hex(" ").upper()
        return result

    header_packet = parsed.header_packet
    image_packet = parsed.image_packet
    payload = bytes(image_packet.payload)
    header_packet_size = int(parsed.header_packet_size)
    image_packet_size = int(parsed.image_packet_size)
    actual_image_packet_size = max(0, len(data) - 8 - header_packet_size)
    image_packet_size_hint = int(image_packet.size_hint)
    image_packet_offset = 4 + header_packet_size + 4
    image_payload_offset = image_packet_offset + 8

    result.update(
        {
            "header_packet_size": header_packet_size,
            "header_size": header_packet_size,
            "header_packet_tag": int(header_packet.tag),
            "header_packet_tag_hex": _hex(int(header_packet.tag)),
            "header_tag": int(header_packet.tag),
            "header_tag_hex": _hex(int(header_packet.tag)),
            "codec_hint": "spen_screen_codec" if int(header_packet.tag) == 0xAA01 else None,
            "header_reserved": int(header_packet.reserved),
            "header_record_size": int(header_packet.record_size),
            "header_record_reserved": int(header_packet.record_reserved),
            "format_family": int(header_packet.format_family),
            "width": int(header_packet.width),
            "height": int(header_packet.height),
            "texture_width_units": int(header_packet.texture_width_units),
            "texture_width": int(header_packet.texture_width),
            "fixed_00e0": int(header_packet.fixed_00e0),
            "fixed_00e0_hex": _hex(int(header_packet.fixed_00e0)),
            "image_packet_size": image_packet_size,
            "actual_image_packet_size": actual_image_packet_size,
            "image_packet_size_matches_file_size": bool(parsed.image_packet_size_matches_file_size),
            "declared_remaining_size": image_packet_size,
            "actual_remaining_size": actual_image_packet_size,
            "declared_remaining_size_matches_file_size": bool(parsed.image_packet_size_matches_file_size),
            "image_packet_offset": image_packet_offset,
            "image_packet_tag": int(image_packet.tag),
            "image_packet_tag_hex": _hex(int(image_packet.tag)),
            "image_packet_reserved": int(image_packet.reserved),
            "image_packet_size_hint": image_packet_size_hint,
            "image_packet_size_hint_within_payload": image_packet_size_hint <= len(payload),
            "primary_chunk_tag": int(image_packet.tag),
            "primary_chunk_tag_hex": _hex(int(image_packet.tag)),
            "primary_chunk_reserved": int(image_packet.reserved),
            "primary_chunk_size": image_packet_size_hint,
            "primary_chunk_size_within_file": image_packet_size_hint <= len(payload),
            "primary_payload_offset": image_payload_offset,
            "primary_payload_stored_size": len(payload),
            "primary_payload_prefix_hex": payload[:16].hex(" ").upper(),
        }
    )
    result["is_spi_like"] = (
        result["header_packet_size"] == 20
        and result["header_tag"] == 0xAA01
        and result["header_record_size"] == 20
        and result["primary_chunk_tag"] == 0xAA02
        and result["declared_remaining_size_matches_file_size"]
    )
    return result


def parse_spi_file(path: str) -> Dict[str, object]:
    with open(path, "rb") as f:
        return parse_spi_bytes(f.read())


def _load_spi_media_entries(note_root: str) -> Dict[str, Dict[str, object]]:
    media_info_path = os.path.join(note_root, "media", "mediaInfo.dat")
    if not os.path.exists(media_info_path):
        return {}

    with open(media_info_path, "rb") as f:
        media_info = parse_media_info(f.read())

    format_version = int(media_info.get("format_version") or 0)
    entries: Dict[str, Dict[str, object]] = {}
    for entry in media_info.get("entries", []):
        if not isinstance(entry, dict):
            continue
        filename = str(entry.get("filename") or "")
        if not filename.lower().endswith(".spi"):
            continue
        entries[filename] = {
            "bind_id": int(entry.get("bind_id") or 0),
            "filename": filename,
            "file_hash": str(entry.get("file_hash") or ""),
            "ref_count": int(entry.get("ref_count") or 0),
            "modified_time": int(entry.get("modified_time") or 0),
            "is_file_attached": bool(entry.get("is_file_attached")),
            "format_version": format_version,
        }
    return entries


def scan_spi_files(note_root: str) -> List[Dict[str, object]]:
    media_dir = os.path.join(note_root, "media")
    if not os.path.isdir(media_dir):
        return []

    media_entries = _load_spi_media_entries(note_root)
    filenames = set(media_entries)
    for filename in os.listdir(media_dir):
        if filename.lower().endswith(".spi"):
            filenames.add(filename)

    records: List[Dict[str, object]] = []
    for filename in sorted(filenames):
        entry = media_entries.get(filename, {})
        path = os.path.join(media_dir, filename)
        record: Dict[str, object] = {
            "bind_id": entry.get("bind_id"),
            "filename": filename,
            "file_hash": entry.get("file_hash"),
            "ref_count": entry.get("ref_count"),
            "modified_time": entry.get("modified_time"),
            "is_file_attached": entry.get("is_file_attached"),
            "format_version": entry.get("format_version"),
            "path": path,
        }
        if os.path.exists(path):
            try:
                record["spi_info"] = parse_spi_file(path)
            except OSError as exc:
                record["spi_info"] = {"parse_error": str(exc)}
        else:
            record["spi_info"] = {"parse_error": "media file not found"}
        records.append(record)

    return records


__all__ = ["parse_spi_bytes", "parse_spi_file", "scan_spi_files"]
