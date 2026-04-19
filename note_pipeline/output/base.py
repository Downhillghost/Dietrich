from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from note_pipeline.model import ExportResult, NoteDocument


@dataclass
class ExportOptions:
    thickness_scale: float = 0.6
    output_scale: float = 1.0
    text_scale_override: Optional[float] = None


class NoteExporter(ABC):
    format_name = ""

    @abstractmethod
    def export(self, note: NoteDocument, output_dir: str, options: ExportOptions) -> ExportResult:
        raise NotImplementedError
