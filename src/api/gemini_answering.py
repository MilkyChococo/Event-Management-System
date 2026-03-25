from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from src.api.gemini_region_analysis import DEFAULT_GEMINI_MODEL, _load_gemini_backend, _resolve_api_key, _response_text
from src.api.qwen_vl_answering import _build_subgraph_bundles
from src.utils.prompt import get_qwen_subgraph_answer_prompt


@dataclass(slots=True)
class GeminiSubgraphAnswer:
    model: str
    answer: str
    raw_response_text: str
    raw_payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    candidates = [cleaned]
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidates.insert(0, cleaned[first : last + 1])

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def answer_subgraph_with_gemini(
    subgraph_payload: dict[str, Any],
    model: str = DEFAULT_GEMINI_MODEL,
    api_key: str | None = None,
    temperature: float = 0.1,
    max_output_tokens: int = 512,
    max_context_nodes: int = 20,
    max_images: int = 4,
) -> GeminiSubgraphAnswer:
    query = str(subgraph_payload.get("query", "")).strip()
    bundles = _build_subgraph_bundles(
        answer_payload=subgraph_payload,
        max_context_nodes=max_context_nodes,
        max_images=max_images,
    )
    prompt = get_qwen_subgraph_answer_prompt(
        query=query,
        num_subgraphs=len(bundles),
    )

    contents: list[Any] = [prompt]
    for bundle in bundles:
        seed_node = bundle.get("seed_node", {})
        seed_node_id = str(seed_node.get("node_id", "")).strip() or "[unknown]"
        image_ids = [item for item in bundle.get("image_ids", []) if item]
        header_lines = [
            f"Expanded subgraph rank: {bundle['rank']}",
            f"Subgraph id: {bundle['subgraph_id']}",
            f"Seed node: {seed_node_id}",
            f"Subgraph score: {bundle['subgraph_score']:.4f}",
            "Associated region image node ids: " + (", ".join(image_ids) if image_ids else "none"),
        ]
        contents.append("\n".join(header_lines))
        contents.extend(bundle.get("images", []))
        contents.append(f"Expanded subgraph context:\n{bundle['context_block']}")

    resolved_api_key = _resolve_api_key(api_key)
    backend_name, backend, types_module = _load_gemini_backend(resolved_api_key)
    if backend_name == "google.genai":
        config = None
        if types_module is not None:
            config = types_module.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        response = backend.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
    else:
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        gemini_model = backend.GenerativeModel(model_name=model)
        response = gemini_model.generate_content(
            contents,
            generation_config=generation_config,
        )

    raw_text = _response_text(response)
    payload = _extract_json_payload(raw_text)
    if payload:
        payload = {
            "answer": str(payload.get("answer", "")).strip(),
        }
        return GeminiSubgraphAnswer(
            model=model,
            answer=str(payload.get("answer", "")).strip(),
            raw_response_text=raw_text,
            raw_payload=payload,
        )

    return GeminiSubgraphAnswer(
        model=model,
        answer=raw_text.strip(),
        raw_response_text=raw_text,
        raw_payload={},
    )
