from __future__ import annotations

import os
from typing import Dict, List, Optional

from note_pipeline.input.samsung_notes.sidecars import parse_page_id_info


def read_page_id_order(note_root: str) -> List[str]:
    page_id_info_path = os.path.join(note_root, "pageIdInfo.dat")
    if not os.path.exists(page_id_info_path):
        return []

    with open(page_id_info_path, "rb") as handle:
        data = handle.read()

    return [
        str(entry["page_id"])
        for entry in parse_page_id_info(data).get("entries", [])
        if entry.get("page_id")
    ]


def list_page_files(note_root: str) -> List[str]:
    page_files = [
        os.path.join(note_root, name)
        for name in os.listdir(note_root)
        if name.lower().endswith(".page")
    ]
    ordered_ids = read_page_id_order(note_root)
    if not ordered_ids:
        return sorted(page_files, key=lambda path: os.path.basename(path).lower())

    page_map = {os.path.splitext(os.path.basename(path))[0]: path for path in page_files}
    ordered_paths: List[str] = []
    for page_id in ordered_ids:
        page_path = page_map.pop(page_id, None)
        if page_path is not None:
            ordered_paths.append(page_path)

    ordered_paths.extend(sorted(page_map.values(), key=lambda path: os.path.basename(path).lower()))
    return ordered_paths


def looks_like_note_root(path: str) -> bool:
    if not os.path.isdir(path):
        return False
    if os.path.exists(os.path.join(path, "note.note")):
        return True

    try:
        return any(name.lower().endswith(".page") for name in os.listdir(path))
    except OSError:
        return False


def resolve_note_root(path: str) -> str:
    note_root = os.path.abspath(path)
    if looks_like_note_root(note_root):
        return note_root

    try:
        child_dirs = [
            os.path.join(note_root, name)
            for name in os.listdir(note_root)
            if os.path.isdir(os.path.join(note_root, name))
        ]
    except OSError:
        return note_root

    if len(child_dirs) == 1 and looks_like_note_root(child_dirs[0]):
        return child_dirs[0]

    for child_dir in sorted(child_dirs, key=lambda value: os.path.basename(value).lower()):
        if looks_like_note_root(child_dir):
            return child_dir

    return note_root


def default_output_dir(note_root: str, source_path: Optional[str] = None) -> str:
    if source_path and os.path.isfile(source_path) and source_path.lower().endswith(".sdocx"):
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        return os.path.join(os.path.dirname(source_path), f"{base_name}_rendered_pages")
    return os.path.join(note_root, "rendered_pages")


def output_path_for_page(output_dir: str, page_path: str, index: int) -> str:
    base_name = os.path.splitext(os.path.basename(page_path))[0]
    return os.path.join(output_dir, f"{index:03d}_{base_name}.png")


def build_layered_draw_items(
    stroke_records: List[Dict[str, object]],
    image_records: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    draw_items: List[Dict[str, object]] = []

    for sequence, image in enumerate(image_records):
        draw_items.append(
            {
                "kind": "image",
                "record": image,
                "layer_number": int(image.get("layer_number") or 0),
                "object_start": int(image.get("object_start") or 0),
                "sequence": sequence,
            }
        )

    stroke_sequence_base = len(draw_items)
    for sequence, stroke in enumerate(stroke_records):
        draw_items.append(
            {
                "kind": "stroke",
                "record": stroke,
                "layer_number": int(stroke.get("layer_number") or 0),
                "object_start": int(stroke.get("object_start") or stroke.get("start") or 0),
                "sequence": stroke_sequence_base + sequence,
            }
        )

    return sorted(
        draw_items,
        key=lambda item: (
            int(item["layer_number"]),
            int(item["object_start"]),
            int(item["sequence"]),
        ),
    )


def should_skip_trailing_placeholder_page(
    page_model: Dict[str, object],
    text_segments: List[Dict[str, object]],
) -> bool:
    if page_model.get("background_records"):
        return False
    if any(len(stroke["points"]) > 10 for stroke in page_model.get("stroke_records", [])):
        return False
    if any(image.get("media_path") for image in page_model.get("image_records", [])):
        return False
    if any(segment.get("text") for segment in text_segments):
        return False
    return True
