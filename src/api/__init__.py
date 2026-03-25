"""API integration helpers."""

from .gemini_answering import GeminiSubgraphAnswer, answer_subgraph_with_gemini
from .gemini_region_analysis import (
    DEFAULT_GEMINI_MODEL,
    GeminiRegionAnalysis,
    annotate_detections_with_gemini,
    analyze_region_with_gemini,
)
from .qwen_vl_answering import QwenSubgraphAnswer, answer_subgraph_with_qwen
from .qwen_vl_region_analysis import (
    DEFAULT_QWEN_MODEL,
    DEFAULT_SUPPORTED_LABELS,
    QwenRegionAnalysis,
    analyze_region_with_qwen,
    annotate_detections_with_qwen,
    crop_detection_region,
)

__all__ = [
    "DEFAULT_GEMINI_MODEL",
    "DEFAULT_QWEN_MODEL",
    "DEFAULT_SUPPORTED_LABELS",
    "GeminiRegionAnalysis",
    "GeminiSubgraphAnswer",
    "QwenSubgraphAnswer",
    "QwenRegionAnalysis",
    "analyze_region_with_gemini",
    "analyze_region_with_qwen",
    "answer_subgraph_with_gemini",
    "answer_subgraph_with_qwen",
    "annotate_detections_with_gemini",
    "annotate_detections_with_qwen",
    "crop_detection_region",
]
