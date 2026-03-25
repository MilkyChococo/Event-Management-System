from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(payload: Any, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def resolve_existing_path(path: str | Path, base_dir: str | Path | None = None) -> Path:
    candidate = Path(path)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    if candidate.exists():
        return candidate.resolve()
    if base_dir is not None:
        base_candidate = Path(base_dir) / candidate
        if base_candidate.exists():
            return base_candidate.resolve()
    raise FileNotFoundError(f"Path not found: {path}")


def resolve_existing_file(path: str | Path, base_dir: str | Path | None = None) -> Path:
    resolved = resolve_existing_path(path, base_dir=base_dir)
    if not resolved.is_file():
        raise FileNotFoundError(f"Expected a file path but found: {resolved}")
    return resolved


def resolve_existing_dir(path: str | Path, base_dir: str | Path | None = None) -> Path:
    resolved = resolve_existing_path(path, base_dir=base_dir)
    if not resolved.is_dir():
        raise FileNotFoundError(f"Expected a directory path but found: {resolved}")
    return resolved
