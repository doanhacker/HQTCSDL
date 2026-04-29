from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd

from leaflib.config import MysqlConfig
from leaflib.console import configure_utf8_output
from leaflib.dataset import build_manifest, resolve_split_dir
from leaflib.features import extract_features_for_image, extract_split_features
from leaflib.modeling import (
    attach_faiss_ids,
    build_faiss_ivf,
    choose_k_by_elbow,
    dump_outputs,
    feature_columns,
    summarize_dataset,
    zscore_normalize,
)
from leaflib.storage import save_metadata_to_mysql, save_schema_file


configure_utf8_output()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract handcrafted image features, normalize them, choose K via Elbow, and build a Faiss IVF index."
    )
    parser.add_argument("--dataset-root", type=Path, default=Path("."))
    parser.add_argument("--train-dir", type=Path, default=Path("train") / "train")
    parser.add_argument("--valid-dir", type=Path, default=Path("valid") / "valid")
    parser.add_argument("--test-dir", type=Path, default=Path("test") / "test")
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--image-size", type=int, default=256)
    parser.add_argument("--max-k", type=int, default=10)
    parser.add_argument("--n-init", type=int, default=10)
    parser.add_argument("--save-mysql", action="store_true")
    parser.add_argument("--mysql-host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument("--mysql-port", type=int, default=int(os.getenv("MYSQL_PORT", "3306")))
    parser.add_argument("--mysql-user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument("--mysql-password", default=os.getenv("MYSQL_PASSWORD", ""))
    parser.add_argument("--mysql-database", default=os.getenv("MYSQL_DATABASE", "leaf_features"))
    return parser.parse_args()


def mysql_config_from_args(args: argparse.Namespace) -> MysqlConfig:
    return MysqlConfig(
        host=args.mysql_host,
        port=args.mysql_port,
        user=args.mysql_user,
        password=args.mysql_password,
        database=args.mysql_database,
    )


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    train_dir = resolve_split_dir(args.dataset_root, args.train_dir)
    valid_dir = resolve_split_dir(args.dataset_root, args.valid_dir)
    test_dir = resolve_split_dir(args.dataset_root, args.test_dir)

    train_manifest = build_manifest("train", train_dir)
    valid_manifest = build_manifest("valid", valid_dir)
    test_manifest = build_manifest("test", test_dir)

    train_df = extract_split_features(train_manifest, image_size=args.image_size)
    valid_df = extract_split_features(valid_manifest, image_size=args.image_size)
    test_df = extract_split_features(test_manifest, image_size=args.image_size)

    train_df, valid_df, test_df, scaler = zscore_normalize(train_df, valid_df, test_df)
    elbow_info = choose_k_by_elbow(
        train_df[feature_columns(train_df)].to_numpy(dtype="float32"),
        max_k=args.max_k,
        n_init=args.n_init,
        output_dir=output_dir,
    )

    train_df = attach_faiss_ids(train_df)
    build_faiss_ivf(train_df, elbow_info["chosen_k"], output_dir)
    dump_outputs(train_df, valid_df, test_df, scaler, output_dir)
    summarize_dataset(train_df, valid_df, test_df, output_dir)

    combined_df = pd.concat([train_df, valid_df, test_df], ignore_index=True)
    if args.save_mysql:
        mysql_ok = save_metadata_to_mysql(combined_df, mysql_config_from_args(args), output_dir)
        print(f"MySQL status: {'OK' if mysql_ok else 'FAILED'}")
    else:
        save_schema_file(output_dir, args.mysql_database)
        print("Đã tạo file schema MySQL, chưa thực hiện insert vì bạn chưa bật --save-mysql")

    print(f"Chosen K: {elbow_info['chosen_k']}")
    print(elbow_info["reason"])
    print(f"Outputs saved to: {output_dir}")


__all__ = [
    "build_manifest",
    "extract_features_for_image",
    "feature_columns",
    "MysqlConfig",
    "parse_args",
    "resolve_split_dir",
    "save_metadata_to_mysql",
]


if __name__ == "__main__":
    main()
