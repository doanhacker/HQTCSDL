from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd
from skimage.feature import graycomatrix, graycoprops, hog, local_binary_pattern
from tqdm import tqdm

from leaflib.config import (
    HOG_CELLS_PER_BLOCK,
    HOG_IMAGE_SIZE,
    HOG_ORIENTATIONS,
    HOG_PIXELS_PER_CELL,
    LBP_METHOD,
    LBP_POINTS,
    LBP_RADIUS,
)


def load_image_bgr(image_path: str, image_size: int) -> np.ndarray:
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Không đọc được ảnh: {image_path}")
    return cv2.resize(image, (image_size, image_size), interpolation=cv2.INTER_AREA)


def preprocess_leaf(image_bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    blurred = cv2.GaussianBlur(image_bgr, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    sat = hsv[:, :, 1]
    _, mask = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if np.count_nonzero(mask) < mask.size * 0.05:
        value = hsv[:, :, 2]
        _, mask = cv2.threshold(value, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, threshold1=100, threshold2=200)
    return blurred, hsv, gray, mask, edges


def masked_stats(channel: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    values = channel[mask > 0]
    if values.size == 0:
        values = channel.reshape(-1)
    return float(np.mean(values)), float(np.std(values))


def largest_contour(mask: np.ndarray) -> np.ndarray | None:
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    return max(contours, key=cv2.contourArea)


def glcm_features(gray: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    if np.count_nonzero(mask) == 0:
        roi = gray
    else:
        ys, xs = np.where(mask > 0)
        y1, y2 = int(ys.min()), int(ys.max()) + 1
        x1, x2 = int(xs.min()), int(xs.max()) + 1
        roi = gray[y1:y2, x1:x2]

    quantized = (roi / 8).astype(np.uint8)
    glcm = graycomatrix(quantized, distances=[1], angles=[0], levels=32, symmetric=True, normed=True)
    return {
        "glcm_contrast": float(graycoprops(glcm, "contrast")[0, 0]),
        "glcm_energy": float(graycoprops(glcm, "energy")[0, 0]),
        "glcm_homogeneity": float(graycoprops(glcm, "homogeneity")[0, 0]),
    }


def lbp_features(gray: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    lbp = local_binary_pattern(gray, P=LBP_POINTS, R=LBP_RADIUS, method=LBP_METHOD)
    masked_lbp = lbp[mask > 0] if np.count_nonzero(mask) > 0 else lbp.reshape(-1)
    n_bins = LBP_POINTS + 2
    hist, _ = np.histogram(masked_lbp, bins=np.arange(0, n_bins + 1), range=(0, n_bins), density=True)
    return {f"lbp_uniform_{idx}": float(value) for idx, value in enumerate(hist)}


def hog_features(gray: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    masked_gray = cv2.bitwise_and(gray, gray, mask=mask) if np.count_nonzero(mask) > 0 else gray
    resized = cv2.resize(masked_gray, HOG_IMAGE_SIZE, interpolation=cv2.INTER_AREA)
    descriptor = hog(
        resized,
        orientations=HOG_ORIENTATIONS,
        pixels_per_cell=HOG_PIXELS_PER_CELL,
        cells_per_block=HOG_CELLS_PER_BLOCK,
        block_norm="L2-Hys",
        visualize=False,
        feature_vector=True,
    )
    return {f"hog_{idx}": float(value) for idx, value in enumerate(descriptor)}


def shape_features(mask: np.ndarray) -> dict[str, float]:
    contour = largest_contour(mask)
    if contour is None:
        return {"area": 0.0, "perimeter": 0.0, "aspect_ratio": 0.0}

    area = float(cv2.contourArea(contour))
    perimeter = float(cv2.arcLength(contour, closed=True))
    _, _, w, h = cv2.boundingRect(contour)
    aspect_ratio = float(w / h) if h else 0.0
    return {"area": area, "perimeter": perimeter, "aspect_ratio": aspect_ratio}


def edge_features(edges: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    masked_edges = edges[mask > 0] if np.count_nonzero(mask) > 0 else edges.reshape(-1)
    edge_pixels = float(np.count_nonzero(masked_edges))
    total_pixels = float(masked_edges.size) if masked_edges.size else 1.0
    return {
        "canny_edge_pixels": edge_pixels,
        "canny_edge_density": edge_pixels / total_pixels,
    }


def extract_features_for_image(image_path: str, image_size: int) -> dict[str, float]:
    image_bgr = load_image_bgr(image_path, image_size=image_size)
    _, hsv, gray, mask, edges = preprocess_leaf(image_bgr)

    features: dict[str, float] = {}
    for idx, channel_name in enumerate(["h", "s", "v"]):
        mean_value, std_value = masked_stats(hsv[:, :, idx], mask)
        features[f"mean_{channel_name}"] = mean_value
        features[f"std_{channel_name}"] = std_value

    features.update(glcm_features(gray, mask))
    features.update(lbp_features(gray, mask))
    features.update(hog_features(gray, mask))
    features.update(shape_features(mask))
    features.update(edge_features(edges, mask))
    features["foreground_ratio"] = float(np.count_nonzero(mask) / mask.size)
    return features


def extract_split_features(manifest: pd.DataFrame, image_size: int) -> pd.DataFrame:
    feature_rows: list[dict[str, Any]] = []
    records = manifest.to_dict("records")
    split_name = str(manifest.iloc[0]["split"]) if not manifest.empty else "split"
    iterator = tqdm(records, total=len(records), desc=f"Extract {split_name}")

    for row in iterator:
        features = extract_features_for_image(str(row["absolute_path"]), image_size=image_size)
        feature_rows.append({**row, **features})

    return pd.DataFrame(feature_rows)
