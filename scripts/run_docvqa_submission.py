"""
scripts/run_docvqa_submission.py

Pipeline hoàn chỉnh để sinh submission_test.json cho DocVQA-2026.

Flow:
  parquet → [offline store] → CSE query → RGAT re-rank → Qwen answer

Yêu cầu:
  - Đã chạy scripts/run_offline_index_parquet.py --split test
  - Đã có artifacts/models/rgat_model.pt (từ scripts/train_rgat.py)

Usage:
  # Inference test set
  python -m scripts.run_docvqa_submission --split test

  # Evaluate val set
  python -m scripts.run_docvqa_submission --split val --evaluate

  # Debug 1 doc
  python -m scripts.run_docvqa_submission --split test --doc-ids infographics_5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algo.cse_query import run_multi_subgraph_cse_from_store, save_cse_subgraph
from src.algo.rgat_reranker import load_rgat_model, rerank_multi_subgraph_payload
from src.api.qwen_vl_answering import answer_subgraph_with_qwen
from src.utils.config import DEFAULT_QWEN_EMBED_MODEL, DEFAULT_QWEN_VL_MODEL
from src.utils.fallback import backfill_document_from_sibling_graph


# ── Config mặc định ───────────────────────────────────────────────────────────

PARQUET_FILES = {
    "test": PROJECT_ROOT / "DocVQA-2026" / "test.parquet",
    "val":  PROJECT_ROOT / "DocVQA-2026" / "val.parquet",
}
STORE_ROOT  = PROJECT_ROOT / "artifacts" / "node_stores"
MODEL_PATH  = str(PROJECT_ROOT / "artifacts" / "models" / "rgat_model.pt")
OUT_TEST    = PROJECT_ROOT / "submission_test.json"
OUT_VAL     = PROJECT_ROOT / "submission_val.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--split",          default="test", choices=["test", "val"])
    p.add_argument("--evaluate",       action="store_true",
                   help="Tính ANLS sau khi inference (chỉ val set có GT)")
    p.add_argument("--no-rgat",        action="store_true",
                   help="Bỏ qua RGAT re-ranking (chạy CSE thuần để so sánh)")
    p.add_argument("--rgat-blend",     type=float, default=0.4,
                   help="Trọng số RGAT trong blended score (default: 0.4)")
    p.add_argument("--doc-ids",        default="",
                   help="Comma-separated doc_ids để chạy thử (debug)")
    # CSE params
    p.add_argument("--top-k",          type=int,   default=10)
    p.add_argument("--hops",           type=int,   default=5)
    p.add_argument("--top-m",          type=int,   default=5)
    p.add_argument("--threshold",      type=float, default=0.2)
    p.add_argument("--alpha",          type=float, default=0.5)
    p.add_argument("--lambda-hub",     type=float, default=0.05)
    p.add_argument("--max-nodes",      type=int,   default=100)
    p.add_argument("--max-edges",      type=int,   default=200)
    # Embed params
    p.add_argument("--embed-model",    default=DEFAULT_QWEN_EMBED_MODEL)
    p.add_argument("--embed-device",   default="auto")
    p.add_argument("--embed-dtype",    default="auto")
    # Qwen answer params
    p.add_argument("--answer-model",   default=DEFAULT_QWEN_VL_MODEL)
    p.add_argument("--answer-device",  default="auto")
    p.add_argument("--answer-dtype",   default="auto")
    p.add_argument("--max-new-tokens", type=int,   default=128)
    p.add_argument("--temperature",    type=float, default=0.0)
    p.add_argument("--max-context-nodes", type=int, default=20)
    p.add_argument("--max-images",     type=int,   default=4)
    return p.parse_args()


# ── Data helpers ──────────────────────────────────────────────────────────────

def parse_sample(sample) -> tuple[list[str], list[str], list[str]]:
    """→ (q_ids, q_texts, gt_answers)"""
    q = sample["questions"]
    a = sample["answers"]
    q_ids   = [str(x) for x in q["question_id"]]
    q_texts = [str(x) for x in q["question"]]
    ans_map = {
        str(qid): str(ans)
        for qid, ans in zip(
            a.get("question_id", []),
            a.get("answer", []),
        )
    }
    gt = [ans_map.get(qid, "NULL") for qid in q_ids]
    return q_ids, q_texts, gt


# ── ANLS ──────────────────────────────────────────────────────────────────────

def _edit_dist(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, n + 1):
            tmp = dp[j]
            dp[j] = prev if s1[i-1] == s2[j-1] else 1 + min(prev, dp[j], dp[j-1])
            prev = tmp
    return dp[n]


def anls_score(pred: str, gold: str) -> float:
    p, g = pred.strip().lower(), gold.strip().lower()
    if not g or g == "null":
        return 0.0
    ml = max(len(p), len(g))
    if ml == 0:
        return 1.0
    nl = _edit_dist(p, g) / ml
    return 1.0 - nl if nl < 0.5 else 0.0


# ── Core inference cho 1 câu hỏi ─────────────────────────────────────────────

def answer_one_question(
    doc_id: str,
    question: str,
    args: argparse.Namespace,
    rgat_model,
) -> str:
    """
    Pipeline đầy đủ cho 1 câu hỏi:
      1. Load CSE store của doc_id
      2. Chạy CSE → multi-subgraph payload
      3. RGAT re-rank nodes trong mỗi subgraph
      4. Qwen đọc subgraph → answer
    """
    store_dir = STORE_ROOT / doc_id
    enriched_path = store_dir / "graph_enriched.json"

    # Kiểm tra store tồn tại
    if not enriched_path.exists():
        print(f"    [WARN] No store for {doc_id}, returning 'unanswerable'")
        return "unanswerable"

    # ── Bước 1: CSE ──────────────────────────────────────────────────────────
    try:
        subgraph_payload = run_multi_subgraph_cse_from_store(
            store_dir=store_dir,
            query=question,
            top_k=args.top_k,
            hops=args.hops,
            top_m=args.top_m,
            threshold=args.threshold,
            alpha=args.alpha,
            lambda_hub=args.lambda_hub,
            max_nodes=args.max_nodes,
            max_edges=args.max_edges,
            allowed_seed_node_types=("line", "chunk", "region", "fine"),
            embed_model=args.embed_model,
            embed_device=args.embed_device,
            embed_dtype=args.embed_dtype,
        )
    except Exception as e:
        print(f"    [CSE error] {e}")
        return "unanswerable"

    # Backfill document path (cần cho Qwen crop images)
    subgraph_payload = backfill_document_from_sibling_graph(
        subgraph_payload,
        store_dir / "graph_enriched.json",
    )

    # ── Bước 2: RGAT re-rank ─────────────────────────────────────────────────
    if not args.no_rgat and rgat_model is not None:
        subgraph_payload = rerank_multi_subgraph_payload(
            multi_payload=subgraph_payload,
            rgat_model=rgat_model,
            score_blend=args.rgat_blend,
        )

    # ── Bước 3: Qwen answer ──────────────────────────────────────────────────
    try:
        result = answer_subgraph_with_qwen(
            subgraph_payload=subgraph_payload,
            model=args.answer_model,
            device=args.answer_device,
            dtype=args.answer_dtype,
            max_new_tokens=args.max_new_tokens,
            temperature=args.temperature,
            max_context_nodes=args.max_context_nodes,
            max_images=args.max_images,
        )
        return result.answer if result.answer else "unanswerable"
    except Exception as e:
        print(f"    [Qwen error] {e}")
        return "unanswerable"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # Load RGAT model 1 lần
    rgat_model = None
    if not args.no_rgat:
        from src.algo.rgat_reranker import DEVICE
        rgat_model = load_rgat_model(MODEL_PATH, device=DEVICE)

    # Load parquet
    parquet_path = PARQUET_FILES[args.split]
    print(f"Loading {parquet_path}...")
    df = pd.read_parquet(parquet_path)
    print(f"{args.split}: {len(df)} documents")

    filter_ids = set()
    if args.doc_ids:
        filter_ids = {s.strip() for s in args.doc_ids.split(",") if s.strip()}

    results: dict[str, str] = {}
    total_anls, anls_cnt = 0.0, 0

    for i in range(len(df)):
        sample = df.iloc[i]
        doc_id = str(sample["doc_id"])

        if filter_ids and doc_id not in filter_ids:
            continue

        q_ids, q_texts, gt_answers = parse_sample(sample)
        n_q = len(q_ids)

        print(f"\n[{i+1}/{len(df)}] {doc_id} | {n_q} questions")

        for j, (qid, qtext) in enumerate(zip(q_ids, q_texts)):
            print(f"  Q{j+1}/{n_q}: {qtext[:80]}...")

            answer = answer_one_question(
                doc_id=doc_id,
                question=qtext,
                args=args,
                rgat_model=rgat_model,
            )
            results[qid] = answer
            print(f"  → {answer[:80]}")

            # ANLS nếu có GT
            if args.evaluate:
                gold = gt_answers[j] if j < len(gt_answers) else "NULL"
                if gold and gold != "NULL":
                    score = anls_score(answer, gold)
                    total_anls += score
                    anls_cnt   += 1
                    print(f"  ANLS: {score:.4f} (gold: {gold})")

    # Save submission
    out_path = OUT_VAL if args.split == "val" else OUT_TEST
    out_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n{'='*60}")
    print(f"Saved: {out_path} ({len(results)} answers)")

    # In sample
    print("Sample entries:")
    for k, v in list(results.items())[:5]:
        print(f"  {k!r}: {v!r}")

    # ANLS summary
    if args.evaluate and anls_cnt > 0:
        print(f"\nANLS = {total_anls/anls_cnt:.4f}  ({anls_cnt} questions with GT)")
    elif args.evaluate:
        print("\nNo GT answers found for ANLS evaluation.")

    mode = "CSE only" if args.no_rgat else f"CSE + RGAT (blend={args.rgat_blend})"
    print(f"Pipeline mode: {mode}")


if __name__ == "__main__":
    main()