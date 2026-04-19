from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.font_manager import FontProperties

from note_pipeline.input.samsung_notes.constants import (
    AUTO_TEXT_SCALE_PRESETS,
    AUTO_TEXT_SCALE_TOLERANCE,
    DEFAULT_RENDER_DPI,
    DEFAULT_TEXT_COLOR,
    DEFAULT_TEXT_FONT,
    DEFAULT_TEXT_SIZE,
    IMAGE_LAYOUT_WRAP_TEXT_AROUND,
    MAX_TEXT_SCALE,
    MIN_TEXT_SCALE,
    PARAGRAPH_TYPE_ALIGN,
    PARAGRAPH_TYPE_BULLET,
    PARAGRAPH_TYPE_DIRECTION,
    PARAGRAPH_TYPE_INDENT,
    PARAGRAPH_TYPE_LINE_SPACING,
    PARAGRAPH_TYPE_PARSING_STATE,
    SPAN_TYPE_BACKGROUND,
    SPAN_TYPE_BOLD,
    SPAN_TYPE_FONT_NAME,
    SPAN_TYPE_FONT_SIZE,
    SPAN_TYPE_FOREGROUND,
    SPAN_TYPE_ITALIC,
    SPAN_TYPE_STRIKETHROUGH,
    SPAN_TYPE_UNDERLINE,
)


class TextMeasurer:
    def __init__(self, dpi: float = DEFAULT_RENDER_DPI):
        self.dpi = dpi
        self.figure = plt.figure(figsize=(2.0, 2.0), dpi=dpi)
        self.canvas = FigureCanvasAgg(self.figure)
        self.canvas.draw()
        self.renderer = self.canvas.get_renderer()
        self._cache: Dict[Tuple[object, ...], Tuple[float, float, float]] = {}

    def measure(
        self,
        text: str,
        font_name: str,
        font_size_pt: float,
        bold: bool,
        italic: bool,
    ) -> Tuple[float, float, float]:
        if not text:
            return 0.0, 0.0, 0.0

        key = (
            text,
            font_name,
            round(font_size_pt, 3),
            bool(bold),
            bool(italic),
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        font_properties = FontProperties(
            family=font_name or DEFAULT_TEXT_FONT,
            size=max(1.0, font_size_pt),
            weight="bold" if bold else "normal",
            style="italic" if italic else "normal",
        )
        width, height, descent = self.renderer.get_text_width_height_descent(
            text,
            font_properties,
            ismath=False,
        )
        metrics = (float(width), float(height), float(descent))
        self._cache[key] = metrics
        return metrics

    def close(self) -> None:
        plt.close(self.figure)


def resolve_default_text_style() -> Dict[str, object]:
    return {
        "color_int": DEFAULT_TEXT_COLOR,
        "background_color_int": None,
        "font_size": DEFAULT_TEXT_SIZE,
        "font_name": DEFAULT_TEXT_FONT,
        "bold": False,
        "italic": False,
        "underline": False,
        "underline_color_int": None,
        "strikethrough": False,
    }


def apply_span_to_style(style: Dict[str, object], span: Dict[str, object]) -> None:
    span_type = int(span.get("type") or 0)
    value = span.get("value")

    if span_type == SPAN_TYPE_FOREGROUND and isinstance(value, int):
        style["color_int"] = value
    elif span_type == SPAN_TYPE_BACKGROUND and isinstance(value, int):
        alpha = (value & 0xFFFFFFFF) >> 24
        style["background_color_int"] = value if alpha else None
    elif span_type == SPAN_TYPE_FONT_SIZE and isinstance(value, float):
        style["font_size"] = max(1.0, value)
    elif span_type == SPAN_TYPE_FONT_NAME and isinstance(value, str) and value:
        style["font_name"] = value
    elif span_type == SPAN_TYPE_BOLD and isinstance(value, bool):
        style["bold"] = value
    elif span_type == SPAN_TYPE_ITALIC and isinstance(value, bool):
        style["italic"] = value
    elif span_type == SPAN_TYPE_UNDERLINE and isinstance(value, bool):
        style["underline"] = value
        underline_color = span.get("underline_color")
        if isinstance(underline_color, int):
            alpha = (underline_color & 0xFFFFFFFF) >> 24
            style["underline_color_int"] = underline_color if alpha else None
    elif span_type == SPAN_TYPE_STRIKETHROUGH and isinstance(value, bool):
        style["strikethrough"] = value


def build_character_styles(
    text: str,
    spans: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    styles = [resolve_default_text_style() for _ in text]
    for span in spans:
        start = max(0, min(len(text), int(span.get("start") or 0)))
        end = max(start, min(len(text), int(span.get("end") or 0)))
        for index in range(start, end):
            apply_span_to_style(styles[index], span)
    return styles


def split_paragraphs(text: str) -> List[Dict[str, int]]:
    paragraphs: List[Dict[str, int]] = []
    if not text:
        return [{"index": 0, "start": 0, "end": 0, "break_len": 0}]

    cursor = 0
    while cursor < len(text):
        end = cursor
        while end < len(text) and text[end] not in "\r\n":
            end += 1

        break_len = 0
        if end < len(text):
            break_len = 1
            if text[end] == "\r" and end + 1 < len(text) and text[end + 1] == "\n":
                break_len = 2

        paragraphs.append(
            {
                "index": len(paragraphs),
                "start": cursor,
                "end": end,
                "break_len": break_len,
            }
        )
        cursor = end + break_len

    if text.endswith("\r") or text.endswith("\n"):
        paragraphs.append(
            {
                "index": len(paragraphs),
                "start": len(text),
                "end": len(text),
                "break_len": 0,
            }
        )

    return paragraphs


def resolve_paragraph_style(
    paragraph_index: int,
    paragraph_records: List[Dict[str, object]],
) -> Dict[str, object]:
    style: Dict[str, object] = {
        "align": 0,
        "indent_level": 0,
        "indent_direction": 0,
        "line_spacing_type": 0,
        "line_spacing": 0.0,
        "bullet_type": 0,
        "bullet_value": 0,
        "bullet_checked": False,
        "direction": 0,
        "parsing_state": None,
    }

    for record in paragraph_records:
        record_start = int(record.get("start") or 0)
        record_end = int(record.get("end") or 0)
        if not (record_start <= paragraph_index < max(record_end, record_start + 1)):
            continue

        record_type = int(record.get("type") or 0)
        if record_type == PARAGRAPH_TYPE_DIRECTION:
            style["direction"] = int(record.get("value") or 0)
        elif record_type == PARAGRAPH_TYPE_INDENT:
            style["indent_level"] = int(record.get("level") or 0)
            style["indent_direction"] = int(record.get("direction") or 0)
        elif record_type == PARAGRAPH_TYPE_ALIGN:
            style["align"] = int(record.get("value") or 0)
        elif record_type == PARAGRAPH_TYPE_LINE_SPACING:
            style["line_spacing_type"] = int(record.get("spacing_type") or 0)
            style["line_spacing"] = float(record.get("spacing") or 0.0)
        elif record_type == PARAGRAPH_TYPE_BULLET:
            style["bullet_type"] = int(record.get("bullet_type") or 0)
            style["bullet_value"] = int(record.get("bullet_value") or 0)
            style["bullet_checked"] = bool(record.get("checked"))
        elif record_type == PARAGRAPH_TYPE_PARSING_STATE:
            style["parsing_state"] = bool(record.get("value"))

    return style


def roman_numeral(value: int) -> str:
    numerals = [
        (1000, "m"),
        (900, "cm"),
        (500, "d"),
        (400, "cd"),
        (100, "c"),
        (90, "xc"),
        (50, "l"),
        (40, "xl"),
        (10, "x"),
        (9, "ix"),
        (5, "v"),
        (4, "iv"),
        (1, "i"),
    ]
    remaining = max(1, value)
    result = []
    for amount, glyph in numerals:
        while remaining >= amount:
            result.append(glyph)
            remaining -= amount
    return "".join(result)


def bullet_marker_for_style(style: Dict[str, object], paragraph_index: int) -> str:
    bullet_type = int(style.get("bullet_type") or 0)
    bullet_value = int(style.get("bullet_value") or 0)
    counter = bullet_value if bullet_value > 0 else paragraph_index + 1

    if bullet_type == 1:
        return ">"
    if bullet_type == 2:
        return "[x]" if style.get("bullet_checked") else "[ ]"
    if bullet_type == 3:
        return "<>"
    if bullet_type == 4:
        return f"{counter}."
    if bullet_type == 5:
        return f"({counter})"
    if bullet_type == 6:
        letter_index = max(0, counter - 1) % 26
        return f"{chr(ord('a') + letter_index)}."
    if bullet_type == 7:
        return f"{roman_numeral(counter)}."
    if bullet_type == 8:
        return "*"
    return ""


def wrap_char_items(
    char_items: List[Dict[str, object]],
    start_index: int,
    available_width: float,
) -> Tuple[List[Dict[str, object]], int]:
    if start_index >= len(char_items):
        return [], start_index
    if available_width <= 0.0:
        return [char_items[start_index]], start_index + 1

    width = 0.0
    last_break_index: Optional[int] = None
    index = start_index

    while index < len(char_items):
        next_width = width + float(char_items[index]["width"])
        if next_width > available_width and index > start_index:
            break

        width = next_width
        if char_items[index]["char"] in (" ", "\t"):
            last_break_index = index
        index += 1

    if index >= len(char_items):
        return char_items[start_index:index], index

    if last_break_index is not None and last_break_index >= start_index:
        end_index = last_break_index
        while end_index > start_index and char_items[end_index - 1]["char"] in (" ", "\t"):
            end_index -= 1

        next_index = last_break_index + 1
        while next_index < len(char_items) and char_items[next_index]["char"] in (" ", "\t"):
            next_index += 1

        if end_index == start_index:
            return char_items[start_index : last_break_index + 1], last_break_index + 1
        return char_items[start_index:end_index], next_index

    if index == start_index:
        return [char_items[start_index]], start_index + 1
    return char_items[start_index:index], index


def style_signature(item: Dict[str, object]) -> Tuple[object, ...]:
    return (
        item.get("color_int"),
        item.get("background_color_int"),
        item.get("font_name"),
        round(float(item.get("font_size_pt") or 0.0), 3),
        bool(item.get("bold")),
        bool(item.get("italic")),
        bool(item.get("underline")),
        item.get("underline_color_int"),
        bool(item.get("strikethrough")),
    )


def build_segment_records(
    line_chars: List[Dict[str, object]],
    start_x: float,
    baseline_y: float,
) -> List[Dict[str, object]]:
    if not line_chars:
        return []

    segments: List[Dict[str, object]] = []
    current_chars: List[str] = []
    current_signature: Optional[Tuple[object, ...]] = None
    current_start_x = start_x
    current_width = 0.0
    current_ascent = 0.0
    current_descent = 0.0
    current_style: Optional[Dict[str, object]] = None
    cursor_x = start_x

    for item in line_chars:
        item_signature = style_signature(item)
        if current_signature is None:
            current_signature = item_signature
            current_style = item
            current_start_x = cursor_x
        elif item_signature != current_signature:
            segments.append(
                {
                    "text": "".join(current_chars),
                    "x": current_start_x,
                    "baseline_y": baseline_y,
                    "width": current_width,
                    "ascent": current_ascent,
                    "descent": current_descent,
                    "color_int": current_style["color_int"],
                    "background_color_int": current_style["background_color_int"],
                    "font_name": current_style["font_name"],
                    "font_size_pt": current_style["font_size_pt"],
                    "bold": current_style["bold"],
                    "italic": current_style["italic"],
                    "underline": current_style["underline"],
                    "underline_color_int": current_style["underline_color_int"],
                    "strikethrough": current_style["strikethrough"],
                }
            )
            current_chars = []
            current_signature = item_signature
            current_style = item
            current_start_x = cursor_x
            current_width = 0.0
            current_ascent = 0.0
            current_descent = 0.0

        current_chars.append(str(item["char"]))
        current_width += float(item["width"])
        current_ascent = max(current_ascent, float(item["ascent"]))
        current_descent = max(current_descent, float(item["descent"]))
        cursor_x += float(item["width"])

    if current_signature is not None and current_style is not None:
        segments.append(
            {
                "text": "".join(current_chars),
                "x": current_start_x,
                "baseline_y": baseline_y,
                "width": current_width,
                "ascent": current_ascent,
                "descent": current_descent,
                "color_int": current_style["color_int"],
                "background_color_int": current_style["background_color_int"],
                "font_name": current_style["font_name"],
                "font_size_pt": current_style["font_size_pt"],
                "bold": current_style["bold"],
                "italic": current_style["italic"],
                "underline": current_style["underline"],
                "underline_color_int": current_style["underline_color_int"],
                "strikethrough": current_style["strikethrough"],
            }
        )

    return segments


def build_segment_records_in_fragments(
    line_chars: List[Dict[str, object]],
    fragments: List[Tuple[float, float]],
    baseline_y: float,
) -> List[Dict[str, object]]:
    if not line_chars or not fragments:
        return []

    positioned_chars: List[Tuple[Dict[str, object], float]] = []
    fragment_index = 0
    cursor_x = fragments[0][0]

    for item in line_chars:
        width = float(item["width"])
        while fragment_index < len(fragments):
            fragment_left, fragment_right = fragments[fragment_index]
            if cursor_x < fragment_left:
                cursor_x = fragment_left

            remaining_width = fragment_right - cursor_x
            if width <= remaining_width + 0.5 or fragment_index == len(fragments) - 1:
                positioned_chars.append((item, cursor_x))
                cursor_x += width
                break

            fragment_index += 1
            if fragment_index < len(fragments):
                cursor_x = fragments[fragment_index][0]

    if not positioned_chars:
        return []

    segments: List[Dict[str, object]] = []
    current_chars: List[str] = []
    current_signature: Optional[Tuple[object, ...]] = None
    current_style: Optional[Dict[str, object]] = None
    current_start_x = 0.0
    current_width = 0.0
    current_ascent = 0.0
    current_descent = 0.0
    previous_right = 0.0

    for item, item_x in positioned_chars:
        item_signature = style_signature(item)
        item_width = float(item["width"])
        contiguous = current_signature is not None and abs(item_x - previous_right) <= 0.5

        if current_signature is None:
            current_chars = []
            current_signature = item_signature
            current_style = item
            current_start_x = item_x
            current_width = 0.0
            current_ascent = 0.0
            current_descent = 0.0
        elif item_signature != current_signature or not contiguous:
            if current_style is not None:
                segments.append(
                    {
                        "text": "".join(current_chars),
                        "x": current_start_x,
                        "baseline_y": baseline_y,
                        "width": current_width,
                        "ascent": current_ascent,
                        "descent": current_descent,
                        "color_int": current_style["color_int"],
                        "background_color_int": current_style["background_color_int"],
                        "font_name": current_style["font_name"],
                        "font_size_pt": current_style["font_size_pt"],
                        "bold": current_style["bold"],
                        "italic": current_style["italic"],
                        "underline": current_style["underline"],
                        "underline_color_int": current_style["underline_color_int"],
                        "strikethrough": current_style["strikethrough"],
                    }
                )
            current_chars = []
            current_signature = item_signature
            current_style = item
            current_start_x = item_x
            current_width = 0.0
            current_ascent = 0.0
            current_descent = 0.0

        current_chars.append(str(item["char"]))
        current_width += item_width
        current_ascent = max(current_ascent, float(item["ascent"]))
        current_descent = max(current_descent, float(item["descent"]))
        previous_right = item_x + item_width

    if current_signature is not None and current_style is not None:
        segments.append(
            {
                "text": "".join(current_chars),
                "x": current_start_x,
                "baseline_y": baseline_y,
                "width": current_width,
                "ascent": current_ascent,
                "descent": current_descent,
                "color_int": current_style["color_int"],
                "background_color_int": current_style["background_color_int"],
                "font_name": current_style["font_name"],
                "font_size_pt": current_style["font_size_pt"],
                "bold": current_style["bold"],
                "italic": current_style["italic"],
                "underline": current_style["underline"],
                "underline_color_int": current_style["underline_color_int"],
                "strikethrough": current_style["strikethrough"],
            }
        )

    return segments


def compute_line_height(
    base_height: float,
    base_font_px: float,
    paragraph_style: Dict[str, object],
    scale_y: float,
    text_scale: float,
) -> float:
    spacing_type = int(paragraph_style.get("line_spacing_type") or 0)
    spacing_value = float(paragraph_style.get("line_spacing") or 0.0)
    default_height = max(base_height, base_font_px * 1.2)

    if spacing_type == 1 and spacing_value > 0.0:
        return max(default_height, base_height * (spacing_value / 100.0))
    if spacing_type == 0 and spacing_value > 0.0:
        return max(default_height, base_height + (spacing_value * scale_y * text_scale))
    return default_height


def resolve_first_visible_text_line_top(
    line_top: float,
    line_height: float,
    image_rects: List[Tuple[float, float, float, float]],
    gap: float,
) -> float:
    adjusted_top = line_top
    while True:
        overlapping_bottoms = [
            bottom
            for _, top, _, bottom in image_rects
            if adjusted_top < bottom and adjusted_top + line_height > top
        ]
        if not overlapping_bottoms:
            return adjusted_top
        adjusted_top = max(adjusted_top, max(overlapping_bottoms) + gap)


def resolve_text_line_top_against_block_images(
    line_top: float,
    line_height: float,
    image_rects: List[Tuple[float, float, float, float]],
    gap: float,
) -> float:
    adjusted_top = line_top
    while True:
        overlapping_bottoms = [
            bottom
            for _, top, _, bottom in image_rects
            if adjusted_top < bottom and adjusted_top + line_height > top
        ]
        if not overlapping_bottoms:
            return adjusted_top
        adjusted_top = max(adjusted_top, max(overlapping_bottoms) + gap)


def subtract_interval(
    intervals: List[Tuple[float, float]],
    obstacle_left: float,
    obstacle_right: float,
) -> List[Tuple[float, float]]:
    remaining: List[Tuple[float, float]] = []
    for left, right in intervals:
        if obstacle_right <= left or obstacle_left >= right:
            remaining.append((left, right))
            continue
        if obstacle_left > left:
            remaining.append((left, min(obstacle_left, right)))
        if obstacle_right < right:
            remaining.append((max(obstacle_right, left), right))
    return [(left, right) for left, right in remaining if right - left > 1.0]


def resolve_wrap_text_fragments(
    line_left: float,
    line_right: float,
    line_top: float,
    line_height: float,
    image_rects: List[Tuple[float, float, float, float]],
    gap: float,
) -> Tuple[List[Tuple[float, float]], bool]:
    fragments: List[Tuple[float, float]] = [(line_left, line_right)]
    overlaps_image = False

    for left, top, right, bottom in image_rects:
        if line_top >= bottom or line_top + line_height <= top:
            continue
        overlaps_image = True
        fragments = subtract_interval(fragments, left - gap, right + gap)
        if not fragments:
            break

    return fragments, overlaps_image


def fragments_total_width(fragments: List[Tuple[float, float]]) -> float:
    return sum(max(0.0, right - left) for left, right in fragments)


def order_wrap_fragments(
    fragments: List[Tuple[float, float]],
    preferred_side: str,
) -> List[Tuple[float, float]]:
    if preferred_side == "right" and len(fragments) > 1:
        return list(reversed(fragments))
    return fragments


def build_text_section_ranges(
    text_length: int,
    page_count: int,
    sections: List[Dict[str, object]],
) -> List[Tuple[int, int]]:
    if page_count <= 0:
        return []

    if not sections:
        return [(0, text_length)] + [(text_length, text_length) for _ in range(page_count - 1)]

    ranges: List[Tuple[int, int]] = []
    for page_index in range(page_count):
        if page_index >= len(sections):
            ranges.append((text_length, text_length))
            continue

        start = max(0, min(text_length, int(sections[page_index].get("a") or 0)))
        length = max(0, int(sections[page_index].get("b") or 0))
        end = max(start, min(text_length, start + length))
        ranges.append((start, end))

    return ranges


def paragraph_intersects_text_range(
    paragraph: Dict[str, int],
    range_start: int,
    range_end: int,
) -> bool:
    paragraph_start = int(paragraph.get("start") or 0)
    paragraph_end = int(paragraph.get("end") or 0) + int(paragraph.get("break_len") or 0)
    if range_start == range_end:
        return paragraph_start == range_start and paragraph_end == range_end
    return paragraph_start < range_end and paragraph_end > range_start


def clamp_text_scale(value: float) -> float:
    return max(MIN_TEXT_SCALE, min(MAX_TEXT_SCALE, value))


def estimate_keyboard_text_scale(note_metadata: Dict[str, object]) -> Tuple[float, str]:
    note_width = float(note_metadata.get("width") or 0.0)
    if note_width <= 0.0:
        return 1.0, "fallback default (missing note width)"

    presets = AUTO_TEXT_SCALE_PRESETS
    if not presets:
        return 1.0, "fallback default (no auto-scale presets configured)"

    first_width, first_scale = presets[0]
    if abs(note_width - first_width) <= AUTO_TEXT_SCALE_TOLERANCE:
        return first_scale, f"auto from {first_width:.0f}-width note family"

    for lower, upper in zip(presets, presets[1:]):
        lower_width, lower_scale = lower
        upper_width, upper_scale = upper
        if abs(note_width - upper_width) <= AUTO_TEXT_SCALE_TOLERANCE:
            return upper_scale, f"auto from {upper_width:.0f}-width note family"
        if lower_width < note_width < upper_width:
            ratio = (note_width - lower_width) / (upper_width - lower_width)
            interpolated_scale = lower_scale + ((upper_scale - lower_scale) * ratio)
            return (
                clamp_text_scale(interpolated_scale),
                (
                    f"interpolated between {lower_width:.0f}- and "
                    f"{upper_width:.0f}-width note families"
                ),
            )

    if note_width < first_width:
        scaled = first_scale * (note_width / first_width)
        return clamp_text_scale(scaled), f"scaled from {first_width:.0f}-width note family"

    last_width, last_scale = presets[-1]
    scaled = last_scale * (note_width / last_width)
    return clamp_text_scale(scaled), f"scaled from {last_width:.0f}-width note family"


def build_keyboard_text_layout(
    note_metadata: Dict[str, object],
    body_text: Dict[str, object],
    page_metadatas: List[Dict[str, object]],
    page_image_records: Optional[List[List[Dict[str, object]]]] = None,
    dpi: float = DEFAULT_RENDER_DPI,
    text_scale: float = 1.0,
) -> Dict[str, object]:
    empty_result = {
        "pages": [[] for _ in page_metadatas],
        "truncated": False,
        "line_count": 0,
        "segment_count": 0,
        "character_count": 0,
    }
    if not page_metadatas:
        return empty_result

    text = str(body_text.get("text") or "")
    if not text:
        return empty_result

    note_width = float(note_metadata.get("width") or 0.0)
    note_height = float(note_metadata.get("height") or 0.0)
    horizontal_padding = float(note_metadata.get("page_horizontal_padding") or 0.0)
    vertical_padding = float(note_metadata.get("page_vertical_padding") or 0.0)
    page_width = float(page_metadatas[0].get("page_width") or 0.0)
    page_height = float(page_metadatas[0].get("page_height") or 0.0)
    page_count = len(page_metadatas)
    if page_width <= 0.0 or page_height <= 0.0 or page_count <= 0:
        return empty_result

    logical_page_width = max(1.0, note_width - (horizontal_padding * 2.0))
    logical_page_height = max(1.0, (note_height - (vertical_padding * 2.0)) / page_count)
    scale_x = page_width / logical_page_width
    scale_y = page_height / logical_page_height

    margins = body_text.get("margins", (16.0, 10.0, 16.0, 10.0))
    content_left = float(margins[0]) * scale_x
    content_top = float(margins[1]) * scale_y
    content_right = page_width - (float(margins[2]) * scale_x)
    content_bottom = page_height - (float(margins[3]) * scale_y)
    if content_right <= content_left:
        content_right = page_width
    if content_bottom <= content_top:
        content_bottom = page_height

    paragraph_records = list(body_text.get("paragraphs", []))
    character_styles = build_character_styles(text, list(body_text.get("spans", [])))
    paragraphs = split_paragraphs(text)
    paragraph_styles = [
        resolve_paragraph_style(int(paragraph["index"]), paragraph_records)
        for paragraph in paragraphs
    ]
    text_section_ranges = build_text_section_ranges(
        len(text),
        page_count,
        list(body_text.get("object_refs", [])),
    )
    per_page_segments: List[List[Dict[str, object]]] = [[] for _ in page_metadatas]
    page_block_image_rects: List[List[Tuple[float, float, float, float]]] = [[] for _ in page_metadatas]
    page_wrap_image_rects: List[List[Tuple[float, float, float, float]]] = [[] for _ in page_metadatas]
    page_legacy_first_line_image_rects: List[List[Tuple[float, float, float, float]]] = [[] for _ in page_metadatas]
    page_has_ambiguous_wrap_hint = [
        any(
            style.get("parsing_state") is False
            and paragraph_intersects_text_range(paragraphs[paragraph_index], section_start, section_end)
            for paragraph_index, style in enumerate(paragraph_styles)
        )
        for section_start, section_end in text_section_ranges
    ]
    if page_image_records:
        for page_index, records in enumerate(page_image_records[: len(page_block_image_rects)]):
            block_rects: List[Tuple[float, float, float, float]] = []
            wrap_rects: List[Tuple[float, float, float, float]] = []
            legacy_rects: List[Tuple[float, float, float, float]] = []
            for record in records:
                rect = record.get("rect")
                if not isinstance(rect, tuple) or len(rect) != 4:
                    continue
                normalized_rect = tuple(float(value) for value in rect)
                layout_type = record.get("layout_type")
                if isinstance(layout_type, int):
                    if layout_type == IMAGE_LAYOUT_WRAP_TEXT_AROUND:
                        wrap_rects.append(normalized_rect)
                    else:
                        block_rects.append(normalized_rect)
                else:
                    legacy_rects.append(normalized_rect)

            if page_has_ambiguous_wrap_hint[page_index] and block_rects and not wrap_rects:
                wrap_rects = list(block_rects)
                block_rects = []

            page_block_image_rects[page_index] = block_rects
            page_wrap_image_rects[page_index] = wrap_rects
            page_legacy_first_line_image_rects[page_index] = legacy_rects

    measurer = TextMeasurer(dpi=dpi)
    page_index = 0
    line_top = content_top
    line_count = 0
    truncated = False
    page_has_visible_text = [False for _ in page_metadatas]

    try:
        for paragraph_index, paragraph in enumerate(paragraphs):
            if page_index >= page_count:
                truncated = True
                break

            paragraph_style = paragraph_styles[paragraph_index]
            preferred_wrap_side = "right" if paragraph_style.get("parsing_state") is False else "left"
            raw_chars = []
            for char_index in range(paragraph["start"], paragraph["end"]):
                style = character_styles[char_index]
                font_size_px = max(
                    1.0,
                    float(style.get("font_size") or DEFAULT_TEXT_SIZE) * scale_y * text_scale,
                )
                font_size_pt = font_size_px * 72.0 / dpi
                width, height, descent = measurer.measure(
                    text[char_index],
                    str(style.get("font_name") or DEFAULT_TEXT_FONT),
                    font_size_pt,
                    bool(style.get("bold")),
                    bool(style.get("italic")),
                )
                raw_chars.append(
                    {
                        **style,
                        "char": text[char_index],
                        "width": width,
                        "height": height,
                        "ascent": max(0.0, height - descent),
                        "descent": descent,
                        "font_size_px": font_size_px,
                        "font_size_pt": font_size_pt,
                    }
                )

            marker = bullet_marker_for_style(paragraph_style, paragraph_index)
            if raw_chars:
                base_style = raw_chars[0]
            elif character_styles:
                style_index = min(paragraph["start"], len(character_styles) - 1)
                base_style = character_styles[style_index]
            else:
                base_style = resolve_default_text_style()

            base_font_px = max(
                1.0,
                float(base_style.get("font_size") or DEFAULT_TEXT_SIZE) * scale_y * text_scale,
            )
            base_font_pt = base_font_px * 72.0 / dpi
            _, base_height, base_descent = measurer.measure(
                "Ag",
                str(base_style.get("font_name") or DEFAULT_TEXT_FONT),
                base_font_pt,
                bool(base_style.get("bold")),
                bool(base_style.get("italic")),
            )
            base_ascent = max(0.0, base_height - base_descent)
            indent_level = max(0.0, float(paragraph_style.get("indent_level") or 0.0))
            indent_px = indent_level * max(16.0 * text_scale, base_font_px * 1.5)

            marker_item: Optional[Dict[str, object]] = None
            marker_total_width = 0.0
            if marker:
                marker_width, marker_height, marker_descent = measurer.measure(
                    marker,
                    str(base_style.get("font_name") or DEFAULT_TEXT_FONT),
                    base_font_pt,
                    bool(base_style.get("bold")),
                    bool(base_style.get("italic")),
                )
                marker_item = {
                    **base_style,
                    "char": marker,
                    "width": marker_width,
                    "height": marker_height,
                    "ascent": max(0.0, marker_height - marker_descent),
                    "descent": marker_descent,
                    "font_size_pt": base_font_pt,
                }
                marker_total_width = marker_width + max(4.0, base_font_px * 0.5)

            line_start = 0
            first_visual_line = True
            if not raw_chars:
                raw_chars = []

            while line_start < len(raw_chars) or (not raw_chars and first_visual_line):
                if page_index >= page_count:
                    truncated = True
                    break

                line_origin_x = content_left + indent_px
                text_origin_x = line_origin_x + (marker_total_width if marker else 0.0)
                block_image_rects = page_block_image_rects[page_index]
                wrap_image_rects = page_wrap_image_rects[page_index]
                gap = max(4.0, base_font_px * 0.15)
                available_width = max(1.0, content_right - text_origin_x)
                candidate_line_top = line_top
                line_chars: List[Dict[str, object]] = []
                next_index = line_start
                line_text_width = 0.0
                line_ascent = base_ascent
                line_descent = base_descent
                line_height = compute_line_height(
                    base_ascent + base_descent,
                    base_font_px,
                    paragraph_style,
                    scale_y,
                    text_scale,
                )
                wrap_fragments: List[Tuple[float, float]] = []
                uses_wrap_fragments = False

                for _ in range(3):
                    line_chars, next_index = wrap_char_items(raw_chars, line_start, available_width)
                    if not raw_chars:
                        next_index = line_start

                    line_text_width = sum(float(item["width"]) for item in line_chars)
                    line_ascent = max([float(item["ascent"]) for item in line_chars], default=base_ascent)
                    line_descent = max([float(item["descent"]) for item in line_chars], default=base_descent)
                    if first_visual_line and marker_item is not None:
                        line_ascent = max(line_ascent, float(marker_item["ascent"]))
                        line_descent = max(line_descent, float(marker_item["descent"]))

                    line_height = compute_line_height(
                        line_ascent + line_descent,
                        base_font_px,
                        paragraph_style,
                        scale_y,
                        text_scale,
                    )

                    candidate_line_top = line_top
                    if block_image_rects:
                        candidate_line_top = resolve_text_line_top_against_block_images(
                            candidate_line_top,
                            line_height,
                            block_image_rects,
                            gap,
                        )
                    elif line_chars and not page_has_visible_text[page_index]:
                        candidate_line_top = resolve_first_visible_text_line_top(
                            candidate_line_top,
                            line_height,
                            page_legacy_first_line_image_rects[page_index],
                            gap,
                        )

                    wrap_fragments = []
                    uses_wrap_fragments = False
                    if wrap_image_rects:
                        raw_fragments, overlaps_wrap = resolve_wrap_text_fragments(
                            text_origin_x,
                            content_right,
                            candidate_line_top,
                            line_height,
                            wrap_image_rects,
                            gap,
                        )
                        if overlaps_wrap and raw_fragments:
                            wrap_fragments = order_wrap_fragments(
                                raw_fragments,
                                preferred_wrap_side,
                            )
                            wrap_width = fragments_total_width(wrap_fragments)
                            uses_wrap_fragments = wrap_width > 1.0
                            if raw_chars and uses_wrap_fragments and abs(wrap_width - available_width) > 0.5:
                                available_width = wrap_width
                                continue
                    break

                if candidate_line_top + line_height > content_bottom and page_index + 1 < page_count:
                    page_index += 1
                    line_top = content_top
                    continue
                if candidate_line_top + line_height > content_bottom:
                    truncated = True
                    page_index = page_count
                    break

                baseline_y = candidate_line_top + line_ascent
                align = int(paragraph_style.get("align") or 0)
                line_shift = 0.0
                if not marker and not uses_wrap_fragments:
                    available_width = max(0.0, content_right - line_origin_x)
                    if align == 1:
                        line_shift = max(0.0, available_width - line_text_width)
                    elif align == 2:
                        line_shift = max(0.0, (available_width - line_text_width) / 2.0)

                if first_visual_line and marker_item is not None:
                    per_page_segments[page_index].append(
                        {
                            "text": marker,
                            "x": line_origin_x,
                            "baseline_y": baseline_y,
                            "width": float(marker_item["width"]),
                            "ascent": float(marker_item["ascent"]),
                            "descent": float(marker_item["descent"]),
                            "color_int": marker_item["color_int"],
                            "background_color_int": None,
                            "font_name": marker_item["font_name"],
                            "font_size_pt": marker_item["font_size_pt"],
                            "bold": marker_item["bold"],
                            "italic": marker_item["italic"],
                            "underline": False,
                            "underline_color_int": None,
                            "strikethrough": False,
                        }
                    )

                if uses_wrap_fragments:
                    per_page_segments[page_index].extend(
                        build_segment_records_in_fragments(
                            line_chars,
                            wrap_fragments,
                            baseline_y,
                        )
                    )
                else:
                    per_page_segments[page_index].extend(
                        build_segment_records(
                            line_chars,
                            text_origin_x + line_shift,
                            baseline_y,
                        )
                    )
                if line_chars:
                    page_has_visible_text[page_index] = True

                line_top = candidate_line_top + line_height
                line_count += 1
                first_visual_line = False

                if not raw_chars:
                    break
                line_start = next_index

            if truncated:
                break
    finally:
        measurer.close()

    return {
        "pages": per_page_segments,
        "truncated": truncated,
        "line_count": line_count,
        "segment_count": sum(len(page) for page in per_page_segments),
        "character_count": len(text),
        "scale_x": scale_x,
        "scale_y": scale_y,
        "logical_page_width": logical_page_width,
        "logical_page_height": logical_page_height,
    }
