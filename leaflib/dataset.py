from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def resolve_split_dir(dataset_root: Path, split_dir: Path) -> Path:
    resolved = dataset_root / split_dir
    if not resolved.exists():
        raise FileNotFoundError(f"Không tìm thấy thư mục dataset: {resolved}")
    return resolved


def build_manifest(split_name: str, split_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for class_dir in sorted(path for path in split_dir.iterdir() if path.is_dir()):
        for image_path in sorted(class_dir.rglob("*")):
            if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp"}:
                continue
            rows.append(
                {
                    "split": split_name,
                    "label": class_dir.name,
                    "image_name": image_path.name,
                    "relative_path": str(image_path.relative_to(split_dir.parent)),
                    "absolute_path": str(image_path.resolve()),
                }
            )

    if not rows:
        raise ValueError(f"Không có ảnh nào trong {split_dir}")
    return pd.DataFrame(rows)
