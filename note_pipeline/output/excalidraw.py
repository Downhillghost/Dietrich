from __future__ import annotations

import base64
from hashlib import sha1
from io import BytesIO
import json
import math
import os
from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt

from note_pipeline.model import (
    ExportResult,
    ImageElement,
    NoteDocument,
    PdfBackgroundElement,
    StrokeElement,
    TextElement,
    UnsupportedElement,
)
from note_pipeline.output.base import ExportOptions, NoteExporter
import note_pipeline.output.raster as raster


def _stable_id(*parts: object) -> str:
    digest = sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _stable_int(*parts: object) -> int:
    return int(_stable_id(*parts), 16) % 2147483647


def _rgba_to_hex(rgba: Tuple[float, float, float, float]) -> str:
    r = max(0, min(255, int(round(rgba[0] * 255))))
    g = max(0, min(255, int(round(rgba[1] * 255))))
    b = max(0, min(255, int(round(rgba[2] * 255))))
    return f"#{r:02x}{g:02x}{b:02x}"


def _argb_to_hex(color_int: int) -> str:
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}"


def _opacity_from_argb(color_int: int) -> int:
    alpha = (color_int >> 24) & 0xFF
    return max(0, min(100, int(round((alpha / 255.0) * 100))))


def _finite_float_series(values: object, expected_length: int) -> List[float]:
    if not isinstance(values, list) or len(values) != expected_length:
        return []

    result: List[float] = []
    for value in values:
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return []
        result.append(float(value))
    return result


def _excalidraw_pressures(values: object, expected_length: int) -> List[float]:
    pressures = _finite_float_series(values, expected_length)
    if not pressures:
        return []

    clamped = [max(0.0, min(1.0, pressure)) for pressure in pressures]
    if max(clamped) <= 0.0:
        return []
    return [round(pressure, 4) for pressure in clamped]


def _encode_png_data_url(image_array) -> str:
    buffer = BytesIO()
    plt.imsave(buffer, image_array, format="png")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, set):
        return [_json_safe(item) for item in value]
    if isinstance(value, bytes):
        return {
            "__type__": "bytes_summary",
            "length": len(value),
            "sha1": sha1(value).hexdigest(),
        }
    return value


def _base_element(element_id: str, element_type: str, x: float, y: float, width: float, height: float) -> Dict[str, object]:
    return {
        "id": element_id,
        "type": element_type,
        "x": float(x),
        "y": float(y),
        "width": float(width),
        "height": float(height),
        "angle": 0,
        "strokeColor": "#1e1e1e",
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "strokeStyle": "solid",
        "roughness": 0,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": _stable_int(element_id, "seed"),
        "version": 1,
        "versionNonce": _stable_int(element_id, "nonce"),
        "isDeleted": False,
        "boundElements": [],
        "updated": 0,
        "link": None,
        "locked": False,
    }


class ExcalidrawExporter(NoteExporter):
    format_name = "excalidraw"
    FRAME_MARGIN = 160.0
    STROKE_WIDTH_SCALE = 0.15

    def export(self, note: NoteDocument, output_dir: str, options: ExportOptions) -> ExportResult:
        os.makedirs(output_dir, exist_ok=True)
        elements: List[Dict[str, object]] = []
        files: Dict[str, Dict[str, object]] = {}
        warnings: List[str] = []

        current_y = 0.0
        for surface in note.surfaces:
            frame_id: Optional[str] = None
            if surface.surface_kind == "page":
                frame_id = f"frame-{_stable_id(surface.surface_id, 'frame')}"
                surface_width = float(surface.width or 0.0)
                surface_height = float(surface.height or 0.0)
                page_offset = (0.0, current_y)
                frame = _base_element(frame_id, "frame", 0.0, current_y, surface_width, surface_height)
                frame["name"] = f"Page {surface.index + 1}"
                elements.append(frame)
                current_y += surface_height + self.FRAME_MARGIN
            else:
                page_offset = (float(surface.origin_x), float(surface.origin_y))

            page_text_elements: List[TextElement] = []

            for element in surface.elements:
                if isinstance(element, UnsupportedElement):
                    warnings.append(f"Omitted unsupported element {element.unsupported_type} on surface {surface.surface_id}.")
                    continue
                if isinstance(element, TextElement):
                    page_text_elements.append(element)
                    continue
                excalidraw_element = self._export_element(note, page_offset, element, files)
                if excalidraw_element is not None:
                    if frame_id is not None:
                        excalidraw_element["frameId"] = frame_id
                    elements.append(excalidraw_element)

            page_text = self._export_page_text(page_offset, surface.surface_id, page_text_elements)
            if page_text is not None:
                if frame_id is not None:
                    page_text["frameId"] = frame_id
                elements.append(page_text)

        scene = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://github.com/excalidraw/excalidraw",
            "elements": elements,
            "appState": {
                "viewBackgroundColor": "#ffffff",
                "gridSize": None,
            },
            "files": files,
            "vendorExtensions": _json_safe(note.vendor_extensions),
            "notePipeline": self._build_pipeline_summary(note),
            "exportWarnings": warnings,
        }

        output_path = os.path.join(output_dir, f"{note.source.display_name}.excalidraw")
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(scene, handle, ensure_ascii=False, indent=2)

        return ExportResult(
            format_name="excalidraw",
            output_paths=[output_path],
            warnings=warnings,
            metadata={
                "surface_count": len(note.surfaces),
                "element_count": len(elements),
                "asset_file_count": len(files),
            },
        )

    def _build_pipeline_summary(self, note: NoteDocument) -> Dict[str, object]:
        return {
            "source": {
                "sourcePath": note.source.source_path,
                "sourceKind": note.source.source_kind,
                "noteRoot": note.source.note_root,
                "displayName": note.source.display_name,
                "extractedFromArchive": note.source.extracted_from_archive,
                "sourceArchivePath": note.source.source_archive_path,
            },
            "document": {
                "noteId": note.note_id,
                "title": note.title,
                "layoutKind": note.layout_kind,
                "metadata": _json_safe(note.metadata),
                "vendorExtensions": _json_safe(note.vendor_extensions),
            },
            "assets": {
                asset_id: {
                    "mediaType": asset.media_type,
                    "sourcePath": asset.source_path,
                    "sourceRef": asset.source_ref,
                    "derivedRasterPath": asset.derived_raster_path,
                    "vendorExtensions": _json_safe(asset.vendor_extensions),
                }
                for asset_id, asset in note.assets.items()
            },
            "surfaces": [
                {
                    "surfaceId": surface.surface_id,
                    "surfaceKind": surface.surface_kind,
                    "index": surface.index,
                    "originX": surface.origin_x,
                    "originY": surface.origin_y,
                    "width": surface.width,
                    "height": surface.height,
                    "background": {
                        "colorInt": surface.background.color_int,
                        "colorArgb": surface.background.color_argb,
                        "vendorExtensions": _json_safe(surface.background.vendor_extensions),
                    },
                    "vendorExtensions": _json_safe(surface.vendor_extensions),
                    "unsupportedElements": [
                        {
                            "elementId": element.element_id,
                            "unsupportedType": element.unsupported_type,
                            "layerNumber": element.layer_number,
                            "sourceOrder": element.source_order,
                            "zIndex": element.z_index,
                            "bounds": _json_safe(element.bounds),
                            "vendorExtensions": _json_safe(element.vendor_extensions),
                        }
                        for element in surface.elements
                        if isinstance(element, UnsupportedElement)
                    ],
                }
                for surface in note.surfaces
            ],
        }

    def _export_element(
        self,
        note: NoteDocument,
        page_offset: Tuple[float, float],
        element,
        files: Dict[str, Dict[str, object]],
    ) -> Optional[Dict[str, object]]:
        if isinstance(element, PdfBackgroundElement):
            return self._export_pdf_background(note, page_offset, element, files)
        if isinstance(element, ImageElement):
            return self._export_image(note, page_offset, element, files)
        if isinstance(element, StrokeElement):
            return self._export_stroke(page_offset, element)
        return None

    def _register_file(self, file_id: str, data_url: str) -> Dict[str, object]:
        return {
            "id": file_id,
            "dataURL": data_url,
            "mimeType": "image/png",
            "created": 0,
            "lastRetrieved": 0,
        }

    def _export_pdf_background(
        self,
        note: NoteDocument,
        page_offset: Tuple[float, float],
        element: PdfBackgroundElement,
        files: Dict[str, Dict[str, object]],
    ) -> Optional[Dict[str, object]]:
        asset = note.assets.get(element.asset_id or "")
        if asset is None or asset.source_path is None:
            return None

        left, top, right, bottom = element.rect
        image_array = raster.load_pdf_background_array(
            asset.source_path,
            element.page_index,
            abs(float(right) - float(left)),
            abs(float(bottom) - float(top)),
            overlay_tags_to_strip=element.overlay_tags_to_strip,
        )
        if image_array is None:
            return None

        file_id = f"file-{_stable_id(element.element_id, 'background')}"
        files[file_id] = self._register_file(file_id, _encode_png_data_url(image_array))

        x_offset, y_offset = page_offset
        excalidraw_element = _base_element(
            element.element_id,
            "image",
            x_offset + left,
            y_offset + top,
            right - left,
            bottom - top,
        )
        excalidraw_element["fileId"] = file_id
        excalidraw_element["status"] = "saved"
        excalidraw_element["scale"] = [1, 1]
        excalidraw_element["zIndex"] = element.z_index
        return excalidraw_element

    def _export_image(
        self,
        note: NoteDocument,
        page_offset: Tuple[float, float],
        element: ImageElement,
        files: Dict[str, Dict[str, object]],
    ) -> Optional[Dict[str, object]]:
        asset = note.assets.get(element.asset_id or "")
        if asset is None or asset.source_path is None:
            return None

        image_array = raster.load_image_array(asset.source_path)
        if image_array is None:
            return None

        image_array = raster.crop_image_array(
            image_array,
            element.crop_rect,
            os.path.basename(asset.source_path),
        )
        file_id = f"file-{_stable_id(element.element_id, 'image')}"
        files[file_id] = self._register_file(file_id, _encode_png_data_url(image_array))

        left, top, right, bottom = element.rect
        x_offset, y_offset = page_offset
        excalidraw_element = _base_element(
            element.element_id,
            "image",
            x_offset + left,
            y_offset + top,
            right - left,
            bottom - top,
        )
        excalidraw_element["fileId"] = file_id
        excalidraw_element["status"] = "saved"
        excalidraw_element["scale"] = [1, 1]
        excalidraw_element["zIndex"] = element.z_index
        return excalidraw_element

    def _export_stroke(self, page_offset: Tuple[float, float], element: StrokeElement) -> Optional[Dict[str, object]]:
        if not element.points:
            return None

        x_offset, y_offset = page_offset
        xs = [point[0] for point in element.points]
        ys = [point[1] for point in element.points]
        min_x = min(xs)
        min_y = min(ys)
        max_x = max(xs)
        max_y = max(ys)
        points = [[point[0] - min_x, point[1] - min_y] for point in element.points]

        excalidraw_element = _base_element(
            element.element_id,
            "freedraw",
            x_offset + min_x,
            y_offset + min_y,
            max_x - min_x,
            max_y - min_y,
        )
        excalidraw_element["strokeColor"] = _rgba_to_hex(element.rgba)
        excalidraw_element["strokeWidth"] = round(max(0.5, float(element.pen_size) * self.STROKE_WIDTH_SCALE), 2)
        excalidraw_element["opacity"] = _opacity_from_argb(element.color_int)
        excalidraw_element["points"] = points
        excalidraw_element["pressures"] = _excalidraw_pressures(element.pressures, len(points))
        excalidraw_element["simulatePressure"] = False
        excalidraw_element["lastCommittedPoint"] = points[-1]
        excalidraw_element["zIndex"] = element.z_index
        return excalidraw_element

    def _export_page_text(
        self,
        page_offset: Tuple[float, float],
        page_id: str,
        text_elements: List[TextElement],
    ) -> Optional[Dict[str, object]]:
        if not text_elements:
            return None

        lines = self._group_text_lines(text_elements)
        line_texts = [self._line_text(line) for line in lines]
        full_text = "\n".join(text for text in line_texts if text)
        if not full_text:
            return None

        left = min(float(element.x) for element in text_elements)
        top = min(float(element.baseline_y - element.ascent) for element in text_elements)
        right = max(float(element.x + element.width) for element in text_elements)
        bottom = max(float(element.baseline_y + element.descent) for element in text_elements)
        dominant_style = self._dominant_text_style(text_elements)
        x_offset, y_offset = page_offset
        excalidraw_element = _base_element(
            f"page-text-{_stable_id(page_id, 'text')}",
            "text",
            x_offset + left,
            y_offset + top,
            right - left,
            bottom - top,
        )
        excalidraw_element["strokeColor"] = _argb_to_hex(int(dominant_style["color_int"]))
        excalidraw_element["backgroundColor"] = (
            _argb_to_hex(int(dominant_style["background_color_int"]))
            if isinstance(dominant_style.get("background_color_int"), int)
            else "transparent"
        )
        excalidraw_element["opacity"] = _opacity_from_argb(int(dominant_style["color_int"]))
        excalidraw_element["text"] = full_text
        excalidraw_element["originalText"] = full_text
        excalidraw_element["fontSize"] = int(round(float(dominant_style["font_size_pt"])))
        excalidraw_element["fontFamily"] = 3 if dominant_style.get("font_name") else 1
        excalidraw_element["textAlign"] = "left"
        excalidraw_element["verticalAlign"] = "top"
        excalidraw_element["containerId"] = None
        excalidraw_element["lineHeight"] = 1.25
        excalidraw_element["autoResize"] = False
        excalidraw_element["zIndex"] = max(int(element.z_index) for element in text_elements)
        return excalidraw_element

    def _group_text_lines(self, text_elements: List[TextElement]) -> List[List[TextElement]]:
        sorted_elements = sorted(
            text_elements,
            key=lambda element: (
                round(float(element.baseline_y), 2),
                round(float(element.x), 2),
                int(element.source_order),
            ),
        )
        lines: List[List[TextElement]] = []
        for element in sorted_elements:
            if not lines:
                lines.append([element])
                continue

            last_line = lines[-1]
            line_baseline = sum(float(item.baseline_y) for item in last_line) / len(last_line)
            tolerance = max(
                2.0,
                max(float(item.font_size_pt or raster.DEFAULT_TEXT_SIZE) for item in last_line + [element]) * 0.35,
            )
            if abs(float(element.baseline_y) - line_baseline) <= tolerance:
                last_line.append(element)
            else:
                lines.append([element])

        for line in lines:
            line.sort(key=lambda element: (float(element.x), int(element.source_order)))
        return lines

    def _line_text(self, line: List[TextElement]) -> str:
        parts: List[str] = []
        previous_right: Optional[float] = None
        previous_char_width = 8.0

        for element in line:
            if previous_right is not None:
                gap = float(element.x) - previous_right
                if gap > max(4.0, previous_char_width * 0.75):
                    spaces = min(4, max(1, int(round(gap / max(previous_char_width, 4.0)))))
                    parts.append(" " * spaces)
            parts.append(element.text)
            previous_right = float(element.x + element.width)
            char_count = max(1, len(element.text))
            previous_char_width = max(1.0, float(element.width) / char_count)

        return "".join(parts).rstrip()

    def _dominant_text_style(self, text_elements: List[TextElement]) -> Dict[str, object]:
        style_weights: Dict[Tuple[object, ...], int] = {}
        for element in text_elements:
            style_key = (
                int(element.color_int),
                int(element.background_color_int) if isinstance(element.background_color_int, int) else None,
                float(element.font_size_pt or raster.DEFAULT_TEXT_SIZE),
                str(element.font_name or ""),
                bool(element.is_bold),
                bool(element.is_italic),
            )
            style_weights[style_key] = style_weights.get(style_key, 0) + max(1, len(element.text))

        dominant_key = max(style_weights.items(), key=lambda item: item[1])[0]
        return {
            "color_int": dominant_key[0],
            "background_color_int": dominant_key[1],
            "font_size_pt": dominant_key[2],
            "font_name": dominant_key[3],
            "is_bold": dominant_key[4],
            "is_italic": dominant_key[5],
        }
