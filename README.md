# VQA KLTN

Pipeline DocVQA theo hướng:
- OCR `word -> line -> chunk`
- layout detection `table / figure / chart / image`
- region analysis bằng `Qwen2.5-VL`
- node embedding bằng `Qwen3-VL-Embedding`
- Controlled Subgraph Expansion (CSE)
- final answer bằng `Qwen2.5-VL`

## Cấu trúc chính

```text
scripts/
  run_offline_index.py   # build graph + embeddings + enriched graph
  run_cse_qa.py          # query -> CSE -> answer

src/
  extract/               # OCR, layout, graph construction
  api/                   # Qwen region analysis + final QA
  database/              # graph store + node embedding
  algo/                  # offline CSE indexing + online CSE
  utils/                 # prompt, io, fallback
```

## Workflow hiện tại

### 1. Offline indexing

Input:
- document image
- OCR JSON

Các bước:
1. OCR words -> lines
2. lines -> chunks
3. build text/region graph
4. detect layout bằng DocLayout-YOLO
5. phân tích region bằng `Qwen/Qwen2.5-VL-3B-Instruct`
6. save `graph.json`
7. embed node context bằng `Qwen/Qwen3-VL-Embedding-2B`
8. save `embeddings.npy` + `embedding_meta.json`
9. tính `deg`, `hub`, `conf_off`
10. save `graph_enriched.json`

### 2. Online QA

Input:
- indexed document store
- query

Các bước:
1. embed query
2. tính `rel(v|Q)` với toàn bộ node
3. chọn top-k seed nodes
4. chạy CSE trên `graph_enriched.json`
5. lấy top k expanded subgraph liên quan
6. nếu subgraph có region node thì crop region image
7. đưa subgraph + image crops vào `Qwen2.5-VL`
8. trả lời

## Chạy offline indexing

Ví dụ:

```bash
python scripts/run_offline_index.py dataset/spdocvqa/spdocvqa_images/fggh0224_12.png --detect-layout --analyze-regions-with-qwen --embed-device cpu --embed-dtype float32
```

Nếu muốn chạy nhẹ hơn để debug:

```bash
python scripts/run_offline_index.py dataset/spdocvqa/spdocvqa_images/fggh0224_12.png --detect-layout --analyze-regions-with-qwen --embed-device cpu --embed-dtype float32 --embed-node-types chunk,region --embed-batch-size 2
```

Output mặc định:

```text
artifacts/node_stores/<image_stem>/
  graph.json
  embeddings.npy
  embedding_meta.json
  graph_enriched.json
```

Lưu ý:
- `graph.json` được save sớm ngay sau khi build graph.
- `embeddings.npy`, `embedding_meta.json`, `graph_enriched.json` chỉ xuất hiện sau khi embedding chạy xong.

## Chạy online CSE + QA

Ví dụ:

```bash
python scripts/run_cse_qa.py artifacts/node_stores/fggh0224_12 "what is the effective date?" --embed-device cpu --embed-dtype float32 --answer-device cpu --answer-dtype float32
```

Script này sẽ:
- load `graph_enriched.json`
- embed query
- chạy CSE
- gọi `Qwen2.5-VL` để answer

## Các file dữ liệu chính

### `graph.json`

Chứa:
- `document`
- `stats`
- `nodes`
- `edges`

Node hiện có thể là:
- `line`
- `chunk`
- `region`
- `fine`

### `embedding_meta.json`

Map giữa dòng trong `embeddings.npy` và node:

```json
{
  "row": 12,
  "node_id": "p1_chunk_003",
  "node_type": "chunk",
  "page": 1,
  "context_text": "..."
}
```

### `graph_enriched.json`

Là graph dùng cho CSE, có thêm:
- `embedding_row`
- `deg_in`
- `deg_out`
- `deg`
- `hub`
- `neighbors`
- `conf_off` trên edge

## Công thức CSE đang dùng

Offline:

```text
conf_off(u, v) = (1 + cos(e(u), e(v))) / 2
hub(v) = log(1 + deg(v))
```

Online:

```text
rel(v | Q) = (1 + cos(q, e(v))) / 2
score(u, v) = alpha * conf_off(u, v) + rel(v | Q) - lambda * hub(v)
```

Baseline hiện tại:
- `alpha = 0.5`
- `lambda = 0.1`

## Models đang dùng

- Layout detection:
  - `anyformat/doclayout-yolo-docstructbench`
- Region analysis / final answer:
  - `Qwen/Qwen2.5-VL-3B-Instruct`
- Node embedding:
  - `Qwen/Qwen3-VL-Embedding-2B`

## Lưu ý vận hành

- Chạy CPU sẽ chậm, nhất là phần Qwen.
- Nếu offline index dừng giữa chừng thì có thể chỉ thấy `graph.json`.
- Để chạy local nhẹ hơn, nên giới hạn:
  - `--embed-node-types chunk,region`
  - `--embed-batch-size 1` hoặc `2`

## File liên quan hữu ích

- [scripts/run_offline_index.py](e:/project/vqa_kltn/scripts/run_offline_index.py)
- [scripts/run_cse_qa.py](e:/project/vqa_kltn/scripts/run_cse_qa.py)
- [src/extract/document_pipeline.py](e:/project/vqa_kltn/src/extract/document_pipeline.py)
- [src/algo/cse_indexing.py](e:/project/vqa_kltn/src/algo/cse_indexing.py)
- [src/algo/cse_query.py](e:/project/vqa_kltn/src/algo/cse_query.py)
- [src/api/qwen_vl_region_analysis.py](e:/project/vqa_kltn/src/api/qwen_vl_region_analysis.py)
- [src/api/qwen_vl_answering.py](e:/project/vqa_kltn/src/api/qwen_vl_answering.py)
