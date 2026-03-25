from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.algo import enrich_graph_for_cse, load_embedding_store, save_enriched_graph
from src.utils.io import resolve_existing_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the basic offline CSE index from graph.json and node embeddings."
    )
    parser.add_argument(
        "store_dir",
        type=Path,
        help="Directory containing graph.json, embeddings.npy, and embedding_meta.json.",
    )
    parser.add_argument(
        "--lambda-hub",
        type=float,
        default=0.1,
        help="Hub-penalty lambda stored in the enriched graph.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional enriched graph output path. Defaults to <store_dir>/graph_enriched.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    store_dir = resolve_existing_dir(args.store_dir, base_dir=PROJECT_ROOT)

    graph_path = store_dir / "graph.json"
    embeddings_path = store_dir / "embeddings.npy"
    meta_path = store_dir / "embedding_meta.json"

    if not graph_path.exists():
        raise FileNotFoundError(f"Missing graph file: {graph_path}")
    if not embeddings_path.exists():
        raise FileNotFoundError(f"Missing embeddings file: {embeddings_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing embedding metadata file: {meta_path}")

    store = load_embedding_store(
        graph_path=graph_path,
        embeddings_path=embeddings_path,
        meta_path=meta_path,
    )
    enriched_graph = enrich_graph_for_cse(
        graph=store.graph,
        embeddings=store.embeddings,
        node_to_row=store.node_to_row,
        lambda_hub=args.lambda_hub,
    )

    if args.output is not None:
        output_path = args.output
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
    else:
        output_path = store_dir / "graph_enriched.json"

    saved_path = save_enriched_graph(enriched_graph, output_path)
    print(f"Nodes: {len(enriched_graph.get('nodes', []))}")
    print(f"Edges: {len(enriched_graph.get('edges', []))}")
    print(f"Saved enriched graph to: {saved_path}")


if __name__ == "__main__":
    main()
