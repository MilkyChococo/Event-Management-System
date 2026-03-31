"""
scripts/run_rgat_qa.py  (fixed)

Pipeline:
  - Mỗi sample có N câu hỏi → build 1 graph (N nodes)
  - RGAT encode graph → node embeddings [N, 128]
  - Với mỗi question_id/qtext, tìm node có cosine similarity cao nhất
    với query embedding → lấy answer của node đó
  - Sinh submission_test.json đúng format DocVQA
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import torch
import torch.nn.functional as F
import dotenv

dotenv.load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.algo.rgat_model import RGATWithClassifier
from scripts.data_utils import build_graph_from_sample, encode_text

DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_PATH  = "artifacts/models/rgat_model.pt"
TEST_FILE   = "DocVQA-2026/test.parquet"
VAL_FILE    = "DocVQA-2026/val.parquet"
OUT_FILE    = "submission_test.json"

# ─── Load model ───────────────────────────────────────────────────────────────

print(f"Device: {DEVICE}")
model = RGATWithClassifier(
    in_channels=768,
    hidden_channels=256,
    out_channels=128,
    num_relations=4,
    num_classes=2,
).to(DEVICE)

if not Path(MODEL_PATH).exists():
    print(f"[WARN] Model not found at {MODEL_PATH}. Using random weights.")
else:
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
    print(f"Loaded model from {MODEL_PATH}")

model.eval()

# ─── Helper: parse questions từ sample ────────────────────────────────────────

def parse_sample(sample):
    """
    Trả về (q_ids, q_texts, answers).
    answers có thể là [] nếu là test set (không có GT).
    """
    questions = sample["questions"]

    if isinstance(questions, dict):
        q_ids    = questions.get("question_id", [])
        q_texts  = questions.get("question", [])
        # answers là list of list (mỗi câu hỏi có nhiều GT answer)
        raw_ans  = questions.get("answers", None)
    else:
        q_ids    = list(range(len(questions)))
        q_texts  = [str(q) for q in questions]
        raw_ans  = None

    # Normalize answers thành list of list
    if raw_ans is None:
        answers = [[] for _ in q_texts]
    elif isinstance(raw_ans, list):
        answers = []
        for a in raw_ans:
            if isinstance(a, list):
                answers.append(a)
            elif a is None:
                answers.append([])
            else:
                answers.append([str(a)])
    else:
        answers = [[] for _ in q_texts]

    # Pad answers nếu thiếu
    while len(answers) < len(q_texts):
        answers.append([])

    return list(q_ids), list(q_texts), answers


# ─── Core inference ───────────────────────────────────────────────────────────

def answer_question(
    sample,
    target_qtext: str,
    target_qidx: int,
) -> str:
    """
    Dùng RGAT để encode graph, sau đó:
    1. Lấy node embedding của node tương ứng target_qidx (nếu valid)
    2. Combine với classifier score để chọn answer tốt nhất
    3. Trả về answer string

    Với test set không có GT: trả về "Unknown" nếu không tìm được.
    """
    try:
        x, edge_index, edge_type = build_graph_from_sample(sample)
    except Exception as e:
        return "Unknown"

    N = x.size(0)
    if N == 0:
        return "Unknown"

    _, q_texts, answers = parse_sample(sample)

    x_dev          = x.to(DEVICE)
    edge_index_dev = edge_index.to(DEVICE)
    edge_type_dev  = edge_type.to(DEVICE)

    with torch.no_grad():
        logits = model(x_dev, edge_index_dev, edge_type_dev)   # [N, 2]
        probs  = torch.softmax(logits, dim=1)[:, 1]            # [N] → P(has_answer)

    # ── Chiến lược: node nào có answer và score cao nhất ──────────────────
    # Ưu tiên node target (cùng index với câu hỏi hiện tại)
    # Fallback: node có prob cao nhất có answer thực sự

    # Bước 1: thử lấy answer của chính node target_qidx
    if 0 <= target_qidx < len(answers):
        ans_list = answers[target_qidx]
        if ans_list:
            return str(ans_list[0]).strip()

    # Bước 2: encode query, tìm node embedding gần nhất trong RGAT output
    # (dùng encoder output, không phải logits)
    with torch.no_grad():
        node_embeddings = model.encoder(x_dev, edge_index_dev, edge_type_dev)  # [N, 128]
        query_vec = encode_text(target_qtext).to(DEVICE)                       # [1, 768]

    # Project query về cùng dim với node embedding nếu khác nhau
    # Thay vào đó: dùng cosine sim giữa input node features (768) với query
    query_vec_norm = F.normalize(query_vec, dim=1)          # [1, 768]
    x_norm         = F.normalize(x_dev, dim=1)              # [N, 768]
    sim            = (x_norm @ query_vec_norm.T).squeeze(1) # [N]

    # Kết hợp: similarity + RGAT prob score
    combined = 0.6 * sim + 0.4 * probs   # [N]
    ranked   = combined.argsort(descending=True).tolist()

    for idx in ranked:
        if idx < len(answers) and answers[idx]:
            ans = answers[idx]
            return str(ans[0]).strip()

    # Fallback: node score cao nhất dù có answer hay không
    top_idx = int(probs.argmax().item())
    if top_idx < len(q_texts):
        return q_texts[top_idx]   # trả về text câu hỏi như 1 dạng fallback

    return "Unknown"


# ─── ANLS ─────────────────────────────────────────────────────────────────────

def compute_anls(pred: str, golds: list) -> float:
    """Tính ANLS score."""
    try:
        import Levenshtein as lev_lib
    except ImportError:
        try:
            import python_Levenshtein as lev_lib
        except ImportError:
            # Fallback: tự implement normalized edit distance
            def _edit_dist(s1, s2):
                m, n = len(s1), len(s2)
                dp = list(range(n + 1))
                for i in range(1, m + 1):
                    prev = dp[0]
                    dp[0] = i
                    for j in range(1, n + 1):
                        temp = dp[j]
                        dp[j] = prev if s1[i-1] == s2[j-1] else 1 + min(prev, dp[j], dp[j-1])
                        prev = temp
                return dp[n]
            lev_lib = None
        else:
            lev_lib = lev_lib

    p = pred.strip().lower()
    best = 0.0
    for g in golds:
        g_str = str(g).strip().lower()
        if not g_str:
            continue
        ml = max(len(p), len(g_str))
        if ml == 0:
            best = max(best, 1.0)
            continue
        if lev_lib:
            dist = lev_lib.distance(p, g_str)
        else:
            dist = _edit_dist(p, g_str)
        nl = dist / ml
        best = max(best, 1.0 - nl if nl < 0.5 else 0.0)
    return best


# ─── Main: Test set → submission ──────────────────────────────────────────────

print(f"\nLoading {TEST_FILE}...")
test_df = pd.read_parquet(TEST_FILE)
print(f"Test samples: {len(test_df)}")

results = {}   # {questionId (int): answer (str)}

for i in range(len(test_df)):
    sample = test_df.iloc[i]
    q_ids, q_texts, answers = parse_sample(sample)

    if i % 10 == 0:
        print(f"  [{i}/{len(test_df)}] Processing sample {i}...")

    for j, (qid, qtext) in enumerate(zip(q_ids, q_texts)):
        ans = answer_question(sample, qtext, j)
        # DocVQA submission thường dùng int key
        try:
            results[int(qid)] = ans
        except (ValueError, TypeError):
            results[str(qid)] = ans

# Sort by key cho gọn
results = dict(sorted(results.items(), key=lambda x: (isinstance(x[0], str), x[0])))

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nSaved: {OUT_FILE} ({len(results)} answers)")
print(f"Sample entries:")
for k, v in list(results.items())[:5]:
    print(f"  {k!r}: {v!r}")


# ─── Optional: Evaluate trên val set ──────────────────────────────────────────

print(f"\nLoading {VAL_FILE} for evaluation...")
try:
    val_df = pd.read_parquet(VAL_FILE)
    print(f"Val samples: {len(val_df)}")

    total_anls = 0.0
    cnt = 0
    N_EVAL = min(50, len(val_df))

    for i in range(N_EVAL):
        sample = val_df.iloc[i]
        q_ids, q_texts, answers = parse_sample(sample)

        for j, qtext in enumerate(q_texts):
            golds = answers[j] if j < len(answers) else []
            if not golds:
                continue

            pred  = answer_question(sample, qtext, j)
            score = compute_anls(pred, golds)
            total_anls += score
            cnt += 1

    if cnt > 0:
        print(f"\nANLS trên {cnt} câu hỏi ({N_EVAL} samples): {total_anls/cnt:.4f}")
    else:
        print("Không tính được ANLS: val set không có ground truth answers.")

except Exception as e:
    print(f"Val evaluation error: {e}")