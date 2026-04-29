# Leaf Feature Pipeline

Pipeline nay thuc hien bai toan theo cac buoc:

1. Tien xu ly anh:
   - Gaussian Blur de loai nhieu nhe.
   - Chuyen RGB/BGR sang HSV.
   - Tach nen bang threshold + Otsu tren kenh Saturation, co fallback sang kenh Value.
2. Trich xuat dac trung:
   - Mau: `mean_h`, `mean_s`, `mean_v`, `std_h`, `std_s`, `std_v`
   - Be mat: `glcm_contrast`, `glcm_energy`, `glcm_homogeneity`
   - Texture LBP uniform: histogram `lbp_uniform_0` ... `lbp_uniform_9`
   - Hinh dang: `area`, `perimeter`, `aspect_ratio`
   - Canh: `canny_edge_pixels`, `canny_edge_density`
3. Chuan hoa z-score bang train set.
4. Chon `K` bang Elbow va ve bieu do.
5. Luu vector train vao Faiss IVF.
6. Luu metadata vao MySQL/XAMPP neu bat tuy chon `--save-mysql`.

## Cai dat

```powershell
python -m pip install opencv-python-headless scikit-image scikit-learn faiss-cpu mysql-connector-python tqdm
```

## Chay pipeline

Chi tao artifact va file schema MySQL:

```powershell
python leaf_feature_pipeline.py
```

Day metadata vao MySQL/XAMPP:

```powershell
python leaf_feature_pipeline.py --save-mysql --mysql-host 127.0.0.1 --mysql-port 3306 --mysql-user root --mysql-password "" --mysql-database leaf_features
```

Neu ban da co CSV trong `artifacts/` va chi muon import lai MySQL:

```powershell
python import_features_to_mysql.py --mysql-host 127.0.0.1 --mysql-port 3306 --mysql-user root --mysql-database leaf_features
```

Tim anh tuong tu bang Faiss IVF:

```powershell
python faiss_leaf_search.py --query-image "test\\test\\Mango\\0001_0001.JPG" --top-k 5
```

Chay giao dien Streamlit:

```powershell
streamlit run streamlit_leaf_app.py
```

## Chay thu tung buoc

1. Tao dac trung va Faiss:

```powershell
python leaf_feature_pipeline.py
```

2. Neu muon luu metadata vao XAMPP MySQL, bat MySQL trong XAMPP roi chay:

```powershell
python import_features_to_mysql.py --mysql-host 127.0.0.1 --mysql-port 3306 --mysql-user root --mysql-database leaf_features
```

3. Thu tim kiem bang dong lenh:

```powershell
python faiss_leaf_search.py --query-image "test\\test\\Mango\\0001_0001.JPG" --top-k 5 --nprobe 3
```

4. Mo giao dien web:

```powershell
streamlit run streamlit_leaf_app.py
```

5. Trong giao dien:

- Upload mot anh `.jpg/.png`
- Chon `Top-k`
- Bam `Tim anh tuong tu`
- Xem:
  - nhan du doan
  - ti le voting
  - top-k anh gan nhat
  - metadata tu MySQL

## Dau ra

Tat ca dau ra nam trong thu muc `artifacts/`:

- `train_features_zscore.csv`
- `valid_features_zscore.csv`
- `test_features_zscore.csv`
- `zscore_scaler.json`
- `elbow_plot.png`
- `chosen_k.json`
- `leaf_features_ivf.faiss`
- `faiss_id_mapping.csv`
- `mysql_schema.sql`
- `dataset_summary.json`

## Tim kiem voi Faiss

- Script: `faiss_leaf_search.py`
- Dau vao: anh truy van + artifact da tao
- Dau ra: top-k anh train gan nhat theo khoang cach L2 tren vector dac trung da z-score

## Giao dien

- File app: `streamlit_leaf_app.py`
- Cho phep upload anh, tim top-k, xem anh ket qua, khoang cach L2, va metadata tu MySQL neu co

## Ghi chu

- `chosen_k.json` co chua ly do chon `K`.
- Faiss IVF duoc train tren vector da chuan hoa z-score.
- Neu MySQL/XAMPP chua mo, script van chay va luu `mysql_schema.sql` de ban import sau.
