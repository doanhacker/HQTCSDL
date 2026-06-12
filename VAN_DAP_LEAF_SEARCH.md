# Tai lieu on van dap - Leaf Feature Search

## 1. Tong quan de tai

De tai xay dung he thong tim kiem anh la cay tuong tu dua tren dac trung anh thu cong.

He thong khong dung deep learning. Thay vao do, moi anh la cay duoc bien doi thanh mot vector dac trung gom mau sac, ket cau, hinh dang va canh. Sau do cac vector cua tap train duoc dua vao FAISS de tim kiem anh gan nhat.

Luong tong quat:

1. Doc dataset gom `train`, `valid`, `test`.
2. Tao manifest chua nhan, ten anh, duong dan anh.
3. Tien xu ly anh: resize, lam mo, chuyen HSV, tach nen.
4. Trich xuat dac trung: HSV, GLCM, LBP, HOG, shape, Canny.
5. Chuan hoa dac trung bang z-score.
6. Chon `K` bang Elbow.
7. Build FAISS IVF index tren tap train.
8. Luu artifact ra thu muc `artifacts/`.
9. Day metadata vao MySQL/XAMPP neu can.
10. Giao dien Streamlit cho phep upload anh va tim anh tuong tu.

So lieu hien tai:

- Train: `4274` anh
- Valid: `110` anh
- Test: `110` anh
- Tong metadata trong MySQL: `4494` dong
- So lop: `12`
- So chieu vector dac trung: `349`
- K chon bang Elbow: `4`

## 2. Vai tro cac file chinh

### `leaf_feature_pipeline.py`

Day la file dieu phoi pipeline offline.

Khi chay:

```powershell
python leaf_feature_pipeline.py
```

chuong trinh se:

1. Doc tham so dong lenh.
2. Xac dinh duong dan dataset.
3. Tao manifest cho train, valid, test.
4. Trich xuat dac trung tung anh.
5. Chuan hoa z-score.
6. Chon K bang Elbow.
7. Tao FAISS IVF index.
8. Luu CSV, scaler, FAISS index, mapping, summary.
9. Tao file schema MySQL.

Neu chay voi `--save-mysql`, chuong trinh se day metadata vao MySQL/XAMPP.

### `leaflib/dataset.py`

File nay quan ly viec doc cau truc thu muc dataset.

Ham quan trong:

```python
build_manifest(split_name, split_dir)
```

Ham nay duyet cac thu muc con. Moi thu muc con la mot lop, vi du:

```text
train/train/Mango
train/train/Lemon
train/train/Basil
```

Moi anh duoc luu thanh mot dong gom:

- `split`: train, valid hoac test
- `label`: ten lop
- `image_name`: ten file anh
- `relative_path`: duong dan tuong doi
- `absolute_path`: duong dan tuyet doi

Neu thay hoi vi sao can manifest:

> Manifest giup tach phan quan ly du lieu khoi phan xu ly anh. Cac buoc sau chi can lam viec voi bang manifest thay vi phai duyet thu muc lai nhieu lan.

### `leaflib/features.py`

File nay thuc hien tien xu ly va trich xuat dac trung anh.

Ham quan trong:

```python
load_image_bgr()
preprocess_leaf()
extract_features_for_image()
extract_split_features()
```

### `leaflib/modeling.py`

File nay xu ly cac buoc lien quan den vector dac trung va FAISS:

- Chon cot dac trung.
- Chuan hoa z-score.
- Chon K bang Elbow.
- Gan `faiss_id`.
- Build FAISS IVF index.
- Luu artifact.
- Tao summary dataset.

### `leaflib/storage.py`

File nay tao schema MySQL va insert metadata vao bang `leaf_image_metadata`.

### `faiss_leaf_search.py`

File nay dung de tim anh tuong tu bang dong lenh.

Vi du:

```powershell
python faiss_leaf_search.py --query-image "test\test\Mango\0001_0001.JPG" --top-k 5
```

### `streamlit_leaf_app.py`

File nay la giao dien web Streamlit. Nguoi dung upload anh, chon top-k, bam tim kiem va xem ket qua.

## 3. Tien xu ly anh

Tien xu ly nam trong ham:

```python
preprocess_leaf()
```

### Buoc 1: Resize anh

Anh duoc doc bang OpenCV:

```python
cv2.imread(image_path, cv2.IMREAD_COLOR)
```

Sau do resize ve kich thuoc mac dinh `256 x 256`.

Muc dich:

- Dong nhat kich thuoc anh.
- Giam chi phi tinh toan.
- Dam bao vector dac trung co kich thuoc on dinh.

### Buoc 2: Gaussian Blur

```python
blurred = cv2.GaussianBlur(image_bgr, (5, 5), 0)
```

Muc dich:

- Giam nhieu nhe.
- Lam anh on dinh hon truoc khi tach nen.

Neu thay hoi:

> Gaussian Blur giup giam nhieu cuc bo, tranh viec Otsu va Canny bi anh huong boi cac diem nhieu nho.

### Buoc 3: Chuyen BGR sang HSV

```python
hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
```

HSV gom:

- H: Hue, sac do mau.
- S: Saturation, do bao hoa.
- V: Value, do sang.

Ly do dung HSV thay RGB:

> RGB bi anh huong manh boi anh sang. HSV tach rieng sac do, do bao hoa va do sang nen phu hop hon de mo ta mau la cay.

### Buoc 4: Tach nen bang Otsu tren kenh Saturation

```python
sat = hsv[:, :, 1]
_, mask = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
```

Otsu tu dong tim nguong tach foreground va background.

Voi anh la cay, kenh Saturation thuong giup tach vung la tot vi la co mau bao hoa hon nen.

### Buoc 5: Fallback sang kenh Value

```python
if np.count_nonzero(mask) < mask.size * 0.05:
    value = hsv[:, :, 2]
    _, mask = cv2.threshold(value, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
```

Neu mask co so pixel foreground nho hon 5% tong anh, code xem nhu tach nen that bai. Khi do thu lai bang kenh Value.

Neu thay hoi vi sao co fallback:

> Vi khong phai anh nao kenh Saturation cung tach la tot. Neu mask qua nho, em coi ket qua khong dang tin va thu lai bang kenh do sang Value de xu ly truong hop nen va anh sang khac biet.

### Buoc 6: Morphological Open va Close

```python
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
```

Y nghia:

- Open: loai cac diem nhieu nho.
- Close: lap cac lo nho trong vung la.

### Buoc 7: Anh xam va Canny Edge

```python
gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
edges = cv2.Canny(gray, threshold1=100, threshold2=200)
```

Canny duoc dung de lay thong tin canh, gan la va duong vien la.

## 4. Cac nhom dac trung

Ham tong hop:

```python
extract_features_for_image()
```

Vector dac trung hien tai co `349` chieu.

### 4.1. Dac trung mau HSV

Cot dac trung:

```text
mean_h, mean_s, mean_v
std_h, std_s, std_v
```

Code tinh mean va std chi tren vung la:

```python
values = channel[mask > 0]
```

Y nghia:

- `mean_h`, `mean_s`, `mean_v`: mau trung binh cua la.
- `std_h`, `std_s`, `std_v`: muc do bien thien mau, giup phan biet la co dom, loang, khac mau.

Neu mask rong, code lay toan anh de tranh loi.

### 4.2. Dac trung GLCM

Cot dac trung:

```text
glcm_contrast
glcm_energy
glcm_homogeneity
```

GLCM la Gray-Level Co-occurrence Matrix, mo ta tan suat xuat hien dong thoi cua cap muc xam.

Code cat vung ROI theo mask, sau do luong tu hoa anh xam:

```python
quantized = (roi / 8).astype(np.uint8)
```

Anh xam 256 muc duoc giam xuong 32 muc.

Neu thay hoi vi sao luong tu hoa:

> Neu dung 256 muc xam, GLCM co kich thuoc 256 x 256, tinh toan nang va de nhieu. Giam xuong 32 muc giup dac trung on dinh va tinh nhanh hon.

Y nghia:

- `contrast`: do tuong phan ket cau.
- `energy`: muc do dong deu cua texture.
- `homogeneity`: muc do min va dong nhat.

### 4.3. Dac trung LBP

Cau hinh:

```python
LBP_POINTS = 8
LBP_RADIUS = 1
LBP_METHOD = "uniform"
```

Cot dac trung:

```text
lbp_uniform_0 ... lbp_uniform_9
```

Vi `P = 8`, uniform LBP co `P + 2 = 10` bins.

Y nghia:

> LBP mo ta texture cuc bo bang cach so sanh pixel trung tam voi cac pixel xung quanh. No phu hop de mo ta van la, do nham va be mat la.

Neu thay hoi LBP khac GLCM the nao:

> GLCM mo ta thong ke cap muc xam tren mot vung anh, con LBP mo ta pattern nhi phan cuc bo quanh tung pixel. GLCM thien ve thong ke texture toan vung, LBP thien ve mau cuc bo.

### 4.4. Dac trung HOG

Cau hinh:

```python
HOG_ORIENTATIONS = 9
HOG_PIXELS_PER_CELL = (8, 8)
HOG_CELLS_PER_BLOCK = (2, 2)
HOG_IMAGE_SIZE = (32, 32)
```

Cot dac trung:

```text
hog_0 ... hog_323
```

Tong HOG co `324` chieu.

Cach tinh so chieu:

- Anh HOG resize ve `32 x 32`.
- Moi cell `8 x 8`, nen co `4 x 4 = 16` cells.
- Moi block gom `2 x 2` cells.
- So block la `(4 - 1) x (4 - 1) = 3 x 3 = 9`.
- Moi block co `2 x 2 x 9 = 36` gia tri.
- Tong la `9 x 36 = 324`.

Y nghia:

> HOG mo ta phan bo huong gradient, giup nam bat hinh dang cuc bo, duong vien va gan la.

### 4.5. Dac trung hinh dang

Cot dac trung:

```text
area
perimeter
aspect_ratio
```

Code lay contour lon nhat:

```python
contour = largest_contour(mask)
```

Y nghia:

- `area`: dien tich vung la.
- `perimeter`: chu vi la.
- `aspect_ratio`: ty le rong/cao cua bounding box.

Neu thay hoi vi sao lay contour lon nhat:

> Sau khi tach nen, vung la thuong la connected component lon nhat. Cac vung nho hon thuong la nhieu nen bi bo qua.

### 4.6. Dac trung canh Canny

Cot dac trung:

```text
canny_edge_pixels
canny_edge_density
```

Y nghia:

- `canny_edge_pixels`: so pixel canh.
- `canny_edge_density`: ty le pixel canh tren tong pixel.

Dac trung nay phan anh do phuc tap cua duong vien va gan la.

### 4.7. Foreground ratio

```python
foreground_ratio = np.count_nonzero(mask) / mask.size
```

Y nghia:

> Cho biet vung la chiem bao nhieu phan tram trong anh.

## 5. Chuan hoa z-score

Ham:

```python
zscore_normalize()
```

Cong thuc:

```text
z = (x - mean) / std
```

Code:

```python
scaler.fit_transform(train_df[cols])
scaler.transform(valid_df[cols])
scaler.transform(test_df[cols])
```

Diem quan trong:

> Scaler chi duoc fit tren train. Valid va test chi transform theo mean/std cua train.

Neu thay hoi vi sao khong fit tren ca train, valid, test:

> Vi nhu vay se gay ro ri du lieu danh gia vao qua trinh huan luyen. Em chi fit tren train de mo phong dung truong hop thuc te, khi du lieu moi phai dung thong ke da hoc tu train.

Neu thay hoi vi sao can chuan hoa:

> Cac dac trung co thang do khac nhau. Vi du `area` co the rat lon, con `canny_edge_density` chi tu 0 den 1. Neu khong chuan hoa, khoang cach L2 se bi chi phoi boi cac dac trung co gia tri lon.

## 6. Chon K bang Elbow

Ham:

```python
choose_k_by_elbow()
```

Chuong trinh chay KMeans voi K tu 1 den `max_k`, mac dinh la 10. Moi K tinh inertia:

```python
model.inertia_
```

Inertia la tong khoang cach binh phuong tu diem du lieu den tam cum gan nhat.

K cang tang thi inertia cang giam. Elbow la diem ma sau do inertia giam cham lai.

Code chon K bang cach:

- Noi diem dau va diem cuoi cua duong inertia.
- Tinh khoang cach moi diem toi duong thang do.
- Chon diem co khoang cach lon nhat.

Ket qua hien tai:

```text
K = 4
```

Neu thay hoi K nay co phai so lop khong:

> Khong. K o day la so cum coarse cho FAISS IVF, tuc `nlist`, khong phai so nhan phan loai. Dataset co 12 lop, nhung FAISS IVF co the chia khong gian vector thanh 4 cum de tang toc tim kiem.

## 7. FAISS IVF

Ham:

```python
build_faiss_ivf()
```

Code:

```python
quantizer = faiss.IndexFlatL2(dim)
index = faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)
index.train(vectors)
index.add_with_ids(vectors, faiss_ids)
```

Giai thich:

- `IndexFlatL2`: index co so dung khoang cach L2.
- `IndexIVFFlat`: chia khong gian vector thanh cac cum de tim kiem nhanh.
- `nlist`: so cum IVF, lay theo K da chon.
- `train(vectors)`: hoc cac centroid.
- `add_with_ids()`: them vector train vao index kem `faiss_id`.

Chi tap train duoc dua vao FAISS.

Neu thay hoi vi sao chi dung train:

> Train la tap tham chieu chinh de tim kiem. Valid/test dung de danh gia hoac truy van thu. Neu dua valid/test vao index thi viec danh gia co the kem khach quan.

File tao ra:

- `leaf_features_ivf.faiss`
- `faiss_id_mapping.csv`

## 8. Tim kiem anh tuong tu

File:

```text
faiss_leaf_search.py
```

Luong tim kiem:

1. Doc anh query.
2. Trich dac trung query bang cung pipeline.
3. Load `zscore_scaler.json`.
4. Chuan hoa query bang mean/std cua train.
5. Load FAISS index.
6. Search top-k anh gan nhat.
7. Dung `faiss_id_mapping.csv` de lay nhan, ten anh, duong dan.
8. Du doan nhan bang weighted voting.

Chuan hoa query:

```python
query_vector = (vector - mean) / scale
```

Neu `scale = 0`, code thay bang `1.0` de tranh chia cho 0.

## 9. Khoang cach L2

FAISS tra ve `distance_l2`.

Khoang cach cang nho thi anh cang giong nhau trong khong gian dac trung.

Neu thay hoi vi sao dung L2:

> Sau khi z-score, cac chieu dac trung da duoc dua ve cung thang do. Khi do L2 la cach do tu nhien de tinh do gan giua cac vector lien tuc, va FAISS ho tro L2 rat toi uu.

## 10. Weighted voting de du doan nhan

Ham:

```python
predict_label_from_neighbors()
```

Code tinh trong so:

```python
weight = 1.0 / (distance_l2 + 1e-8)
```

Anh cang gan thi distance cang nho, trong so cang lon.

Sau do gom theo label:

```python
groupby("label").agg(vote_score=("weight", "sum"))
```

Nhan co tong vote lon nhat la nhan du doan.

Neu thay hoi vi sao khong vote deu:

> Neu vote deu, mot anh rat gan va mot anh kha xa co anh huong nhu nhau. Em dung weighted voting de anh gan hon co anh huong lon hon toi ket qua.

## 11. MySQL/XAMPP

File:

```text
leaflib/storage.py
```

Bang:

```text
leaf_image_metadata
```

Luong luu MySQL:

1. Tao database `leaf_features` neu chua co.
2. Tao bang `leaf_image_metadata` neu chua co.
3. `TRUNCATE TABLE` de xoa du lieu cu.
4. Insert metadata theo batch, moi batch 250 dong.

Lenh import lai metadata:

```powershell
python import_features_to_mysql.py --mysql-host 127.0.0.1 --mysql-port 3306 --mysql-user root --mysql-database leaf_features
```

Bang MySQL luu:

- split
- label
- image name
- relative path
- faiss_id
- HSV
- GLCM
- shape
- Canny
- foreground ratio

Diem can noi ro:

> CSV va FAISS dung day du 349 dac trung, bao gom ca LBP va HOG. MySQL chi luu metadata can thiet de hien thi va tra cuu, khong luu toan bo HOG/LBP vi HOG co rat nhieu chieu va khong can cho giao dien.

Neu thay hoi vi sao valid/test co `faiss_id` null:

> Vi chi train duoc add vao FAISS index. Valid/test duoc luu metadata de quan ly nhung khong nam trong index tim kiem, nen `faiss_id` cua chung la null.

## 12. Giao dien Streamlit

File:

```text
streamlit_leaf_app.py
```

Chay:

```powershell
streamlit run streamlit_leaf_app.py
```

Luong giao dien:

1. Load `dataset_summary.json`.
2. Load `chosen_k.json`.
3. Hien thi so anh train, so lop, K da chon.
4. Nguoi dung chon `top-k`, `nprobe`, `image_size`.
5. Nguoi dung upload anh.
6. Anh upload duoc luu tam bang `tempfile`.
7. Trich dac trung anh upload.
8. Chuan hoa query.
9. Search FAISS.
10. Du doan nhan bang voting.
11. Lay metadata tu MySQL theo `faiss_id`.
12. Hien thi anh gan nhat, distance, confidence, path va metadata.

## 13. nprobe trong FAISS

Trong FAISS IVF, vector duoc chia thanh nhieu cum.

`nprobe` la so cum se duoc do khi tim kiem.

- `nprobe` nho: tim nhanh hon, nhung co the bo sot ket qua tot.
- `nprobe` lon: chinh xac hon, nhung cham hon.

Neu thay hoi:

> `nprobe` dieu khien trade-off giua toc do va do chinh xac trong FAISS IVF.

## 14. Cac artifact dau ra

Tat ca nam trong thu muc:

```text
artifacts/
```

Cac file quan trong:

- `train_features_zscore.csv`: dac trung train da chuan hoa.
- `valid_features_zscore.csv`: dac trung valid da chuan hoa.
- `test_features_zscore.csv`: dac trung test da chuan hoa.
- `zscore_scaler.json`: mean/std cua train.
- `chosen_k.json`: K duoc chon bang Elbow.
- `elbow_plot.png`: bieu do Elbow.
- `leaf_features_ivf.faiss`: FAISS index.
- `faiss_id_mapping.csv`: anh xa `faiss_id` sang anh train.
- `mysql_schema.sql`: schema MySQL.
- `dataset_summary.json`: thong ke dataset.

## 15. Cau tra loi mau: "Em hay trinh bay quy trinh lam"

Em xay dung mot pipeline tim kiem anh la cay tuong tu. Dau tien em duyet dataset theo tung split train, valid, test va tao manifest chua nhan, ten anh va duong dan. Sau do moi anh duoc resize, lam mo Gaussian, chuyen sang HSV, tach vung la bang Otsu tren kenh Saturation va co fallback sang kenh Value neu mask qua nho.

Tu vung la, em trich cac dac trung mau HSV, texture GLCM, texture LBP, HOG, hinh dang contour, canh Canny va foreground ratio. Cac dac trung duoc chuan hoa z-score bang thong ke cua tap train. Sau do em dung Elbow de chon so cum IVF cho FAISS, hien tai K duoc chon la 4.

Tap train sau khi chuan hoa duoc dua vao FAISS IVF index. Khi co anh truy van, he thong trich dac trung theo dung quy trinh cu, chuan hoa bang scaler cua train, tim top-k anh gan nhat bang khoang cach L2, roi du doan nhan bang weighted voting theo nghich dao khoang cach. Metadata duoc luu ra CSV va day vao MySQL/XAMPP de giao dien Streamlit hien thi ket qua.

## 16. Cac cau hoi thay co the hoi sau

### 1. Vi sao khong dung CNN?

Tra loi:

> Vi muc tieu cua em la xay dung he thong dua tren dac trung thu cong, co kha nang giai thich tung dac trung. Cach nay nhe hon, khong can GPU va phu hop voi dataset vua phai. Tuy nhien CNN co the cho ket qua tot hon neu co du lieu lon va tai nguyen tinh toan tot hon.

### 2. Nhuoc diem cua cach lam nay la gi?

Tra loi:

> He thong phu thuoc vao chat luong tach nen, anh sang va goc chup. Neu anh query khac nhieu so voi tap train, mask va dac trung co the sai. Dac trung thu cong cung kem linh hoat hon deep learning.

### 3. FAISS co phai model phan loai khong?

Tra loi:

> Khong. FAISS la thu vien tim kiem nearest neighbor. Em dung FAISS de tim cac anh train gan anh query nhat. Viec du doan nhan duoc thuc hien sau do bang weighted voting.

### 4. K trong Elbow co phai top-k khong?

Tra loi:

> Khong. K trong Elbow la so cum IVF, tuc `nlist`. Con top-k la so luong ket qua gan nhat tra ve khi truy van.

### 5. K trong Elbow co phai so lop khong?

Tra loi:

> Khong. Dataset co 12 lop, nhung K = 4 o day la so cum chia khong gian vector trong FAISS IVF. No phuc vu tang toc tim kiem, khong phai nhan phan loai.

### 6. Vi sao phai chuan hoa z-score?

Tra loi:

> Vi cac dac trung co thang do khac nhau. Neu khong chuan hoa, cac dac trung co gia tri lon nhu area se chi phoi khoang cach L2. Z-score giup cac chieu dac trung can bang hon.

### 7. Vi sao chi fit scaler tren train?

Tra loi:

> De tranh ro ri du lieu. Valid, test va anh query phai duoc chuan hoa bang mean/std hoc tu train, giong nhu du lieu moi trong thuc te.

### 8. Confidence trong app co phai xac suat khong?

Tra loi:

> Khong phai xac suat tuyet doi. Do la do tin cay tuong doi tinh tu trong so khoang cach cua cac ket qua top-k.

### 9. Neu upload anh khong phai la cay thi sao?

Tra loi:

> He thong van se tim anh gan nhat trong FAISS, nhung ket qua co the khong co y nghia vi chua co co che reject anh ngoai mien du lieu. Co the cai tien bang nguong distance hoac them lop unknown.

### 10. Tai sao MySQL khong luu HOG va LBP?

Tra loi:

> HOG va LBP da duoc luu trong CSV va FAISS index de phuc vu tim kiem. MySQL chi dung de luu metadata can hien thi. Neu luu toan bo 349 chieu vao MySQL, bang se rat rong va khong can thiet cho giao dien.

### 11. Tai sao dung Otsu?

Tra loi:

> Otsu tu dong tim nguong tach hai nhom pixel dua tren phan bo histogram, nen khong can dat nguong thu cong cho tung anh. Dieu nay phu hop khi anh co dieu kien sang va nen khac nhau.

### 12. Tai sao dung Canny?

Tra loi:

> Canny giup lay thong tin canh va duong bien. Voi la cay, canh co the phan anh vien la, gan la va do phuc tap cua cau truc be mat.

### 13. Tai sao dung weighted voting?

Tra loi:

> Vi trong top-k, khong phai anh nao cung quan trong nhu nhau. Anh co khoang cach nho hon nen co trong so lon hon vi no giong query hon.

### 14. Neu FAISS tra ve distance lon thi sao?

Tra loi:

> Distance lon nghia la anh query khong gan voi cac anh trong tap train. Co the dung nguong distance de canh bao ket qua khong dang tin hoac anh ngoai mien du lieu.

### 15. He thong co the cai tien nhu the nao?

Tra loi:

> Co the cai tien bang cach them buoc danh gia accuracy tren valid/test, luu them metric, them nguong reject anh ngoai mien, cai thien tach nen bang segmentation tot hon, hoac dung CNN/transfer learning de trich dac trung manh hon.

## 17. Diem can nho de khong bi bat be

1. FAISS khong phai model phan loai.
2. K Elbow khong phai top-k va cung khong phai so lop.
3. Z-score chi fit tren train.
4. FAISS index chi chua train.
5. MySQL luu metadata hien thi, khong luu day du HOG/LBP.
6. CSV va FAISS moi la noi luu vector dac trung day du.
7. Confidence trong app la tuong doi, khong phai xac suat that.
8. Neu anh ngoai mien du lieu, he thong van tra ket qua gan nhat nhung co the khong dang tin.

