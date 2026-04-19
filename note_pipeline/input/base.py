from __future__ import annotations

from abc import ABC, abstractmethod

from note_pipeline.model import NoteDocument


class NoteImporter(ABC):
    @classmethod
    @abstractmethod
    def supports_path(cls, note_source: str) -> bool:
        raise NotImplementedError

    def __enter__(self) -> "NoteImporter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @abstractmethod
    def import_path(self, note_source: str) -> NoteDocument:
        raise NotImplementedError

    def close(self) -> None:
        return None
