from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render graph.json into an interactive node-link HTML graph view."
    )
    parser.add_argument(
        "graph_json",
        type=Path,
        help="Path to graph.json produced by the export script.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output HTML path. Defaults to <graph_json_stem>_view.html.",
    )
    return parser.parse_args()


def build_graph_view_html(payload: dict[str, Any]) -> str:
    stats = payload.get("stats", {})
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    image_path = html.escape(str(payload.get("document", {}).get("image_path", "")))
    ocr_path = html.escape(str(payload.get("document", {}).get("ocr_path", "")))
    node_type_counts = Counter(str(node.get("node_type", "unknown")) for node in nodes)
    relation_counts = Counter(str(edge.get("relation", "unknown")) for edge in edges)
    data_json = json.dumps(payload, ensure_ascii=False)

    stats_cards = "\n".join(
        f"""
        <div class="stat">
          <div class="stat-label">{html.escape(str(key))}</div>
          <div class="stat-value">{html.escape(str(value))}</div>
        </div>
        """.strip()
        for key, value in stats.items()
    )

    node_type_checks = "\n".join(
        f"""
        <label class="check">
          <input type="checkbox" class="node-type-filter" value="{html.escape(node_type)}" checked>
          <span>{html.escape(node_type)} ({count})</span>
        </label>
        """.strip()
        for node_type, count in sorted(node_type_counts.items())
    )

    relation_checks = "\n".join(
        f"""
        <label class="check">
          <input type="checkbox" class="edge-type-filter" value="{html.escape(relation)}" checked>
          <span>{html.escape(relation)} ({count})</span>
        </label>
        """.strip()
        for relation, count in sorted(relation_counts.items())
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Graph View</title>
  <style>
    :root {{
      --bg: #f5efe4;
      --panel: #fffdf8;
      --line: #d8cfbf;
      --ink: #201c18;
      --muted: #6f675e;
      --accent: #005f73;
      --accent-2: #bb3e03;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: "Segoe UI", system-ui, sans-serif;
      background:
        radial-gradient(circle at top left, #fff8dc 0, transparent 24%),
        linear-gradient(145deg, #f5efe4 0%, #ece2d4 100%);
    }}
    .wrap {{
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 18px;
      padding: 20px;
      min-height: 100vh;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(0,0,0,0.06);
    }}
    h1, h2, h3 {{
      margin: 0 0 12px;
    }}
    .muted {{
      color: var(--muted);
    }}
    .path {{
      font-family: Consolas, monospace;
      font-size: 12px;
      overflow-wrap: anywhere;
      margin-bottom: 8px;
    }}
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin: 14px 0 18px;
    }}
    .stat {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
    }}
    .stat-label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .04em;
      color: var(--muted);
    }}
    .stat-value {{
      font-size: 22px;
      font-weight: 700;
      color: var(--accent);
      margin-top: 4px;
    }}
    .section {{
      margin-top: 18px;
    }}
    .check-list {{
      display: grid;
      gap: 8px;
      max-height: 220px;
      overflow: auto;
      padding-right: 4px;
    }}
    .check {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }}
    .search {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
    }}
    .legend {{
      display: grid;
      gap: 8px;
      font-size: 13px;
    }}
    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .swatch {{
      width: 14px;
      height: 14px;
      border-radius: 4px;
      display: inline-block;
      border: 1px solid rgba(0,0,0,0.12);
    }}
    .viewer {{
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 14px;
    }}
    .toolbar {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .btn {{
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #fff;
      cursor: pointer;
    }}
    .canvas-wrap {{
      overflow: auto;
      border-radius: 18px;
      border: 1px solid var(--line);
      background:
        linear-gradient(0deg, rgba(255,255,255,.72), rgba(255,255,255,.72)),
        linear-gradient(90deg, #f6efe1 1px, transparent 1px),
        linear-gradient(#f6efe1 1px, transparent 1px);
      background-size: auto, 28px 28px, 28px 28px;
    }}
    svg {{
      display: block;
      min-width: 100%;
    }}
    .node {{
      cursor: pointer;
    }}
    .node text {{
      font-size: 11px;
      pointer-events: none;
    }}
    .edge {{
      opacity: .42;
    }}
    .edge.highlight {{
      opacity: .95;
      stroke-width: 3;
    }}
    .node.dim {{
      opacity: .22;
    }}
    .edge.dim {{
      opacity: .06;
    }}
    .detail {{
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px;
      min-height: 180px;
    }}
    @media (max-width: 1100px) {{
      .wrap {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <aside class="panel">
      <h1>Graph View</h1>
      <div class="muted">Image</div>
      <div class="path">{image_path}</div>
      <div class="muted">OCR</div>
      <div class="path">{ocr_path}</div>

      <div class="stats">{stats_cards}</div>

      <div class="section">
        <h2>Node Types</h2>
        <div class="check-list">{node_type_checks}</div>
      </div>

      <div class="section">
        <h2>Relations</h2>
        <div class="check-list">{relation_checks}</div>
      </div>

      <div class="section">
        <h2>Search</h2>
        <input id="searchInput" class="search" type="text" placeholder="Search node id or text">
      </div>

      <div class="section">
        <h2>Legend</h2>
        <div class="legend">
          <div class="legend-row"><span class="swatch" style="background:#2a9d8f"></span> line</div>
          <div class="legend-row"><span class="swatch" style="background:#f4a261"></span> chunk</div>
          <div class="legend-row"><span class="swatch" style="background:#52b788"></span> region</div>
          <div class="legend-row"><span class="swatch" style="background:#4ea8de"></span> fine</div>
        </div>
      </div>

      <div class="section">
        <h2>Selected Node</h2>
        <div id="nodeDetail" class="detail">Click a node to inspect its content and metadata.</div>
      </div>
    </aside>

    <main class="viewer">
      <section class="panel toolbar">
        <button id="resetBtn" class="btn">Reset Highlight</button>
        <span class="muted">Layout is column-based: line -> chunk -> region -> fine</span>
      </section>
      <section class="canvas-wrap panel">
        <svg id="graphSvg"></svg>
      </section>
    </main>
  </div>

  <script>
    const payload = {data_json};
    const nodes = payload.nodes || [];
    const edges = payload.edges || [];

    const NODE_COLORS = {{
      line: '#2a9d8f',
      chunk: '#f4a261',
      region: '#52b788',
      fine: '#4ea8de',
      unknown: '#8d99ae',
    }};

    const EDGE_COLORS = {{
      next_line: '#84cc16',
      line_to_chunk: '#d946ef',
      chunk_to_line: '#38bdf8',
      next_chunk: '#f59e0b',
      line_to_region: '#c026d3',
      region_to_line: '#8b5cf6',
      chunk_to_region: '#ef4444',
      region_to_chunk: '#fb7185',
      chunk_to_region_lexical: '#8b5cf6',
      region_to_chunk_lexical: '#a855f7',
      next_region: '#22c55e',
      coarse_to_fine: '#eab308',
      fine_to_coarse: '#ca8a04',
    }};

    const COLUMN_X = {{
      line: 140,
      chunk: 430,
      region: 720,
      fine: 1010,
      unknown: 1180,
    }};

    const searchInput = document.getElementById('searchInput');
    const resetBtn = document.getElementById('resetBtn');
    const graphSvg = document.getElementById('graphSvg');
    const nodeDetail = document.getElementById('nodeDetail');
    const nodeTypeChecks = [...document.querySelectorAll('.node-type-filter')];
    const edgeTypeChecks = [...document.querySelectorAll('.edge-type-filter')];

    let selectedNodeId = null;

    function escapeHtml(value) {{
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }}

    function activeValues(checks) {{
      return new Set(checks.filter((item) => item.checked).map((item) => item.value));
    }}

    function sortNodes(items) {{
      return [...items].sort((a, b) => {{
        const pageA = Number(a.page ?? 0);
        const pageB = Number(b.page ?? 0);
        if (pageA !== pageB) return pageA - pageB;
        const topA = Number(a.bbox?.top ?? 0);
        const topB = Number(b.bbox?.top ?? 0);
        if (topA !== topB) return topA - topB;
        const leftA = Number(a.bbox?.left ?? 0);
        const leftB = Number(b.bbox?.left ?? 0);
        if (leftA !== leftB) return leftA - leftB;
        return String(a.id).localeCompare(String(b.id));
      }});
    }}

    function prettyNode(node) {{
      return JSON.stringify(node, null, 2);
    }}

    function buildLayout(filteredNodes) {{
      const grouped = {{
        line: [],
        chunk: [],
        region: [],
        fine: [],
        unknown: [],
      }};
      for (const node of sortNodes(filteredNodes)) {{
        const key = grouped[node.node_type] ? node.node_type : 'unknown';
        grouped[key].push(node);
      }}

      const positions = new Map();
      const counts = Object.values(grouped).map((items) => items.length);
      const maxCount = Math.max(1, ...counts);
      const svgHeight = Math.max(960, 120 + maxCount * 60);
      const svgWidth = 1280;

      for (const [type, items] of Object.entries(grouped)) {{
        items.forEach((node, index) => {{
          const x = COLUMN_X[type] ?? COLUMN_X.unknown;
          const y = 90 + index * 60;
          positions.set(node.id, {{ x, y }});
        }});
      }}

      return {{ positions, svgWidth, svgHeight }};
    }}

    function render() {{
      const query = searchInput.value.trim().toLowerCase();
      const activeNodeTypes = activeValues(nodeTypeChecks);
      const activeEdgeTypes = activeValues(edgeTypeChecks);

      const filteredNodes = nodes.filter((node) => {{
        const typeOk = activeNodeTypes.has(node.node_type);
        const hay = JSON.stringify([node.id, node.text, node.metadata]).toLowerCase();
        const queryOk = !query || hay.includes(query);
        return typeOk && queryOk;
      }});

      const visibleNodeIds = new Set(filteredNodes.map((node) => node.id));
      const filteredEdges = edges.filter((edge) => {{
        return activeEdgeTypes.has(edge.relation)
          && visibleNodeIds.has(edge.source_id)
          && visibleNodeIds.has(edge.target_id);
      }});

      const adjacency = new Map();
      for (const edge of filteredEdges) {{
        if (!adjacency.has(edge.source_id)) adjacency.set(edge.source_id, new Set());
        if (!adjacency.has(edge.target_id)) adjacency.set(edge.target_id, new Set());
        adjacency.get(edge.source_id).add(edge.target_id);
        adjacency.get(edge.target_id).add(edge.source_id);
      }}

      const {{ positions, svgWidth, svgHeight }} = buildLayout(filteredNodes);
      const connectedToSelected = new Set();
      if (selectedNodeId && adjacency.has(selectedNodeId)) {{
        connectedToSelected.add(selectedNodeId);
        for (const item of adjacency.get(selectedNodeId)) connectedToSelected.add(item);
      }}

      const defs = `
        <defs>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto">
            <path d="M0,0 L10,5 L0,10 z" fill="#8b8b8b"></path>
          </marker>
        </defs>
      `;

      const edgeMarkup = filteredEdges.map((edge) => {{
        const source = positions.get(edge.source_id);
        const target = positions.get(edge.target_id);
        if (!source || !target) return '';
        const color = EDGE_COLORS[edge.relation] || '#9ca3af';
        const isHighlighted = selectedNodeId && (
          edge.source_id === selectedNodeId ||
          edge.target_id === selectedNodeId
        );
        return `
          <line
            class="edge ${{isHighlighted ? 'highlight' : ''}} ${{selectedNodeId && !isHighlighted ? 'dim' : ''}}"
            x1="${{source.x}}"
            y1="${{source.y}}"
            x2="${{target.x}}"
            y2="${{target.y}}"
            stroke="${{color}}"
            stroke-width="${{isHighlighted ? 3 : 1.4}}"
            marker-end="url(#arrow)">
            <title>${{escapeHtml(`${{edge.source_id}} -> ${{edge.target_id}} [${{edge.relation}}] score=${{Number(edge.score ?? 1).toFixed(4)}}`)}}</title>
          </line>
        `;
      }}).join('');

      const nodeMarkup = filteredNodes.map((node) => {{
        const pos = positions.get(node.id);
        const color = NODE_COLORS[node.node_type] || NODE_COLORS.unknown;
        const isSelected = selectedNodeId === node.id;
        const isConnected = !selectedNodeId || connectedToSelected.has(node.id);
        const displayText = String(node.id).slice(0, 26);
        const x = pos.x - 52;
        const y = pos.y - 17;
        return `
          <g class="node ${{isSelected ? 'selected' : ''}} ${{!isConnected ? 'dim' : ''}}" data-node-id="${{escapeHtml(node.id)}}" transform="translate(${{x}},${{y}})">
            <rect x="0" y="0" rx="11" ry="11" width="104" height="34" fill="${{color}}" stroke="${{isSelected ? '#111827' : 'rgba(0,0,0,0.12)'}}" stroke-width="${{isSelected ? 3 : 1}}"></rect>
            <text x="52" y="21" fill="#ffffff" text-anchor="middle">${{escapeHtml(displayText)}}</text>
            <title>${{escapeHtml(node.id)}}</title>
          </g>
        `;
      }}).join('');

      const columnGuides = Object.entries(COLUMN_X).map(([type, x]) => `
        <g>
          <text x="${{x}}" y="38" text-anchor="middle" fill="#6f675e" font-size="13" font-weight="700">${{type}}</text>
          <line x1="${{x}}" y1="52" x2="${{x}}" y2="${{svgHeight - 24}}" stroke="#e5dccd" stroke-width="1" stroke-dasharray="4 6"></line>
        </g>
      `).join('');

      graphSvg.setAttribute('viewBox', `0 0 ${{svgWidth}} ${{svgHeight}}`);
      graphSvg.setAttribute('width', String(svgWidth));
      graphSvg.setAttribute('height', String(svgHeight));
      graphSvg.innerHTML = defs + columnGuides + edgeMarkup + nodeMarkup;

      for (const element of graphSvg.querySelectorAll('[data-node-id]')) {{
        element.addEventListener('click', () => {{
          selectedNodeId = element.getAttribute('data-node-id');
          const node = nodes.find((item) => item.id === selectedNodeId);
          nodeDetail.textContent = node ? prettyNode(node) : 'Node not found.';
          render();
        }});
      }}
    }}

    for (const item of nodeTypeChecks) item.addEventListener('change', render);
    for (const item of edgeTypeChecks) item.addEventListener('change', render);
    searchInput.addEventListener('input', render);
    resetBtn.addEventListener('click', () => {{
      selectedNodeId = null;
      nodeDetail.textContent = 'Click a node to inspect its content and metadata.';
      render();
    }});

    render();
  </script>
</body>
</html>
"""


def main() -> None:
    args = parse_args()
    graph_json_path = args.graph_json.resolve()
    payload = json.loads(graph_json_path.read_text(encoding="utf-8"))

    if args.output is not None:
      output_path = args.output
      if not output_path.is_absolute():
          output_path = (Path.cwd() / output_path).resolve()
    else:
      output_path = graph_json_path.with_name(f"{graph_json_path.stem}_view.html")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_graph_view_html(payload), encoding="utf-8")
    print(f"Saved graph view HTML to: {output_path}")


if __name__ == "__main__":
    main()
