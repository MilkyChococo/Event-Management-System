from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Sequence


class BlockType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    IMAGE = "image"


@dataclass(slots=True, frozen=True)
class BoundingBox:
    left: float
    top: float
    right: float
    bottom: float

    @classmethod
    def from_polygon(cls, polygon: Sequence[float]) -> "BoundingBox":
        if len(polygon) < 8 or len(polygon) % 2 != 0:
            raise ValueError("OCR polygon must have an even number of coordinates.")
        xs = [float(value) for value in polygon[0::2]]
        ys = [float(value) for value in polygon[1::2]]
        return cls(min(xs), min(ys), max(xs), max(ys))

    @classmethod
    def merge(cls, boxes: Iterable["BoundingBox"]) -> "BoundingBox":
        items = list(boxes)
        if not items:
            raise ValueError("At least one bounding box is required to merge.")
        return cls(
            left=min(box.left for box in items),
            top=min(box.top for box in items),
            right=max(box.right for box in items),
            bottom=max(box.bottom for box in items),
        )

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    @property
    def center_x(self) -> float:
        return self.left + (self.width / 2.0)

    @property
    def center_y(self) -> float:
        return self.top + (self.height / 2.0)

    def horizontal_overlap(self, other: "BoundingBox") -> float:
        return max(0.0, min(self.right, other.right) - max(self.left, other.left))

    def vertical_overlap(self, other: "BoundingBox") -> float:
        return max(0.0, min(self.bottom, other.bottom) - max(self.top, other.top))

    def horizontal_overlap_ratio(self, other: "BoundingBox") -> float:
        base = min(self.width, other.width)
        if base <= 0.0:
            return 0.0
        return self.horizontal_overlap(other) / base

    def vertical_overlap_ratio(self, other: "BoundingBox") -> float:
        base = min(self.height, other.height)
        if base <= 0.0:
            return 0.0
        return self.vertical_overlap(other) / base

    def vertical_gap(self, other: "BoundingBox") -> float:
        if other.top >= self.bottom:
            return other.top - self.bottom
        if self.top >= other.bottom:
            return self.top - other.bottom
        return 0.0


@dataclass(slots=True)
class OCRWord:
    id: str
    page: int
    text: str
    bbox: BoundingBox
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class OCRLine:
    id: str
    page: int
    text: str
    bbox: BoundingBox
    words: list[OCRWord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentBlock:
    id: str
    page: int
    bbox: BoundingBox
    text: str
    block_type: BlockType = BlockType.TEXT
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentPage:
    page_number: int
    width: float
    height: float
    unit: str = "pixel"
    lines: list[OCRLine] = field(default_factory=list)
    blocks: list[DocumentBlock] = field(default_factory=list)


@dataclass(slots=True)
class DocumentSample:
    sample_id: str
    source_path: str
    pages: list[DocumentPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
