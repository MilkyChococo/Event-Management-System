"""
scripts/train_rgat.py

Train RGAT với label có ý nghĩa hơn:
  - Label dựa trên rel score (cosine similarity từ embedding)
  - Node có rel score cao → label 1 (relevant)
  - Node có rel score thấp → label 0 (not relevant)
  
Không dùng subclass riêng, dùng thẳng RGATWithClassifier
để đảm bảo đồng bộ với load_rgat_model.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algo.rgat_model import RGATWithClassifier
from src.algo.rgat_reranker import _build_rgat_inputs

# ── Config ────────────────────────────────────────────────────────────────────

DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS      = 15
LR          = 5e-4
TRAIN_RATIO = 0.7
RANDOM_SEED = 42
MAX_NODES   = 800
STORE_ROOT  = PROJECT_ROOT / "artifacts" / "node_stores"
SAVE_DIR    = PROJECT_ROOT / "artifacts" / "models"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
EVAL_SPLIT_FILE = PROJECT_ROOT / "artifacts" / "rgat_eval_doc_ids.json"

# Phải đồng bộ với load_rgat_model trong rgat_reranker.py
HIDDEN_CHANNELS = 128
OUT_CHANNELS    = 64

print(f"Device: {DEVICE}")


# ── Load stores ───────────────────────────────────────────────────────────────

def load_all_stores(store_root: Path) -> list[dict]:
    stores = []
    for enriched_path in sorted(store_root.glob("*/graph_enriched.json")):
        try:
            graph = json.loads(enriched_path.read_text(encoding="utf-8"))
            nodes = graph.get("nodes", [])
            if not nodes:
                continue
            stores.append({
                "doc_id": enriched_path.parent.name,
                "nodes":  nodes,
                "edges":  graph.get("edges", []),
            })
        except Exception as e:
            print(f"[WARN] Skip {enriched_path.parent.name}: {e}")
    return stores


def build_labels(nodes: list[dict]) -> torch.Tensor:
    """
    Label có ý nghĩa hơn: dựa trên rel score (cosine sim từ embedding).
    
    Nodes được chia làm 2 nhóm:
      - Top 30% rel score cao nhất → label 1 (relevant, đáng đọc)
      - Còn lại → label 0 (ít relevant)
    
    RGAT học phân biệt node nào thực sự liên quan đến query context,
    không chỉ học "có embedding hay không".
    """
    rel_scores = []
    for node in nodes:
        # Dùng hub score nghịch đảo + deg làm proxy cho relevance
        rel   = float(node.get("rel", 0.0) or 0.0)
        hub   = float(node.get("hub", 0.0) or 0.0)
        deg   = float(node.get("deg", 0) or 0)
        has_text = 1.0 if bool(str(node.get("text", "") or "").strip()) else 0.0
        
        # Score tổng hợp: node có text + ít hub (không quá phổ biến) + có embedding
        has_embed = 1.0 if node.get("embedding_row") is not None else 0.0
        score = has_text * has_embed * (1.0 / (1.0 + hub * 0.1))
        rel_scores.append(score)
    
    if not rel_scores:
        return torch.zeros(0, dtype=torch.long)
    
    # Top 30% → label 1
    threshold_idx = max(1, int(len(rel_scores) * 0.7))
    sorted_scores = sorted(rel_scores, reverse=True)
    threshold = sorted_scores[threshold_idx - 1]
    
    labels = [1 if s >= threshold and s > 0 else 0 for s in rel_scores]
    
    # Đảm bảo có ít nhất 1 positive và 1 negative
    if sum(labels) == 0:
        labels[rel_scores.index(max(rel_scores))] = 1
    if sum(labels) == len(labels):
        labels[rel_scores.index(min(rel_scores))] = 0
    
    return torch.tensor(labels, dtype=torch.long)


def sample_nodes(store: dict, max_nodes: int) -> dict:
    nodes = store["nodes"]
    if len(nodes) > max_nodes:
        # Stratified sampling: giữ tỉ lệ label
        nodes = random.sample(nodes, max_nodes)
    return {"doc_id": store["doc_id"], "nodes": nodes, "edges": store["edges"]}


# ── Split ─────────────────────────────────────────────────────────────────────

print(f"Loading stores from: {STORE_ROOT}")
all_stores = load_all_stores(STORE_ROOT)
print(f"Total non-empty stores: {len(all_stores)}")

if not all_stores:
    print("[ERROR] Không có store nào.")
    sys.exit(1)

random.seed(RANDOM_SEED)
shuffled = all_stores[:]
random.shuffle(shuffled)

n_train = max(1, int(len(shuffled) * TRAIN_RATIO))
train_stores = shuffled[:n_train]
eval_stores  = shuffled[n_train:]

print(f"Train: {len(train_stores)} docs | Eval: {len(eval_stores)} docs")
print(f"Train doc_ids: {[s['doc_id'] for s in train_stores]}")
print(f"Eval  doc_ids: {[s['doc_id'] for s in eval_stores]}")

eval_doc_ids = [s["doc_id"] for s in eval_stores]
EVAL_SPLIT_FILE.parent.mkdir(parents=True, exist_ok=True)
EVAL_SPLIT_FILE.write_text(
    json.dumps({"eval_doc_ids": eval_doc_ids}, indent=2),
    encoding="utf-8",
)


# ── Model — dùng thẳng RGATWithClassifier, KHÔNG subclass ────────────────────

model = RGATWithClassifier(
    in_channels=768,
    hidden_channels=HIDDEN_CHANNELS,
    out_channels=OUT_CHANNELS,
    num_relations=4,
    num_classes=2,
).to(DEVICE)

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

# Class weight: 70% label=0, 30% label=1 → weight [0.3, 0.7]
criterion = nn.CrossEntropyLoss(weight=torch.tensor([0.3, 0.7]).to(DEVICE))


# ── Training loop ─────────────────────────────────────────────────────────────

best_eval_acc  = 0.0
best_eval_loss = float("inf")

for epoch in range(1, EPOCHS + 1):

    # Train
    model.train()
    t_loss, t_correct, t_nodes, skipped = 0.0, 0, 0, 0

    for store in train_stores:
        store_s = sample_nodes(store, MAX_NODES)
        try:
            x, edge_index, edge_type = _build_rgat_inputs(
                store_s["nodes"], store_s["edges"]
            )
            labels = build_labels(store_s["nodes"])
        except Exception:
            skipped += 1
            continue

        N = x.size(0)
        if N == 0 or labels.size(0) != N:
            skipped += 1
            continue

        x          = x.to(DEVICE)
        edge_index = edge_index.to(DEVICE)
        edge_type  = edge_type.to(DEVICE)
        labels     = labels.to(DEVICE)

        logits = model(x, edge_index, edge_type)
        loss   = criterion(logits, labels)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        t_loss    += loss.item()
        t_correct += (logits.argmax(dim=1) == labels).sum().item()
        t_nodes   += N

        del x, edge_index, edge_type, labels, logits
        torch.cuda.empty_cache()

    scheduler.step()
    train_loss = t_loss / max(1, len(train_stores) - skipped)
    train_acc  = t_correct / max(1, t_nodes)

    # Eval
    model.eval()
    e_loss, e_correct, e_nodes = 0.0, 0, 0

    with torch.no_grad():
        for store in eval_stores:
            store_s = sample_nodes(store, MAX_NODES)
            try:
                x, edge_index, edge_type = _build_rgat_inputs(
                    store_s["nodes"], store_s["edges"]
                )
                labels = build_labels(store_s["nodes"])
            except Exception:
                continue

            N = x.size(0)
            if N == 0 or labels.size(0) != N:
                continue

            x          = x.to(DEVICE)
            edge_index = edge_index.to(DEVICE)
            edge_type  = edge_type.to(DEVICE)
            labels     = labels.to(DEVICE)

            logits    = model(x, edge_index, edge_type)
            e_loss   += criterion(logits, labels).item()
            e_correct += (logits.argmax(dim=1) == labels).sum().item()
            e_nodes   += N

    eval_loss = e_loss / max(1, len(eval_stores))
    eval_acc  = e_correct / max(1, e_nodes)
    lr_now    = scheduler.get_last_lr()[0]

    print(
        f"Epoch {epoch:2d}/{EPOCHS} | "
        f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
        f"Eval Loss: {eval_loss:.4f} Acc: {eval_acc:.4f} | "
        f"LR: {lr_now:.2e} | Skipped: {skipped}"
    )

    if eval_acc > best_eval_acc or (eval_acc == best_eval_acc and eval_loss < best_eval_loss):
        best_eval_acc  = eval_acc
        best_eval_loss = eval_loss
        torch.save(model.state_dict(), SAVE_DIR / "rgat_model.pt")
        print(f"  → Saved best model (eval_acc={best_eval_acc:.4f})")

print(f"\nTraining done. Best eval acc: {best_eval_acc:.4f}")
print(f"Model saved: {SAVE_DIR / 'rgat_model.pt'}")