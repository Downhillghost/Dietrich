from __future__ import annotations

from typing import Dict

from note_pipeline.input.samsung_notes.note_adapters import note_source_to_metadata
from note_pipeline.input.samsung_notes.source import load_samsung_note_source


class SamsungNotesNoteParser:
    def __init__(self, note_path: str):
        self.note_path = note_path

    def parse(self) -> Dict[str, object]:
        return note_source_to_metadata(load_samsung_note_source(self.note_path))


__all__ = ["SamsungNotesNoteParser"]
