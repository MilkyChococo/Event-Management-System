# scripts/inspect_data.py  — chạy 1 lần để xem cấu trúc data
import pandas as pd
import json

for fname in ["DocVQA-2026/test.parquet", "DocVQA-2026/val.parquet"]:
    print(f"\n{'='*60}")
    print(f"FILE: {fname}")
    df = pd.read_parquet(fname)
    print(f"Rows: {len(df)}, Columns: {list(df.columns)}")
    
    row = df.iloc[0]
    for col in df.columns:
        val = row[col]
        print(f"\n  [{col}] type={type(val).__name__}")
        if isinstance(val, dict):
            print(f"    keys: {list(val.keys())}")
            for k, v in val.items():
                print(f"    .{k} = {repr(v)[:120]}")
        elif isinstance(val, (list, tuple)):
            print(f"    len={len(val)}, first={repr(val[0])[:120] if val else 'empty'}")
        elif isinstance(val, bytes):
            print(f"    bytes, len={len(val)}")
        else:
            print(f"    = {repr(val)[:120]}")