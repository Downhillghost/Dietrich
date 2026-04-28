from __future__ import annotations

import json
import math
import mimetypes
import os
import re
from urllib.parse import unquote
from dataclasses import dataclass
from hashlib import sha1
from typing import Dict, Iterable, List, Optional, Tuple

from note_pipeline.input.base import NoteImporter
from note_pipeline.model import (
    Asset,
    FrameElement,
    ImageElement,
    NoteBackground,
    NoteCanvas,
    NoteDocument,
    NoteElement,
    NotePage,
    SourceInfo,
    StrokeElement,
    TextElement,
    UnsupportedElement,
)


Rect = Tuple[float, float, float, float]

DEFAULT_CANVAS_WIDTH = 1440
DEFAULT_CANVAS_HEIGHT = 2037
INFINITE_CANVAS_MARGIN = 120.0
STROKE_WIDTH_SCALE = 0.15
SHAPE_EDGE_STEP = 8.0
SHAPE_EDGE_MAX_SEGMENTS = 128
SHAPE_CORNER_REPEATS = 3
TEXT_FONT_SIZE_SCALE = 2.0 / 3.0
TEXT_BOX_WIDTH_SCALE = 1.0
TEXT_BOX_HEIGHT_SCALE = 1.0
FRAME_LABEL_FONT_SIZE = 32.0
ARROW_HEAD_ANGLE_RADIANS = math.radians(30.0)
_LZSTRING_BASE64_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
_LZSTRING_BASE64_INDEX = {char: index for index, char in enumerate(_LZSTRING_BASE64_ALPHABET)}


@dataclass(frozen=True)
class _FrameInfo:
    element_id: str
    name: str
    rect: Rect
    page: NotePage


def _stable_id(*parts: object) -> str:
    digest = sha1("::".join(str(part) for part in parts).encode("utf-8")).hexdigest()
    return digest[:16]


def _finite_number(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return default


def _is_deleted(element: Dict[str, object]) -> bool:
    return bool(element.get("isDeleted"))


def _normal_rect(x: float, y: float, width: float, height: float) -> Rect:
    left = min(x, x + width)
    top = min(y, y + height)
    right = max(x, x + width)
    bottom = max(y, y + height)
    return left, top, right, bottom


def _element_angle(element: Dict[str, object]) -> float:
    return _finite_number(element.get("angle"))


def _rotate_point(point: Tuple[float, float], center: Tuple[float, float], angle: float) -> Tuple[float, float]:
    if abs(angle) < 0.000001:
        return point
    px, py = point
    cx, cy = center
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    dx = px - cx
    dy = py - cy
    return (
        cx + (dx * cos_a) - (dy * sin_a),
        cy + (dx * sin_a) + (dy * cos_a),
    )


def _densify_closed_polyline(vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if len(vertices) < 2:
        return vertices

    points: List[Tuple[float, float]] = []
    for index, start in enumerate(vertices):
        end = vertices[(index + 1) % len(vertices)]
        points.extend(start for _ in range(SHAPE_CORNER_REPEATS))
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        segment_count = max(1, min(SHAPE_EDGE_MAX_SEGMENTS, int(math.ceil(length / SHAPE_EDGE_STEP))))
        for segment in range(1, segment_count):
            t = segment / segment_count
            points.append(
                (
                    start[0] + ((end[0] - start[0]) * t),
                    start[1] + ((end[1] - start[1]) * t),
                )
            )

    points.extend(vertices[0] for _ in range(SHAPE_CORNER_REPEATS))
    return points


def _densify_open_polyline(vertices: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    if len(vertices) < 2:
        return vertices

    points: List[Tuple[float, float]] = []
    for index, start in enumerate(vertices[:-1]):
        end = vertices[index + 1]
        if index == 0:
            points.extend(start for _ in range(SHAPE_CORNER_REPEATS))
        length = math.hypot(end[0] - start[0], end[1] - start[1])
        segment_count = max(1, min(SHAPE_EDGE_MAX_SEGMENTS, int(math.ceil(length / SHAPE_EDGE_STEP))))
        for segment in range(1, segment_count + 1):
            t = segment / segment_count
            points.append(
                (
                    start[0] + ((end[0] - start[0]) * t),
                    start[1] + ((end[1] - start[1]) * t),
                )
            )

    points.extend(vertices[-1] for _ in range(SHAPE_CORNER_REPEATS))
    return points


def _bounds_from_points(points: List[Tuple[float, float]]) -> Optional[Rect]:
    if not points:
        return None
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def _merge_bounds(bounds: Iterable[Rect]) -> Optional[Rect]:
    rects = list(bounds)
    if not rects:
        return None
    return (
        min(rect[0] for rect in rects),
        min(rect[1] for rect in rects),
        max(rect[2] for rect in rects),
        max(rect[3] for rect in rects),
    )


def _rect_contains(rect: Rect, x: float, y: float) -> bool:
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def _element_bounds(element: Dict[str, object]) -> Optional[Rect]:
    element_type = str(element.get("type") or "")
    x = _finite_number(element.get("x"))
    y = _finite_number(element.get("y"))

    if element_type == "freedraw":
        raw_points = element.get("points")
        if not isinstance(raw_points, list) or not raw_points:
            return None
        points: List[Tuple[float, float]] = []
        for point in raw_points:
            if not isinstance(point, list) or len(point) < 2:
                continue
            points.append((x + _finite_number(point[0]), y + _finite_number(point[1])))
        if not points:
            return None
        return (
            min(point[0] for point in points),
            min(point[1] for point in points),
            max(point[0] for point in points),
            max(point[1] for point in points),
        )

    width = _finite_number(element.get("width"))
    height = _finite_number(element.get("height"))
    angle = _element_angle(element)
    if abs(angle) >= 0.000001:
        left, top, right, bottom = _normal_rect(x, y, width, height)
        center = ((left + right) / 2.0, (top + bottom) / 2.0)
        rotated = [
            _rotate_point(point, center, angle)
            for point in ((left, top), (right, top), (right, bottom), (left, bottom))
        ]
        bounds = _bounds_from_points(rotated)
        if bounds is not None:
            return bounds
    return _normal_rect(x, y, width, height)


def _hex_to_argb(color: object, opacity: object = 100) -> int:
    if not isinstance(color, str) or color.lower() == "transparent":
        rgb = 0x000000
    else:
        value = color.strip()
        if value.startswith("#"):
            value = value[1:]
        if len(value) == 3:
            value = "".join(char * 2 for char in value)
        try:
            rgb = int(value[:6], 16)
        except ValueError:
            rgb = 0x000000

    alpha = max(0, min(255, int(round((_finite_number(opacity, 100.0) / 100.0) * 255))))
    return ((alpha << 24) | rgb) & 0xFFFFFFFF


def _argb_to_rgba(color_int: int) -> Tuple[float, float, float, float]:
    alpha = (color_int >> 24) & 0xFF
    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    return (
        red / 255.0,
        green / 255.0,
        blue / 255.0,
        alpha / 255.0,
    )


def _background_from_scene(scene: Dict[str, object]) -> NoteBackground:
    app_state = scene.get("appState")
    background_color = None
    if isinstance(app_state, dict):
        background_color = app_state.get("viewBackgroundColor")
    color_int = _hex_to_argb(background_color or "#ffffff", 100)
    return NoteBackground(color_int=color_int, color_argb=f"0x{color_int:08X}")


def _normalized_text(value: object) -> str:
    text = str(value or "")
    if not text:
        return ""
    try:
        text.encode("utf-16le")
        return text
    except UnicodeEncodeError:
        return text.encode("utf-16le", errors="surrogatepass").decode("utf-16le", errors="replace")


def _decode_json_text(text: str) -> Dict[str, object]:
    try:
        scene = json.loads(text)
    except json.JSONDecodeError:
        scene = json.loads(unquote(text))
    if not isinstance(scene, dict):
        raise ValueError("Excalidraw scene JSON must be an object")
    return scene


def _decompress_lzstring_base64(payload: str) -> str:
    compact = "".join(payload.split())
    if not compact:
        return ""
    return _decompress_lzstring(
        length=len(compact),
        reset_value=32,
        get_next_value=lambda index: _LZSTRING_BASE64_INDEX.get(compact[index], 0),
    )


def _decompress_lzstring(length: int, reset_value: int, get_next_value) -> str:
    dictionary: Dict[int, object] = {0: 0, 1: 1, 2: 2}
    enlarge_in = 4
    dict_size = 4
    num_bits = 3
    data_value = get_next_value(0)
    data_position = reset_value
    data_index = 1

    def read_bits(bit_count: int) -> int:
        nonlocal data_value, data_position, data_index
        bits = 0
        power = 1
        max_power = 1 << bit_count
        while power != max_power:
            resb = data_value & data_position
            data_position >>= 1
            if data_position == 0:
                data_position = reset_value
                data_value = get_next_value(data_index) if data_index < length else 0
                data_index += 1
            if resb > 0:
                bits |= power
            power <<= 1
        return bits

    next_value = read_bits(2)
    if next_value == 0:
        current = chr(read_bits(8))
    elif next_value == 1:
        current = chr(read_bits(16))
    elif next_value == 2:
        return ""
    else:
        raise ValueError("Invalid compressed Excalidraw payload")

    dictionary[3] = current
    previous = current
    result = [current]

    while True:
        if data_index > length:
            raise ValueError("Invalid compressed Excalidraw payload")

        code = read_bits(num_bits)
        if code == 0:
            dictionary[dict_size] = chr(read_bits(8))
            code = dict_size
            dict_size += 1
            enlarge_in -= 1
        elif code == 1:
            dictionary[dict_size] = chr(read_bits(16))
            code = dict_size
            dict_size += 1
            enlarge_in -= 1
        elif code == 2:
            return "".join(result)

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1

        if code in dictionary:
            entry = str(dictionary[code])
        elif code == dict_size:
            entry = previous + previous[0]
        else:
            raise ValueError("Invalid compressed Excalidraw payload")

        result.append(entry)
        dictionary[dict_size] = previous + entry[0]
        dict_size += 1
        enlarge_in -= 1
        previous = entry

        if enlarge_in == 0:
            enlarge_in = 1 << num_bits
            num_bits += 1


def _scene_from_markdown(text: str) -> Dict[str, object]:
    fence_pattern = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)
    for match in fence_pattern.finditer(text):
        language = match.group(1).strip().lower()
        payload = match.group(2).strip()
        if language == "compressed-json":
            return _decode_json_text(_decompress_lzstring_base64(payload))
        if language in ("json", "excalidraw-json", "excalidraw"):
            return _decode_json_text(payload)

    raise ValueError("No Excalidraw JSON block found in markdown file")


def _load_scene(source_path: str) -> Dict[str, object]:
    with open(source_path, "r", encoding="utf-8-sig") as handle:
        text = handle.read()

    stripped = text.lstrip()
    if stripped.startswith("{"):
        return _decode_json_text(stripped)
    return _scene_from_markdown(text)


def _embedded_file_refs(source_path: str) -> Dict[str, str]:
    try:
        with open(source_path, "r", encoding="utf-8-sig") as handle:
            text = handle.read()
    except OSError:
        return {}

    refs: Dict[str, str] = {}
    pattern = re.compile(r"^\s*([^:\s]+)\s*:\s*\[\[([^\]]+)\]\]", re.MULTILINE)
    for match in pattern.finditer(text):
        file_id = match.group(1).strip()
        ref = match.group(2).split("|", 1)[0].strip()
        if file_id and ref:
            refs[file_id] = ref.replace("\\", "/")
    return refs


def _guess_media_type(path: str, fallback: str = "image") -> str:
    media_type, _ = mimetypes.guess_type(path)
    return media_type or fallback


def _display_name_for_path(source_path: str) -> str:
    basename = os.path.basename(source_path)
    lower = basename.lower()
    if lower.endswith(".excalidraw.md"):
        return basename[: -len(".excalidraw.md")]
    return os.path.splitext(basename)[0]


class ExcalidrawImporter(NoteImporter):
    @classmethod
    def supports_path(cls, note_source: str) -> bool:
        source_path = os.path.abspath(note_source)
        lower_path = source_path.lower()
        return os.path.isfile(source_path) and (
            lower_path.endswith(".excalidraw") or lower_path.endswith(".excalidraw.md")
        )

    def __init__(self, text_scale_override: Optional[float] = None):
        self.text_scale_override = text_scale_override
        self._assets: Dict[str, Asset] = {}
        self._source_path = ""
        self._scene_files: Dict[str, object] = {}
        self._embedded_refs: Dict[str, str] = {}

    def import_path(self, note_source: str) -> NoteDocument:
        source_path = os.path.abspath(note_source)
        scene = _load_scene(source_path)

        raw_elements = scene.get("elements")
        if not isinstance(raw_elements, list):
            raw_elements = []
        elements = [element for element in raw_elements if isinstance(element, dict) and not _is_deleted(element)]
        frames = [element for element in elements if str(element.get("type") or "") == "frame"]
        drawable_elements = elements
        self._assets = {}
        self._source_path = source_path
        raw_files = scene.get("files")
        self._scene_files = dict(raw_files) if isinstance(raw_files, dict) else {}
        self._embedded_refs = _embedded_file_refs(source_path)

        source = SourceInfo(
            source_path=source_path,
            source_kind="excalidraw",
            note_root=os.path.dirname(source_path),
            display_name=_display_name_for_path(source_path),
        )
        note_id = str(scene.get("id") or source.display_name)
        background = _background_from_scene(scene)

        return self._import_infinite_canvas(
            source=source,
            note_id=note_id,
            scene=scene,
            drawable_elements=drawable_elements,
            background=background,
            frame_count=len(frames),
        )

    def _import_framed_scene(
        self,
        source: SourceInfo,
        note_id: str,
        scene: Dict[str, object],
        frames: List[Dict[str, object]],
        drawable_elements: List[Dict[str, object]],
        background: NoteBackground,
    ) -> NoteDocument:
        frame_infos: List[_FrameInfo] = []
        for index, frame in enumerate(sorted(frames, key=lambda item: (_finite_number(item.get("y")), _finite_number(item.get("x"))))):
            rect = _element_bounds(frame) or (0.0, 0.0, float(DEFAULT_CANVAS_WIDTH), float(DEFAULT_CANVAS_HEIGHT))
            width = max(1, int(math.ceil(rect[2] - rect[0])))
            height = max(1, int(math.ceil(rect[3] - rect[1])))
            frame_id = str(frame.get("id") or f"frame-{index}")
            page = NotePage(
                page_id=frame_id,
                index=index,
                width=width,
                height=height,
                background=background,
                vendor_extensions={
                    "excalidraw": {
                        "frame_id": frame_id,
                        "frame_name": _normalized_text(frame.get("name") or f"Page {index + 1}"),
                        "origin_x": rect[0],
                        "origin_y": rect[1],
                    }
                },
            )
            frame_infos.append(
                _FrameInfo(
                    element_id=frame_id,
                    name=_normalized_text(frame.get("name") or f"Page {index + 1}"),
                    rect=rect,
                    page=page,
                )
            )

        unassigned: List[Dict[str, object]] = []
        frame_by_id = {frame.element_id: frame for frame in frame_infos}
        for order, element in enumerate(drawable_elements):
            frame_ref = element.get("frameId")
            target = frame_by_id.get(str(frame_ref)) if frame_ref is not None else None
            if target is None:
                target = self._containing_frame(frame_infos, element)
            if target is None:
                unassigned.append(element)
                continue
            target.page.elements.extend(self._build_elements(element, target.rect[0], target.rect[1], order))

        pages = [frame.page for frame in frame_infos]
        if unassigned:
            pages.extend(
                self._build_unassigned_pages(
                    starting_index=len(pages),
                    elements=unassigned,
                    background=background,
                )
            )

        for page in pages:
            page.elements.sort(key=lambda element: (int(element.z_index), int(element.source_order)))

        return NoteDocument(
            source=source,
            note_id=note_id,
            title=source.display_name,
            layout_kind="pages",
            metadata={
                "source_format": "excalidraw",
                "frame_count": len(frame_infos),
                "unassigned_element_count": len(unassigned),
            },
            pages=pages,
            assets=dict(self._assets),
            vendor_extensions={"excalidraw": self._scene_summary(scene)},
        )

    def _import_infinite_canvas(
        self,
        source: SourceInfo,
        note_id: str,
        scene: Dict[str, object],
        drawable_elements: List[Dict[str, object]],
        background: NoteBackground,
        frame_count: int = 0,
    ) -> NoteDocument:
        bounds = _merge_bounds(rect for rect in (_element_bounds(element) for element in drawable_elements) if rect is not None)
        if bounds is None:
            origin_x = 0.0
            origin_y = 0.0
            width = DEFAULT_CANVAS_WIDTH
            height = DEFAULT_CANVAS_HEIGHT
        else:
            origin_x = math.floor(bounds[0] - INFINITE_CANVAS_MARGIN)
            origin_y = math.floor(bounds[1] - INFINITE_CANVAS_MARGIN)
            width = max(1, int(math.ceil(bounds[2] - origin_x + INFINITE_CANVAS_MARGIN)))
            height = max(1, int(math.ceil(bounds[3] - origin_y + INFINITE_CANVAS_MARGIN)))

        canvas = NoteCanvas(
            canvas_id=f"canvas-{_stable_id(source.source_path, 'infinite')}",
            index=0,
            origin_x=float(origin_x),
            origin_y=float(origin_y),
            width=width,
            height=height,
            background=background,
            vendor_extensions={
                "excalidraw": {
                    "origin_x": float(origin_x),
                    "origin_y": float(origin_y),
                    "content_bounds": bounds,
                    "materialized_margin": INFINITE_CANVAS_MARGIN,
                }
            },
        )
        built_by_order: Dict[int, List[str]] = {}
        for order, element in enumerate(drawable_elements):
            built_elements = self._build_elements(element, float(origin_x), float(origin_y), order)
            built_by_order[order] = [built.element_id for built in built_elements if not isinstance(built, FrameElement)]
            canvas.elements.extend(built_elements)
        self._assign_frame_children(drawable_elements, canvas.elements, built_by_order)
        canvas.elements.sort(key=lambda element: (int(element.z_index), int(element.source_order)))

        return NoteDocument(
            source=source,
            note_id=note_id,
            title=source.display_name,
            layout_kind="infinite_canvas",
            metadata={
                "source_format": "excalidraw",
                "materialized_width": width,
                "materialized_height": height,
                "frame_count": frame_count,
            },
            canvases=[canvas],
            assets=dict(self._assets),
            vendor_extensions={"excalidraw": self._scene_summary(scene)},
        )

    def _build_unassigned_pages(
        self,
        starting_index: int,
        elements: List[Dict[str, object]],
        background: NoteBackground,
    ) -> List[NotePage]:
        bounds = _merge_bounds(rect for rect in (_element_bounds(element) for element in elements) if rect is not None)
        if bounds is None:
            origin_x = 0.0
            origin_y = 0.0
            width = DEFAULT_CANVAS_WIDTH
            height = DEFAULT_CANVAS_HEIGHT
        else:
            origin_x = math.floor(bounds[0] - INFINITE_CANVAS_MARGIN)
            origin_y = math.floor(bounds[1] - INFINITE_CANVAS_MARGIN)
            width = max(1, int(math.ceil(bounds[2] - origin_x + INFINITE_CANVAS_MARGIN)))
            height = max(1, int(math.ceil(bounds[3] - origin_y + INFINITE_CANVAS_MARGIN)))

        page = NotePage(
            page_id=f"unframed-{_stable_id(starting_index, origin_x, origin_y)}",
            index=starting_index,
            width=width,
            height=height,
            background=background,
            vendor_extensions={
                "excalidraw": {
                    "origin_x": origin_x,
                    "origin_y": origin_y,
                    "source": "unassigned elements",
                }
            },
        )
        built_by_order: Dict[int, List[str]] = {}
        for order, element in enumerate(elements):
            built_elements = self._build_elements(element, float(origin_x), float(origin_y), order)
            built_by_order[order] = [built.element_id for built in built_elements if not isinstance(built, FrameElement)]
            page.elements.extend(built_elements)
        self._assign_frame_children(elements, page.elements, built_by_order)
        page.elements.sort(key=lambda element: (int(element.z_index), int(element.source_order)))
        return [page]

    def _containing_frame(self, frames: List[_FrameInfo], element: Dict[str, object]) -> Optional[_FrameInfo]:
        bounds = _element_bounds(element)
        if bounds is None:
            return None
        center_x = (bounds[0] + bounds[2]) / 2.0
        center_y = (bounds[1] + bounds[3]) / 2.0
        for frame in frames:
            if _rect_contains(frame.rect, center_x, center_y):
                return frame
        return None

    def _assign_frame_children(
        self,
        raw_elements: List[Dict[str, object]],
        note_elements: List[NoteElement],
        built_by_order: Dict[int, List[str]],
    ) -> None:
        frame_records: List[Tuple[int, str, Rect]] = []
        for order, raw_element in enumerate(raw_elements):
            if str(raw_element.get("type") or "") != "frame":
                continue
            frame_id = str(raw_element.get("id") or f"frame-{order}")
            bounds = _element_bounds(raw_element)
            if bounds is not None:
                frame_records.append((order, frame_id, bounds))

        if not frame_records:
            return

        frame_elements = {
            element.element_id: element for element in note_elements if isinstance(element, FrameElement)
        }
        child_ids_by_frame: Dict[str, List[str]] = {frame_id: [] for _, frame_id, _ in frame_records}
        frame_bounds_by_id = {frame_id: bounds for _, frame_id, bounds in frame_records}

        for order, raw_element in enumerate(raw_elements):
            if str(raw_element.get("type") or "") == "frame":
                continue
            child_ids = built_by_order.get(order, [])
            if not child_ids:
                continue

            frame_ref = raw_element.get("frameId")
            target_frame_id = str(frame_ref) if frame_ref is not None and str(frame_ref) in frame_bounds_by_id else None
            if target_frame_id is None:
                bounds = _element_bounds(raw_element)
                if bounds is None:
                    continue
                center_x = (bounds[0] + bounds[2]) / 2.0
                center_y = (bounds[1] + bounds[3]) / 2.0
                for _, frame_id, frame_bounds in frame_records:
                    if _rect_contains(frame_bounds, center_x, center_y):
                        target_frame_id = frame_id
                        break

            if target_frame_id is not None:
                child_ids_by_frame[target_frame_id].extend(child_ids)

        for frame_id, child_ids in child_ids_by_frame.items():
            frame_element = frame_elements.get(frame_id)
            if frame_element is not None:
                frame_element.child_element_ids = child_ids

    def _build_elements(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
        order: int,
    ) -> List[NoteElement]:
        element_type = str(element.get("type") or "")
        if element_type == "freedraw":
            note_element = self._build_stroke(element, origin_x, origin_y, order)
            return [note_element] if note_element is not None else []
        if element_type == "text":
            return [self._build_text(element, origin_x, origin_y, order)]
        if element_type == "image":
            return [self._build_image(element, origin_x, origin_y, order)]
        if element_type == "arrow":
            return self._build_arrow_strokes(element, origin_x, origin_y, order)
        if element_type in {"rectangle", "diamond", "ellipse", "line"}:
            note_element = self._build_shape_stroke(element, origin_x, origin_y, order)
            return [note_element] if note_element is not None else []
        if element_type == "frame":
            note_element = self._build_frame_element(element, origin_x, origin_y, order)
            return [note_element] if note_element is not None else []

        bounds = _element_bounds(element)
        return [UnsupportedElement(
            element_id=str(element.get("id") or f"unsupported-{order}"),
            unsupported_type=f"excalidraw_{element_type or 'unknown'}",
            layer_number=0,
            source_order=order,
            z_index=self._z_index(element, order),
            bounds=(
                (bounds[0] - origin_x, bounds[1] - origin_y, bounds[2] - origin_x, bounds[3] - origin_y)
                if bounds is not None
                else None
            ),
            vendor_extensions={"excalidraw": dict(element)},
        )]

    def _build_shape_stroke(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
        order: int,
    ) -> Optional[StrokeElement]:
        element_type = str(element.get("type") or "")
        points = self._shape_points(element, origin_x, origin_y)
        if len(points) < 2:
            return None

        return self._stroke_from_points(
            element=element,
            points=points,
            order=order,
            element_id=str(element.get("id") or f"{element_type}-{order}"),
            style_source="excalidraw-shape-outline",
            shape_type=element_type,
        )

    def _build_arrow_strokes(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
        order: int,
    ) -> List[StrokeElement]:
        shaft = self._build_shape_stroke(element, origin_x, origin_y, order)
        if shaft is None:
            return []

        points = list(shaft.points)
        end = points[-1]
        previous = next((point for point in reversed(points[:-1]) if math.hypot(end[0] - point[0], end[1] - point[1]) > 0.001), None)
        if previous is None:
            return [shaft]

        direction_length = math.hypot(end[0] - previous[0], end[1] - previous[1])
        shaft_length = sum(
            math.hypot(points[index + 1][0] - points[index][0], points[index + 1][1] - points[index][1])
            for index in range(len(points) - 1)
        )
        if direction_length <= 0.001 or shaft_length <= 0.001:
            return [shaft]

        stroke_width = max(0.5, _finite_number(element.get("strokeWidth"), 2.0))
        head_length = max(10.0, min(45.0, shaft_length * 0.12)) * max(0.7, min(1.8, stroke_width / 2.0))
        direction = math.atan2(end[1] - previous[1], end[0] - previous[0])
        back_direction = direction + math.pi
        head_points = [
            (
                end[0] + math.cos(back_direction + ARROW_HEAD_ANGLE_RADIANS) * head_length,
                end[1] + math.sin(back_direction + ARROW_HEAD_ANGLE_RADIANS) * head_length,
            ),
            (
                end[0] + math.cos(back_direction - ARROW_HEAD_ANGLE_RADIANS) * head_length,
                end[1] + math.sin(back_direction - ARROW_HEAD_ANGLE_RADIANS) * head_length,
            ),
        ]
        base_id = str(element.get("id") or f"arrow-{order}")
        heads = [
            self._stroke_from_points(
                element=element,
                points=_densify_open_polyline([end, head_point]),
                order=order,
                element_id=f"{base_id}-head-{index}",
                style_source="excalidraw-arrowhead",
                shape_type="arrow",
            )
            for index, head_point in enumerate(head_points, start=1)
        ]
        return [shaft, *(head for head in heads if head is not None)]

    def _build_frame_element(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
        order: int,
    ) -> Optional[FrameElement]:
        bounds = _element_bounds(element)
        if bounds is None:
            return None

        color_int = _hex_to_argb(element.get("strokeColor") or "#555555", element.get("opacity", 100))
        stroke_width = max(0.5, _finite_number(element.get("strokeWidth"), 2.0))
        return FrameElement(
            element_id=str(element.get("id") or f"frame-{order}"),
            rect=(bounds[0] - origin_x, bounds[1] - origin_y, bounds[2] - origin_x, bounds[3] - origin_y),
            name=_normalized_text(element.get("name") or "Frame"),
            color_int=color_int,
            color_hex_argb=f"0x{color_int:08X}",
            rgba=_argb_to_rgba(color_int),
            stroke_width=stroke_width,
            layer_number=0,
            source_order=order,
            z_index=self._z_index(element, order),
            label_font_size_pt=FRAME_LABEL_FONT_SIZE,
            vendor_extensions={"excalidraw": dict(element)},
        )

    def _build_image(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
        order: int,
    ) -> NoteElement:
        bounds = _element_bounds(element)
        file_id = str(element.get("fileId") or "")
        asset_id = self._register_image_asset(file_id)
        if bounds is None or asset_id is None:
            return UnsupportedElement(
                element_id=str(element.get("id") or f"image-{order}"),
                unsupported_type="excalidraw_image",
                layer_number=0,
                source_order=order,
                z_index=self._z_index(element, order),
                bounds=(
                    (bounds[0] - origin_x, bounds[1] - origin_y, bounds[2] - origin_x, bounds[3] - origin_y)
                    if bounds is not None
                    else None
                ),
                vendor_extensions={
                    "excalidraw": dict(element),
                    "reason": "missing_or_unresolved_image_asset",
                    "embedded_ref": self._embedded_refs.get(file_id),
                },
            )

        return ImageElement(
            element_id=str(element.get("id") or f"image-{order}"),
            rect=(bounds[0] - origin_x, bounds[1] - origin_y, bounds[2] - origin_x, bounds[3] - origin_y),
            asset_id=asset_id,
            layer_number=0,
            source_order=order,
            z_index=self._z_index(element, order),
            vendor_extensions={"excalidraw": dict(element)},
        )

    def _register_image_asset(self, file_id: str) -> Optional[str]:
        if not file_id:
            return None

        file_record = self._scene_files.get(file_id)
        if isinstance(file_record, dict):
            data_url = file_record.get("dataURL")
            if isinstance(data_url, str) and data_url.startswith("data:"):
                media_type = str(file_record.get("mimeType") or "image")
                filename = os.path.basename(self._embedded_refs.get(file_id, "")) or f"{file_id}"
                asset_id = f"asset-{_stable_id('excalidraw-data-url', self._source_path, file_id)}"
                self._assets.setdefault(
                    asset_id,
                    Asset(
                        asset_id=asset_id,
                        media_type=media_type,
                        source_path=None,
                        source_ref=file_id,
                        vendor_extensions={
                            "excalidraw": {
                                "file_id": file_id,
                                "filename": filename,
                                "data_url": data_url,
                                "file": dict(file_record),
                            }
                        },
                    ),
                )
                return asset_id

        source_path = self._resolve_embedded_file_path(file_id)
        if source_path is None:
            return None

        asset_id = f"asset-{_stable_id('excalidraw-image', source_path, file_id)}"
        self._assets.setdefault(
            asset_id,
            Asset(
                asset_id=asset_id,
                media_type=_guess_media_type(source_path),
                source_path=source_path,
                source_ref=file_id,
                vendor_extensions={
                    "excalidraw": {
                        "file_id": file_id,
                        "embedded_ref": self._embedded_refs.get(file_id),
                    }
                },
            ),
        )
        return asset_id

    def _resolve_embedded_file_path(self, file_id: str) -> Optional[str]:
        ref = self._embedded_refs.get(file_id)
        if not ref:
            return None
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", ref):
            return None

        source_dir = os.path.dirname(self._source_path)
        candidates: List[str] = []
        if os.path.isabs(ref):
            candidates.append(ref)
        else:
            basename = os.path.basename(ref)
            candidates.extend(
                [
                    os.path.join(source_dir, ref),
                    os.path.join(source_dir, basename),
                    os.path.join(source_dir, "attachments", ref),
                    os.path.join(source_dir, "attachments", basename),
                    os.path.join(source_dir, "assets", ref),
                    os.path.join(source_dir, "assets", basename),
                ]
            )

        for candidate in candidates:
            absolute = os.path.abspath(os.path.normpath(candidate))
            if os.path.isfile(absolute):
                return absolute

        basename = os.path.basename(ref)
        if basename:
            for root, _, files in os.walk(source_dir):
                if basename in files:
                    return os.path.abspath(os.path.join(root, basename))
        return None

    def _stroke_from_points(
        self,
        element: Dict[str, object],
        points: List[Tuple[float, float]],
        order: int,
        element_id: str,
        style_source: str,
        shape_type: str,
    ) -> StrokeElement:
        color_int = _hex_to_argb(element.get("strokeColor"), element.get("opacity", 100))
        stroke_width = max(0.5, _finite_number(element.get("strokeWidth"), 2.0))
        return StrokeElement(
            element_id=element_id,
            points=points,
            color_int=color_int,
            color_hex_argb=f"0x{color_int:08X}",
            rgba=_argb_to_rgba(color_int),
            pen_size=max(0.5, stroke_width / STROKE_WIDTH_SCALE),
            style={
                "source": style_source,
                "shape_type": shape_type,
                "stroke_width": stroke_width,
                "roughness": element.get("roughness"),
                "background_color": element.get("backgroundColor"),
            },
            layer_number=0,
            source_order=order,
            z_index=self._z_index(element, order),
            pressures=[0.5 for _ in points],
            timestamps=[index * 8 for index in range(len(points))],
            vendor_extensions={"excalidraw": dict(element)},
        )

    def _shape_points(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
    ) -> List[Tuple[float, float]]:
        element_type = str(element.get("type") or "")
        source_x = _finite_number(element.get("x"))
        source_y = _finite_number(element.get("y"))
        width = _finite_number(element.get("width"))
        height = _finite_number(element.get("height"))
        left, top, right, bottom = _normal_rect(source_x, source_y, width, height)
        center = ((left + right) / 2.0, (top + bottom) / 2.0)
        angle = _element_angle(element)

        def to_surface(points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
            return [
                (
                    rotated[0] - origin_x,
                    rotated[1] - origin_y,
                )
                for rotated in (_rotate_point(point, center, angle) for point in points)
            ]

        if element_type in {"line", "arrow"}:
            raw_points = element.get("points")
            if isinstance(raw_points, list) and raw_points:
                points: List[Tuple[float, float]] = []
                for raw_point in raw_points:
                    if isinstance(raw_point, list) and len(raw_point) >= 2:
                        points.append((source_x + _finite_number(raw_point[0]), source_y + _finite_number(raw_point[1])))
                return to_surface(_densify_open_polyline(points))
            return to_surface(_densify_open_polyline([(source_x, source_y), (source_x + width, source_y + height)]))

        if element_type in {"rectangle", "frame"}:
            vertices = [(left, top), (right, top), (right, bottom), (left, bottom)]
            return to_surface(_densify_closed_polyline(vertices))

        if element_type == "diamond":
            center_x, center_y = center
            vertices = [(center_x, top), (right, center_y), (center_x, bottom), (left, center_y)]
            return to_surface(_densify_closed_polyline(vertices))

        if element_type == "ellipse":
            center_x, center_y = center
            radius_x = max(0.5, abs(right - left) / 2.0)
            radius_y = max(0.5, abs(bottom - top) / 2.0)
            points = []
            for step in range(65):
                ellipse_angle = (math.tau * step) / 64.0
                points.append((center_x + math.cos(ellipse_angle) * radius_x, center_y + math.sin(ellipse_angle) * radius_y))
            return to_surface(points)

        return []

    def _build_stroke(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
        order: int,
    ) -> Optional[StrokeElement]:
        raw_points = element.get("points")
        if not isinstance(raw_points, list):
            return None

        base_x = _finite_number(element.get("x"))
        base_y = _finite_number(element.get("y"))
        points: List[Tuple[float, float]] = []
        for raw_point in raw_points:
            if not isinstance(raw_point, list) or len(raw_point) < 2:
                continue
            points.append(
                (
                    base_x + _finite_number(raw_point[0]) - origin_x,
                    base_y + _finite_number(raw_point[1]) - origin_y,
                )
            )
        if len(points) < 2:
            return None

        color_int = _hex_to_argb(element.get("strokeColor"), element.get("opacity", 100))
        stroke_width = max(0.5, _finite_number(element.get("strokeWidth"), 2.0))
        pressures = self._pressure_values(element.get("pressures"), len(points))

        return StrokeElement(
            element_id=str(element.get("id") or f"stroke-{order}"),
            points=points,
            color_int=color_int,
            color_hex_argb=f"0x{color_int:08X}",
            rgba=_argb_to_rgba(color_int),
            pen_size=max(0.5, stroke_width / STROKE_WIDTH_SCALE),
            style={
                "source": "excalidraw",
                "stroke_width": stroke_width,
                "roughness": element.get("roughness"),
            },
            layer_number=0,
            source_order=order,
            z_index=self._z_index(element, order),
            pressures=pressures,
            timestamps=[index * 8 for index in range(len(points))],
            vendor_extensions={"excalidraw": dict(element)},
        )

    def _build_text(
        self,
        element: Dict[str, object],
        origin_x: float,
        origin_y: float,
        order: int,
    ) -> TextElement:
        x = _finite_number(element.get("x")) - origin_x
        y = _finite_number(element.get("y")) - origin_y
        source_font_size = max(1.0, _finite_number(element.get("fontSize"), 20.0))
        font_size = max(1.0, source_font_size * TEXT_FONT_SIZE_SCALE)
        color_int = _hex_to_argb(element.get("strokeColor"), element.get("opacity", 100))
        text = _normalized_text(element.get("text") or element.get("originalText") or "")
        source_width = max(1.0, _finite_number(element.get("width"), len(text) * source_font_size * 0.55))
        source_height = max(source_font_size, _finite_number(element.get("height"), source_font_size * 1.25))
        neutral_width = source_width * TEXT_BOX_WIDTH_SCALE
        neutral_height = source_height * TEXT_BOX_HEIGHT_SCALE
        return TextElement(
            element_id=str(element.get("id") or f"text-{order}"),
            text=text,
            x=x,
            baseline_y=y + font_size,
            width=max(1.0, neutral_width),
            ascent=font_size,
            descent=max(font_size * 0.25, neutral_height - font_size),
            color_int=color_int,
            layer_number=0,
            source_order=order,
            z_index=self._z_index(element, order),
            font_size_pt=font_size,
            font_name=None,
            vendor_extensions={"excalidraw": dict(element)},
        )

    def _pressure_values(self, raw_pressures: object, point_count: int) -> List[float]:
        if not isinstance(raw_pressures, list) or len(raw_pressures) != point_count:
            return [0.5 for _ in range(point_count)]
        pressures: List[float] = []
        for raw_value in raw_pressures:
            pressure = _finite_number(raw_value, 0.5)
            pressures.append(max(0.0, min(1.0, pressure)))
        return pressures

    def _z_index(self, element: Dict[str, object], order: int) -> int:
        z_index = element.get("zIndex")
        if isinstance(z_index, int):
            return z_index
        return order

    def _scene_summary(self, scene: Dict[str, object]) -> Dict[str, object]:
        elements = scene.get("elements")
        return {
            "type": scene.get("type"),
            "version": scene.get("version"),
            "source": scene.get("source"),
            "element_count": len(elements) if isinstance(elements, list) else 0,
        }
