from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def bbox_to_dict(bbox: Any) -> dict[str, float]:
    return {
        "left": float(bbox.left),
        "top": float(bbox.top),
        "right": float(bbox.right),
        "bottom": float(bbox.bottom),
        "width": float(bbox.width),
        "height": float(bbox.height),
        "center_x": float(bbox.center_x),
        "center_y": float(bbox.center_y),
    }


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "left") and hasattr(value, "top") and hasattr(value, "right") and hasattr(value, "bottom"):
        return bbox_to_dict(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    return value


def relation_to_dict(relation: Any) -> dict[str, Any]:
    return {
        "source_id": relation.source_id,
        "target_id": relation.target_id,
        "relation": relation.relation,
        "score": float(getattr(relation, "score", 1.0)),
    }


def build_graph_payload(pipeline: Any) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []

    for line in pipeline.lines:
        nodes.append(
            {
                "id": line.id,
                "node_type": "line",
                "page": line.page,
                "text": line.text,
                "bbox": bbox_to_dict(line.bbox),
                "metadata": to_jsonable(dict(line.metadata)),
            }
        )

    for chunk in pipeline.chunks:
        nodes.append(
            {
                "id": chunk.id,
                "node_type": "chunk",
                "page": chunk.page,
                "text": chunk.text,
                "bbox": bbox_to_dict(chunk.bbox),
                "line_ids": [line.id for line in chunk.lines],
            }
        )

    for region in pipeline.regions:
        nodes.append(
            {
                "id": region.id,
                "node_type": "region",
                "page": region.page,
                "label": region.label,
                "score": float(region.score),
                "text": region.content,
                "bbox": bbox_to_dict(region.bbox),
                "metadata": to_jsonable(dict(region.metadata)),
            }
        )

    for fine_node in pipeline.fine_nodes:
        nodes.append(
            {
                "id": fine_node.id,
                "node_type": "fine",
                "page": fine_node.page,
                "modality": fine_node.modality,
                "text": fine_node.text,
                "bbox": bbox_to_dict(fine_node.bbox),
                "parent_id": fine_node.parent_id,
                "metadata": to_jsonable(dict(fine_node.metadata)),
            }
        )

    edges = [
        *[relation_to_dict(item) for item in pipeline.line_relations],
        *[relation_to_dict(item) for item in pipeline.chunk_relations],
        *[relation_to_dict(item) for item in pipeline.region_relations],
        *[relation_to_dict(item) for item in pipeline.hierarchical_relations],
    ]

    return {
        "document": {
            "image_path": str(pipeline.image_path),
            "ocr_path": str(pipeline.ocr_path),
        },
        "stats": {
            "num_words": len(pipeline.words),
            "num_lines": len(pipeline.lines),
            "num_paragraph_lines": len(pipeline.paragraph_lines),
            "num_region_lines": len(pipeline.region_lines),
            "num_chunks": len(pipeline.chunks),
            "num_regions": len(pipeline.regions),
            "num_fine_nodes": len(pipeline.fine_nodes),
            "num_edges": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }


def save_graph_payload(payload: dict[str, Any], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def load_graph_payload(graph_path: str | Path) -> dict[str, Any]:
    graph_path = Path(graph_path)
    return json.loads(graph_path.read_text(encoding="utf-8"))
