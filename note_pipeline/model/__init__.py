from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union


Rect = Tuple[float, float, float, float]
Point = Tuple[float, float]
IntRect = Tuple[int, int, int, int]


@dataclass
class SourceInfo:
    source_path: str
    source_kind: str
    note_root: str
    display_name: str
    extracted_from_archive: bool = False
    source_archive_path: Optional[str] = None


@dataclass
class Asset:
    asset_id: str
    media_type: str
    source_path: Optional[str]
    source_ref: Optional[str] = None
    derived_raster_path: Optional[str] = None
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


@dataclass
class NoteBackground:
    color_int: Optional[int] = None
    color_argb: Optional[str] = None
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


@dataclass
class StrokeElement:
    element_id: str
    points: List[Point]
    color_int: int
    color_hex_argb: str
    rgba: Tuple[float, float, float, float]
    pen_size: float
    style: Optional[Dict[str, object]]
    layer_number: int
    source_order: int
    z_index: int
    pressures: List[float] = field(default_factory=list)
    timestamps: List[int] = field(default_factory=list)
    tilts: List[float] = field(default_factory=list)
    orientations: List[float] = field(default_factory=list)
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


@dataclass
class ImageElement:
    element_id: str
    rect: Rect
    asset_id: Optional[str]
    layer_number: int
    source_order: int
    z_index: int
    crop_rect: Optional[IntRect] = None
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


@dataclass
class TextElement:
    element_id: str
    text: str
    x: float
    baseline_y: float
    width: float
    ascent: float
    descent: float
    color_int: int
    layer_number: int
    source_order: int
    z_index: int
    font_size_pt: Optional[float] = None
    font_name: Optional[str] = None
    is_bold: bool = False
    is_italic: bool = False
    underline: bool = False
    underline_color_int: Optional[int] = None
    strikethrough: bool = False
    background_color_int: Optional[int] = None
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


@dataclass
class FrameElement:
    element_id: str
    rect: Rect
    name: Optional[str]
    color_int: int
    color_hex_argb: str
    rgba: Tuple[float, float, float, float]
    stroke_width: float
    layer_number: int
    source_order: int
    z_index: int
    label_font_size_pt: Optional[float] = None
    child_element_ids: List[str] = field(default_factory=list)
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


@dataclass
class PdfBackgroundElement:
    element_id: str
    rect: Rect
    asset_id: Optional[str]
    page_index: int
    layer_number: int
    source_order: int
    z_index: int
    overlay_tags_to_strip: Tuple[str, ...] = ()
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


@dataclass
class UnsupportedElement:
    element_id: str
    unsupported_type: str
    layer_number: int
    source_order: int
    z_index: int
    bounds: Optional[Rect] = None
    vendor_extensions: Dict[str, object] = field(default_factory=dict)


NoteElement = Union[
    StrokeElement,
    ImageElement,
    TextElement,
    FrameElement,
    PdfBackgroundElement,
    UnsupportedElement,
]


@dataclass
class NotePage:
    page_id: str
    index: int
    width: int
    height: int
    background: NoteBackground = field(default_factory=NoteBackground)
    elements: List[NoteElement] = field(default_factory=list)
    vendor_extensions: Dict[str, object] = field(default_factory=dict)

    @property
    def surface_id(self) -> str:
        return self.page_id

    @property
    def surface_kind(self) -> str:
        return "page"

    @property
    def origin_x(self) -> float:
        return 0.0

    @property
    def origin_y(self) -> float:
        return 0.0


@dataclass
class NoteCanvas:
    canvas_id: str
    index: int
    origin_x: float = 0.0
    origin_y: float = 0.0
    width: Optional[int] = None
    height: Optional[int] = None
    background: NoteBackground = field(default_factory=NoteBackground)
    elements: List[NoteElement] = field(default_factory=list)
    vendor_extensions: Dict[str, object] = field(default_factory=dict)

    @property
    def surface_id(self) -> str:
        return self.canvas_id

    @property
    def surface_kind(self) -> str:
        return "infinite_canvas"


@dataclass
class NoteDocument:
    source: SourceInfo
    note_id: str
    title: Optional[str] = None
    layout_kind: str = "pages"
    metadata: Dict[str, object] = field(default_factory=dict)
    pages: List[NotePage] = field(default_factory=list)
    canvases: List[NoteCanvas] = field(default_factory=list)
    assets: Dict[str, Asset] = field(default_factory=dict)
    vendor_extensions: Dict[str, object] = field(default_factory=dict)

    @property
    def surfaces(self) -> List[Union[NotePage, NoteCanvas]]:
        if self.layout_kind == "infinite_canvas":
            return list(self.canvases)
        return list(self.pages)


@dataclass
class ExportResult:
    format_name: str
    output_paths: List[str]
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)
