from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def resolve_payload_image_path(payload: dict[str, Any]) -> Path | None:
    document = payload.get("document")
    if not isinstance(document, dict):
        return None

    image_path = str(document.get("image_path", "")).strip()
    if not image_path:
        return None

    candidate = Path(image_path)
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def backfill_document_from_sibling_graph(
    payload: dict[str, Any],
    payload_path: str | Path,
    sibling_graph_name: str = "graph_enriched.json",
) -> dict[str, Any]:
    if resolve_payload_image_path(payload) is not None:
        return payload

    payload_path = Path(payload_path)
    sibling_graph = payload_path.parent / sibling_graph_name
    if not sibling_graph.exists():
        return payload

    graph_payload = json.loads(sibling_graph.read_text(encoding="utf-8"))
    if "document" in graph_payload:
        payload["document"] = graph_payload["document"]
    return payload
