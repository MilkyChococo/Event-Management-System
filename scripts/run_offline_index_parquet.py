"""
scripts/run_offline_index_parquet.py  — FINAL

Fix: OCR từ Qwen2.5-VL dùng đúng pattern của _load_model_and_processor
     (có cache, không OOM, đúng format input)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algo import enrich_graph_for_cse, save_enriched_graph
from src.database import (
    Qwen3VLEmbeddingConfig,
    Qwen3VLNodeEmbedder,
    build_graph_payload,
    build_node_embedding_records,
    save_embedding_store,
    save_graph_payload,
)
from src.extract.document_pipeline import run_document_pipeline
from src.utils.config import DEFAULT_QWEN_EMBED_MODEL, DEFAULT_QWEN_VL_MODEL
from src.utils.io import save_json

# ── Dùng _load_model_and_processor có cache từ qwen_vl_region_analysis ────────
from src.api.qwen_vl_region_analysis import _load_model_and_processor

PARQUET_FILES = {
    "test": PROJECT_ROOT / "DocVQA-2026" / "test.parquet",
    "val":  PROJECT_ROOT / "DocVQA-2026" / "val.parquet",
}
STORE_ROOT  = PROJECT_ROOT / "artifacts" / "node_stores"
IMAGES_ROOT = PROJECT_ROOT / "artifacts" / "parquet_images"
OCR_ROOT    = PROJECT_ROOT / "artifacts" / "parquet_ocr"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--split",            default="test", choices=["test", "val"])
    p.add_argument("--embed-model",      default=DEFAULT_QWEN_EMBED_MODEL)
    p.add_argument("--embed-device",     default="auto")
    p.add_argument("--embed-dtype",      default="auto")
    p.add_argument("--embed-batch-size", type=int, default=4)
    p.add_argument("--qwen-model",       default=DEFAULT_QWEN_VL_MODEL)
    p.add_argument("--qwen-device",      default="auto")
    p.add_argument("--qwen-dtype",       default="auto")
    p.add_argument("--detect-layout",    action="store_true")
    p.add_argument("--skip-existing",    action="store_true")
    p.add_argument("--doc-ids",          default="")
    return p.parse_args()


# ── OCR từ Qwen2.5-VL ─────────────────────────────────────────────────────────

def _extract_text_lines_with_qwen(
    image_path: Path,
    model_id: str,
    device: str,
    dtype: str,
) -> list[str]:
    """
    Dùng Qwen2.5-VL extract text từ ảnh → list dòng.
    Dùng _load_model_and_processor có cache → không load lại model.
    """
    import torch

    processor, qwen_model, resolved_device = _load_model_and_processor(
        model_id=model_id,
        device=device,
        dtype=dtype,
    )

    img = Image.open(image_path).convert("RGB")
    prompt = (
        "Extract all text from this document image. "
        "Output each line of text on a new line. "
        "Output only the text, no explanation."
    )

    # Đúng format như _build_model_inputs trong qwen_vl_region_analysis.py
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    chat_text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = processor(
        text=[chat_text],
        images=[img],
        padding=True,
        return_tensors="pt",
    )
    inputs = {
        k: v.to(resolved_device) if hasattr(v, "to") else v
        for k, v in inputs.items()
    }

    with torch.inference_mode():
        out_ids = qwen_model.generate(
            **inputs,
            max_new_tokens=1024,
            do_sample=False,
        )

    prompt_len = int(inputs["input_ids"].shape[1])
    raw = processor.batch_decode(
        out_ids[:, prompt_len:],
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0].strip()

    lines = [l.strip() for l in raw.split("\n") if l.strip()]
    return lines if lines else ["[no text]"]


def _make_ocr_json(image_path: Path, page_number: int, text_lines: list[str]) -> dict:
    """
    Tạo OCR JSON đúng format recognitionResults từ list dòng text.
    BBox ước lượng đều theo chiều dọc của ảnh.
    """
    try:
        img = Image.open(image_path)
        img_w, img_h = img.size
    except Exception:
        img_w, img_h = 1000, 1400

    n = len(text_lines)
    line_h = img_h / max(n, 1)

    ocr_lines = []
    for i, line_text in enumerate(text_lines):
        words = line_text.split()
        if not words:
            continue
        y1 = i * line_h
        y2 = y1 + line_h * 0.85
        word_w = img_w / max(len(words), 1)
        ocr_words = []
        for j, word in enumerate(words):
            x1 = j * word_w
            x2 = x1 + word_w * 0.9
            ocr_words.append({
                "text": word,
                # polygon 8 điểm: [x1,y1, x2,y1, x2,y2, x1,y2]
                "boundingBox": [x1, y1, x2, y1, x2, y2, x1, y2],
            })
        ocr_lines.append({"words": ocr_words})

    return {
        "recognitionResults": [
            {"page": page_number, "lines": ocr_lines}
        ]
    }


def get_or_create_ocr(
    doc_id: str,
    page_path: Path,
    page_number: int,
    model_id: str,
    device: str,
    dtype: str,
) -> Path:
    """Cache OCR JSON vào artifacts/parquet_ocr/<doc_id>/page_<N>.json"""
    ocr_dir = OCR_ROOT / doc_id
    ocr_dir.mkdir(parents=True, exist_ok=True)
    ocr_path = ocr_dir / f"page_{page_number}.json"

    if ocr_path.exists():
        return ocr_path

    print(f"      [OCR] Extracting text from page {page_number}...")
    text_lines = _extract_text_lines_with_qwen(page_path, model_id, device, dtype)
    ocr_data = _make_ocr_json(page_path, page_number, text_lines)
    ocr_path.write_text(
        json.dumps(ocr_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"      [OCR] {len(text_lines)} lines → {ocr_path.name}")
    return ocr_path


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_page_images(sample) -> list[bytes]:
    doc = sample["document"]
    pages = []
    if isinstance(doc, np.ndarray):
        for item in doc:
            if isinstance(item, dict) and "bytes" in item:
                pages.append(bytes(item["bytes"]))
            elif isinstance(item, (bytes, bytearray)):
                pages.append(bytes(item))
    elif isinstance(doc, dict) and "bytes" in doc:
        pages.append(bytes(doc["bytes"]))
    return pages


def save_page_images(doc_id: str, page_bytes_list: list[bytes]) -> list[Path]:
    doc_img_dir = IMAGES_ROOT / doc_id
    doc_img_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, pb in enumerate(page_bytes_list):
        p = doc_img_dir / f"page_{i+1}.png"
        if not p.exists():
            p.write_bytes(pb)
        paths.append(p)
    return paths


def build_node_to_row(records) -> dict[str, int]:
    return {r.node_id: r.row for r in records}


# ── Per-document indexing ─────────────────────────────────────────────────────

def index_document(
    doc_id: str,
    page_paths: list[Path],
    args: argparse.Namespace,
) -> Path:
    output_dir = STORE_ROOT / doc_id
    output_dir.mkdir(parents=True, exist_ok=True)

    target_node_types = ("line", "chunk", "region", "fine")
    embed_config = Qwen3VLEmbeddingConfig(
        model=args.embed_model,
        device=args.embed_device,
        dtype=args.embed_dtype,
        batch_size=args.embed_batch_size,
        target_node_types=target_node_types,
    )

    all_nodes: list = []
    all_edges: list = []
    image_path_str = str(page_paths[0])

    for page_num, page_path in enumerate(page_paths, start=1):
        print(f"    Page {page_num}/{len(page_paths)}: {page_path.name}")
        try:
            # 1. Tạo OCR JSON từ Qwen (có cache)
            ocr_path = get_or_create_ocr(
                doc_id=doc_id,
                page_path=page_path,
                page_number=page_num,
                model_id=args.qwen_model,
                device=args.qwen_device,
                dtype=args.qwen_dtype,
            )

            # 2. Chạy document pipeline
            pipeline = run_document_pipeline(
                image_path=page_path,
                ocr_path=ocr_path,
                page_number=page_num,
                detect_layout=args.detect_layout,
                # Chỉ analyze region nếu có detect layout
                analyze_regions_with_qwen=args.detect_layout,
                qwen_model=args.qwen_model,
                qwen_device=args.qwen_device,
                qwen_dtype=args.qwen_dtype,
            )

            # 3. Build graph payload
            gp = build_graph_payload(pipeline)

            # 4. Prefix IDs tránh trùng giữa các trang
            for node in gp.get("nodes", []):
                node["id"] = f"p{page_num}_{node['id']}"
                node["page"] = page_num
            for edge in gp.get("edges", []):
                edge["source_id"] = f"p{page_num}_{edge['source_id']}"
                edge["target_id"] = f"p{page_num}_{edge['target_id']}"

            all_nodes.extend(gp.get("nodes", []))
            all_edges.extend(gp.get("edges", []))
            print(f"      → {len(gp.get('nodes', []))} nodes, "
                  f"{len(gp.get('edges', []))} edges")

        except Exception as e:
            print(f"    [WARN] Page {page_num} failed: {e}")
            continue

    # ── Không build được node nào → minimal store ─────────────────────────────
    if not all_nodes:
        print(f"  [WARN] No nodes for {doc_id}, minimal store.")
        dummy = {
            "document": {"image_path": image_path_str, "ocr_path": ""},
            "stats": {}, "nodes": [], "edges": [],
        }
        save_graph_payload(dummy, output_dir / "graph.json")
        np.save(output_dir / "embeddings.npy", np.zeros((0, 1), dtype=np.float32))
        save_json([], output_dir / "embedding_meta.json")
        enriched = enrich_graph_for_cse(
            graph=dummy,
            embeddings=np.zeros((0, 1), dtype=np.float32),
            node_to_row={},
        )
        save_enriched_graph(enriched, output_dir / "graph_enriched.json")
        return output_dir

    # ── Merge và save ─────────────────────────────────────────────────────────
    merged = {
        "document": {"image_path": image_path_str, "ocr_path": ""},
        "stats": {"num_nodes": len(all_nodes), "num_edges": len(all_edges)},
        "nodes": all_nodes,
        "edges": all_edges,
    }

    records = build_node_embedding_records(
        graph_payload=merged,
        target_node_types=target_node_types,
    )

    save_graph_payload(merged, output_dir / "graph.json")
    save_json([r.to_payload() for r in records], output_dir / "embedding_meta.json")

    print(f"  Embedding {len(records)} nodes...")
    embedder = Qwen3VLNodeEmbedder(config=embed_config)
    embeddings = embedder.embed_texts(
        texts=[r.context_text for r in records],
        instruction=embed_config.document_instruction,
    )

    save_embedding_store(
        output_dir=output_dir,
        embeddings=embeddings,
        records=records,
        graph_payload=merged,
    )

    node_to_row = build_node_to_row(records)
    enriched = enrich_graph_for_cse(
        graph=merged,
        embeddings=embeddings,
        node_to_row=node_to_row,
    )
    save_enriched_graph(enriched, output_dir / "graph_enriched.json")

    print(f"  ✓ {doc_id}: {len(all_nodes)} nodes, "
          f"{len(records)} embedded → {output_dir}")
    return output_dir


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    parquet_path = PARQUET_FILES[args.split]
    print(f"Loading {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    print(f"{args.split}: {len(df)} documents")

    filter_ids = set()
    if args.doc_ids:
        filter_ids = {s.strip() for s in args.doc_ids.split(",") if s.strip()}

    for i in range(len(df)):
        sample = df.iloc[i]
        doc_id = str(sample["doc_id"])

        if filter_ids and doc_id not in filter_ids:
            continue

        if args.skip_existing:
            if (STORE_ROOT / doc_id / "graph_enriched.json").exists():
                print(f"[{i+1}/{len(df)}] Skip {doc_id} (already indexed)")
                continue

        print(f"\n[{i+1}/{len(df)}] Indexing {doc_id}...")
        page_bytes = get_page_images(sample)
        if not page_bytes:
            print(f"  [WARN] No pages for {doc_id}")
            continue

        page_paths = save_page_images(doc_id, page_bytes)
        index_document(doc_id, page_paths, args)

    print(f"\nDone. Stores: {STORE_ROOT}")


if __name__ == "__main__":
    main()