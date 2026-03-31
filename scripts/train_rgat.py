"""
scripts/train_rgat.py

Train RGAT trên 80% val stores, evaluate trên 20% còn lại.
Tránh data leakage: không train trên data dùng để đánh giá ANLS.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algo.rgat_model import RGATWithClassifier
from src.algo.rgat_reranker import _build_rgat_inputs

# ── Config ────────────────────────────────────────────────────────────────────

DEVICE       = "cuda" if torch.cuda.is_available() else "cpu"
EPOCHS       = 10
LR           = 1e-3
TRAIN_RATIO  = 0.8          # 80% train, 20% eval
RANDOM_SEED  = 42
STORE_ROOT   = PROJECT_ROOT / "artifacts" / "node_stores"
SAVE_DIR     = PROJECT_ROOT / "artifacts" / "models"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

BATCH_SIZE   = 16

# File ghi lại doc_ids nào dùng để eval (để run_docvqa_submission biết)
EVAL_SPLIT_FILE = PROJECT_ROOT / "artifacts" / "rgat_eval_doc_ids.json"

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
    labels = []
    for node in nodes:
        has_embed = node.get("embedding_row") is not None
        has_text  = bool(str(node.get("text", "") or "").strip())
        labels.append(1 if (has_embed and has_text) else 0)
    return torch.tensor(labels, dtype=torch.long)


# ── Split ─────────────────────────────────────────────────────────────────────

print(f"Loading stores from: {STORE_ROOT}")
all_stores = load_all_stores(STORE_ROOT)
print(f"Total non-empty stores: {len(all_stores)}")

if not all_stores:
    print("[ERROR] Không có store nào. Chạy run_offline_index_parquet --split val trước.")
    sys.exit(1)

random.seed(RANDOM_SEED)
shuffled = all_stores[:]
random.shuffle(shuffled)

n_train = max(1, int(len(shuffled) * TRAIN_RATIO))
train_stores = shuffled[:n_train]
eval_stores  = shuffled[n_train:]

print(f"Train stores: {len(train_stores)} | Eval stores: {len(eval_stores)}")
print(f"Train doc_ids: {[s['doc_id'] for s in train_stores]}")
print(f"Eval  doc_ids: {[s['doc_id'] for s in eval_stores]}")

# Ghi eval doc_ids ra file để run_docvqa_submission dùng
eval_doc_ids = [s["doc_id"] for s in eval_stores]
EVAL_SPLIT_FILE.parent.mkdir(parents=True, exist_ok=True)
EVAL_SPLIT_FILE.write_text(
    json.dumps({"eval_doc_ids": eval_doc_ids}, indent=2),
    encoding="utf-8",
)
print(f"Eval split saved: {EVAL_SPLIT_FILE}")


# ── Model ─────────────────────────────────────────────────────────────────────

model = RGATWithClassifier(
    in_channels=768,
    hidden_channels=256,
    out_channels=128,
    num_relations=4,
    num_classes=2,
).to(DEVICE)

optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
criterion = nn.CrossEntropyLoss(weight=torch.tensor([0.3, 0.7]).to(DEVICE))


# ── Training loop ─────────────────────────────────────────────────────────────

best_acc  = 0.0
best_loss = float("inf")

train_loader = DataLoader(train_stores, batch_size=BATCH_SIZE, shuffle=True)
eval_loader  = DataLoader(eval_stores, batch_size=BATCH_SIZE, shuffle=False)

for epoch in range(1, EPOCHS + 1):

    # ── Train ────────────────────────────────────────────────────────────────
    model.train()
    t_loss, t_correct, t_nodes, skipped = 0.0, 0, 0, 0

    for batch in train_loader:
        for store in batch:
            try:
                x, edge_index, edge_type = _build_rgat_inputs(
                    store["nodes"], store["edges"]
                )
                labels = build_labels(store["nodes"])
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

    scheduler.step()

    train_loss = t_loss / max(1, len(train_stores) - skipped)
    train_acc  = t_correct / max(1, t_nodes)

    # ── Eval ────────────────────────────────────────────────────────────────
    model.eval()
    e_loss, e_correct, e_nodes = 0.0, 0, 0

    with torch.no_grad():
        for batch in eval_loader:
            for store in batch:
                try:
                    x, edge_index, edge_type = _build_rgat_inputs(
                        store["nodes"], store["edges"]
                    )
                    labels = build_labels(store["nodes"])
                except Exception:
                    continue

                N = x.size(0)
                if N == 0 or labels.size(0) != N:
                    continue

                x          = x.to(DEVICE)
                edge_index = edge_index.to(DEVICE)
                edge_type  = edge_type.to(DEVICE)
                labels     = labels.to(DEVICE)

                logits   = model(x, edge_index, edge_type)
                e_loss  += criterion(logits, labels).item()
                e_correct += (logits.argmax(dim=1) == labels).sum().item()
                e_nodes   += N

    eval_loss = e_loss / max(1, len(eval_stores))
    eval_acc  = e_correct / max(1, e_nodes)

    lr_now = scheduler.get_last_lr()[0]
    print(
        f"Epoch {epoch:2d}/{EPOCHS} | "
        f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
        f"Eval Loss: {eval_loss:.4f} Acc: {eval_acc:.4f} | "
        f"LR: {lr_now:.2e} | Skipped: {skipped}"
    )

    # Save best dựa trên eval acc
    if eval_acc > best_acc or (eval_acc == best_acc and eval_loss < best_loss):
        best_acc  = eval_acc
        best_loss = eval_loss
        torch.save(model.state_dict(), SAVE_DIR / "rgat_model.pt")
        print(f"  → Saved best model (eval_acc={best_acc:.4f})")

print(f"\nTraining done.")
print(f"Best eval acc: {best_acc:.4f}")
print(f"Model: {SAVE_DIR / 'rgat_model.pt'}")
print(f"Eval doc_ids (dùng cho ANLS evaluation): {eval_doc_ids}")
