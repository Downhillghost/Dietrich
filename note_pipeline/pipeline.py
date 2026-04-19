from __future__ import annotations

from typing import Optional

from note_pipeline.input import get_importer_class_for_path
from note_pipeline.model import ExportResult
from note_pipeline.output import ExportOptions
from note_pipeline.output.registry import get_exporter_class


def export_note_source(
    note_source: str,
    output_dir: str,
    output_format: str = "png",
    thickness_scale: float = 0.6,
    text_scale_override: Optional[float] = None,
    output_scale: float = 1.0,
) -> ExportResult:
    format_name = output_format.lower().strip()
    exporter_cls = get_exporter_class(format_name)
    if exporter_cls is None:
        raise ValueError(f"Unsupported output format: {output_format}")

    importer_cls = get_importer_class_for_path(note_source)
    if importer_cls is None:
        raise ValueError(f"Unsupported note source: {note_source}")

    with importer_cls(text_scale_override=text_scale_override) as importer:
        note = importer.import_path(note_source)
        options = ExportOptions(
            thickness_scale=thickness_scale,
            output_scale=output_scale,
            text_scale_override=text_scale_override,
        )
        exporter = exporter_cls()
        return exporter.export(note, output_dir=output_dir, options=options)
