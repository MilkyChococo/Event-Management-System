from __future__ import annotations

import argparse
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render an exported graph JSON file into a browsable HTML report."
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
        help="Optional output HTML path. Defaults to <graph_json_stem>.html next to the JSON file.",
    )
    return parser.parse_args()


def build_html_report(payload: dict[str, Any]) -> str:
    stats = payload.get("stats", {})
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    node_type_counts = Counter(str(node.get("node_type", "unknown")) for node in nodes)
    relation_counts = Counter(str(edge.get("relation", "unknown")) for edge in edges)

    stats_cards = "\n".join(
        f"""
        <div class="card">
          <div class="label">{html.escape(str(key))}</div>
          <div class="value">{html.escape(str(value))}</div>
        </div>
        """.strip()
        for key, value in stats.items()
    )

    node_type_rows = "\n".join(
        f"<tr><td>{html.escape(node_type)}</td><td>{count}</td></tr>"
        for node_type, count in sorted(node_type_counts.items())
    )
    relation_rows = "\n".join(
        f"<tr><td>{html.escape(relation)}</td><td>{count}</td></tr>"
        for relation, count in sorted(relation_counts.items())
    )

    data_json = json.dumps(payload, ensure_ascii=False)
    image_path = html.escape(str(payload.get("document", {}).get("image_path", "")))
    ocr_path = html.escape(str(payload.get("document", {}).get("ocr_path", "")))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Graph Report</title>
  <style>
    :root {{
      --bg: #f7f4eb;
      --panel: #fffdf7;
      --ink: #1f1d1a;
      --muted: #6d655d;
      --line: #d7cfc0;
      --accent: #005f73;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", system-ui, sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #fff6d7 0, transparent 26%),
        linear-gradient(135deg, #f7f4eb 0%, #efe6d7 100%);
    }}
    .wrap {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px 24px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.06);
      margin-bottom: 18px;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    .muted {{ color: var(--muted); }}
    .path {{
      font-family: Consolas, monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .card {{
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
    }}
    .label {{
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: .04em;
    }}
    .value {{
      margin-top: 6px;
      font-size: 24px;
      font-weight: 700;
      color: var(--accent);
    }}
    .grid {{
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 18px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 8px 20px rgba(0,0,0,0.05);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      position: sticky;
      top: 0;
      background: var(--panel);
    }}
    .controls {{
      display: flex;
      gap: 10px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }}
    input, select {{
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 10px 12px;
      background: #fff;
      color: var(--ink);
    }}
    .scroll {{
      max-height: 70vh;
      overflow: auto;
    }}
    .pill {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 999px;
      background: #e9f3f5;
      color: var(--accent);
      font-size: 12px;
      font-weight: 600;
    }}
    .text {{
      max-width: 520px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
    .meta {{
      max-width: 380px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-family: Consolas, monospace;
      font-size: 12px;
    }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Document Graph Report</h1>
      <div class="muted">Image</div>
      <div class="path">{image_path}</div>
      <div class="muted" style="margin-top:10px;">OCR</div>
      <div class="path">{ocr_path}</div>
      <div class="cards">{stats_cards}</div>
    </section>

    <section class="grid">
      <div class="panel">
        <h2>Node Types</h2>
        <table>
          <thead><tr><th>Type</th><th>Count</th></tr></thead>
          <tbody>{node_type_rows}</tbody>
        </table>
        <h2 style="margin-top:18px;">Relations</h2>
        <table>
          <thead><tr><th>Relation</th><th>Count</th></tr></thead>
          <tbody>{relation_rows}</tbody>
        </table>
      </div>

      <div class="panel">
        <div class="controls">
          <input id="nodeSearch" type="text" placeholder="Search node text or id">
          <select id="nodeTypeFilter">
            <option value="">All node types</option>
          </select>
        </div>
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Page</th>
                <th>Text</th>
                <th>Metadata</th>
              </tr>
            </thead>
            <tbody id="nodesTable"></tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel" style="margin-top:18px;">
      <div class="controls">
        <input id="edgeSearch" type="text" placeholder="Search source / target / relation">
        <select id="edgeTypeFilter">
          <option value="">All relations</option>
        </select>
      </div>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Target</th>
              <th>Relation</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody id="edgesTable"></tbody>
        </table>
      </div>
    </section>
  </div>

  <script>
    const payload = {data_json};
    const nodes = payload.nodes || [];
    const edges = payload.edges || [];

    const nodeSearch = document.getElementById('nodeSearch');
    const nodeTypeFilter = document.getElementById('nodeTypeFilter');
    const edgeSearch = document.getElementById('edgeSearch');
    const edgeTypeFilter = document.getElementById('edgeTypeFilter');
    const nodesTable = document.getElementById('nodesTable');
    const edgesTable = document.getElementById('edgesTable');

    function uniqueSorted(values) {{
      return [...new Set(values)].filter(Boolean).sort();
    }}

    function populateSelect(select, values) {{
      for (const value of uniqueSorted(values)) {{
        const option = document.createElement('option');
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
      }}
    }}

    function escapeHtml(value) {{
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;');
    }}

    function renderNodes() {{
      const query = nodeSearch.value.trim().toLowerCase();
      const type = nodeTypeFilter.value;
      const filtered = nodes.filter((node) => {{
        const hay = JSON.stringify([node.id, node.node_type, node.text, node.metadata]).toLowerCase();
        return (!type || node.node_type === type) && (!query || hay.includes(query));
      }});

      nodesTable.innerHTML = filtered.map((node) => `
        <tr>
          <td><span class="pill">${{escapeHtml(node.id)}}</span></td>
          <td>${{escapeHtml(node.node_type)}}</td>
          <td>${{escapeHtml(node.page ?? '')}}</td>
          <td><div class="text">${{escapeHtml(node.text ?? '')}}</div></td>
          <td><div class="meta">${{escapeHtml(JSON.stringify(node.metadata ?? {{}}, null, 2))}}</div></td>
        </tr>
      `).join('');
    }}

    function renderEdges() {{
      const query = edgeSearch.value.trim().toLowerCase();
      const relation = edgeTypeFilter.value;
      const filtered = edges.filter((edge) => {{
        const hay = JSON.stringify([edge.source_id, edge.target_id, edge.relation]).toLowerCase();
        return (!relation || edge.relation === relation) && (!query || hay.includes(query));
      }});

      edgesTable.innerHTML = filtered.map((edge) => `
        <tr>
          <td>${{escapeHtml(edge.source_id)}}</td>
          <td>${{escapeHtml(edge.target_id)}}</td>
          <td>${{escapeHtml(edge.relation)}}</td>
          <td>${{Number(edge.score ?? 1).toFixed(4)}}</td>
        </tr>
      `).join('');
    }}

    populateSelect(nodeTypeFilter, nodes.map((node) => node.node_type));
    populateSelect(edgeTypeFilter, edges.map((edge) => edge.relation));

    nodeSearch.addEventListener('input', renderNodes);
    nodeTypeFilter.addEventListener('change', renderNodes);
    edgeSearch.addEventListener('input', renderEdges);
    edgeTypeFilter.addEventListener('change', renderEdges);

    renderNodes();
    renderEdges();
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
        output_path = graph_json_path.with_suffix(".html")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_html_report(payload), encoding="utf-8")
    print(f"Saved graph HTML to: {output_path}")


if __name__ == "__main__":
    main()
