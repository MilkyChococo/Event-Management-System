from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from src.api.qwen_vl_region_analysis import DEFAULT_QWEN_MODEL, _load_model_and_processor, _torch
from src.utils.fallback import resolve_payload_image_path
from src.utils.prompt import get_qwen_subgraph_answer_prompt


@dataclass(slots=True)
class QwenSubgraphAnswer:
    model: str
    answer: str
    raw_response_text: str
    raw_payload: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


def _iter_expanded_subgraphs(answer_payload: dict[str, Any]) -> list[dict[str, Any]]:
    subgraphs = answer_payload.get("subgraphs")
    if isinstance(subgraphs, list) and subgraphs:
        return subgraphs

    if answer_payload.get("nodes") or answer_payload.get("edges"):
        return [
            {
                "subgraph_id": str(answer_payload.get("subgraph_id", "subgraph_001")),
                "rank": 1,
                "seed_node": {},
                "subgraph_score": 0.0,
                "stats": dict(answer_payload.get("stats", {})),
                "nodes": list(answer_payload.get("nodes", [])),
                "edges": list(answer_payload.get("edges", [])),
                "expansion_trace": list(answer_payload.get("expansion_trace", [])),
            }
        ]
    return []


def crop_subgraph_region_images(
    answer_payload: dict[str, Any],
    subgraph_payload: dict[str, Any],
    max_images: int = 4,
) -> list[tuple[str, Image.Image]]:
    image_path = resolve_payload_image_path(answer_payload)
    if image_path is None:
        return []

    page_image = Image.open(image_path).convert("RGB")
    width, height = page_image.size

    region_nodes = [
        node
        for node in subgraph_payload.get("nodes", [])
        if str(node.get("node_type", "")).strip().lower() == "region"
    ]
    region_nodes.sort(key=lambda item: float(item.get("rel", 0.0)), reverse=True)

    crops: list[tuple[str, Image.Image]] = []
    for node in region_nodes[:max_images]:
        bbox = node.get("bbox", {})
        x1 = int(float(bbox.get("left", 0.0)))
        y1 = int(float(bbox.get("top", 0.0)))
        x2 = int(float(bbox.get("right", 0.0)))
        y2 = int(float(bbox.get("bottom", 0.0)))

        x1 = max(0, min(width - 1, x1))
        y1 = max(0, min(height - 1, y1))
        x2 = max(0, min(width, x2))
        y2 = max(0, min(height, y2))
        if x2 <= x1 or y2 <= y1:
            continue

        crops.append((str(node.get("id", "")), page_image.crop((x1, y1, x2, y2))))
    return crops


def build_subgraph_context_block(
    subgraph_payload: dict[str, Any],
    max_nodes: int = 20,
) -> str:
    nodes = sorted(
        subgraph_payload.get("nodes", []),
        key=lambda item: float(item.get("final_score", item.get("rel", 0.0))),
        reverse=True,
    )[:max_nodes]

    blocks: list[str] = []
    for node in nodes:
        node_id = str(node.get("id", ""))
        node_type = str(node.get("node_type", ""))
        rel = float(node.get("rel", 0.0))
        final_score = float(node.get("final_score", rel))
        label = str(node.get("label", "") or node.get("modality", "")).strip()
        text = str(node.get("text", "")).strip()

        header = f"[{node_id}] type={node_type} rel={rel:.4f} final={final_score:.4f}"
        if label:
            header += f" label={label}"
        blocks.append(f"{header}\n{text}".strip())
    return "\n\n".join(blocks)


def _build_subgraph_bundles(
    answer_payload: dict[str, Any],
    max_context_nodes: int = 20,
    max_images: int = 4,
) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    for subgraph in _iter_expanded_subgraphs(answer_payload):
        context_block = build_subgraph_context_block(
            subgraph_payload=subgraph,
            max_nodes=max_context_nodes,
        )
        image_pairs = crop_subgraph_region_images(
            answer_payload=answer_payload,
            subgraph_payload=subgraph,
            max_images=max_images,
        )
        bundles.append(
            {
                "subgraph_id": str(subgraph.get("subgraph_id", "")),
                "rank": int(subgraph.get("rank", len(bundles) + 1)),
                "seed_node": dict(subgraph.get("seed_node", {})),
                "subgraph_score": float(subgraph.get("subgraph_score", 0.0) or 0.0),
                "context_block": context_block,
                "image_ids": [node_id for node_id, _ in image_pairs],
                "images": [image for _, image in image_pairs],
            }
        )
    return bundles


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


def _build_model_inputs(
    processor: Any,
    prompt: str,
    bundles: list[dict[str, Any]],
) -> dict[str, Any]:
    content: list[dict[str, str]] = [{"type": "text", "text": prompt}]
    ordered_images: list[Image.Image] = []

    for bundle in bundles:
        seed_node = bundle.get("seed_node", {})
        seed_node_id = str(seed_node.get("node_id", "")).strip()
        image_ids = [item for item in bundle.get("image_ids", []) if item]
        header_lines = [
            f"Expanded subgraph rank: {bundle['rank']}",
            f"Subgraph id: {bundle['subgraph_id']}",
            f"Seed node: {seed_node_id or '[unknown]'}",
            f"Subgraph score: {bundle['subgraph_score']:.4f}",
        ]
        if image_ids:
            header_lines.append("Associated region image node ids: " + ", ".join(image_ids))
        else:
            header_lines.append("Associated region image node ids: none")
        content.append({"type": "text", "text": "\n".join(header_lines)})

        for image in bundle["images"]:
            ordered_images.append(image)
            content.append({"type": "image"})

        content.append(
            {
                "type": "text",
                "text": f"Expanded subgraph context:\n{bundle['context_block']}".strip(),
            }
        )

    messages = [{"role": "user", "content": content}]
    chat_text = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    if ordered_images:
        return processor(
            text=[chat_text],
            images=ordered_images,
            padding=True,
            return_tensors="pt",
        )
    return processor(
        text=[chat_text],
        padding=True,
        return_tensors="pt",
    )


def answer_subgraph_with_qwen(
    subgraph_payload: dict[str, Any],
    model: str = DEFAULT_QWEN_MODEL,
    device: str = "auto",
    dtype: str = "auto",
    max_new_tokens: int = 512,
    temperature: float = 0.1,
    max_context_nodes: int = 20,
    max_images: int = 4,
) -> QwenSubgraphAnswer:
    torch = _torch()
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

    processor, qwen_model, resolved_device = _load_model_and_processor(
        model_id=model,
        device=device,
        dtype=dtype,
    )
    inputs = _build_model_inputs(
        processor=processor,
        prompt=prompt,
        bundles=bundles,
    )
    inputs = {
        key: value.to(resolved_device) if hasattr(value, "to") else value
        for key, value in inputs.items()
    }

    do_sample = temperature > 0.0
    generate_kwargs: dict[str, Any] = {
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
    }
    if do_sample:
        generate_kwargs["temperature"] = temperature

    with torch.inference_mode():
        generated_ids = qwen_model.generate(**inputs, **generate_kwargs)

    prompt_length = int(inputs["input_ids"].shape[1])
    generated_trimmed = generated_ids[:, prompt_length:]
    raw_text = processor.batch_decode(
        generated_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )[0].strip()

    payload = _extract_json_payload(raw_text)
    if not payload:
        payload = {
            "answer": raw_text.strip(),
        }
    else:
        payload = {
            "answer": str(payload.get("answer", "")).strip(),
        }

    return QwenSubgraphAnswer(
        model=model,
        answer=str(payload.get("answer", "")).strip(),
        raw_response_text=raw_text,
        raw_payload=payload,
    )
