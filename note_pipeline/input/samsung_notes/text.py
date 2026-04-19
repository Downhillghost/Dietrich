from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from note_pipeline.input.samsung_notes.note_adapters import body_text_source_to_dict
from note_pipeline.input.samsung_notes.source import SamsungNoteSource
from note_pipeline.input.samsung_notes.text_layout import (
    build_keyboard_text_layout,
    estimate_keyboard_text_scale,
)


def materialize_keyboard_text(
    note_metadata: Dict[str, object],
    page_metadatas: List[Dict[str, object]],
    page_image_records: List[List[Dict[str, object]]],
    text_scale_override: Optional[float] = None,
) -> Tuple[Dict[str, object], float, str]:
    body_text = note_metadata.get("body_text")
    if not isinstance(body_text, dict):
        return (
            {
                "pages": [[] for _ in page_metadatas],
                "truncated": False,
                "line_count": 0,
                "segment_count": 0,
                "character_count": 0,
            },
            1.0,
            "no body text",
        )

    if text_scale_override is not None:
        resolved_text_scale = float(text_scale_override)
        text_scale_reason = "provided via override"
    else:
        resolved_text_scale, text_scale_reason = estimate_keyboard_text_scale(note_metadata)

    keyboard_layout = build_keyboard_text_layout(
        note_metadata=note_metadata,
        body_text=body_text,
        page_metadatas=page_metadatas,
        page_image_records=page_image_records,
        text_scale=resolved_text_scale,
    )
    return keyboard_layout, resolved_text_scale, text_scale_reason


def _empty_keyboard_layout(page_metadatas: List[Dict[str, object]]) -> Dict[str, object]:
    return {
        "pages": [[] for _ in page_metadatas],
        "truncated": False,
        "line_count": 0,
        "segment_count": 0,
        "character_count": 0,
    }


def materialize_keyboard_text_from_source(
    note_source: Optional[SamsungNoteSource],
    page_metadatas: List[Dict[str, object]],
    page_image_records: List[List[Dict[str, object]]],
    text_scale_override: Optional[float] = None,
) -> Tuple[Dict[str, object], float, str]:
    if note_source is None or note_source.note is None or note_source.body_text is None:
        return _empty_keyboard_layout(page_metadatas), 1.0, "no body text"

    parsed_note = note_source.note
    note_layout_metadata: Dict[str, object] = {
        "width": int(parsed_note.width),
        "height": int(parsed_note.height),
        "page_horizontal_padding": int(parsed_note.page_horizontal_padding),
        "page_vertical_padding": int(parsed_note.page_vertical_padding),
    }
    body_text = body_text_source_to_dict(note_source.body_text)
    if body_text is None:
        return _empty_keyboard_layout(page_metadatas), 1.0, "no body text"

    if text_scale_override is not None:
        resolved_text_scale = float(text_scale_override)
        text_scale_reason = "provided via override"
    else:
        resolved_text_scale, text_scale_reason = estimate_keyboard_text_scale(note_layout_metadata)

    keyboard_layout = build_keyboard_text_layout(
        note_metadata=note_layout_metadata,
        body_text=body_text,
        page_metadatas=page_metadatas,
        page_image_records=page_image_records,
        text_scale=resolved_text_scale,
    )
    return keyboard_layout, resolved_text_scale, text_scale_reason
