from __future__ import annotations

from typing import Dict, Optional, Type

from note_pipeline.output.base import NoteExporter
from note_pipeline.output.excalidraw import ExcalidrawExporter
from note_pipeline.output.png import PngExporter


EXPORTERS: Dict[str, Type[NoteExporter]] = {
    "png": PngExporter,
    "excalidraw": ExcalidrawExporter,
}


def get_exporter_class(format_name: str) -> Optional[Type[NoteExporter]]:
    return EXPORTERS.get(format_name.strip().lower())
