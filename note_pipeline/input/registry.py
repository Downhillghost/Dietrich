from __future__ import annotations

from typing import Dict, Optional, Type

from note_pipeline.input.base import NoteImporter
from note_pipeline.input.samsung_notes import SamsungNotesImporter


IMPORTERS: Dict[str, Type[NoteImporter]] = {
    "samsung_notes": SamsungNotesImporter,
}


def get_importer_class_for_path(note_source: str) -> Optional[Type[NoteImporter]]:
    for importer_cls in IMPORTERS.values():
        if importer_cls.supports_path(note_source):
            return importer_cls
    return None


def get_importer_class_by_name(importer_name: str) -> Optional[Type[NoteImporter]]:
    return IMPORTERS.get(importer_name.strip().lower())
