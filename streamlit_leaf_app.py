from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import mysql.connector
import pandas as pd
import streamlit as st
from PIL import Image

from faiss_leaf_search import load_scaler_payload, normalize_query_vector, predict_label_from_neighbors, search_index
from leaf_feature_pipeline import extract_features_for_image


ARTIFACTS_DIR = Path("artifacts")
QUERY_METADATA_BASE_COLUMNS = [
    "mean_h",
    "mean_s",
    "mean_v",
    "std_h",
    "std_s",
    "std_v",
    "glcm_contrast",
    "glcm_energy",
    "glcm_homogeneity",
    "area",
    "perimeter",
    "aspect_ratio",
    "canny_edge_pixels",
    "canny_edge_density",
    "foreground_ratio",
]


@st.cache_data
def load_json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data
def load_mapping_preview(path: Path) -> pd.DataFrame:
    return pd.read_csv(path).head(20)


def artifacts_include_hog_features() -> bool:
    scaler_payload = load_scaler_payload(ARTIFACTS_DIR)
    return any(str(column).startswith("hog_") for column in scaler_payload.get("feature_columns", []))


def resolve_result_image_path(relative_path: str, split_name: str) -> Path:
    candidate = Path(relative_path)
    if candidate.exists():
        return candidate

    split_prefixed = Path(split_name) / candidate
    if split_prefixed.exists():
        return split_prefixed

    cwd_prefixed = Path.cwd() / candidate
    if cwd_prefixed.exists():
        return cwd_prefixed

    cwd_split_prefixed = Path.cwd() / split_prefixed
    if cwd_split_prefixed.exists():
        return cwd_split_prefixed

    return candidate


def fetch_mysql_metadata(faiss_ids: list[int]) -> pd.DataFrame:
    if not faiss_ids:
        return pd.DataFrame()

    conn = mysql.connector.connect(host="127.0.0.1", port=3306, user="root", database="leaf_features")
    try:
        query = """
            SELECT faiss_id, split_name, label_name, image_name, relative_path,
                   mean_h, mean_s, mean_v, std_h, std_s, std_v,
                   glcm_contrast, glcm_energy, glcm_homogeneity,
                   area, perimeter, aspect_ratio, canny_edge_pixels, canny_edge_density, foreground_ratio
            FROM leaf_image_metadata
            WHERE faiss_id IN ({})
        """.format(",".join(["%s"] * len(faiss_ids)))
        cursor = conn.cursor()
        cursor.execute(query, faiss_ids)
        rows = cursor.fetchall()
        description = cursor.description or []
        columns = [column[0] for column in description]
        cursor.close()
        return pd.DataFrame(rows, columns=columns).sort_values("faiss_id")
    finally:
        conn.close()


def add_result_confidence(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return results

    scored = results.copy()
    scored["similarity_weight"] = 1.0 / (1.0 + scored["distance_l2"])
    total_weight = float(scored["similarity_weight"].sum()) or 1.0
    scored["confidence_pct"] = scored["similarity_weight"] / total_weight * 100.0
    return scored


def select_query_metadata_columns(query_features: dict[str, float]) -> list[str]:
    lbp_columns = sorted(column for column in query_features if column.startswith("lbp_uniform_"))
    hog_columns = sorted(column for column in query_features if column.startswith("hog_"))
    return QUERY_METADATA_BASE_COLUMNS + lbp_columns + hog_columns


def build_query_metadata(uploaded_file, image_path: Path, image_size: int) -> pd.DataFrame:
    with Image.open(image_path) as image:
        metadata: dict[str, Any] = {
            "file_name": uploaded_file.name,
            "file_size_kb": round(float(getattr(uploaded_file, "size", 0)) / 1024, 2),
            "image_format": image.format or "unknown",
            "image_mode": image.mode,
            "width_px": image.width,
            "height_px": image.height,
        }

    query_features = extract_features_for_image(str(image_path), image_size=image_size)
    selected_columns = select_query_metadata_columns(query_features)
    metadata.update({key: round(float(query_features[key]), 6) for key in selected_columns})
    return pd.DataFrame([metadata])


def build_normalized_query_metadata(query_features: dict[str, float], scaler_payload: dict[str, Any]) -> pd.DataFrame:
    normalized_metadata: dict[str, float] = {}
    for feature_name, mean_value, scale_value in zip(
        scaler_payload["feature_columns"],
        scaler_payload["mean"],
        scaler_payload["scale"],
    ):
        scale = float(scale_value) if float(scale_value) != 0.0 else 1.0
        normalized_value = (float(query_features[feature_name]) - float(mean_value)) / scale
        normalized_metadata[feature_name] = round(normalized_value, 6)
    return pd.DataFrame([normalized_metadata])


def query_uploaded_image(
    uploaded_file,
    top_k: int,
    nprobe: int,
    image_size: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    suffix = Path(uploaded_file.name).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_path = Path(tmp_file.name)

    try:
        query_metadata = build_query_metadata(uploaded_file, tmp_path, image_size=image_size)
        query_features = extract_features_for_image(str(tmp_path), image_size=image_size)
        scaler_payload = load_scaler_payload(ARTIFACTS_DIR)
        normalized_query_metadata = build_normalized_query_metadata(query_features, scaler_payload)
        query_vector = normalize_query_vector(query_features, scaler_payload)
        results = search_index(
            query_vector=query_vector,
            index_path=ARTIFACTS_DIR / "leaf_features_ivf.faiss",
            mapping_path=ARTIFACTS_DIR / "faiss_id_mapping.csv",
            top_k=top_k,
            nprobe=nprobe,
        )
        return add_result_confidence(results), query_metadata, normalized_query_metadata
    finally:
        tmp_path.unlink(missing_ok=True)


def render_prediction_summary(results: pd.DataFrame) -> None:
    predicted_label, vote_summary = predict_label_from_neighbors(results)
    if not predicted_label:
        return

    top_ratio = float(vote_summary.iloc[0]["vote_ratio"]) if not vote_summary.empty else 0.0
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Nhãn dự đoán", predicted_label)
    metric_col2.metric("Độ tin cậy tương đối", f"{top_ratio * 100:.2f}%")

    with st.expander("Chi tiết voting", expanded=True):
        display_df = vote_summary.copy()
        display_df["vote_score"] = display_df["vote_score"].map(lambda x: round(float(x), 6))
        display_df["vote_ratio"] = display_df["vote_ratio"].map(lambda x: round(float(x), 6))
        st.dataframe(display_df, width="stretch", hide_index=True)


def render_query_metadata(query_metadata: pd.DataFrame, normalized_query_metadata: pd.DataFrame) -> None:
    if query_metadata.empty:
        return

    with st.expander("Metadata ảnh truy vấn", expanded=True):
        st.dataframe(query_metadata, width="stretch", hide_index=True)
        if not normalized_query_metadata.empty:
            st.caption("Metadata da chuan hoa")
            st.dataframe(normalized_query_metadata, width="stretch", hide_index=True)


def render_search_results(
    results: pd.DataFrame,
    query_metadata: pd.DataFrame,
    normalized_query_metadata: pd.DataFrame,
) -> None:
    render_query_metadata(query_metadata, normalized_query_metadata)
    if results.empty:
        st.warning("Không tìm thấy kết quả nào.")
        return

    metadata_df = pd.DataFrame()
    try:
        metadata_df = fetch_mysql_metadata(results["faiss_id"].tolist())
    except Exception as exc:
        st.info(f"Không đọc được metadata từ MySQL: {exc}")

    cols = st.columns(min(3, len(results)))
    for pos, (_, row) in enumerate(results.iterrows()):
        col = cols[pos % len(cols)]
        with col:
            image_path = resolve_result_image_path(str(row["relative_path"]), str(row["split"]))
            if image_path.exists():
                st.image(str(image_path), caption=f"#{row['rank']} | {row['label']}", width="stretch")
            else:
                st.warning(f"Không mở được ảnh: {row['relative_path']}")
            st.write(f"`{row['image_name']}`")
            st.write(f"L2 distance: `{row['distance_l2']:.4f}`")
            st.write(f"Path: `{row['relative_path']}`")

            if not metadata_df.empty:
                current = metadata_df[metadata_df["faiss_id"] == row["faiss_id"]]
                if not current.empty:
                    with st.expander("Metadata"):
                        st.dataframe(current, width="stretch", hide_index=True)


def main() -> None:
    st.set_page_config(page_title="Leaf Search with Faiss", layout="wide")
    st.title("Leaf Feature Search")
    st.caption("Tra cứu ảnh lá cây tương tự bằng HSV + GLCM + LBP + Shape + Canny + Faiss IVF")

    if not ARTIFACTS_DIR.exists():
        st.error("Chưa có thư mục artifacts/. Hãy chạy leaf_feature_pipeline.py trước.")
        st.stop()

    summary = load_json_file(ARTIFACTS_DIR / "dataset_summary.json")
    chosen_k = load_json_file(ARTIFACTS_DIR / "chosen_k.json")

    if not artifacts_include_hog_features():
        st.warning("Artifacts hien tai chua co HOG. Hay chay lai leaf_feature_pipeline.py de HOG tham gia truy van Faiss.")

    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.metric("Tập ảnh", summary["tap_anh"])
    info_col2.metric("Số lớp", summary["num_classes"])
    info_col3.metric("K được chọn", chosen_k["chosen_k"])

    with st.expander("Lý do chọn K và thông tin dataset", expanded=False):
        st.write(chosen_k["reason"])
        st.json(summary)
        st.image(str(ARTIFACTS_DIR / "elbow_plot.png"), caption="Elbow plot", width="stretch")

    with st.sidebar:
        st.header("Tham số truy vấn")
        top_k = st.slider("Top-k", min_value=1, max_value=10, value=5)
        nprobe = st.slider("nprobe", min_value=1, max_value=10, value=3)
        image_size = st.selectbox("Image size", options=[128, 256, 384], index=1)
        st.write("Xem trước mapping:")
        st.dataframe(load_mapping_preview(ARTIFACTS_DIR / "faiss_id_mapping.csv"), width="stretch", hide_index=True)

    uploaded_file = st.file_uploader("Tải ảnh lá cây", type=["jpg", "jpeg", "png", "bmp"])
    if uploaded_file is not None:
        st.image(Image.open(uploaded_file), caption="Ảnh truy vấn", width=320)

        if st.button("Tìm ảnh tương tự", type="primary"):
            with st.spinner("Đang trích đặc trưng và tìm kiếm trong Faiss..."):
                uploaded_file.seek(0)
                results, query_metadata, normalized_query_metadata = query_uploaded_image(
                    uploaded_file,
                    top_k=top_k,
                    nprobe=nprobe,
                    image_size=image_size,
                )
            st.subheader("Kết quả")
            render_search_results(results, query_metadata, normalized_query_metadata)


if __name__ == "__main__":
    main()
