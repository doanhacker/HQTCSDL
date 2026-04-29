from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from leaflib.config import MysqlConfig
from leaflib.console import configure_utf8_output
from leaflib.storage import save_metadata_to_mysql

configure_utf8_output()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import extracted feature CSVs into MySQL in safe batches.")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--mysql-host", default="127.0.0.1")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user", default="root")
    parser.add_argument("--mysql-password", default="")
    parser.add_argument("--mysql-database", default="leaf_features")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifacts_dir = args.artifacts_dir.resolve()

    train_df = pd.read_csv(artifacts_dir / "train_features_zscore.csv")
    valid_df = pd.read_csv(artifacts_dir / "valid_features_zscore.csv")
    test_df = pd.read_csv(artifacts_dir / "test_features_zscore.csv")
    all_df = pd.concat([train_df, valid_df, test_df], ignore_index=True)

    config = MysqlConfig(
        host=args.mysql_host,
        port=args.mysql_port,
        user=args.mysql_user,
        password=args.mysql_password,
        database=args.mysql_database,
    )
    ok = save_metadata_to_mysql(all_df, config, artifacts_dir)
    print(f"MySQL import status: {'OK' if ok else 'FAILED'}")


if __name__ == "__main__":
    main()
