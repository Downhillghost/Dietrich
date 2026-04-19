from __future__ import annotations

import os
import tempfile
import zipfile
from hashlib import sha1
from typing import Dict, List, Optional, Tuple

from note_pipeline.input.base import NoteImporter
from note_pipeline.input.samsung_notes.constants import DEFAULT_TEXT_COLOR, PDF_OVERLAY_TAGS_TO_STRIP
from note_pipeline.input.samsung_notes.package import (
    build_layered_draw_items,
    list_page_files,
    looks_like_note_root,
    resolve_note_root,
    should_skip_trailing_placeholder_page,
)
from note_pipeline.input.samsung_notes.note_adapters import note_source_to_metadata
from note_pipeline.input.samsung_notes.parsers import SpenNotesPageParser
from note_pipeline.input.samsung_notes.source import SamsungNoteSource, load_samsung_note_source
from note_pipeline.input.samsung_notes.spi import scan_spi_files
from note_pipeline.input.samsung_notes.text import materialize_keyboard_text_from_source
from note_pipeline.model import (
    Asset,
    ImageElement,
    NoteBackground,
    NoteDocument,
    NotePage,
    PdfBackgroundElement,
    SourceInfo,
    StrokeElement,
    TextElement,
    UnsupportedElement,
)


def _stable_id(*parts: object) -> str:
    digest = sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _float_series(value: object) -> List[float]:
    if not isinstance(value, list):
        return []
    result: List[float] = []
    for item in value:
        if isinstance(item, (int, float)):
            result.append(float(item))
    return result


def _int_series(value: object) -> List[int]:
    if not isinstance(value, list):
        return []
    result: List[int] = []
    for item in value:
        if isinstance(item, (int, float)):
            result.append(int(item))
    return result


class SamsungNotesImporter(NoteImporter):
    @classmethod
    def supports_path(cls, note_source: str) -> bool:
        source_path = os.path.abspath(note_source)
        if os.path.isfile(source_path) and source_path.lower().endswith(".sdocx"):
            return True
        if not os.path.isdir(source_path):
            return False
        resolved_root = resolve_note_root(source_path)
        return looks_like_note_root(resolved_root)

    def __init__(self, text_scale_override: Optional[float] = None):
        self.text_scale_override = text_scale_override
        self._temp_dirs: List[tempfile.TemporaryDirectory[str]] = []

    def close(self) -> None:
        while self._temp_dirs:
            temp_dir = self._temp_dirs.pop()
            temp_dir.cleanup()

    def import_path(self, note_source: str) -> NoteDocument:
        note_root, source_info = self._prepare_source(note_source)

        samsung_note_source: Optional[SamsungNoteSource] = None
        note_metadata: Dict[str, object] = {}
        note_path = os.path.join(note_root, "note.note")
        if os.path.exists(note_path):
            samsung_note_source = load_samsung_note_source(note_path)
            note_metadata = note_source_to_metadata(samsung_note_source)
        spi_asset_records = scan_spi_files(note_root)

        page_files = list_page_files(note_root)
        page_records: List[Dict[str, object]] = []
        for page_path in page_files:
            page_parser = SpenNotesPageParser(page_path, note_root=note_root)
            page_records.append(
                {
                    "page_path": page_path,
                    "metadata": page_parser.extract_page_metadata(),
                    "background_records": page_parser.extract_background_records(),
                    "stroke_records": page_parser.extract_stroke_records(),
                    "image_records": page_parser.extract_image_records(),
                }
            )

        keyboard_layout, resolved_text_scale, text_scale_reason = materialize_keyboard_text_from_source(
            note_source=samsung_note_source,
            page_metadatas=[record["metadata"] for record in page_records],
            page_image_records=[record["image_records"] for record in page_records],
            text_scale_override=self.text_scale_override,
        )

        if any(record["background_records"] for record in page_records):
            while page_records:
                last_index = len(page_records) - 1
                last_text_segments = keyboard_layout["pages"][last_index] if last_index < len(keyboard_layout["pages"]) else []
                if not should_skip_trailing_placeholder_page(page_records[last_index], last_text_segments):
                    break
                page_records.pop()
                if last_index < len(keyboard_layout["pages"]):
                    keyboard_layout["pages"].pop()

        assets: Dict[str, Asset] = {}
        asset_key_to_id: Dict[Tuple[Optional[str], Optional[str], str], str] = {}
        for spi_record in spi_asset_records:
            bind_id = spi_record.get("bind_id")
            source_ref = str(bind_id) if bind_id is not None else str(spi_record.get("filename") or "")
            self._register_asset(
                assets=assets,
                asset_key_to_id=asset_key_to_id,
                media_type="samsung_spi",
                source_path=str(spi_record.get("path") or "") or None,
                source_ref=source_ref or None,
                vendor_extensions={"samsung_notes": dict(spi_record)},
            )
        pages: List[NotePage] = []
        for page_index, page_record in enumerate(page_records):
            text_segments = keyboard_layout["pages"][page_index] if page_index < len(keyboard_layout["pages"]) else []
            page = self._build_page(
                page_record=page_record,
                page_index=page_index,
                text_segments=text_segments,
                assets=assets,
                asset_key_to_id=asset_key_to_id,
            )
            pages.append(page)

        note_id = str(note_metadata.get("note_id") or source_info.display_name)
        return NoteDocument(
            source=source_info,
            note_id=note_id,
            title=source_info.display_name,
            layout_kind="pages",
            metadata={
                "text_scale": resolved_text_scale,
                "text_scale_reason": text_scale_reason,
                "page_count": len(pages),
                "width": note_metadata.get("width"),
                "height": note_metadata.get("height"),
                "page_horizontal_padding": note_metadata.get("page_horizontal_padding"),
                "page_vertical_padding": note_metadata.get("page_vertical_padding"),
                "spi_asset_count": len(spi_asset_records),
            },
            pages=pages,
            assets=assets,
            vendor_extensions={
                "samsung_notes": {
                    "note_metadata": note_metadata,
                    "keyboard_layout": {
                        "truncated": keyboard_layout.get("truncated"),
                        "line_count": keyboard_layout.get("line_count"),
                        "segment_count": keyboard_layout.get("segment_count"),
                        "character_count": keyboard_layout.get("character_count"),
                    },
                    "body_text": note_metadata.get("body_text"),
                }
            },
        )

    def _prepare_source(self, note_source: str) -> Tuple[str, SourceInfo]:
        source_path = os.path.abspath(note_source)
        if os.path.isdir(source_path):
            note_root = resolve_note_root(source_path)
            return note_root, SourceInfo(
                source_path=source_path,
                source_kind="samsung_notes_folder",
                note_root=note_root,
                display_name=os.path.basename(os.path.normpath(note_root)),
                extracted_from_archive=False,
            )

        if os.path.isfile(source_path) and source_path.lower().endswith(".sdocx"):
            temp_dir = tempfile.TemporaryDirectory(prefix="samsung_notes_pipeline_")
            self._temp_dirs.append(temp_dir)
            with zipfile.ZipFile(source_path, "r") as archive:
                archive.extractall(temp_dir.name)
            note_root = resolve_note_root(temp_dir.name)
            return note_root, SourceInfo(
                source_path=source_path,
                source_kind="samsung_notes_sdocx",
                note_root=note_root,
                display_name=os.path.splitext(os.path.basename(source_path))[0],
                extracted_from_archive=True,
                source_archive_path=source_path,
            )

        raise FileNotFoundError(f"Unsupported Samsung Notes input path: {source_path}")

    def _register_asset(
        self,
        assets: Dict[str, Asset],
        asset_key_to_id: Dict[Tuple[Optional[str], Optional[str], str], str],
        media_type: str,
        source_path: Optional[str],
        source_ref: Optional[str],
        vendor_extensions: Optional[Dict[str, object]] = None,
    ) -> Optional[str]:
        if source_path is None and source_ref is None:
            return None

        key = (source_path, source_ref, media_type)
        asset_id = asset_key_to_id.get(key)
        if asset_id is not None:
            return asset_id

        asset_id = f"asset-{_stable_id(media_type, source_path or '', source_ref or '')}"
        asset_key_to_id[key] = asset_id
        assets[asset_id] = Asset(
            asset_id=asset_id,
            media_type=media_type,
            source_path=source_path,
            source_ref=source_ref,
            vendor_extensions=vendor_extensions or {},
        )
        return asset_id

    def _build_page(
        self,
        page_record: Dict[str, object],
        page_index: int,
        text_segments: List[Dict[str, object]],
        assets: Dict[str, Asset],
        asset_key_to_id: Dict[Tuple[Optional[str], Optional[str], str], str],
    ) -> NotePage:
        metadata = page_record["metadata"]
        page_path = str(page_record["page_path"])
        page_id = str(metadata.get("page_uuid") or os.path.splitext(os.path.basename(page_path))[0])
        page = NotePage(
            page_id=page_id,
            index=page_index,
            width=int(metadata.get("page_width") or 0),
            height=int(metadata.get("page_height") or 0),
            background=NoteBackground(
                color_int=metadata.get("background_color_int") if isinstance(metadata.get("background_color_int"), int) else None,
                color_argb=str(metadata.get("background_color_argb")) if metadata.get("background_color_argb") else None,
                vendor_extensions={"samsung_notes": dict(metadata)},
            ),
            vendor_extensions={
                "samsung_notes": {
                    "page_path": page_path,
                    "metadata": dict(metadata),
                }
            },
        )

        for background_index, background_record in enumerate(list(page_record["background_records"])):
            asset_id = self._register_asset(
                assets=assets,
                asset_key_to_id=asset_key_to_id,
                media_type="pdf_background",
                source_path=background_record.get("media_path"),
                source_ref=str(background_record.get("file_id")),
                vendor_extensions={"samsung_notes": dict(background_record)},
            )
            page.elements.append(
                PdfBackgroundElement(
                    element_id=f"background-{_stable_id(page_id, background_index, 'pdf')}",
                    rect=tuple(float(value) for value in background_record["rect"]),
                    asset_id=asset_id,
                    page_index=int(background_record.get("page_index") or 0),
                    layer_number=-1,
                    source_order=background_index,
                    z_index=background_index,
                    overlay_tags_to_strip=PDF_OVERLAY_TAGS_TO_STRIP,
                    vendor_extensions={"samsung_notes": dict(background_record)},
                )
            )

        for text_index, segment in enumerate(text_segments):
            if not segment.get("text"):
                continue
            page.elements.append(
                TextElement(
                    element_id=f"text-{_stable_id(page_id, text_index, segment.get('text'))}",
                    text=str(segment.get("text") or ""),
                    x=float(segment.get("x") or 0.0),
                    baseline_y=float(segment.get("baseline_y") or 0.0),
                    width=float(segment.get("width") or 0.0),
                    ascent=float(segment.get("ascent") or 0.0),
                    descent=float(segment.get("descent") or 0.0),
                    color_int=int(segment.get("color_int") or DEFAULT_TEXT_COLOR),
                    layer_number=int(segment.get("layer_number") or 0),
                    source_order=text_index,
                    z_index=300000 + text_index,
                    font_size_pt=float(segment.get("font_size_pt") or 0.0) if segment.get("font_size_pt") is not None else None,
                    font_name=str(segment.get("font_name") or "") or None,
                    is_bold=bool(segment.get("is_bold")),
                    is_italic=bool(segment.get("is_italic")),
                    underline=bool(segment.get("underline")),
                    underline_color_int=int(segment["underline_color_int"]) if isinstance(segment.get("underline_color_int"), int) else None,
                    strikethrough=bool(segment.get("strikethrough")),
                    background_color_int=int(segment["background_color_int"]) if isinstance(segment.get("background_color_int"), int) else None,
                    vendor_extensions={"samsung_notes": dict(segment)},
                )
            )

        layered_draw_items = build_layered_draw_items(
            list(page_record["stroke_records"]),
            list(page_record["image_records"]),
        )
        for draw_index, draw_item in enumerate(layered_draw_items):
            record = draw_item["record"]
            z_index = 400000 + draw_index
            if draw_item["kind"] == "image":
                asset_id = self._register_asset(
                    assets=assets,
                    asset_key_to_id=asset_key_to_id,
                    media_type="image",
                    source_path=record.get("media_path"),
                    source_ref=str(record.get("bind_id")) if record.get("bind_id") is not None else None,
                    vendor_extensions={"samsung_notes": dict(record)},
                )
                page.elements.append(
                    ImageElement(
                        element_id=f"image-{_stable_id(page_id, draw_index, record.get('bind_id'))}",
                        rect=tuple(float(value) for value in record["rect"]),
                        asset_id=asset_id,
                        layer_number=int(draw_item.get("layer_number") or 0),
                        source_order=draw_index,
                        z_index=z_index,
                        crop_rect=tuple(int(value) for value in record["crop_rect"]) if isinstance(record.get("crop_rect"), tuple) else None,
                        vendor_extensions={"samsung_notes": dict(record)},
                    )
                )
                continue

            page.elements.append(
                StrokeElement(
                    element_id=f"stroke-{_stable_id(page_id, draw_index, record.get('object_start', record.get('start')))}",
                    points=[(float(point[0]), float(point[1])) for point in record["points"]],
                    color_int=int(record.get("color_int") or 0),
                    color_hex_argb=str(record.get("color_hex_argb") or "0x00000000"),
                    rgba=tuple(float(value) for value in record["rgba"]),
                    pen_size=float(record.get("pen_size") or 0.0),
                    style=dict(record["style"]) if isinstance(record.get("style"), dict) else None,
                    layer_number=int(draw_item.get("layer_number") or 0),
                    source_order=draw_index,
                    z_index=z_index,
                    pressures=_float_series(record.get("pressures")),
                    timestamps=_int_series(record.get("timestamps")),
                    tilts=_float_series(record.get("tilts")),
                    orientations=_float_series(record.get("orientations")),
                    vendor_extensions={"samsung_notes": dict(record)},
                )
            )

        custom_objects = metadata.get("custom_objects")
        if isinstance(custom_objects, list):
            for custom_index, custom_object in enumerate(custom_objects):
                bounds = None
                if isinstance(custom_object, dict) and isinstance(custom_object.get("rect"), tuple):
                    bounds = tuple(float(value) for value in custom_object["rect"])
                page.elements.append(
                    UnsupportedElement(
                        element_id=f"unsupported-{_stable_id(page_id, custom_index, 'custom_object')}",
                        unsupported_type="samsung_custom_object",
                        layer_number=0,
                        source_order=500000 + custom_index,
                        z_index=500000 + custom_index,
                        bounds=bounds,
                        vendor_extensions={"samsung_notes": dict(custom_object) if isinstance(custom_object, dict) else {"value": custom_object}},
                    )
                )

        page.elements.sort(key=lambda element: (int(element.z_index), int(element.layer_number), int(element.source_order)))
        return page
