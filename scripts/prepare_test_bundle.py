from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.io import resolve_existing_dir, resolve_existing_file, save_json


DEFAULT_SOURCE_IMAGE_DIR = PROJECT_ROOT / "dataset" / "spdocvqa" / "spdocvqa_images"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a test bundle by copying or moving referenced SP-DocVQA images into one output folder."
    )
    parser.add_argument(
        "test_json",
        type=Path,
        help="Path to the input test JSON file.",
    )
    parser.add_argument(
        "--source-image-dir",
        type=Path,
        default=DEFAULT_SOURCE_IMAGE_DIR,
        help="Directory containing the source SP-DocVQA images.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "test_bundle",
        help="Output directory. The script will create <output-dir>/images and <output-dir>/test.json.",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Move images instead of copying them.",
    )
    parser.add_argument(
        "--keep-image-field",
        action="store_true",
        help="Keep the original image field in the output JSON instead of rewriting it to images/<filename>.",
    )
    return parser.parse_args()


def _extract_image_filename(image_value: str) -> str:
    return Path(str(image_value).strip()).name


def _load_payload(test_json_path: Path) -> dict:
    return json.loads(test_json_path.read_text(encoding="utf-8"))


def _transfer_file(source_path: Path, target_path: Path, move: bool) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if move:
        shutil.move(str(source_path), str(target_path))
    else:
        shutil.copy2(str(source_path), str(target_path))


def main() -> None:
    args = parse_args()
    test_json_path = resolve_existing_file(args.test_json, base_dir=PROJECT_ROOT)
    source_image_dir = resolve_existing_dir(args.source_image_dir, base_dir=PROJECT_ROOT)

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir
    images_output_dir = output_dir / "images"
    images_output_dir.mkdir(parents=True, exist_ok=True)

    payload = _load_payload(test_json_path)
    data = payload.get("data", [])
    if not isinstance(data, list):
        raise ValueError("Input JSON must contain a list under the 'data' key.")

    transferred: set[str] = set()
    missing: list[str] = []
    kept_entries: list[dict] = []

    for item in data:
        if not isinstance(item, dict):
            continue
        raw_image = str(item.get("image", "")).strip()
        if not raw_image:
            continue

        image_name = _extract_image_filename(raw_image)
        source_path = source_image_dir / image_name
        if not source_path.exists():
            missing.append(image_name)
            continue

        target_path = images_output_dir / image_name
        if image_name not in transferred:
            _transfer_file(source_path, target_path, move=args.move)
            transferred.add(image_name)

        item_copy = dict(item)
        if not args.keep_image_field:
            item_copy["image"] = f"images/{image_name}"
        kept_entries.append(item_copy)

    output_payload = dict(payload)
    output_payload["data"] = kept_entries

    output_json_path = output_dir / "test.json"
    save_json(output_payload, output_json_path)

    print(f"Input entries: {len(data)}")
    print(f"Output entries: {len(kept_entries)}")
    print(f"Transferred images: {len(transferred)}")
    print(f"Missing images: {len(missing)}")
    if missing:
        print("Missing filenames:")
        for name in missing:
            print(f"  - {name}")
    print(f"Images directory: {images_output_dir}")
    print(f"Output JSON: {output_json_path}")


if __name__ == "__main__":
    main()
