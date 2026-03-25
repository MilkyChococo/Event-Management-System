from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(slots=True)
class EmbeddingStore:
    graph: dict[str, Any]
    embeddings: np.ndarray
    meta: list[dict[str, Any]]
    node_to_row: dict[str, int]


def load_embedding_store(
    graph_path: str | Path,
    embeddings_path: str | Path,
    meta_path: str | Path,
) -> EmbeddingStore:
    graph_path = Path(graph_path)
    embeddings_path = Path(embeddings_path)
    meta_path = Path(meta_path)

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    embeddings = np.load(embeddings_path)
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    node_to_row: dict[str, int] = {}
    for item in meta:
        node_id = str(item.get("node_id", "")).strip()
        row = int(item.get("row", -1))
        if node_id and row >= 0:
            node_to_row[node_id] = row

    return EmbeddingStore(
        graph=graph,
        embeddings=embeddings,
        meta=meta,
        node_to_row=node_to_row,
    )


def cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    norm_a = float(np.linalg.norm(vector_a))
    norm_b = float(np.linalg.norm(vector_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / (norm_a * norm_b))


def normalized_cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    return (1.0 + cosine_similarity(vector_a, vector_b)) / 2.0


def _empty_neighbor_summary() -> dict[str, Any]:
    return {
        "incoming": [],
        "outgoing": [],
        "neighbor_ids": [],
    }


def enrich_graph_for_cse(
    graph: dict[str, Any],
    embeddings: np.ndarray,
    node_to_row: dict[str, int],
    lambda_hub: float = 0.1,
) -> dict[str, Any]:
    nodes = list(graph.get("nodes", []))
    edges = list(graph.get("edges", []))

    node_index: dict[str, dict[str, Any]] = {}
    neighbor_summary: dict[str, dict[str, Any]] = {}
    deg_in: dict[str, int] = {}
    deg_out: dict[str, int] = {}

    for node in nodes:
        node_id = str(node.get("id", ""))
        node_index[node_id] = node
        neighbor_summary[node_id] = _empty_neighbor_summary()
        deg_in[node_id] = 0
        deg_out[node_id] = 0

    enriched_edges: list[dict[str, Any]] = []
    for edge in edges:
        source_id = str(edge.get("source_id", ""))
        target_id = str(edge.get("target_id", ""))
        source_row = node_to_row.get(source_id)
        target_row = node_to_row.get(target_id)

        conf_off = None
        if (
            source_row is not None
            and target_row is not None
            and 0 <= source_row < embeddings.shape[0]
            and 0 <= target_row < embeddings.shape[0]
        ):
            conf_off = normalized_cosine_similarity(
                embeddings[source_row],
                embeddings[target_row],
            )

        enriched_edge = dict(edge)
        if conf_off is not None:
            enriched_edge["conf_off"] = round(conf_off, 6)
        enriched_edges.append(enriched_edge)

        if source_id in deg_out:
            deg_out[source_id] += 1
        if target_id in deg_in:
            deg_in[target_id] += 1

        if source_id in neighbor_summary:
            neighbor_summary[source_id]["outgoing"].append(
                {
                    "target_id": target_id,
                    "relation": str(edge.get("relation", "")),
                    "conf_off": round(conf_off, 6) if conf_off is not None else None,
                }
            )
        if target_id in neighbor_summary:
            neighbor_summary[target_id]["incoming"].append(
                {
                    "source_id": source_id,
                    "relation": str(edge.get("relation", "")),
                    "conf_off": round(conf_off, 6) if conf_off is not None else None,
                }
            )

    enriched_nodes: list[dict[str, Any]] = []
    for node in nodes:
        node_id = str(node.get("id", ""))
        node_copy = dict(node)

        embedding_row = node_to_row.get(node_id)
        total_deg = deg_in.get(node_id, 0) + deg_out.get(node_id, 0)
        hub = math.log(1.0 + total_deg)

        summary = neighbor_summary.get(node_id, _empty_neighbor_summary())
        neighbor_ids = sorted(
            {
                *(item["target_id"] for item in summary["outgoing"]),
                *(item["source_id"] for item in summary["incoming"]),
            }
        )
        summary["neighbor_ids"] = neighbor_ids

        node_copy["embedding_row"] = embedding_row
        node_copy["deg_in"] = deg_in.get(node_id, 0)
        node_copy["deg_out"] = deg_out.get(node_id, 0)
        node_copy["deg"] = total_deg
        node_copy["hub"] = round(hub, 6)
        node_copy["lambda_hub"] = lambda_hub
        node_copy["neighbors"] = summary
        enriched_nodes.append(node_copy)

    enriched_graph = dict(graph)
    enriched_graph["nodes"] = enriched_nodes
    enriched_graph["edges"] = enriched_edges
    enriched_graph["cse_offline"] = {
        "lambda_hub": lambda_hub,
        "num_embedded_nodes": len(node_to_row),
        "num_edges_with_conf_off": sum(1 for edge in enriched_edges if "conf_off" in edge),
    }
    return enriched_graph


def save_enriched_graph(enriched_graph: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(enriched_graph, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path
