from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
import pandas as pd

from leaf_feature_pipeline import extract_features_for_image
from leaflib.console import configure_utf8_output


configure_utf8_output()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tìm ảnh lá tương tự bằng Faiss IVF.")
    parser.add_argument("--query-image", type=Path, required=True)
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--nprobe", type=int, default=3)
    return parser.parse_args()


def load_scaler_payload(artifacts_path: Path) -> dict[str, Any]:
    scaler_path = artifacts_path if artifacts_path.suffix == ".json" else artifacts_path / "zscore_scaler.json"
    return json.loads(scaler_path.read_text(encoding="utf-8"))


def normalize_query_vector(query_features: dict[str, float], scaler_payload: dict[str, Any]) -> np.ndarray:
    feature_names = scaler_payload["feature_columns"]
    mean = np.asarray(scaler_payload["mean"], dtype=np.float32)
    scale = np.asarray(scaler_payload["scale"], dtype=np.float32)
    vector = np.asarray([query_features[name] for name in feature_names], dtype=np.float32)
    scale = np.where(scale == 0, 1.0, scale)
    return ((vector - mean) / scale).reshape(1, -1).astype(np.float32)


def search_index(
    query_vector: np.ndarray,
    index_path: Path,
    mapping_path: Path,
    top_k: int,
    nprobe: int,
) -> pd.DataFrame:
    index = faiss.read_index(str(index_path))
    if hasattr(index, "nprobe"):
        index.nprobe = max(1, nprobe)

    distances, ids = index.search(query_vector, top_k)
    mapping_df = pd.read_csv(mapping_path)
    id_to_row = mapping_df.set_index("faiss_id")

    results: list[dict[str, Any]] = []
    for rank, (faiss_id, distance) in enumerate(zip(ids[0], distances[0]), start=1):
        if faiss_id == -1:
            continue
        row = id_to_row.loc[int(faiss_id)]
        results.append(
            {
                "rank": rank,
                "faiss_id": int(faiss_id),
                "distance_l2": float(distance),
                "split": row["split"],
                "label": row["label"],
                "image_name": row["image_name"],
                "relative_path": row["relative_path"],
            }
        )
    return pd.DataFrame(results)


def predict_label_from_neighbors(results: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    if results.empty:
        return "", pd.DataFrame(columns=["label", "vote_score", "vote_ratio"])

    vote_df = results.copy()
    vote_df["weight"] = 1.0 / (vote_df["distance_l2"] + 1e-8)
    grouped = vote_df.groupby("label", as_index=False).agg(vote_score=("weight", "sum"))
    summary = (
        grouped
        .sort_values(["vote_score", "label"], ascending=[False, True])
        .reset_index(drop=True)
    )
    total_score = float(summary["vote_score"].sum()) if not summary.empty else 1.0
    summary["vote_ratio"] = summary["vote_score"] / total_score
    predicted_label = str(summary.iloc[0]["label"]) if not summary.empty else ""
    return predicted_label, summary


def main() -> None:
    args = parse_args()
    artifacts_dir = args.artifacts_dir.resolve()

    query_features = extract_features_for_image(str(args.query_image.resolve()), image_size=args.image_size)
    scaler_payload = load_scaler_payload(artifacts_dir)
    query_vector = normalize_query_vector(query_features, scaler_payload)

    results = search_index(
        query_vector=query_vector,
        index_path=artifacts_dir / "leaf_features_ivf.faiss",
        mapping_path=artifacts_dir / "faiss_id_mapping.csv",
        top_k=args.top_k,
        nprobe=args.nprobe,
    )

    if results.empty:
        print("Không tìm thấy kết quả phù hợp.")
        return

    predicted_label, vote_summary = predict_label_from_neighbors(results)
    print(f"Dự đoán nhãn lá: {predicted_label}")
    print("Tổng hợp voting:")
    print(vote_summary.to_string(index=False))
    print("Kết quả top-k gần nhất:")
    print(results.to_string(index=False))


if __name__ == "__main__":
    main()
