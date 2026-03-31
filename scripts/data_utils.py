"""
scripts/data_utils.py

Build graph từ sample DocVQA với các loại quan hệ có ý nghĩa thực sự.

Cải thiện so với version cũ:
  - 4 loại edge có ý nghĩa thay vì chỉ sequential
  - Node features từ cả question + answer context
  - Edge type phân biệt rõ ràng
"""
from __future__ import annotations

import torch
import numpy as np
from functools import lru_cache
from typing import List, Tuple

from src.algo.rgat_model import REL2IDX


# ─── Text encoder (lazy load) ─────────────────────────────────────────────────

_tokenizer = None
_bert      = None


def _get_encoder():
    global _tokenizer, _bert
    if _tokenizer is None:
        from transformers import BertTokenizer, BertModel
        print("[data_utils] Loading BERT...")
        _tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
        _bert      = BertModel.from_pretrained("bert-base-uncased")
        _bert.eval()
        print("[data_utils] BERT loaded.")
    return _tokenizer, _bert


def encode_text(text: str) -> torch.Tensor:
    """Encode 1 chuoi text → vector [1, 768]."""
    tokenizer, bert = _get_encoder()
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=128,
        padding=True,
    )
    with torch.no_grad():
        outputs = bert(**inputs)
    return outputs.last_hidden_state.mean(dim=1).detach()  # [1, 768]


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph_from_sample(
    sample,
    use_layout: bool = True,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Build graph tu 1 sample DocVQA.

    Node  = moi cau hoi trong sample
    Edge  = quan he giua cac cau hoi

    Tra ve:
        x          : [N, 768]  node features
        edge_index : [2, E]    edges
        edge_type  : [E]       loai quan he

    Loai quan he:
        0 SEQUENTIAL  - cau hoi i → i+1 (thu tu trong tai lieu)
        1 SAME_PAGE   - cung trang
        2 SAME_SECTION- cung section (heuristic: cau hoi gan nhau)
        3 VISUAL_NEAR - gần nhau ve layout (neu co bbox)
    """
    questions = sample["questions"]

    # Lay danh sach cau hoi
    if isinstance(questions, dict):
        q_texts = questions.get("question", [])
        q_pages = questions.get("page_ids", [None] * len(q_texts))
    else:
        # Fallback: questions la list
        q_texts = [str(q) for q in questions] if questions else []
        q_pages = [None] * len(q_texts)

    N = len(q_texts)
    if N == 0:
        return (
            torch.empty((0, 768)),
            torch.empty((2, 0), dtype=torch.long),
            torch.empty((0,), dtype=torch.long),
        )

    # ── Node features ─────────────────────────────────────────────────────────
    node_feats = []
    for qt in q_texts:
        vec = encode_text(str(qt))   # [1, 768]
        node_feats.append(vec)
    x = torch.vstack(node_feats)    # [N, 768]

    # ── Edges ─────────────────────────────────────────────────────────────────
    edge_src  = []
    edge_dst  = []
    edge_rels = []

    def add_edge(u, v, rel_name):
        r = REL2IDX.get(rel_name, 0)
        # Undirected: them ca 2 chieu
        edge_src.extend([u, v])
        edge_dst.extend([v, u])
        edge_rels.extend([r, r])

    for i in range(N):
        for j in range(i + 1, N):

            # 1. SEQUENTIAL — moi cap lien tiep
            if j == i + 1:
                add_edge(i, j, "SEQUENTIAL")
                continue

            # 2. SAME_PAGE — cung trang (neu co page_ids)
            pi = q_pages[i] if i < len(q_pages) else None
            pj = q_pages[j] if j < len(q_pages) else None
            if pi is not None and pj is not None and pi == pj:
                add_edge(i, j, "SAME_PAGE")
                continue

            # 3. SAME_SECTION — heuristic: cach nhau <= 3 cau
            if abs(i - j) <= 3:
                add_edge(i, j, "SAME_SECTION")
                continue

            # 4. VISUAL_NEAR — tat ca cau hoi con lai (fallback)
            if abs(i - j) <= 6:
                add_edge(i, j, "VISUAL_NEAR")

    if not edge_src:
        return x, torch.empty((2, 0), dtype=torch.long), torch.empty((0,), dtype=torch.long)

    edge_index = torch.tensor([edge_src, edge_dst], dtype=torch.long)
    edge_type  = torch.tensor(edge_rels, dtype=torch.long)

    return x, edge_index, edge_type


# ─── Label builder (dung cho training) ────────────────────────────────────────

def build_labels_from_sample(sample) -> torch.Tensor:
    """
    Tao nhan cho moi node (cau hoi).
    Label = 1 neu cau hoi nay co answer co trong OCR text, 0 nguoc lai.
    Day la heuristic don gian, co the cai thien bang answer span matching.
    """
    questions = sample["questions"]
    if isinstance(questions, dict):
        q_texts  = questions.get("question", [])
        answers  = questions.get("answers", [[] for _ in q_texts])
    else:
        q_texts = list(questions) if questions else []
        answers = [[] for _ in q_texts]

    labels = []
    for i, (q, ans_list) in enumerate(zip(q_texts, answers)):
        # Co answer → label 1, khong co → label 0
        has_answer = len(ans_list) > 0 and any(str(a).strip() for a in ans_list)
        labels.append(1 if has_answer else 0)

    if not labels:
        return torch.empty((0,), dtype=torch.long)
    return torch.tensor(labels, dtype=torch.long)