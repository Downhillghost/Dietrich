from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import os
from typing import Optional

from kaitaistruct import KaitaiStream

from note_pipeline.input.samsung_notes.generated import SamsungNote, SamsungNoteTextObject, SamsungTextCommon


@dataclass(frozen=True)
class SamsungBodyTextSource:
    text_object: SamsungNoteTextObject
    text_common: SamsungTextCommon
    binary_size: int
    binary_size_offset: int
    binary_payload_offset: int


@dataclass(frozen=True)
class SamsungNoteSource:
    note_path: str
    data: bytes
    note: Optional[SamsungNote]
    body_text: Optional[SamsungBodyTextSource]
    parse_error: Optional[str] = None


def _parse_body_text(note: SamsungNote) -> Optional[SamsungBodyTextSource]:
    text_object = SamsungNoteTextObject(KaitaiStream(BytesIO(note.body_object)))
    if not text_object.has_text_common:
        return None

    text_common_bytes = bytes(text_object.text_common_bytes)
    stream = KaitaiStream(BytesIO(text_common_bytes))
    text_common = SamsungTextCommon(int(note.format_version), stream)
    if stream.pos() != stream.size():
        return None

    binary_size_offset = int(text_object.text_common_size_offset)
    return SamsungBodyTextSource(
        text_object=text_object,
        text_common=text_common,
        binary_size=int(text_object.text_common_size),
        binary_size_offset=binary_size_offset,
        binary_payload_offset=binary_size_offset + 4,
    )


def load_samsung_note_source(note_path: str) -> SamsungNoteSource:
    absolute_path = os.path.abspath(note_path)
    with open(absolute_path, "rb") as f:
        data = f.read()

    if len(data) < 14:
        return SamsungNoteSource(
            note_path=absolute_path,
            data=data,
            note=None,
            body_text=None,
            parse_error="note.note is too small",
        )

    try:
        note = SamsungNote(KaitaiStream(BytesIO(data)))
    except Exception as exc:
        return SamsungNoteSource(
            note_path=absolute_path,
            data=data,
            note=None,
            body_text=None,
            parse_error=str(exc),
        )

    try:
        body_text = _parse_body_text(note)
    except Exception:
        body_text = None

    return SamsungNoteSource(
        note_path=absolute_path,
        data=data,
        note=note,
        body_text=body_text,
    )
