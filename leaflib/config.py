from __future__ import annotations

from dataclasses import dataclass


RANDOM_STATE = 42
LBP_POINTS = 8
LBP_RADIUS = 1
LBP_METHOD = "uniform"
HOG_ORIENTATIONS = 9
HOG_PIXELS_PER_CELL = (8, 8)
HOG_CELLS_PER_BLOCK = (2, 2)
HOG_IMAGE_SIZE = (32, 32)


@dataclass
class MysqlConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
