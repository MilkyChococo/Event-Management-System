from __future__ import annotations


QWEN_REGION_OUTPUT_SCHEMA = """
Return valid JSON only with this exact schema:
{
  "region_type": "string",
  "title_or_topic": "string",
  "summary": "string",
  "structured_content": "string",
  "key_points": ["string"],
  "visible_text": ["string"]
}
Do not wrap the JSON in markdown fences.
""".strip()


QWEN_OCR_GUIDANCE = """
OCR text is optional supporting context.
Use the image as the primary source of truth.
If OCR text conflicts with the visible image content, trust the image and correct the OCR implicitly.
Do not copy OCR text blindly when the image suggests it is wrong or incomplete.
""".strip()


QWEN_TABLE_ANALYSIS_PROMPT = """
You analyze a cropped table region from a document.

Your job:
1. Identify the table topic.
2. Read headers, row labels, and visible values.
3. Preserve the table structure as compactly as possible.
4. Summarize only the important facts supported by the image.

Focus on:
- table topic
- column headers
- row groups or row labels
- important numeric/text values
- partially cropped or unreadable cells

Rules:
- be factual and concise
- do not invent missing values
- if exact cell text is unreadable, say it is unclear
- if the crop contains exactly one table, analyze that table only
- if the crop contains multiple visible items, separate them item by item
- for each item, identify whether it is a table, chart, image, or other figure component
- summarize each item using the right rule for its type
- preserve structure in "structured_content" as either:
  - a compact markdown table, or
  - a key-value block, or
  - CSV-like rows
- group the per-item structured results clearly inside "structured_content"
- use the image as the primary source of truth; OCR text is only supporting context

{schema}
""".strip()


QWEN_CHART_ANALYSIS_PROMPT = """
You analyze a cropped chart, graph, or plot from a document.

Your job is to extract chart semantics useful for retrieval and question answering.

Analyze the chart in this order:
1. Identify the chart type as specifically as possible
   (e.g. line chart, grouped bar chart, stacked bar chart, area chart, scatter plot, pie chart, heatmap).
2. Identify the topic/title.
3. Read the x-axis:
   - axis label
   - category names or time range
   - ordering
4. Read the y-axis:
   - axis label
   - unit
   - visible scale/ticks/range
5. Read the legend:
   - series names
   - line style / marker / color
   - bar colors / stacked segments / shaded regions
6. Identify visual encodings:
   - what each color, pattern, line style, marker shape, stacked segment, or shaded region means
7. Extract data points:
   - if exact values are visible, record them
   - if exact values are not readable, give approximate values only when visually defensible
   - otherwise describe the trend without inventing values
8. Summarize the main findings.

Focus on:
- chart type
- chart topic
- x-axis meaning
- y-axis meaning and unit
- legend entries
- colored regions / stacked parts / line styles / markers
- important peaks, drops, comparisons, rankings, or changes over time
- values by year/month/category when visible

Rules:
- be factual and concise
- never invent exact numbers that are not visually readable
- if the chart is cropped or partial, say so
- if the crop contains exactly one chart, analyze that chart only
- if the crop contains multiple visible items, separate them item by item
- for each item, identify whether it is a chart, table, image, or other figure component
- summarize each item using the right rule for its type
- use "data_points" for exact or approximate extracted values
- use "main_findings" for trends and interpretations grounded in the chart
- use "structured_content" as a compact CSV-like table with columns:
  series, x, y, note
- group the per-item structured results clearly inside "structured_content"
- include major findings in "key_points"
- use the image as the primary source of truth; OCR text is only supporting context

{schema}
""".strip()


QWEN_FIGURE_IMAGE_ANALYSIS_PROMPT = """
You analyze a cropped figure or image region from a document.

This region may contain:
- a single image or diagram
- a single chart
- a single table
- multiple visible items mixed together, such as charts, tables, images, legends, or text blocks

Your task:
1. First decide whether the crop contains exactly one main item or multiple distinct visible items.
2. If there is exactly one main item:
   - analyze that item only
   - identify whether it is primarily an image, chart, table, or other figure component
3. If there are multiple distinct visible items:
   - separate them item by item
   - do not merge different items into one description
   - for each item, identify whether it is an image, chart, table, or other figure component
   - analyze each item using the appropriate rule for its type

Per-item analysis rules:
- For an image or non-chart figure item:
  - identify the main subject
  - identify notable visual elements
  - identify embedded labels, callouts, arrows, symbols, annotations, or visible text
  - describe concise semantic meaning useful for retrieval
  - store a compact structured note list for that item

- For a chart item:
  - identify chart type as specifically as possible
  - identify title/topic
  - identify x-axis label, categories or time range if visible
  - identify y-axis label, scale, and unit if visible
  - identify legend entries, line styles, marker shapes, stacked segments, color-coded regions, or shaded areas if visible
  - extract exact values only when readable
  - if exact values are unclear, summarize the visible trend without inventing values
  - store compact chart context for that item, such as:
    chart_type, x_axis, y_axis, legend, visual_encodings, extracted_values

- For a table item:
  - identify table topic
  - identify headers, row labels, and important visible values
  - do not invent unreadable cells
  - if the table is partial, say so briefly
  - store compact table context for that item as:
    a markdown table, CSV-like rows, or key-value structure

Rules:
- be factual and concise
- do not invent details that are not visible
- use the image as the primary source of truth; OCR text is only supporting context
- if OCR text conflicts with the visible image content, trust the image
- if exact values, labels, or boundaries are unclear, say so briefly
- put all per-item results clearly into "structured_content"
- if there are multiple items, make "structured_content" explicitly grouped item by item
- keep "summary" as the whole-region summary
- keep "key_points" for the most important findings across the visible item or items
- keep "visible_text" grounded only in text actually visible in the crop

{schema}
""".strip()


def get_qwen_region_prompt(label: str, ocr_text: str = "") -> str:
    norm = label.strip().lower().replace("_", " ").replace("-", " ")

    if "table" in norm or norm in {"bordered", "borderless"}:
        base_prompt = QWEN_TABLE_ANALYSIS_PROMPT
    elif any(token in norm for token in ("chart", "graph", "plot")):
        base_prompt = QWEN_CHART_ANALYSIS_PROMPT
    else:
        base_prompt = QWEN_FIGURE_IMAGE_ANALYSIS_PROMPT

    prompt = base_prompt.format(schema=QWEN_REGION_OUTPUT_SCHEMA)
    if ocr_text.strip():
        prompt = (
            f"{prompt}\n\n"
            f"{QWEN_OCR_GUIDANCE}\n\n"
            f"OCR text already detected inside this region:\n{ocr_text.strip()}"
        )
    return prompt


QWEN_SUBGRAPH_ANSWER_SCHEMA = """
Return valid JSON only with this exact schema:
{
  "answer": "string"
}
Do not wrap the JSON in markdown fences.
""".strip()


QWEN_SUBGRAPH_ANSWER_PROMPT = """
You answer a user question using one or more expanded document subgraphs.

You are given:
- a user question
- one or more expanded subgraphs
- text context from graph nodes inside each subgraph
- optionally one or more cropped images from region nodes for each subgraph

Core task:
Determine the answer by first aligning the user question with the visual evidence, then use subgraph structure and node text as supporting evidence, disambiguation, and citation support.

Evidence priority:
1. First, identify what the user is actually asking and which parts of the question require visual evidence.
2. Next, inspect the provided cropped images and extract the visual facts that are directly relevant to the question.
3. Then, use node text and subgraph context to support, refine, or disambiguate what was seen in the images.
4. Use graph structure and neighboring nodes as secondary support, not as the primary source when the image already provides direct evidence.
5. If text and image disagree, trust the image.
6. If no relevant image is provided or the image is not sufficient, answer from the text/subgraph evidence only.

How to reason:
- Start from the user question, not from the subgraph.
- Focus first on the query-image match:
  - what entities, attributes, values, labels, numbers, regions, or relations in the image answer the question
  - whether the image directly answers the question or only partially supports it
- After that, check whether the subgraph text:
  - confirms the visual reading
  - adds missing details
  - resolves ambiguity
  - provides stronger grounding for cited node ids
- Do not overuse peripheral subgraph text if it is not directly relevant to the question.
- Prefer the most local and query-relevant evidence over broad background context.
- If multiple subgraphs are provided, compare them and use the one(s) with the strongest direct evidence.
- If only one subgraph is provided, answer from that subgraph directly.

Grounding rules:
- answer only from the provided expanded subgraph context and cropped images
- do not use outside knowledge
- do not infer details that are not supported by the provided evidence
- answer with the best supported short answer span or phrase, even if the evidence is partial
- keep the answer concise, factual, and grounded
- in the "answer" field, return only the minimal answer span when possible
- do not repeat the question
- do not write full explanatory sentences when a short phrase, entity name, title, number, date, or value is sufficient
- do not add prefixes such as "The answer is", "It is", or quote the whole supporting sentence unless the question explicitly asks for a full sentence
- never place uncertainty statements, evidence commentary, or justification text inside the "answer" field
- phrases such as "The provided context does not mention...", "The image shows...", "It appears that...", or similar must not appear in "answer"
- if the evidence is weak or incomplete, still return the best supported short answer span instead of an explanation

Important:
- Images are primary evidence when relevant to the question.
- Subgraph text is supporting evidence unless the image is absent, irrelevant, or insufficient.
- If the image directly answers the question, do not let less relevant text override that answer.
- Example 1:
  - bad answer: "The 10th title in the Contents is Current Fund Revenues."
  - good answer: "Current Fund Revenues"
- Example 2:
  - bad answer: "The provided context does not mention a railways company. It mentions Vancouver Island Coach Lines Ltd."
  - good answer: "Vancouver Island Coach Lines Ltd."


{schema}
""".strip()


def get_qwen_subgraph_answer_prompt(
    query: str,
    num_subgraphs: int,
) -> str:
    return (
        f"{QWEN_SUBGRAPH_ANSWER_PROMPT.format(schema=QWEN_SUBGRAPH_ANSWER_SCHEMA)}\n\n"
        f"User question:\n{query.strip()}\n\n"
        f"Number of expanded subgraphs:\n{num_subgraphs}"
    )
