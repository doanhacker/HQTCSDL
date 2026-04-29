from __future__ import annotations

from pathlib import Path

import mysql.connector
import numpy as np
import pandas as pd
from mysql.connector import Error as MySQLError

from leaflib.config import MysqlConfig


def mysql_schema_sql(database: str) -> str:
    return f"""
CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `{database}`;

CREATE TABLE IF NOT EXISTS leaf_image_metadata (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    split_name VARCHAR(20) NOT NULL,
    label_name VARCHAR(100) NOT NULL,
    image_name VARCHAR(255) NOT NULL,
    relative_path VARCHAR(500) NOT NULL,
    faiss_id BIGINT NULL,
    mean_h DOUBLE,
    mean_s DOUBLE,
    mean_v DOUBLE,
    std_h DOUBLE,
    std_s DOUBLE,
    std_v DOUBLE,
    glcm_contrast DOUBLE,
    glcm_energy DOUBLE,
    glcm_homogeneity DOUBLE,
    area DOUBLE,
    perimeter DOUBLE,
    aspect_ratio DOUBLE,
    canny_edge_pixels DOUBLE,
    canny_edge_density DOUBLE,
    foreground_ratio DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""".strip()


def save_schema_file(output_dir: Path, database: str) -> Path:
    schema_path = output_dir / "mysql_schema.sql"
    schema_path.write_text(mysql_schema_sql(database), encoding="utf-8")
    return schema_path


def save_metadata_to_mysql(all_df: pd.DataFrame, config: MysqlConfig, output_dir: Path) -> bool:
    schema_path = save_schema_file(output_dir, config.database)
    try:
        connection = mysql.connector.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            autocommit=True,
        )
        cursor = connection.cursor()

        for statement in schema_path.read_text(encoding="utf-8").split(";"):
            sql = statement.strip()
            if sql:
                cursor.execute(sql)

        insert_df = all_df.copy()
        if "faiss_id" not in insert_df.columns:
            insert_df["faiss_id"] = None

        mysql_columns = [
            "split",
            "label",
            "image_name",
            "relative_path",
            "faiss_id",
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
        records_df = insert_df[mysql_columns].replace({np.nan: None})
        records = [tuple(row) for row in records_df.itertuples(index=False, name=None)]

        cursor.execute(f"USE `{config.database}`")
        cursor.execute("TRUNCATE TABLE leaf_image_metadata")

        insert_sql = """
            INSERT INTO leaf_image_metadata (
                split_name, label_name, image_name, relative_path, faiss_id,
                mean_h, mean_s, mean_v, std_h, std_s, std_v,
                glcm_contrast, glcm_energy, glcm_homogeneity,
                area, perimeter, aspect_ratio, canny_edge_pixels, canny_edge_density, foreground_ratio
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """

        batch_size = 250
        for start_idx in range(0, len(records), batch_size):
            cursor.executemany(insert_sql, records[start_idx : start_idx + batch_size])
            connection.commit()

        cursor.close()
        connection.close()
        return True
    except MySQLError as exc:
        print(f"[WARN] Không thể lưu MySQL: {exc}")
        print(f"[INFO] File schema đã lưu tại: {schema_path}")
        return False
