from __future__ import annotations

import os
from typing import List

from note_pipeline.model import (
    ExportResult,
    NoteDocument,
    UnsupportedElement,
)
from note_pipeline.output.base import ExportOptions, NoteExporter
from note_pipeline.output.raster import render_surface_to_png


class PngExporter(NoteExporter):
    format_name = "png"

    def export(self, note: NoteDocument, output_dir: str, options: ExportOptions) -> ExportResult:
        os.makedirs(output_dir, exist_ok=True)
        output_paths: List[str] = []
        warnings: List[str] = []

        for surface in note.surfaces:
            unsupported = sum(1 for element in surface.elements if isinstance(element, UnsupportedElement))
            if unsupported:
                warnings.append(
                    f"Omitted {unsupported} unsupported element(s) while rendering surface {surface.surface_id} to PNG."
                )

            output_path = os.path.join(output_dir, f"{surface.index + 1:03d}_{surface.surface_id}.png")
            render_surface_to_png(
                note,
                surface,
                output_path,
                thickness_scale=options.thickness_scale,
                output_scale=options.output_scale,
            )
            output_paths.append(output_path)

        return ExportResult(
            format_name="png",
            output_paths=output_paths,
            warnings=warnings,
            metadata={"surface_count": len(note.surfaces)},
        )
