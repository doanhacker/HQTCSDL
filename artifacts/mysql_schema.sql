CREATE DATABASE IF NOT EXISTS `leaf_features` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `leaf_features`;

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