from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import faiss
import matplotlib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from leaflib.config import RANDOM_STATE

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def feature_columns(df: pd.DataFrame) -> list[str]:
    exclude = {"split", "label", "image_name", "relative_path", "absolute_path", "faiss_id"}
    return [column for column in df.columns if column not in exclude]


def zscore_normalize(
    train_df: pd.DataFrame, valid_df: pd.DataFrame, test_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, StandardScaler]:
    cols = feature_columns(train_df)
    scaler = StandardScaler()
    train_df.loc[:, cols] = scaler.fit_transform(train_df[cols].astype(np.float32))
    valid_df.loc[:, cols] = scaler.transform(valid_df[cols].astype(np.float32))
    test_df.loc[:, cols] = scaler.transform(test_df[cols].astype(np.float32))
    return train_df, valid_df, test_df, scaler


def choose_k_by_elbow(train_features: np.ndarray, max_k: int, n_init: int, output_dir: Path) -> dict[str, Any]:
    upper_k = min(max_k, len(train_features))
    ks = list(range(1, upper_k + 1))
    inertias: list[float] = []

    for k in ks:
        model = KMeans(n_clusters=k, n_init=n_init, random_state=RANDOM_STATE)
        model.fit(train_features)
        inertias.append(float(model.inertia_))

    points = np.column_stack([ks, inertias]).astype(np.float64)
    start, end = points[0], points[-1]
    line = end - start
    line_norm = np.linalg.norm(line)

    if line_norm == 0:
        distances = np.zeros(len(points))
    else:
        point_vectors = points - start
        distances = np.abs(point_vectors[:, 0] * line[1] - point_vectors[:, 1] * line[0]) / line_norm

    best_index = int(np.argmax(distances))
    chosen_k = ks[best_index]

    plt.figure(figsize=(8, 5))
    plt.plot(ks, inertias, marker="o", linewidth=2)
    plt.axvline(chosen_k, color="red", linestyle="--", label=f"Chosen K = {chosen_k}")
    plt.title("Elbow Method")
    plt.xlabel("K")
    plt.ylabel("Inertia")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "elbow_plot.png", dpi=160)
    plt.close()

    explanation = (
        f"K = {chosen_k} được chọn vì có khoảng cách lớn nhất tới đường nối điểm đầu-cuối của đường Elbow, "
        "nghĩa là vị trí giảm inertia bắt đầu chậm lại rõ ràng."
    )
    result = {
        "k_values": ks,
        "inertias": inertias,
        "distances_to_line": distances.tolist(),
        "chosen_k": chosen_k,
        "reason": explanation,
    }
    (output_dir / "chosen_k.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def attach_faiss_ids(train_df: pd.DataFrame) -> pd.DataFrame:
    train_df = train_df.copy()
    train_df["faiss_id"] = np.arange(len(train_df), dtype=np.int64)
    return train_df


def build_faiss_ivf(train_df: pd.DataFrame, k_value: int, output_dir: Path) -> tuple[Path, Path]:
    cols = feature_columns(train_df)
    vectors = np.ascontiguousarray(train_df[cols].to_numpy(dtype=np.float32))
    dim = vectors.shape[1]
    nlist = max(1, min(k_value, len(vectors)))

    quantizer = faiss.IndexFlatL2(dim)
    index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)
    index_ref = cast(Any, index)
    index_ref.train(vectors)

    faiss_ids = np.ascontiguousarray(np.arange(len(train_df), dtype=np.int64))
    index_ref.add_with_ids(vectors, faiss_ids)

    index_path = output_dir / "leaf_features_ivf.faiss"
    faiss.write_index(index, str(index_path))

    mapping = train_df.loc[:, ["split", "label", "image_name", "relative_path"]].copy()
    mapping["faiss_id"] = faiss_ids
    mapping_path = output_dir / "faiss_id_mapping.csv"
    mapping.to_csv(mapping_path, index=False, encoding="utf-8")
    return index_path, mapping_path


def dump_outputs(
    train_df: pd.DataFrame,
    valid_df: pd.DataFrame,
    test_df: pd.DataFrame,
    scaler: StandardScaler,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    train_df.to_csv(output_dir / "train_features_zscore.csv", index=False, encoding="utf-8")
    valid_df.to_csv(output_dir / "valid_features_zscore.csv", index=False, encoding="utf-8")
    test_df.to_csv(output_dir / "test_features_zscore.csv", index=False, encoding="utf-8")

    scaler_payload = {
        "feature_columns": feature_columns(train_df),
        "mean": np.asarray(getattr(scaler, "mean_"), dtype=np.float64).tolist(),
        "scale": np.asarray(getattr(scaler, "scale_"), dtype=np.float64).tolist(),
    }
    (output_dir / "zscore_scaler.json").write_text(json.dumps(scaler_payload, indent=2), encoding="utf-8")


def summarize_dataset(train_df: pd.DataFrame, valid_df: pd.DataFrame, test_df: pd.DataFrame, output_dir: Path) -> None:
    summary = {
        "train_images": int(len(train_df)),
        "valid_images": int(len(valid_df)),
        "test_images": int(len(test_df)),
        "num_classes": int(train_df["label"].nunique()),
        "feature_dimension": int(len(feature_columns(train_df))),
        "classes": sorted(train_df["label"].unique().tolist()),
    }
    (output_dir / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
