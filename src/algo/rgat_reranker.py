"""
src/algo/rgat_reranker.py

RGAT Re-ranker: nhận subgraph payload từ CSE, dùng RGAT để
re-score các nodes, trả về subgraph payload đã được re-rank.

Vai trò trong pipeline:
  CSE subgraph → [RGAT re-rank nodes] → Qwen answering

RGAT học được quan hệ giữa các nodes (line/chunk/region) trong graph,
cho phép re-score tốt hơn cosine similarity đơn thuần của CSE.
"""
from __future__ import annotations

import math
from typing import Any

import torch
import torch.nn.functional as F

from src.algo.rgat_model import RGATWithClassifier, REL2IDX


# ── Relation mapping từ graph edge types của pipeline gốc ────────────────────
# Pipeline gốc dùng các relation: SAME_LINE, NEXT_LINE, CONTAINS, IN_REGION, v.v.
# Map về 4 loại RGAT đang có

_PIPELINE_REL_TO_RGAT: dict[str, str] = {
    # Line relations
    "NEXT_LINE":        "SEQUENTIAL",
    "PREV_LINE":        "SEQUENTIAL",
    "SAME_LINE":        "SAME_SECTION",
    # Chunk relations
    "NEXT_CHUNK":       "SEQUENTIAL",
    "PREV_CHUNK":       "SEQUENTIAL",
    "SAME_CHUNK":       "SAME_SECTION",
    # Region / hierarchical
    "CONTAINS":         "SAME_PAGE",
    "IN_REGION":        "SAME_PAGE",
    "REGION_OVERLAP":   "VISUAL_NEAR",
    "NEAR":             "VISUAL_NEAR",
    "VISUAL_NEAR":      "VISUAL_NEAR",
    # Fallback
    "SEQUENTIAL":       "SEQUENTIAL",
    "SAME_PAGE":        "SAME_PAGE",
    "SAME_SECTION":     "SAME_SECTION",
}

_DEFAULT_RGAT_REL = "SEQUENTIAL"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def _map_relation(rel: str) -> int:
    rgat_rel = _PIPELINE_REL_TO_RGAT.get(rel.strip(), _DEFAULT_RGAT_REL)
    return REL2IDX.get(rgat_rel, 0)


def _node_to_feature_vector(node: dict[str, Any]) -> list[float]:
    """
    Chuyển 1 node thành feature vector 768-dim để đưa vào RGAT.

    Dùng các signal có sẵn trong node payload (không cần BERT):
    - rel score (cosine sim từ CSE)
    - final_score
    - hub penalty
    - deg_in, deg_out
    - node_type one-hot (4 loại)
    - bbox normalized (4 values)
    - conf_off trung bình của edges liên quan
    - padding zeros đến 768 dim
    """
    NODE_TYPES = ["line", "chunk", "region", "fine"]

    rel       = float(node.get("rel", 0.0) or 0.0)
    final     = float(node.get("final_score", rel) or rel)
    hub       = float(node.get("hub", 0.0) or 0.0)
    deg_in    = float(node.get("deg_in", 0) or 0)
    deg_out   = float(node.get("deg_out", 0) or 0)
    deg       = float(node.get("deg", deg_in + deg_out) or 0)

    # Node type one-hot
    ntype = str(node.get("node_type", "")).strip().lower()
    type_onehot = [1.0 if ntype == t else 0.0 for t in NODE_TYPES]

    # BBox normalized (0–1 range, page thường ~1000x1000px)
    bbox = node.get("bbox") or {}
    if isinstance(bbox, dict):
        bx1 = float(bbox.get("left",   0.0) or 0.0) / 1000.0
        by1 = float(bbox.get("top",    0.0) or 0.0) / 1000.0
        bx2 = float(bbox.get("right",  0.0) or 0.0) / 1000.0
        by2 = float(bbox.get("bottom", 0.0) or 0.0) / 1000.0
    else:
        bx1 = by1 = bx2 = by2 = 0.0

    # Text length signal (log-normalized)
    text_len = math.log(1.0 + len(str(node.get("text", "") or "")))

    # Embedding row available?
    has_embedding = 1.0 if node.get("embedding_row") is not None else 0.0

    # Base features: 14 values
    base = [
        rel, final, hub,
        deg_in / 50.0, deg_out / 50.0, deg / 100.0,
        *type_onehot,
        bx1, by1, bx2, by2,
        text_len / 10.0,
        has_embedding,
    ]

    # Pad đến 768 dim
    feat = base + [0.0] * (768 - len(base))
    return feat


def _build_rgat_inputs(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Chuyển nodes/edges của subgraph → (x, edge_index, edge_type) cho RGAT.
    """
    N = len(nodes)
    if N == 0:
        return (
            torch.empty((0, 768)),
            torch.empty((2, 0), dtype=torch.long),
            torch.empty((0,), dtype=torch.long),
        )

    # Node ID → index
    id_to_idx = {str(node.get("id", "")): i for i, node in enumerate(nodes)}

    # Node features
    x = torch.tensor(
        [_node_to_feature_vector(node) for node in nodes],
        dtype=torch.float32,
    )  # [N, 768]

    # Edges (undirected: thêm cả 2 chiều)
    src_list, dst_list, rel_list = [], [], []
    node_ids_in_sub = set(id_to_idx.keys())

    for edge in edges:
        src_id = str(edge.get("source_id", ""))
        dst_id = str(edge.get("target_id", ""))
        if src_id not in node_ids_in_sub or dst_id not in node_ids_in_sub:
            continue
        rel_idx = _map_relation(str(edge.get("relation", "")))
        u, v = id_to_idx[src_id], id_to_idx[dst_id]
        # Undirected
        src_list += [u, v]
        dst_list += [v, u]
        rel_list += [rel_idx, rel_idx]

    if not src_list:
        edge_index = torch.empty((2, 0), dtype=torch.long)
        edge_type  = torch.empty((0,), dtype=torch.long)
    else:
        edge_index = torch.tensor([src_list, dst_list], dtype=torch.long)
        edge_type  = torch.tensor(rel_list, dtype=torch.long)

    return x, edge_index, edge_type


def rerank_subgraph_nodes_with_rgat(
    subgraph_payload: dict[str, Any],
    rgat_model: RGATWithClassifier,
    device: str = DEVICE,
    score_blend: float = 0.4,
) -> dict[str, Any]:
    """
    Re-rank nodes trong 1 subgraph (single) dùng RGAT.

    Args:
        subgraph_payload : dict có keys 'nodes', 'edges'
        rgat_model       : loaded RGATWithClassifier
        device           : cuda/cpu
        score_blend      : trọng số RGAT (1 - score_blend = CSE score)

    Returns:
        subgraph_payload với nodes đã được re-sort theo rgat_final_score
    """
    nodes = list(subgraph_payload.get("nodes", []))
    edges = list(subgraph_payload.get("edges", []))

    if not nodes:
        return subgraph_payload

    x, edge_index, edge_type = _build_rgat_inputs(nodes, edges)

    x_dev  = x.to(device)
    ei_dev = edge_index.to(device)
    et_dev = edge_type.to(device)

    rgat_model.eval()
    with torch.no_grad():
        logits = rgat_model(x_dev, ei_dev, et_dev)        # [N, 2]
        rgat_probs = torch.softmax(logits, dim=1)[:, 1]   # [N] P(relevant)

    rgat_scores = rgat_probs.cpu().tolist()

    # Blend RGAT score với CSE final_score/rel
    reranked_nodes = []
    for i, node in enumerate(nodes):
        node_copy = dict(node)
        cse_score = float(node.get("final_score", node.get("rel", 0.0)) or 0.0)
        rgat_score = float(rgat_scores[i])

        # Weighted blend
        blended = (1.0 - score_blend) * cse_score + score_blend * rgat_score
        node_copy["rgat_score"]       = round(rgat_score, 6)
        node_copy["rgat_final_score"] = round(blended, 6)
        reranked_nodes.append(node_copy)

    # Sort by blended score
    reranked_nodes.sort(
        key=lambda n: float(n.get("rgat_final_score", 0.0)),
        reverse=True,
    )

    result = dict(subgraph_payload)
    result["nodes"] = reranked_nodes
    result["rgat_reranked"] = True
    return result


def rerank_multi_subgraph_payload(
    multi_payload: dict[str, Any],
    rgat_model: RGATWithClassifier,
    device: str = DEVICE,
    score_blend: float = 0.4,
) -> dict[str, Any]:
    """
    Re-rank tất cả subgraphs trong multi-subgraph payload (output của CSE).
    Sau đó re-sort subgraphs theo avg rgat_final_score của top-3 nodes.

    Đây là hàm chính được gọi từ submission pipeline.
    """
    subgraphs = list(multi_payload.get("subgraphs", []))
    if not subgraphs:
        return multi_payload

    reranked_subgraphs = []
    for sg in subgraphs:
        reranked_sg = rerank_subgraph_nodes_with_rgat(
            subgraph_payload=sg,
            rgat_model=rgat_model,
            device=device,
            score_blend=score_blend,
        )

        # Tính lại subgraph_score từ RGAT scores của top-3 nodes
        top_nodes = reranked_sg.get("nodes", [])[:3]
        top_scores = [
            float(n.get("rgat_final_score", n.get("rel", 0.0)))
            for n in top_nodes
        ]
        new_sg_score = sum(top_scores) / len(top_scores) if top_scores else 0.0
        reranked_sg["subgraph_score"] = round(new_sg_score, 6)
        reranked_subgraphs.append(reranked_sg)

    # Re-sort subgraphs theo subgraph_score mới
    reranked_subgraphs.sort(
        key=lambda sg: -float(sg.get("subgraph_score", 0.0))
    )

    result = dict(multi_payload)
    result["subgraphs"] = reranked_subgraphs
    result["rgat_reranked"] = True
    return result


def load_rgat_model(
    model_path: str,
    device: str = DEVICE,
) -> RGATWithClassifier:
    """Load RGAT model từ checkpoint."""
    from pathlib import Path as _Path
    import torch as _torch

    model = RGATWithClassifier(
        in_channels=768,
        hidden_channels=256,
        out_channels=128,
        num_relations=4,
        num_classes=2,
    ).to(device)

    path = _Path(model_path)
    if path.exists():
        model.load_state_dict(_torch.load(model_path, map_location=device))
        print(f"[RGAT] Loaded model from {model_path}")
    else:
        print(f"[RGAT] WARNING: No model at {model_path}, using random weights.")
        print(f"[RGAT]          Run scripts/train_rgat.py first.")
    model.eval()
    return model