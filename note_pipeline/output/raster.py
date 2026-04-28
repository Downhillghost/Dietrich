from __future__ import annotations

import math
import os
from typing import Dict, Iterable, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

from note_pipeline.model import (
    FrameElement,
    ImageElement,
    IntRect,
    NoteDocument,
    PdfBackgroundElement,
    StrokeElement,
    TextElement,
    UnsupportedElement,
)


DEFAULT_RENDER_DPI = 100.0
DEFAULT_TEXT_COLOR = 0xFF252525
DEFAULT_TEXT_SIZE = 17.0
DEFAULT_TEXT_FONT = "DejaVu Sans"
DEFAULT_THICKNESS_SCALE = 0.6
DEFAULT_FRAME_LABEL_SIZE = 32.0

_PDF_PAGE_CACHE: Dict[Tuple[str, int, int, int, Tuple[str, ...]], Optional[object]] = {}
_PDF_RENDER_WARNING_EMITTED = False


def argb_to_rgba(color_int: int) -> Tuple[float, float, float, float]:
    argb = color_int & 0xFFFFFFFF
    alpha = (argb >> 24) & 0xFF
    red = (argb >> 16) & 0xFF
    green = (argb >> 8) & 0xFF
    blue = argb & 0xFF
    return (
        red / 255.0,
        green / 255.0,
        blue / 255.0,
        alpha / 255.0,
    )


def load_image_array(path: str):
    try:
        return plt.imread(path)
    except Exception as exc:
        print(f"  Warning: failed to load image '{path}': {exc}")
        return None


def crop_image_array(image_array, crop_rect: Optional[IntRect], image_label: str):
    if crop_rect is None:
        return image_array

    shape = getattr(image_array, "shape", ())
    if len(shape) < 2:
        print(f"  Warning: cannot apply crop rect to '{image_label}' because the bitmap shape is invalid.")
        return image_array

    left, top, right, bottom = crop_rect
    image_height = int(shape[0])
    image_width = int(shape[1])

    # The crop rect describes the source bitmap region; the element rect remains
    # the destination box and should not be replaced by crop coordinates.
    if left < 0 or top < 0 or right <= left or bottom <= top:
        print(f"  Warning: ignoring invalid crop rect {crop_rect} for '{image_label}'.")
        return image_array
    if right > image_width or bottom > image_height:
        print(
            f"  Warning: crop rect {crop_rect} exceeds bitmap bounds {image_width}x{image_height} "
            f"for '{image_label}', rendering the full image instead."
        )
        return image_array

    return image_array[top:bottom, left:right]


def make_font_properties(text_element: TextElement) -> FontProperties:
    return FontProperties(
        family=str(text_element.font_name or DEFAULT_TEXT_FONT),
        size=max(1.0, float(text_element.font_size_pt or DEFAULT_TEXT_SIZE)),
        weight="bold" if text_element.is_bold else "normal",
        style="italic" if text_element.is_italic else "normal",
    )


def _is_pdf_whitespace(byte_value: int) -> bool:
    return byte_value in (0x00, 0x09, 0x0A, 0x0C, 0x0D, 0x20)


def _is_pdf_delimiter(byte_value: int) -> bool:
    return byte_value in (0x28, 0x29, 0x3C, 0x3E, 0x5B, 0x5D, 0x7B, 0x7D, 0x2F, 0x25)


def _read_pdf_content_token(stream_data: bytes, offset: int):
    length = len(stream_data)
    pos = offset

    while pos < length:
        byte_value = stream_data[pos]
        if _is_pdf_whitespace(byte_value):
            pos += 1
            continue
        if byte_value == 0x25:  # '%'
            pos += 1
            while pos < length and stream_data[pos] not in (0x0A, 0x0D):
                pos += 1
            continue
        break

    if pos >= length:
        return None

    start = pos
    byte_value = stream_data[pos]

    if byte_value == 0x2F:  # name object
        pos += 1
        while pos < length and not _is_pdf_whitespace(stream_data[pos]) and not _is_pdf_delimiter(stream_data[pos]):
            pos += 1
        raw = stream_data[start:pos]
        return {
            "kind": "name",
            "value": raw[1:].decode("latin-1", errors="ignore"),
            "raw": raw,
            "start": start,
            "end": pos,
        }

    if byte_value == 0x28:  # literal string
        pos += 1
        depth = 1
        escaped = False
        while pos < length and depth > 0:
            current = stream_data[pos]
            if escaped:
                escaped = False
            elif current == 0x5C:  # '\'
                escaped = True
            elif current == 0x28:
                depth += 1
            elif current == 0x29:
                depth -= 1
            pos += 1
        return {
            "kind": "string",
            "value": None,
            "raw": stream_data[start:pos],
            "start": start,
            "end": pos,
        }

    if byte_value == 0x3C:  # '<'
        if pos + 1 < length and stream_data[pos + 1] == 0x3C:
            pos += 2
            return {
                "kind": "delimiter",
                "value": "<<",
                "raw": stream_data[start:pos],
                "start": start,
                "end": pos,
            }
        pos += 1
        while pos < length and stream_data[pos] != 0x3E:
            pos += 1
        pos += 1 if pos < length else 0
        return {
            "kind": "hex",
            "value": None,
            "raw": stream_data[start:pos],
            "start": start,
            "end": pos,
        }

    if byte_value == 0x3E and pos + 1 < length and stream_data[pos + 1] == 0x3E:
        pos += 2
        return {
            "kind": "delimiter",
            "value": ">>",
            "raw": stream_data[start:pos],
            "start": start,
            "end": pos,
        }

    if byte_value in (0x5B, 0x5D, 0x7B, 0x7D, 0x29):
        pos += 1
        return {
            "kind": "delimiter",
            "value": chr(byte_value),
            "raw": stream_data[start:pos],
            "start": start,
            "end": pos,
        }

    while pos < length and not _is_pdf_whitespace(stream_data[pos]) and not _is_pdf_delimiter(stream_data[pos]):
        pos += 1

    raw = stream_data[start:pos]
    return {
        "kind": "word",
        "value": raw.decode("latin-1", errors="ignore"),
        "raw": raw,
        "start": start,
        "end": pos,
    }


def _pdf_word_is_numeric(raw: bytes) -> bool:
    if not raw:
        return False

    has_digit = False
    for byte_value in raw:
        if 0x30 <= byte_value <= 0x39:
            has_digit = True
            continue
        if byte_value in (0x2B, 0x2D, 0x2E):
            continue
        return False
    return has_digit


def _pdf_word_is_operator(token: Dict[str, object]) -> bool:
    if token.get("kind") != "word":
        return False

    raw = token.get("raw")
    if not isinstance(raw, bytes) or _pdf_word_is_numeric(raw):
        return False

    value = str(token.get("value") or "")
    return value not in ("true", "false", "null")


def _strip_marked_content_blocks(stream_data: bytes, tag_names: Iterable[str]) -> Tuple[bytes, int]:
    target_tags = {str(tag) for tag in tag_names if tag}
    if not target_tags:
        return stream_data, 0

    operand_tokens: List[Dict[str, object]] = []
    removal_ranges: List[Tuple[int, int]] = []
    drop_depth = 0
    drop_start: Optional[int] = None
    cursor = 0

    while True:
        token = _read_pdf_content_token(stream_data, cursor)
        if token is None:
            break
        cursor = int(token["end"])

        if not _pdf_word_is_operator(token):
            if drop_depth == 0:
                operand_tokens.append(token)
            continue

        operator = str(token.get("value") or "")
        if drop_depth > 0:
            if operator in ("BMC", "BDC"):
                drop_depth += 1
            elif operator == "EMC":
                drop_depth -= 1
                if drop_depth == 0 and drop_start is not None:
                    removal_ranges.append((drop_start, int(token["end"])))
                    drop_start = None
            operand_tokens = []
            continue

        if operator in ("BMC", "BDC"):
            tag_token = operand_tokens[0] if operand_tokens else None
            tag_name = str(tag_token.get("value") or "") if tag_token and tag_token.get("kind") == "name" else ""
            if tag_name in target_tags and tag_token is not None:
                drop_depth = 1
                drop_start = int(tag_token["start"])

        operand_tokens = []

    if drop_depth > 0 and drop_start is not None:
        removal_ranges.append((drop_start, len(stream_data)))

    if not removal_ranges:
        return stream_data, 0

    merged_ranges: List[Tuple[int, int]] = []
    for start, end in sorted(removal_ranges):
        if not merged_ranges or start > merged_ranges[-1][1]:
            merged_ranges.append((start, end))
        else:
            merged_start, merged_end = merged_ranges[-1]
            merged_ranges[-1] = (merged_start, max(merged_end, end))

    parts: List[bytes] = []
    cursor = 0
    for start, end in merged_ranges:
        parts.append(stream_data[cursor:start])
        parts.append(b"\n")
        cursor = end
    parts.append(stream_data[cursor:])
    return b"".join(parts), len(merged_ranges)


def _open_cleaned_pdf_document(
    fitz_module,
    pdf_path: str,
    page_index: int,
    overlay_tags_to_strip: Iterable[str],
):
    try:
        with open(pdf_path, "rb") as pdf_file:
            raw_pdf_bytes = pdf_file.read()
        document = fitz_module.open(stream=raw_pdf_bytes, filetype="pdf")
    except Exception:
        return None, 0

    try:
        if not 0 <= page_index < document.page_count:
            document.close()
            return None, 0

        page = document.load_page(page_index)
        try:
            content_refs = page.get_contents()
        except Exception:
            document.close()
            return None, 0

        if isinstance(content_refs, int):
            content_xrefs = [content_refs]
        else:
            content_xrefs = [int(xref) for xref in content_refs or []]

        stripped_block_count = 0
        for xref in content_xrefs:
            if xref <= 0:
                continue
            try:
                stream_bytes = document.xref_stream(xref)
            except Exception:
                continue
            if not isinstance(stream_bytes, (bytes, bytearray)):
                continue

            stripped_stream, removed_blocks = _strip_marked_content_blocks(
                bytes(stream_bytes),
                overlay_tags_to_strip,
            )
            if removed_blocks <= 0:
                continue

            try:
                document.update_stream(xref, stripped_stream)
            except Exception:
                document.close()
                return None, 0
            stripped_block_count += removed_blocks

        if stripped_block_count <= 0:
            document.close()
            return None, 0
        return document, stripped_block_count
    except Exception:
        document.close()
        return None, 0


def warn_missing_pdf_renderer() -> None:
    global _PDF_RENDER_WARNING_EMITTED
    if _PDF_RENDER_WARNING_EMITTED:
        return
    print(
        "  Warning: PDF background pages require the optional PyMuPDF package "
        "(`pip install PyMuPDF`). PDF backgrounds will be skipped until it is available."
    )
    _PDF_RENDER_WARNING_EMITTED = True


def load_pdf_background_array(
    pdf_path: str,
    page_index: int,
    target_width: float,
    target_height: float,
    overlay_tags_to_strip: Iterable[str] = (),
):
    overlay_tags = tuple(str(tag) for tag in overlay_tags_to_strip if tag)
    cache_key = (
        os.path.abspath(pdf_path),
        int(page_index),
        max(1, int(round(target_width))),
        max(1, int(round(target_height))),
        overlay_tags,
    )
    if cache_key in _PDF_PAGE_CACHE:
        return _PDF_PAGE_CACHE[cache_key]

    try:
        import fitz
    except ImportError:
        warn_missing_pdf_renderer()
        _PDF_PAGE_CACHE[cache_key] = None
        return None

    try:
        with fitz.open(pdf_path) as original_document:
            if not 0 <= page_index < original_document.page_count:
                print(f"  Warning: PDF page index {page_index} is out of range for '{pdf_path}'.")
                _PDF_PAGE_CACHE[cache_key] = None
                return None

            cleaned_document = None
            stripped_block_count = 0
            try:
                if overlay_tags:
                    cleaned_document, stripped_block_count = _open_cleaned_pdf_document(
                        fitz,
                        pdf_path,
                        page_index,
                        overlay_tags,
                    )

                render_document = cleaned_document or original_document
                page = render_document.load_page(page_index)
                page_rect = page.rect
                if page_rect.width <= 0 or page_rect.height <= 0:
                    print(f"  Warning: PDF page {page_index} in '{pdf_path}' has invalid dimensions.")
                    _PDF_PAGE_CACHE[cache_key] = None
                    return None

                scale = max(
                    max(1.0, target_width) / max(1.0, float(page_rect.width)),
                    max(1.0, target_height) / max(1.0, float(page_rect.height)),
                    1.0,
                )
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                array = np.frombuffer(pixmap.samples, dtype=np.uint8).copy()
                array = array.reshape(pixmap.height, pixmap.width, pixmap.n)
                _PDF_PAGE_CACHE[cache_key] = array
                if stripped_block_count > 0:
                    print(
                        f"  PDF Cleanup:       removed {stripped_block_count} overlay block(s) "
                        f"from '{os.path.basename(pdf_path)}' page {page_index}."
                    )
                return array
            finally:
                if cleaned_document is not None:
                    cleaned_document.close()
    except Exception as exc:
        print(f"  Warning: failed to render PDF background '{pdf_path}' page {page_index}: {exc}")
        _PDF_PAGE_CACHE[cache_key] = None
        return None


def _asset_path(note: NoteDocument, asset_id: Optional[str]) -> Optional[str]:
    asset = note.assets.get(asset_id or "")
    return asset.source_path if asset is not None else None


def _element_sort_key(element) -> Tuple[int, int, int]:
    return (
        int(getattr(element, "z_index", 0)),
        int(getattr(element, "layer_number", 0)),
        int(getattr(element, "source_order", 0)),
    )


def compute_surface_bounds(surface) -> Tuple[float, float, float, float]:
    width = float(surface.width or 0.0)
    height = float(surface.height or 0.0)
    if width > 0.0 and height > 0.0:
        return 0.0, 0.0, width, height

    min_x: Optional[float] = None
    min_y: Optional[float] = None
    max_x: Optional[float] = None
    max_y: Optional[float] = None

    def add_rect(rect: Tuple[float, float, float, float]) -> None:
        nonlocal min_x, min_y, max_x, max_y
        left, top, right, bottom = rect
        min_x = left if min_x is None else min(min_x, left)
        min_y = top if min_y is None else min(min_y, top)
        max_x = right if max_x is None else max(max_x, right)
        max_y = bottom if max_y is None else max(max_y, bottom)

    for element in surface.elements:
        if isinstance(element, StrokeElement):
            for x, y in element.points:
                min_x = x if min_x is None else min(min_x, x)
                min_y = y if min_y is None else min(min_y, y)
                max_x = x if max_x is None else max(max_x, x)
                max_y = y if max_y is None else max(max_y, y)
        elif isinstance(element, (FrameElement, ImageElement, PdfBackgroundElement)):
            add_rect(element.rect)
        elif isinstance(element, TextElement):
            add_rect(
                (
                    float(element.x),
                    float(element.baseline_y - element.ascent),
                    float(element.x + element.width),
                    float(element.baseline_y + element.descent),
                )
            )
        elif isinstance(element, UnsupportedElement) and element.bounds is not None:
            add_rect(element.bounds)

    if None in (min_x, min_y, max_x, max_y):
        return 0.0, 0.0, 1000.0, 1000.0

    padding = 20.0
    return min_x - padding, min_y - padding, max_x + padding, max_y + padding


def _draw_text_element(ax, element: TextElement, zorder: float) -> None:
    if element.background_color_int is not None:
        ax.add_patch(
            Rectangle(
                (
                    float(element.x),
                    float(element.baseline_y) - float(element.ascent),
                ),
                float(element.width),
                float(element.ascent) + float(element.descent),
                facecolor=argb_to_rgba(element.background_color_int),
                edgecolor="none",
                zorder=zorder,
            )
        )

    color = argb_to_rgba(int(element.color_int or DEFAULT_TEXT_COLOR))
    ax.text(
        float(element.x),
        float(element.baseline_y),
        element.text,
        fontproperties=make_font_properties(element),
        color=color,
        ha="left",
        va="baseline",
        zorder=zorder + 0.01,
        clip_on=True,
    )

    if element.underline:
        underline_color = argb_to_rgba(element.underline_color_int or element.color_int or DEFAULT_TEXT_COLOR)
        underline_y = float(element.baseline_y) + max(1.0, float(element.descent) * 0.35)
        ax.plot(
            [float(element.x), float(element.x) + float(element.width)],
            [underline_y, underline_y],
            color=underline_color,
            linewidth=max(1.0, float(element.font_size_pt or 1.0) / 10.0),
            solid_capstyle="round",
            zorder=zorder + 0.02,
        )

    if element.strikethrough:
        strike_y = float(element.baseline_y) - max(1.0, float(element.ascent) * 0.35)
        ax.plot(
            [float(element.x), float(element.x) + float(element.width)],
            [strike_y, strike_y],
            color=color,
            linewidth=max(1.0, float(element.font_size_pt or 1.0) / 10.0),
            solid_capstyle="round",
            zorder=zorder + 0.02,
        )


def _finite_float_series(values: object, expected_length: int) -> List[float]:
    if not isinstance(values, list) or len(values) != expected_length:
        return []

    result: List[float] = []
    for value in values:
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return []
        result.append(float(value))
    return result


def _finite_int_series(values: object, expected_length: int) -> List[int]:
    if not isinstance(values, list) or len(values) != expected_length:
        return []

    result: List[int] = []
    for value in values:
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return []
        result.append(int(value))
    return result


def _stroke_pen_name(element: StrokeElement) -> str:
    style = element.style if isinstance(element.style, dict) else {}
    pen_name = style.get("pen_name")
    if isinstance(pen_name, str):
        return pen_name

    samsung_data = element.vendor_extensions.get("samsung_notes")
    if isinstance(samsung_data, dict):
        value = samsung_data.get("pen_name")
        if isinstance(value, str):
            return value
    return ""


def _segment_speed_factors(element: StrokeElement) -> List[float]:
    point_count = len(element.points)
    timestamps = _finite_int_series(element.timestamps, point_count)
    if point_count < 2 or not timestamps:
        return [1.0] * max(0, point_count - 1)

    speeds: List[float] = []
    for index in range(point_count - 1):
        x0, y0 = element.points[index]
        x1, y1 = element.points[index + 1]
        dt = max(1, timestamps[index + 1] - timestamps[index])
        speeds.append(math.hypot(float(x1) - float(x0), float(y1) - float(y0)) / float(dt))

    positive_speeds = [speed for speed in speeds if speed > 0.0 and math.isfinite(speed)]
    if not positive_speeds:
        return [1.0] * len(speeds)

    reference_speed = float(np.percentile(positive_speeds, 90))
    if reference_speed <= 0.0:
        return [1.0] * len(speeds)

    factors: List[float] = []
    for speed in speeds:
        normalized_speed = max(0.0, min(1.0, speed / reference_speed))
        factors.append(1.15 - (0.35 * normalized_speed))
    return factors


def _segment_direction_factors(element: StrokeElement) -> List[float]:
    point_count = len(element.points)
    if point_count < 2:
        return []

    pen_name = _stroke_pen_name(element).lower()
    nib_like = any(token in pen_name for token in ("fountain", "oblique", "calligraphy"))
    orientations = _finite_float_series(element.orientations, point_count)
    if not nib_like:
        return [1.0] * (point_count - 1)

    factors: List[float] = []
    for index in range(point_count - 1):
        x0, y0 = element.points[index]
        x1, y1 = element.points[index + 1]
        angle = math.atan2(float(y1) - float(y0), float(x1) - float(x0))
        if orientations:
            nib_angle = (orientations[index] + orientations[index + 1]) / 2.0
            factors.append(0.8 + (0.35 * abs(math.sin(angle - nib_angle))))
        else:
            factors.append(0.9 + (0.2 * abs(math.sin(angle + (math.pi / 4.0)))))
    return factors


def _stroke_segment_linewidths(element: StrokeElement, thickness_scale: float) -> List[float]:
    point_count = len(element.points)
    if point_count < 2:
        return []

    base_width = max(0.3, float(element.pen_size) * thickness_scale)
    pressures = _finite_float_series(element.pressures, point_count)
    if pressures:
        pressure_factors = [0.45 + (1.25 * math.sqrt(max(0.0, min(1.0, pressure)))) for pressure in pressures]
    else:
        pressure_factors = [1.0] * point_count

    speed_factors = _segment_speed_factors(element)
    direction_factors = _segment_direction_factors(element)
    widths: List[float] = []
    for index in range(point_count - 1):
        pressure_factor = (pressure_factors[index] + pressure_factors[index + 1]) / 2.0
        speed_factor = speed_factors[index] if index < len(speed_factors) else 1.0
        direction_factor = direction_factors[index] if index < len(direction_factors) else 1.0
        width = base_width * pressure_factor * speed_factor * direction_factor
        widths.append(max(0.3, min(base_width * 2.4, width)))
    return widths


def _draw_stroke_element(ax, element: StrokeElement, zorder: float, thickness_scale: float) -> None:
    xs = [point[0] for point in element.points]
    ys = [point[1] for point in element.points]
    linewidths = _stroke_segment_linewidths(element, thickness_scale)
    has_dynamic_width = bool(linewidths) and any(abs(width - linewidths[0]) > 0.01 for width in linewidths[1:])

    if not has_dynamic_width:
        render_width = max(0.3, float(element.pen_size) * thickness_scale)
        ax.plot(
            xs,
            ys,
            color=element.rgba,
            linewidth=render_width,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=zorder,
        )
        return

    segments = [
        [(xs[index], ys[index]), (xs[index + 1], ys[index + 1])]
        for index in range(len(element.points) - 1)
    ]
    collection = LineCollection(
        segments,
        colors=[element.rgba],
        linewidths=linewidths,
        zorder=zorder,
    )
    if hasattr(collection, "set_capstyle"):
        collection.set_capstyle("round")
    if hasattr(collection, "set_joinstyle"):
        collection.set_joinstyle("round")
    ax.add_collection(collection)


def render_surface_to_png(
    note: NoteDocument,
    surface,
    output_path: str,
    thickness_scale: float = DEFAULT_THICKNESS_SCALE,
    output_scale: float = 1.0,
) -> int:
    valid_backgrounds = [
        element
        for element in surface.elements
        if isinstance(element, PdfBackgroundElement) and _asset_path(note, element.asset_id) is not None
    ]
    valid_strokes = [
        element
        for element in surface.elements
        if isinstance(element, StrokeElement) and len(element.points) >= 2
    ]
    valid_images = [
        element
        for element in surface.elements
        if isinstance(element, ImageElement) and _asset_path(note, element.asset_id) is not None
    ]
    valid_frames = [
        element
        for element in surface.elements
        if isinstance(element, FrameElement)
    ]
    valid_text = [
        element
        for element in surface.elements
        if isinstance(element, TextElement) and element.text
    ]

    if not valid_backgrounds and not valid_strokes and not valid_images and not valid_text and not valid_frames:
        print("No meaningful backgrounds, strokes, images, frames, or text found.")
        return 0

    min_x, min_y, max_x, max_y = compute_surface_bounds(surface)
    canvas_width = max(1.0, max_x - min_x)
    canvas_height = max(1.0, max_y - min_y)
    base_dpi = DEFAULT_RENDER_DPI
    render_dpi = base_dpi * max(0.01, output_scale)
    fig = plt.figure(figsize=(canvas_width / base_dpi, canvas_height / base_dpi), dpi=render_dpi)
    ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])

    if surface.background.color_int is not None:
        face_color = argb_to_rgba(surface.background.color_int)
        ax.set_facecolor(face_color)
        fig.patch.set_facecolor(face_color)

    rendered_backgrounds: List[PdfBackgroundElement] = []
    renderable_elements = sorted(
        [*valid_backgrounds, *valid_frames, *valid_text, *valid_images, *valid_strokes],
        key=_element_sort_key,
    )
    for element in renderable_elements:
        zorder = float(element.z_index)
        if isinstance(element, PdfBackgroundElement):
            media_path = _asset_path(note, element.asset_id)
            if media_path is None:
                continue
            left, top, right, bottom = element.rect
            background_array = load_pdf_background_array(
                media_path,
                element.page_index,
                abs(float(right) - float(left)),
                abs(float(bottom) - float(top)),
                overlay_tags_to_strip=element.overlay_tags_to_strip,
            )
            if background_array is None:
                continue
            rendered_backgrounds.append(element)
            ax.imshow(
                background_array,
                extent=(left, right, bottom, top),
                origin="upper",
                zorder=zorder,
            )
            continue

        if isinstance(element, TextElement):
            _draw_text_element(ax, element, zorder)
            continue

        if isinstance(element, FrameElement):
            left, top, right, bottom = element.rect
            ax.add_patch(
                Rectangle(
                    (left, top),
                    right - left,
                    bottom - top,
                    fill=False,
                    edgecolor=element.rgba,
                    linewidth=max(0.5, float(element.stroke_width) * thickness_scale),
                    zorder=zorder,
                )
            )
            if element.name:
                label_size = max(1.0, float(element.label_font_size_pt or DEFAULT_FRAME_LABEL_SIZE))
                ax.text(
                    left,
                    top - 10.0,
                    str(element.name),
                    color=element.rgba,
                    fontsize=label_size,
                    va="bottom",
                    ha="left",
                    zorder=zorder + 0.1,
                )
            continue

        if isinstance(element, ImageElement):
            media_path = _asset_path(note, element.asset_id)
            if media_path is None:
                continue
            file_name = os.path.basename(media_path)
            image_array = load_image_array(media_path)
            if image_array is None:
                continue
            image_array = crop_image_array(image_array, element.crop_rect, file_name)
            left, top, right, bottom = element.rect
            ax.imshow(
                image_array,
                extent=(left, right, bottom, top),
                origin="upper",
                zorder=zorder,
            )
            continue

        if isinstance(element, StrokeElement):
            _draw_stroke_element(ax, element, zorder, thickness_scale)

    ax.set_xlim(min_x, max_x)
    ax.set_ylim(max_y, min_y)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    fig.savefig(output_path, dpi=render_dpi, facecolor=fig.get_facecolor(), pad_inches=0)
    plt.close(fig)

    print(
        f"Extraction complete! Found {len(rendered_backgrounds)} rendered background(s), "
        f"{len(valid_strokes)} rendered stroke(s), {len(valid_images)} rendered image(s), "
        f"and {len(valid_text)} rendered text segment(s)."
    )
    for index, background in enumerate(rendered_backgrounds[:10]):
        left, top, right, bottom = background.rect
        media_path = _asset_path(note, background.asset_id)
        file_name = os.path.basename(media_path) if media_path else ""
        print(
            f"  B{index + 1}: Rect=({left:.1f}, {top:.1f})-({right:.1f}, {bottom:.1f}) "
            f"Page={background.page_index} File={file_name}"
        )
    for index, stroke in enumerate(valid_strokes[:10]):
        first_point = stroke.points[0]
        print(
            f"  S{index + 1}: Start=({first_point[0]:.1f}, {first_point[1]:.1f}) "
            f"Pts={len(stroke.points)} Color={stroke.color_hex_argb} "
            f"PenSize={stroke.pen_size:.2f} Layer={stroke.layer_number}"
        )
    for index, image in enumerate(valid_images[:10]):
        left, top, right, bottom = image.rect
        media_path = _asset_path(note, image.asset_id)
        file_name = os.path.basename(media_path) if media_path else ""
        crop_suffix = f" Crop={image.crop_rect}" if image.crop_rect is not None else ""
        print(
            f"  I{index + 1}: Rect=({left:.1f}, {top:.1f})-({right:.1f}, {bottom:.1f}) "
            f"Layer={image.layer_number} File={file_name}{crop_suffix}"
        )
    for index, element in enumerate(valid_text[:5]):
        preview = element.text.replace("\n", "\\n")
        if len(preview) > 40:
            preview = preview[:37] + "..."
        print(
            f"  T{index + 1}: Pos=({float(element.x):.1f}, {float(element.baseline_y):.1f}) "
            f"Text='{preview}'"
        )
    print(f"Result saved to {output_path}")
    return len(rendered_backgrounds)


__all__ = [
    "DEFAULT_TEXT_COLOR",
    "DEFAULT_TEXT_SIZE",
    "DEFAULT_THICKNESS_SCALE",
    "argb_to_rgba",
    "compute_surface_bounds",
    "crop_image_array",
    "load_image_array",
    "load_pdf_background_array",
    "render_surface_to_png",
]



