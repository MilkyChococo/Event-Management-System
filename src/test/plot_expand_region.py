from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.extract.region_to_chunk import build_layout_regions
from src.extract.valid_expand_region import build_expanded_region, select_lines_in_region
from src.extract.word_to_line import group_words_to_lines, load_words_from_ocr


DEFAULT_IMAGE_DIR = PROJECT_ROOT / "dataset" / "spdocvqa" / "spdocvqa_images"
DEFAULT_OCR_DIR = PROJECT_ROOT / "dataset" / "spdocvqa" / "spdocvqa_ocr"
DEFAULT_LAYOUT_DIR = PROJECT_ROOT / "artifacts" / "layout"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts" / "visualizations"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot lines inside a region and their horizontally expanded boxes."
    )
    parser.add_argument("image", type=Path, help="Input image path.")
    parser.add_argument(
        "--ocr",
        type=Path,
        default=None,
        help="Optional OCR JSON path. Defaults to the file with the same stem in spdocvqa_ocr.",
    )
    parser.add_argument(
        "--layout-json",
        type=Path,
        required=True,
        help="Layout detection JSON path.",
    )
    parser.add_argument(
        "--region-index",
        type=int,
        default=0,
        help="Region index in the layout detections list.",
    )
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="OCR page number.",
    )
    parser.add_argument(
        "--min-overlap",
        type=float,
        default=0.5,
        help="Minimum line/region overlap ratio.",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=0.0,
        help="Horizontal padding when expanding.",
    )
    parser.add_argument(
        "--clamp-to-region",
        action="store_true",
        help="Clamp the expanded box inside the region bbox.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output image path.",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Save without opening a matplotlib window.",
    )
    return parser.parse_args()


def resolve_path(path: Path, fallback_dir: Path | None = None) -> Path:
    if path.is_absolute():
        return path
    if path.exists():
        return path.resolve()
    candidate = PROJECT_ROOT / path
    if candidate.exists():
        return candidate.resolve()
    if fallback_dir is not None:
        candidate = fallback_dir / path.name
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"Path not found: {path}")


def resolve_ocr_path(image_path: Path, ocr_path: Path | None) -> Path:
    if ocr_path is not None:
        return resolve_path(ocr_path)
    candidate = DEFAULT_OCR_DIR / f"{image_path.stem}.json"
    if candidate.exists():
        return candidate.resolve()
    raise FileNotFoundError(f"Could not infer OCR JSON for {image_path.stem}")


def load_layout_detections(layout_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(layout_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        detections = payload.get("detections", [])
    elif isinstance(payload, list):
        detections = payload
    else:
        raise ValueError(f"Unsupported layout payload type: {type(payload)!r}")
    if not isinstance(detections, list):
        raise ValueError("Layout detections must be a list.")
    return detections


def draw_expanded_region(
    image: Image.Image,
    region: Any,
    region_expansion: Any,
    selected_lines: list[Any],
) -> Image.Image:
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()

    draw.rectangle(
        [(region.bbox.left, region.bbox.top), (region.bbox.right, region.bbox.bottom)],
        outline="yellow",
        width=3,
    )
    draw.text(
        (region.bbox.left + 2, max(0, region.bbox.top - 12)),
        f"{region.id} [{region.label}] original",
        fill="yellow",
        font=font,
    )

    draw.rectangle(
        [
            (region_expansion.expanded_bbox.left, region_expansion.expanded_bbox.top),
            (region_expansion.expanded_bbox.right, region_expansion.expanded_bbox.bottom),
        ],
        outline="magenta",
        width=2,
    )
    draw.text(
        (
            region_expansion.expanded_bbox.left + 2,
            max(0, region_expansion.expanded_bbox.bottom + 2),
        ),
        f"expanded lines={region_expansion.num_lines}",
        fill="magenta",
        font=font,
    )

    for line in selected_lines:
        original = line.bbox
        draw.rectangle(
            [(original.left, original.top), (original.right, original.bottom)],
            outline="cyan",
            width=1,
        )
        draw.text(
            (original.left + 2, max(0, original.top - 10)),
            line.id,
            fill="cyan",
            font=font,
        )

    return canvas


def show_image(image: Image.Image, title: str) -> None:
    plt.figure(figsize=(14, 10))
    plt.imshow(image)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.show()


def main() -> None:
    args = parse_args()
    image_path = resolve_path(args.image, fallback_dir=DEFAULT_IMAGE_DIR)
    ocr_path = resolve_ocr_path(image_path, args.ocr)
    layout_path = resolve_path(args.layout_json, fallback_dir=DEFAULT_LAYOUT_DIR)

    detections = load_layout_detections(layout_path)
    regions = build_layout_regions(detections=detections, page_number=args.page)
    if not regions:
        raise ValueError(f"No regions found in: {layout_path}")
    if args.region_index < 0 or args.region_index >= len(regions):
        raise IndexError(f"region-index out of range: {args.region_index}")

    words = load_words_from_ocr(ocr_path=ocr_path, page_number=args.page)
    lines = group_words_to_lines(words)
    region = regions[args.region_index]
    selected_lines = select_lines_in_region(
        lines=lines,
        region=region,
        min_line_overlap_ratio=args.min_overlap,
    )
    region_expansion = build_expanded_region(
        lines=lines,
        region=region,
        min_line_overlap_ratio=args.min_overlap,
        horizontal_padding=args.padding,
        clamp_to_region=args.clamp_to_region,
    )

    image = Image.open(image_path)
    plotted = draw_expanded_region(
        image=image,
        region=region,
        region_expansion=region_expansion,
        selected_lines=selected_lines,
    )

    output_path = (
        args.output
        if args.output is not None
        else DEFAULT_OUTPUT_DIR / f"{image_path.stem}_region_expand_{args.region_index:03d}.png"
    )
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plotted.save(output_path)

    print(f"Region: {region.id} [{region.label}]")
    print(f"Expanded lines: {len(selected_lines)}")
    print(
        "Region left/right:"
        f" {region_expansion.original_bbox.left:.1f}, {region_expansion.original_bbox.right:.1f}"
    )
    print(
        "Expanded left/right:"
        f" {region_expansion.expanded_bbox.left:.1f}, {region_expansion.expanded_bbox.right:.1f}"
    )
    print(f"Saved overlay to: {output_path}")

    if not args.no_show:
        show_image(
            plotted,
            title=f"{image_path.name} | region={region.id} | expanded_lines={len(selected_lines)}",
        )


if __name__ == "__main__":
    main()
