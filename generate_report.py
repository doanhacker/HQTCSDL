"""Script tạo báo cáo Word (.docx) cho dự án Leaf Feature Pipeline."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor


ARTIFACTS = Path("artifacts")
OUTPUT = Path("BaoCao_LeafSearch_v2.docx")


# ── Helpers ────────────────────────────────────────────────────────────────────

def set_heading_color(paragraph, color: RGBColor):
    for run in paragraph.runs:
        run.font.color.rgb = color


def add_table_border(table):
    """Thêm border cho toàn bộ table."""
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    tblBorders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "888888")
        tblBorders.append(el)
    tblPr.append(tblBorders)
    if tbl.tblPr is None:
        tbl.append(tblPr)


def shade_row(row, hex_color: str):
    for cell in row.cells:
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)


def add_code_block(doc: Document, code: str):
    """Thêm block code với nền xám, font Courier."""
    for line in code.strip().split("\n"):
        p = doc.add_paragraph(line)
        p.style = doc.styles["Normal"]
        for run in p.runs:
            run.font.name = "Courier New"
            run.font.size = Pt(10)
        pPr = p._p.get_or_add_pPr()
        pBdr = OxmlElement("w:pBdr")
        for edge in ("top", "left", "bottom", "right"):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:space"), "4" if edge in ("top", "bottom") else "8")
            el.set(qn("w:color"), "AAAAAA")
            pBdr.append(el)
        pPr.append(pBdr)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "F4F4F4")
        pPr.append(shd)


# ── Document build ─────────────────────────────────────────────────────────────

def build(doc: Document):
    GREEN = RGBColor(0x1F, 0x4E, 0x3D)
    BLUE  = RGBColor(0x1A, 0x55, 0x99)

    # ── Cover ──────────────────────────────────────────────────────────────────
    title = doc.add_heading("Báo Cáo Dự Án", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_heading_color(title, GREEN)

    sub = doc.add_heading("Hệ Thống Tìm Kiếm Ảnh Lá Cây Dựa Trên Đặc Trưng", level=1)
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_heading_color(sub, BLUE)

    doc.add_paragraph()
    info_lines = [
        "Môn học  : Hệ Cơ Sở Dữ Liệu",
        "Ngày báo cáo : 04 / 05 / 2026",
    ]
    for line in info_lines:
        p = doc.add_paragraph(line)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_page_break()

    # ── 1. Giới thiệu bài toán ─────────────────────────────────────────────────
    h = doc.add_heading("1. Giới Thiệu Bài Toán", level=1)
    set_heading_color(h, GREEN)

    doc.add_paragraph(
        "Bài toán đặt ra là xây dựng một hệ thống có khả năng nhận vào một ảnh lá cây "
        "bất kỳ, sau đó tìm và trả về các ảnh lá cây trong cơ sở dữ liệu có nội dung "
        "hình ảnh tương đồng nhất. Đây là bài toán Content-Based Image Retrieval (CBIR) "
        "ứng dụng trong nhận dạng thực vật."
    )

    doc.add_heading("1.1. Mục tiêu", level=2)
    goals = [
        "Trích xuất vector đặc trưng đặc thù cho ảnh lá cây (màu sắc, hình dạng, texture).",
        "Chuẩn hóa dữ liệu và lưu trữ vector vào chỉ mục FAISS IVF để tìm kiếm nhanh.",
        "Lưu metadata vào MySQL/XAMPP để phục vụ truy vấn chi tiết.",
        "Cung cấp giao diện web (Streamlit) cho phép upload ảnh và xem kết quả top-5.",
    ]
    for g in goals:
        doc.add_paragraph(g, style="List Bullet")

    doc.add_heading("1.2. Tập dữ liệu", level=2)
    doc.add_paragraph(
        "Dữ liệu sử dụng là bộ ảnh lá cây gồm 12 loài, được chia thành 3 tập "
        "train / valid / test."
    )

    tbl = doc.add_table(rows=1, cols=4)
    add_table_border(tbl)
    hdr = tbl.rows[0].cells
    for i, text in enumerate(["Tập dữ liệu", "Số ảnh", "Số lớp", "Số chiều đặc trưng"]):
        hdr[i].text = text
        hdr[i].paragraphs[0].runs[0].bold = True
    shade_row(tbl.rows[0], "D6E4FF")

    for row_data in [
        ("Train", "4 274", "12", "349"),
        ("Valid", "110",   "12", "349"),
        ("Test",  "110",   "12", "349"),
    ]:
        row = tbl.add_row()
        for i, val in enumerate(row_data):
            row.cells[i].text = val

    doc.add_paragraph()
    doc.add_paragraph("Danh sách 12 lớp:", style="Normal")
    classes = [
        "Alstonia Scholaris", "Arjun", "Bael", "Basil",
        "Chinar", "Gauva", "Jamun", "Jatropha",
        "Lemon", "Mango", "Pomegranate", "Pongamia Pinnata",
    ]
    doc.add_paragraph(", ".join(classes))

    doc.add_page_break()

    # ── 2. Xây dựng bộ thuộc tính đặc trưng ───────────────────────────────────
    h = doc.add_heading("2. Xây Dựng Bộ Thuộc Tính Đặc Trưng", level=1)
    set_heading_color(h, GREEN)

    doc.add_paragraph(
        "Sau khi đã thu thập và tổ chức dữ liệu ảnh lá cây thành các tập train/valid/test, "
        "nhóm tiến hành xây dựng bộ thuộc tính đặc trưng để biến mỗi ảnh thành một vector số "
        "có thể xử lý bằng các thuật toán học máy và truy hồi ảnh."
    )

    h21 = doc.add_heading("2.1. Dữ liệu đầu vào cho bước trích đặc trưng", level=2)
    set_heading_color(h21, BLUE)
    doc.add_paragraph(
        "Mỗi ảnh được đọc dưới dạng ma trận màu BGR, sau đó chuẩn hóa về kích thước 256x256 "
        "pixel nhằm đảm bảo toàn bộ ảnh có cùng định dạng trước khi trích đặc trưng."
    )
    doc.add_paragraph(
        "Việc chuẩn hóa kích thước giúp các đặc trưng hình học và gradient (đặc biệt là HOG) "
        "ổn định hơn, đồng thời tăng tính nhất quán giữa tập train và ảnh truy vấn."
    )

    h22 = doc.add_heading("2.2. Quy trình xây dựng bộ đặc trưng", level=2)
    set_heading_color(h22, BLUE)
    pipeline_steps = [
        "Tiền xử lý ảnh: Gaussian Blur -> chuyển BGR sang HSV -> tách nền bằng Otsu -> làm sạch mask bằng morphology.",
        "Tạo các dữ liệu trung gian: ảnh xám, mask vùng lá, bản đồ cạnh Canny.",
        "Trích xuất các nhóm đặc trưng theo thứ tự cố định: HSV, GLCM, LBP, HOG, Shape, Edge, Foreground.",
        "Ghép các nhóm thành vector đặc trưng 349 chiều cho từng ảnh.",
        "Chuẩn hóa toàn bộ vector bằng z-score dựa trên tham số của tập train.",
        "Lưu đặc trưng đã chuẩn hóa và metadata vào thư mục artifacts để phục vụ FAISS và truy vấn sau này.",
    ]
    for s in pipeline_steps:
        doc.add_paragraph(s, style="List Number")

    h23 = doc.add_heading("2.3. Thành phần bộ thuộc tính 349 chiều", level=2)
    set_heading_color(h23, BLUE)
    comp = [
        ("HSV", "6", "mean_h, mean_s, mean_v, std_h, std_s, std_v"),
        ("GLCM", "3", "glcm_contrast, glcm_energy, glcm_homogeneity"),
        ("LBP", "10", "lbp_uniform_0 ... lbp_uniform_9"),
        ("HOG", "324", "hog_0 ... hog_323"),
        ("Shape", "3", "area, perimeter, aspect_ratio"),
        ("Canny Edge", "2", "canny_edge_pixels, canny_edge_density"),
        ("Foreground", "1", "foreground_ratio"),
        ("TONG", "349", ""),
    ]
    tbl_feat = doc.add_table(rows=1, cols=3)
    add_table_border(tbl_feat)
    for i, txt in enumerate(["Nhom", "So chieu", "Thuoc tinh"]):
        tbl_feat.rows[0].cells[i].text = txt
        tbl_feat.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    shade_row(tbl_feat.rows[0], "D6E4FF")
    for name, dims, detail in comp:
        row = tbl_feat.add_row()
        row.cells[0].text = name
        row.cells[1].text = dims
        row.cells[2].text = detail
        if name == "TONG":
            shade_row(row, "E8F5E9")
            for cell in row.cells:
                if cell.paragraphs[0].runs:
                    cell.paragraphs[0].runs[0].bold = True

    doc.add_paragraph("Vector đặc trưng tổng hợp cho mỗi ảnh:")
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        v = [HSV(6), GLCM(3), LBP(10), HOG(324), Shape(3), Edge(2), Foreground(1)]")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    h24 = doc.add_heading("2.4. Chuẩn hóa và lưu kết quả", level=2)
    set_heading_color(h24, BLUE)
    doc.add_paragraph(
        "Do các nhóm đặc trưng có thang đo khác nhau, hệ thống chuẩn hóa z-score theo từng "
        "chiều bằng tham số học từ tập train trước khi đưa vào FAISS."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        z_j = (x_j - mu_j) / sigma_j")
    run.font.name = "Courier New"
    run.font.size = Pt(11)
    doc.add_paragraph(
        "Các tệp kết quả được lưu vào artifacts gồm: train_features_zscore.csv, "
        "valid_features_zscore.csv, test_features_zscore.csv và zscore_scaler.json."
    )

    h25 = doc.add_heading("2.5. Ý nghĩa của bước xây dựng bộ đặc trưng", level=2)
    set_heading_color(h25, BLUE)
    benefits = [
        "Biến đổi dữ liệu ảnh thô thành biểu diễn số có cấu trúc, phù hợp cho KMeans và FAISS.",
        "Kết hợp thông tin màu sắc, texture và hình dạng giúp tăng khả năng phân biệt giữa các loài lá.",
        "Đảm bảo ảnh train và ảnh truy vấn đi qua cùng một pipeline, tăng độ tin cậy của kết quả tìm kiếm.",
    ]
    for b in benefits:
        doc.add_paragraph(b, style="List Bullet")

    doc.add_page_break()

    # ── 3. Sơ đồ luồng xử lý ──────────────────────────────────────────────────
    h = doc.add_heading("3. Sơ Đồ Luồng Xử Lý", level=1)
    set_heading_color(h, GREEN)

    doc.add_heading("3.1. Luồng xây dựng CSDL (Training Pipeline)", level=2)
    steps_build = [
        "Thu thập bộ dữ liệu ảnh lá cây (4 274 ảnh train, 12 lớp).",
        "Chuẩn hóa ảnh về kích thước 256×256 pixel.",
        "Tiền xử lý: Gaussian Blur (5×5) → chuyển RGB→HSV → tách nền bằng Otsu trên kênh Saturation.",
        "Trích xuất 349 đặc trưng (màu sắc, hình dạng, GLCM texture, LBP, Canny edge, HOG).",
        "Chuẩn hóa z-score theo tập train, lưu tham số vào zscore_scaler.json.",
        "Chọn K tối ưu bằng phương pháp Elbow (K = 4).",
        "Xây dựng chỉ mục FAISS IVF với nlist = K, lưu file .faiss.",
        "Lưu mapping faiss_id → metadata vào CSV; đẩy metadata vào MySQL (tùy chọn).",
    ]
    for s in steps_build:
        doc.add_paragraph(s, style="List Number")

    doc.add_heading("3.2. Luồng tìm kiếm ảnh mới (Query Pipeline)", level=2)
    steps_query = [
        "Người dùng upload ảnh lá cây mới qua giao diện Streamlit.",
        "Tiền xử lý ảnh truy vấn (giống pipeline training).",
        "Trích xuất vector đặc trưng 349 chiều.",
        "Chuẩn hóa z-score bằng tham số đã lưu từ tập train.",
        "Tìm kiếm top-5 ảnh gần nhất trong chỉ mục FAISS IVF (khoảng cách L2, nprobe = 3).",
        "Dự đoán nhãn bằng weighted voting dựa trên khoảng cách.",
        "Hiển thị ảnh kết quả, nhãn dự đoán và độ tin cậy trên giao diện.",
    ]
    for s in steps_query:
        doc.add_paragraph(s, style="List Number")

    doc.add_page_break()

    # ── 4. Pipeline trích xuất đặc trưng ──────────────────────────────────────
    h = doc.add_heading("4. Các Thuộc Tính và Kỹ Thuật Sử Dụng", level=1)
    set_heading_color(h, GREEN)

    # ── 4.1. Tiền xử lý ───────────────────────────────────────────────────────
    h = doc.add_heading("4.1. Tiền Xử Lý", level=2)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "Trong hệ thống của nhóm, khi người dùng cung cấp một file ảnh (thường ở định dạng "
        ".jpg hoặc .png), hệ thống nạp toàn bộ dữ liệu ảnh vào bộ nhớ và thực hiện các bước "
        "tiền xử lý để chuẩn bị cho việc trích xuất đặc trưng."
    )
    doc.add_paragraph(
        "Cụ thể, đầu tiên ảnh được đọc vào dưới dạng ma trận BGR với kích thước 256×256 pixel "
        "thông qua hàm cv2.imread() và cv2.resize(). Sau đó hệ thống thực hiện lần lượt các bước sau:"
    )

    doc.add_paragraph(
        "Bước 1 – Làm mịn ảnh bằng Gaussian Blur (5×5): "
        "Áp dụng bộ lọc Gaussian kích thước nhân 5×5 lên toàn bộ ảnh nhằm giảm nhiễu và các chi "
        "tiết nhỏ không cần thiết, giúp các bước xử lý tiếp theo ổn định hơn.",
        style="List Number"
    )
    doc.add_paragraph(
        "Bước 2 – Chuyển không gian màu BGR → HSV: "
        "Không gian màu HSV (Hue – Saturation – Value) tách biệt thông tin màu sắc (H) khỏi độ "
        "sáng (V), giúp việc tách nền lá cây ít bị ảnh hưởng bởi điều kiện ánh sáng hơn so với "
        "BGR hay RGB.",
        style="List Number"
    )
    doc.add_paragraph(
        "Bước 3 – Tách nền bằng ngưỡng Otsu trên kênh Saturation: "
        "Kênh Saturation (S) trong HSV có giá trị cao tại vùng lá (màu sắc rõ) và thấp tại nền "
        "trắng/xám. Thuật toán Otsu tự động tìm ngưỡng tối ưu để phân tách vùng lá và nền, kết "
        "quả là một mặt nạ nhị phân (mask) 0/255.",
        style="List Number"
    )
    doc.add_paragraph(
        "Bước 4 – Fallback sang kênh Value (V) khi lá nhạt màu: "
        "Nếu tỉ lệ pixel được chọn trong mask nhỏ hơn 5% diện tích ảnh (lá quá nhạt, kênh S không "
        "phân biệt được), hệ thống chuyển sang dùng kênh V với ngưỡng Otsu đảo (THRESH_BINARY_INV) "
        "để tách vùng tối (lá) khỏi nền sáng.",
        style="List Number"
    )
    doc.add_paragraph(
        "Bước 5 – Morphological Open và Close (kernel 5×5): "
        "Phép mở (Open = erosion → dilation) loại bỏ các điểm nhiễu nhỏ rời rạc trên mask. "
        "Phép đóng (Close = dilation → erosion) lấp đầy các lỗ hổng nhỏ bên trong vùng lá. "
        "Cả hai phép đều dùng kernel hình vuông 5×5.",
        style="List Number"
    )
    doc.add_paragraph(
        "Việc chuẩn hóa tiền xử lý này giúp: (1) đảm bảo tất cả ảnh đầu vào có cùng kích thước "
        "256×256; (2) tách biệt vùng lá cần phân tích ra khỏi phần nền; "
        "(3) giảm ảnh hưởng của nhiễu và điều kiện chụp ảnh khác nhau lên các đặc trưng được trích xuất."
    )

    doc.add_paragraph()

    # ── 4.2. Trích xuất đặc trưng ─────────────────────────────────────────────
    h = doc.add_heading(
        "4.2. Trích Rút Đặc Trưng Màu Sắc, Texture, Hình Dạng và Gradient", level=2
    )
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "Sau bước tiền xử lý, hệ thống trích xuất 349 đặc trưng từ mỗi ảnh lá cây, "
        "gồm 7 nhóm đặc trưng: màu sắc HSV, GLCM texture, LBP texture, hình dạng contour, "
        "Canny edge, tỉ lệ foreground và HOG gradient."
    )

    # ── 4.2.1. Màu sắc HSV ────────────────────────────────────────────────────
    h = doc.add_heading("4.2.1. Trích Rút Đặc Trưng Màu Sắc HSV (6 chiều)", level=3)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "Để biểu diễn thông tin màu sắc của lá cây, hệ thống tính giá trị thống kê "
        "trên từng kênh H, S, V của vùng lá (vùng có mask > 0)."
    )
    doc.add_paragraph(
        "Với mỗi kênh c ∈ {H, S, V}, gọi {x₁, x₂, …, xₙ} là tập hợp n pixel thuộc vùng lá "
        "trên kênh đó. Hai đặc trưng được tính:"
    )

    doc.add_paragraph(
        "Giá trị trung bình (mean):",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        μ_c  =  (1/N) · Σᵢ xᵢ")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Độ lệch chuẩn (standard deviation):",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        σ_c  =  √[ (1/N) · Σᵢ (xᵢ − μ_c)² ]")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Kết quả thu được 6 giá trị: mean_h, mean_s, mean_v, std_h, std_s, std_v. "
        "Các đặc trưng này phản ánh màu sắc đặc trưng và độ đồng đều màu của từng loài lá."
    )

    # ── 4.2.2. GLCM ───────────────────────────────────────────────────────────
    h = doc.add_heading("4.2.2. Trích Rút Đặc Trưng Texture bằng GLCM (3 chiều)", level=3)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "GLCM (Gray-Level Co-occurrence Matrix – Ma trận đồng xuất hiện mức xám) mô tả "
        "mối quan hệ không gian giữa các cặp pixel trong ảnh xám, qua đó nắm bắt được "
        "cấu trúc texture của bề mặt lá."
    )
    doc.add_paragraph(
        "Để xây dựng GLCM, hệ thống thực hiện các bước:"
    )
    doc.add_paragraph(
        "Trích vùng ROI: Cắt bounding-box nhỏ nhất bao quanh toàn bộ vùng mask "
        "(min/max của tọa độ pixel thuộc lá), thu được ảnh xám vùng lá.",
        style="List Number"
    )
    doc.add_paragraph(
        "Lượng hóa mức xám: Chia các giá trị xám (0–255) thành 32 mức bằng phép "
        "quantized = gray // 8, giảm kích thước ma trận GLCM và tăng tốc tính toán.",
        style="List Number"
    )
    doc.add_paragraph(
        "Xây dựng GLCM: Đếm số lần cặp pixel (i, j) xuất hiện cạnh nhau theo góc 0° "
        "(hướng ngang) với khoảng cách 1 pixel. Ma trận được đối xứng hóa và chuẩn hóa "
        "(normed=True) thành phân phối xác suất P(i, j).",
        style="List Number"
    )
    doc.add_paragraph(
        "Tính 3 đặc trưng từ GLCM:",
        style="List Number"
    )

    doc.add_paragraph(
        "Độ tương phản (Contrast) – đo mức độ biến thiên cục bộ của cường độ sáng:",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        Contrast  =  Σᵢ Σⱼ (i − j)² · P(i,j)")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Năng lượng (Energy) – đo mức độ đồng đều của texture (texture đồng đều → Energy cao):",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        Energy  =  Σᵢ Σⱼ P(i,j)²")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Tính đồng nhất (Homogeneity) – đo mức độ gần đường chéo của GLCM:",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        Homogeneity  =  Σᵢ Σⱼ P(i,j) / (1 + |i − j|)")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Ba giá trị glcm_contrast, glcm_energy, glcm_homogeneity tạo thành 3 chiều đặc trưng "
        "texture, giúp phân biệt các lá có cấu trúc bề mặt khác nhau (nhẵn, gân lá rõ, sần sùi)."
    )

    # ── 4.2.3. LBP ────────────────────────────────────────────────────────────
    h = doc.add_heading("4.2.3. Trích Rút Đặc Trưng Texture bằng LBP (10 chiều)", level=3)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "LBP (Local Binary Pattern – Mẫu nhị phân cục bộ) là bộ mô tả texture cục bộ "
        "không nhạy cảm với thay đổi độ sáng đơn điệu (monotonic illumination change)."
    )
    doc.add_paragraph(
        "Với mỗi pixel p có cường độ sáng g_c, hệ thống xét P = 8 điểm lân cận trên vòng "
        "tròn bán kính R = 1. Giá trị LBP được tính:"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        LBP(p)  =  Σₙ₌₀^{P−1}  s(gₙ − g_c) · 2ⁿ")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "trong đó s(x) = 1 nếu x ≥ 0, s(x) = 0 nếu x < 0."
    )
    doc.add_paragraph(
        "Phương pháp 'uniform' được sử dụng: chỉ giữ lại các pattern có số lần chuyển đổi "
        "0↔1 không quá 2 (gọi là uniform pattern). Với P = 8, có P+2 = 10 bins trong histogram. "
        "Hệ thống tính histogram LBP trên toàn bộ pixel thuộc vùng lá (mask > 0), "
        "sau đó chuẩn hóa thành phân phối xác suất (density=True)."
    )
    doc.add_paragraph(
        "Kết quả là vector 10 chiều lbp_uniform_0 … lbp_uniform_9, biểu diễn phân bố "
        "các micro-pattern cục bộ trên bề mặt lá."
    )

    # ── 4.2.4. Hình dạng ──────────────────────────────────────────────────────
    h = doc.add_heading("4.2.4. Trích Rút Đặc Trưng Hình Dạng Contour (3 chiều)", level=3)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "Hình dạng của lá cây (tròn, bầu dục, dài hẹp…) là đặc trưng quan trọng để phân "
        "biệt các loài. Hệ thống phân tích contour lớn nhất trên mask nhị phân."
    )
    doc.add_paragraph(
        "Quá trình thực hiện:"
    )
    doc.add_paragraph(
        "Tìm tất cả contour ngoài (RETR_EXTERNAL) trên mask bằng thuật toán "
        "CHAIN_APPROX_SIMPLE (chỉ lưu điểm đầu/cuối đoạn thẳng).",
        style="List Number"
    )
    doc.add_paragraph(
        "Chọn contour có diện tích lớn nhất làm contour đại diện cho lá.",
        style="List Number"
    )
    doc.add_paragraph(
        "Tính 3 đặc trưng:",
        style="List Number"
    )

    doc.add_paragraph(
        "Diện tích (area): Số pixel bên trong contour lá.",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        area  =  cv2.contourArea(contour)")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Chu vi (perimeter): Tổng chiều dài đường biên của lá.",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        perimeter  =  cv2.arcLength(contour, closed=True)")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Tỉ lệ cạnh (aspect_ratio): Tỉ lệ chiều rộng / chiều cao của bounding-box bao quanh lá.",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        aspect_ratio  =  w / h       (w, h từ cv2.boundingRect)")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Ba giá trị area, perimeter, aspect_ratio biểu diễn kích thước và hình dạng tổng thể "
        "của lá, giúp phân biệt các loài có hình dạng khác nhau rõ rệt."
    )

    # ── 4.2.5. Canny Edge ─────────────────────────────────────────────────────
    h = doc.add_heading("4.2.6. Trích Rút Đặc Trưng Cạnh Canny (2 chiều)", level=3)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "Thuật toán Canny phát hiện cạnh (viền) trong ảnh xám bằng cách tìm các vùng "
        "có gradient cường độ sáng thay đổi đột ngột. Hệ thống áp dụng Canny với "
        "ngưỡng dưới threshold1 = 100 và ngưỡng trên threshold2 = 200 lên ảnh xám "
        "đã qua Gaussian Blur."
    )
    doc.add_paragraph(
        "Quá trình thực hiện:"
    )
    doc.add_paragraph(
        "Tính bản đồ cạnh Canny trên toàn bộ ảnh xám 256×256.",
        style="List Number"
    )
    doc.add_paragraph(
        "Lọc chỉ lấy các pixel cạnh nằm trong vùng lá (mask > 0).",
        style="List Number"
    )
    doc.add_paragraph(
        "Tính 2 đặc trưng:",
        style="List Number"
    )

    doc.add_paragraph(
        "Số pixel cạnh (canny_edge_pixels): Tổng số pixel có giá trị khác 0 trong vùng lá.",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        edge_pixels  =  count_nonzero(edges[mask > 0])")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Mật độ cạnh (canny_edge_density): Tỉ lệ pixel cạnh trên tổng pixel vùng lá.",
        style="List Bullet"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        edge_density  =  edge_pixels / total_pixels_in_mask")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Mật độ cạnh cao tương ứng với lá có nhiều gân, răng cưa hoặc viền phức tạp; "
        "ngược lại mật độ thấp tương ứng với lá có viền trơn, nhẵn."
    )

    # ── 4.2.6. Foreground ratio ────────────────────────────────────────────────
    h = doc.add_heading("4.2.6. Tỉ Lệ Foreground (1 chiều)", level=3)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "Tỉ lệ foreground (foreground_ratio) biểu diễn diện tích tương đối của lá so với "
        "toàn bộ ảnh, phản ánh kích thước lá trong khung hình."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        foreground_ratio  =  count_nonzero(mask) / (256 × 256)")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Giá trị này nằm trong khoảng (0, 1]. Lá chiếm phần lớn ảnh sẽ có foreground_ratio "
        "cao, ngược lại lá nhỏ hoặc bị che khuất sẽ có giá trị thấp."
    )

    # ── 4.2.7. HOG ────────────────────────────────────────────────────────────
    h = doc.add_heading("4.2.7. Trích Rút Đặc Trưng Gradient bằng HOG (324 chiều)", level=3)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "HOG (Histogram of Oriented Gradients) mô tả phân bố hướng gradient trong các vùng "
        "cục bộ của ảnh, nắm bắt được cấu trúc hình dạng chi tiết và texture của lá cây."
    )
    doc.add_paragraph(
        "Hệ thống thực hiện các bước:"
    )
    doc.add_paragraph(
        "Áp mask lên ảnh xám: Các pixel ngoài vùng lá được đặt về 0 "
        "(cv2.bitwise_and), đảm bảo HOG chỉ mô tả vùng lá thực sự.",
        style="List Number"
    )
    doc.add_paragraph(
        "Resize về HOG_IMAGE_SIZE = 32×32: Chuẩn hóa kích thước đầu vào "
        "cho HOG, giúp đặc trưng bất biến với kích thước lá trong ảnh.",
        style="List Number"
    )
    doc.add_paragraph(
        "Tính HOG với các tham số:",
        style="List Number"
    )

    hog_params = [
        ("HOG_ORIENTATIONS = 9",     "Chia gradient thành 9 bin hướng (0°–180°, mỗi bin 20°)."),
        ("HOG_PIXELS_PER_CELL = (8, 8)", "Mỗi cell gồm 8×8 pixel, ảnh 32×32 có 4×4 = 16 cells."),
        ("HOG_CELLS_PER_BLOCK = (2, 2)", "Mỗi block gồm 2×2 cells = 4 cells, chuẩn hóa L2-Hys."),
        ("block_norm = 'L2-Hys'",    "Chuẩn hóa L2 rồi clipping giá trị > 0.2, tăng tính bất biến sáng."),
    ]
    tbl_hog = doc.add_table(rows=1, cols=2)
    add_table_border(tbl_hog)
    tbl_hog.rows[0].cells[0].text = "Tham số"
    tbl_hog.rows[0].cells[1].text = "Ý nghĩa"
    for c in tbl_hog.rows[0].cells:
        c.paragraphs[0].runs[0].bold = True
    shade_row(tbl_hog.rows[0], "D6E4FF")
    for param, meaning in hog_params:
        r = tbl_hog.add_row()
        r.cells[0].text = param
        r.cells[1].text = meaning

    doc.add_paragraph()
    doc.add_paragraph(
        "Số chiều HOG = số blocks × cells per block × orientations. "
        "Với ảnh 32×32, cell 8×8, block 2×2, bước trượt 1 cell:"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run(
        "        Số blocks theo mỗi chiều  =  (4 − 2 + 1) = 3  →  3×3 = 9 blocks\n"
        "        Số chiều HOG  =  9 blocks × 4 cells/block × 9 orientations  =  324 chiều"
    )
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "324 giá trị HOG biểu diễn cấu trúc gradient chi tiết của vùng lá, "
        "là thành phần chiếm tỉ trọng lớn nhất (324/349 ≈ 93%) trong vector đặc trưng tổng hợp."
    )

    doc.add_paragraph()
    # Bảng tổng hợp
    h = doc.add_heading("4.3. Tổng Hợp Vector Đặc Trưng 349 Chiều", level=2)
    set_heading_color(h, BLUE)

    doc.add_paragraph(
        "Sau khi trích xuất xong tất cả các nhóm, hệ thống ghép nối (concatenate) "
        "thành một vector đặc trưng duy nhất 349 chiều theo thứ tự cố định:"
    )

    summary_groups = [
        ("Màu sắc HSV",  "6",   "mean_h, mean_s, mean_v, std_h, std_s, std_v"),
        ("GLCM Texture", "3",   "glcm_contrast, glcm_energy, glcm_homogeneity"),
        ("LBP Texture",  "10",  "lbp_uniform_0 … lbp_uniform_9"),
        ("HOG Gradient", "324", "hog_0 … hog_323"),
        ("Hình dạng",    "3",   "area, perimeter, aspect_ratio"),
        ("Canny Edge",   "2",   "canny_edge_pixels, canny_edge_density"),
        ("Foreground",   "1",   "foreground_ratio"),
        ("TỔNG",         "349", ""),
    ]
    tbl_sum = doc.add_table(rows=1, cols=3)
    add_table_border(tbl_sum)
    for i, txt in enumerate(["Nhóm đặc trưng", "Số chiều", "Tên đặc trưng"]):
        tbl_sum.rows[0].cells[i].text = txt
        tbl_sum.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    shade_row(tbl_sum.rows[0], "D6E4FF")
    for name, dims, cols_text in summary_groups:
        row = tbl_sum.add_row()
        row.cells[0].text = name
        row.cells[1].text = dims
        row.cells[2].text = cols_text
        if name == "TỔNG":
            shade_row(row, "E8F5E9")
            for cell in row.cells:
                if cell.paragraphs[0].runs:
                    cell.paragraphs[0].runs[0].bold = True

    doc.add_paragraph()

    h44 = doc.add_heading("4.4. Chuẩn Hóa Z-Score", level=2)
    set_heading_color(h44, BLUE)
    doc.add_paragraph(
        "Trước khi đưa vào chỉ mục FAISS, vector 349 chiều được chuẩn hóa z-score "
        "để đảm bảo các đặc trưng có tầm quan trọng đồng đều, tránh các đặc trưng "
        "có giá trị lớn (như area, hog_*) lấn át các đặc trưng nhỏ (như foreground_ratio)."
    )
    doc.add_paragraph(
        "Với mỗi chiều đặc trưng j, tham số chuẩn hóa μⱼ và σⱼ được tính từ tập train "
        "và lưu vào artifacts/zscore_scaler.json. Khi chuẩn hóa một vector mới:"
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        z_j  =  (x_j − μ_j) / σ_j")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Quy tắc này áp dụng nhất quán cho cả tập train/valid/test và cho ảnh truy vấn "
        "mới, đảm bảo không có data leakage (tham số μ, σ chỉ được tính từ tập train)."
    )

    doc.add_paragraph()

    h45 = doc.add_heading("4.5. Xây Dựng Bộ Thuộc Tính Đặc Trưng Theo Hệ Thống", level=2)
    set_heading_color(h45, BLUE)
    doc.add_paragraph(
        "Trong hệ thống tìm kiếm ảnh lá cây, mỗi ảnh đầu vào được biểu diễn bởi một vector "
        "đặc trưng cố định 349 chiều. Vector này mô tả đồng thời màu sắc, kết cấu bề mặt và "
        "hình dạng hình học của lá cây để phục vụ phân cụm và truy hồi ảnh tương tự."
    )

    h451 = doc.add_heading("4.5.1. Cấu trúc vector đặc trưng 349 chiều", level=3)
    set_heading_color(h451, BLUE)
    doc.add_paragraph("Cấu trúc vector đặc trưng được tổ chức như sau:")
    structure_rows = [
        ("HSV", "6", "mean_h, mean_s, mean_v, std_h, std_s, std_v"),
        ("GLCM", "3", "glcm_contrast, glcm_energy, glcm_homogeneity"),
        ("LBP", "10", "lbp_uniform_0 ... lbp_uniform_9"),
        ("Shape", "3", "area, perimeter, aspect_ratio"),
        ("Canny Edge", "2", "canny_edge_pixels, canny_edge_density"),
        ("Foreground", "1", "foreground_ratio"),
        ("HOG", "324", "hog_0 ... hog_323"),
        ("TONG", "349", ""),
    ]
    tbl_structure = doc.add_table(rows=1, cols=3)
    add_table_border(tbl_structure)
    for i, txt in enumerate(["Nhom", "So chieu", "Thanh phan"]):
        tbl_structure.rows[0].cells[i].text = txt
        tbl_structure.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    shade_row(tbl_structure.rows[0], "D6E4FF")
    for name, dims, detail in structure_rows:
        row = tbl_structure.add_row()
        row.cells[0].text = name
        row.cells[1].text = dims
        row.cells[2].text = detail
        if name == "TONG":
            shade_row(row, "E8F5E9")
            for cell in row.cells:
                if cell.paragraphs[0].runs:
                    cell.paragraphs[0].runs[0].bold = True

    doc.add_paragraph("Vector tong hop:")
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        v = [HSV(6), GLCM(3), LBP(10), Shape(3), Edge(2), Foreground(1), HOG(324)]")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    h452 = doc.add_heading("4.5.2. Nhom thuoc tinh mau sac HSV (6 chieu)", level=3)
    set_heading_color(h452, BLUE)
    doc.add_paragraph(
        "Tren tung kenh H, S, V, he thong tinh gia tri trung binh va do lech chuan tren vung la "
        "(mask > 0). Hai thong ke nay phan anh tong quan mau la va do dong deu mau tren be mat la."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        mu = (1/N) * sum(x_i),     sigma = sqrt((1/N) * sum((x_i - mu)^2))")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    h453 = doc.add_heading("4.5.3. Nhom ket cau GLCM (3 chieu)", level=3)
    set_heading_color(h453, BLUE)
    doc.add_paragraph(
        "Anh xam vung la duoc luong hoa ve 32 muc xam, sau do xay dung GLCM voi distance = 1, "
        "angle = 0 do, symmetric = True, normed = True. Tu do trich 3 thong so contrast, energy "
        "va homogeneity de mo ta muc do nhan-sen cua texture."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        Contrast = sum((i-j)^2 * P(i,j));  Energy = sum(P(i,j)^2);  Homogeneity = sum(P(i,j)/(1+|i-j|))")
    run.font.name = "Courier New"
    run.font.size = Pt(10)

    h454 = doc.add_heading("4.5.4. Nhom ket cau LBP uniform (10 chieu)", level=3)
    set_heading_color(h454, BLUE)
    doc.add_paragraph(
        "LBP duoc tinh voi P = 8, R = 1, method = uniform tren anh xam. Histogram LBP duoc tinh "
        "tren vung mask va chuan hoa theo mat do xac suat, tao ra 10 bins (P + 2)."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        LBP(p) = sum( s(g_n - g_c) * 2^n ),  s(t)=1 if t>=0 else 0")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    h455 = doc.add_heading("4.5.5. Nhom hinh dang contour (3 chieu)", level=3)
    set_heading_color(h455, BLUE)
    doc.add_paragraph(
        "Tu mask nhi phan, he thong lay contour ngoai lon nhat va tinh 3 thuoc tinh hinh hoc: "
        "dien tich (area), chu vi (perimeter) va ti le khung bao (aspect_ratio = w/h)."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        area = contourArea(C);  perimeter = arcLength(C, closed=True);  aspect_ratio = w/h")
    run.font.name = "Courier New"
    run.font.size = Pt(10)

    h456 = doc.add_heading("4.5.6. Nhom canh Canny va foreground ratio (3 chieu)", level=3)
    set_heading_color(h456, BLUE)
    doc.add_paragraph(
        "Ban do canh Canny duoc tinh tren anh xam, sau do chi giu pixel canh trong vung mask. "
        "He thong trich xuat so pixel canh, mat do canh va them ti le foreground cua toan anh."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        edge_density = edge_pixels / total_pixels;  foreground_ratio = count_nonzero(mask) / (H*W)")
    run.font.name = "Courier New"
    run.font.size = Pt(10)

    h457 = doc.add_heading("4.5.7. Nhom HOG gradient (324 chieu)", level=3)
    set_heading_color(h457, BLUE)
    doc.add_paragraph(
        "HOG duoc tinh tren anh xam da ap mask va resize 32x32, voi tham so orientations = 9, "
        "pixels_per_cell = (8,8), cells_per_block = (2,2), block_norm = L2-Hys."
    )
    doc.add_paragraph(
        "Voi cau hinh nay: 32x32 tao ra 4x4 cells; block 2x2 truot 1 cell tao 3x3 = 9 blocks; "
        "moi block co 2x2x9 = 36 gia tri; tong so chieu HOG = 9 x 36 = 324."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        hog_dims = ((4-2+1)*(4-2+1)) * (2*2*9) = 324")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    h458 = doc.add_heading("4.5.8. Chuan hoa va y nghia doi voi tim kiem", level=3)
    set_heading_color(h458, BLUE)
    doc.add_paragraph(
        "Tat ca 349 thuoc tinh duoc chuan hoa z-score bang tham so hoc tu tap train truoc khi dua "
        "vao FAISS IVF, giup khoang cach L2 phan anh dong deu cac nhom thuoc tinh."
    )
    p = doc.add_paragraph(style="Normal")
    run = p.add_run("        z_j = (x_j - mu_j) / sigma_j")
    run.font.name = "Courier New"
    run.font.size = Pt(11)

    doc.add_paragraph(
        "Bo thuoc tinh 349 chieu phu hop voi bai toan vi ket hop thong tin toan cuc (mau, dien tich) "
        "va thong tin cuc bo (texture, gradient), tu do tang kha nang phan tach giua cac loai la co "
        "mau hoac hinh dang gan nhau."
    )

    doc.add_page_break()

    # ── 5. FAISS IVF Search ────────────────────────────────────────────────────
    h = doc.add_heading("5. Tìm Kiếm Bằng FAISS IVF", level=1)
    set_heading_color(h, GREEN)

    doc.add_heading("5.1. Tổng quan FAISS IVF", level=2)
    doc.add_paragraph(
        "FAISS (Facebook AI Similarity Search) là thư viện tìm kiếm vector hiệu năng cao. "
        "Chỉ mục IVF (Inverted File Index) phân chia không gian vector thành các cluster "
        "(voronoi cells), sau đó chỉ tìm kiếm trong một số ít cluster gần nhất thay vì "
        "duyệt toàn bộ, giảm đáng kể thời gian tìm kiếm."
    )

    doc.add_heading("5.2. Cấu hình chỉ mục", level=2)
    faiss_config = [
        ("Index type", "IndexIVFFlat (L2)"),
        ("nlist (số cluster)", "4 (bằng K tối ưu từ Elbow)"),
        ("nprobe (số cluster tìm kiếm)", "3"),
        ("Số vector train", "4 274"),
        ("Số chiều vector", "349"),
        ("top-k mặc định", "5"),
    ]
    tbl4 = doc.add_table(rows=1, cols=2)
    add_table_border(tbl4)
    tbl4.rows[0].cells[0].text = "Tham số"
    tbl4.rows[0].cells[1].text = "Giá trị"
    for c in tbl4.rows[0].cells:
        c.paragraphs[0].runs[0].bold = True
    shade_row(tbl4.rows[0], "D6E4FF")
    for param, val in faiss_config:
        row = tbl4.add_row()
        row.cells[0].text = param
        row.cells[1].text = val

    doc.add_paragraph()

    doc.add_heading("5.3. Chọn K bằng Elbow Method", level=2)
    doc.add_paragraph(
        "Để chọn số cluster tối ưu, hệ thống chạy K-Means với K từ 1 đến 10, "
        "tính inertia và tìm điểm 'khuỷu tay' — điểm có khoảng cách lớn nhất "
        "tới đường thẳng nối điểm đầu và cuối trên đường Elbow. "
        "Kết quả: K = 4 (inertia tại K=4: 1 246 849)."
    )

    elbow_img = ARTIFACTS / "elbow_plot.png"
    if elbow_img.exists():
        doc.add_picture(str(elbow_img), width=Inches(4.5))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = doc.add_paragraph("Hình 1: Đồ thị Elbow Method – K tối ưu = 4")
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_heading("5.4. Dự đoán nhãn bằng Weighted Voting", level=2)
    doc.add_paragraph(
        "Sau khi tìm được top-5 ảnh gần nhất, hệ thống áp dụng weighted voting: "
        "mỗi ảnh được gán trọng số w = 1 / (d + ε) với d là khoảng cách L2. "
        "Nhãn có tổng trọng số cao nhất được chọn làm nhãn dự đoán. "
        "Độ tin cậy = tổng trọng số của nhãn dự đoán / tổng trọng số tất cả k ảnh."
    )

    doc.add_page_break()

    # ── 6. Kết quả thử nghiệm / demo ──────────────────────────────────────────
    h = doc.add_heading("6. Kết Quả Thử Nghiệm", level=1)
    set_heading_color(h, GREEN)

    doc.add_heading("6.1. Thống kê tập dữ liệu", level=2)
    tbl5 = doc.add_table(rows=1, cols=3)
    add_table_border(tbl5)
    for i, txt in enumerate(["Tập", "Số ảnh", "Số lớp"]):
        tbl5.rows[0].cells[i].text = txt
        tbl5.rows[0].cells[i].paragraphs[0].runs[0].bold = True
    shade_row(tbl5.rows[0], "D6E4FF")
    for r in [("Train", "4 274", "12"), ("Valid", "110", "12"), ("Test", "110", "12")]:
        row = tbl5.add_row()
        for i, v in enumerate(r):
            row.cells[i].text = v

    doc.add_paragraph()

    doc.add_heading("6.2. Hiệu năng tìm kiếm", level=2)
    doc.add_paragraph(
        "Với chỉ mục FAISS IVF (nlist=4, nprobe=3), hệ thống tìm kiếm top-5 trong "
        "4 274 vector đặc trưng trong thời gian dưới 5ms trên CPU. "
        "Giao diện Streamlit hiển thị ảnh kết quả, nhãn dự đoán và điểm voting chi tiết."
    )

    doc.add_heading("6.3. Demo giao diện", level=2)
    demo_steps = [
        "Mở giao diện: chạy lệnh streamlit run streamlit_leaf_app.py",
        "Upload ảnh lá cây bất kỳ (.jpg/.png) từ máy tính.",
        "Hệ thống hiển thị metadata ảnh truy vấn (kích thước, đặc trưng trích xuất).",
        "Top-5 ảnh tương đồng nhất được hiển thị kèm nhãn, khoảng cách L2 và độ tin cậy.",
        "Bảng voting chi tiết cho biết tỉ lệ bầu chọn của từng nhãn.",
    ]
    for s in demo_steps:
        doc.add_paragraph(s, style="List Number")

    doc.add_page_break()

    # ── 7. Hướng dẫn chạy dự án ───────────────────────────────────────────────
    h = doc.add_heading("7. Hướng Dẫn Cài Đặt và Chạy Dự Án", level=1)
    set_heading_color(h, GREEN)

    doc.add_heading("7.1. Cài đặt thư viện", level=2)
    add_code_block(doc, "python -m pip install opencv-python-headless scikit-image scikit-learn faiss-cpu mysql-connector-python tqdm streamlit Pillow python-docx")

    doc.add_heading("7.2. Chạy pipeline (tạo artifacts)", level=2)
    add_code_block(doc, "python leaf_feature_pipeline.py")

    doc.add_heading("7.3. Import metadata vào MySQL (tùy chọn)", level=2)
    doc.add_paragraph("Yêu cầu: bật MySQL trong XAMPP trước.")
    add_code_block(doc, "python import_features_to_mysql.py --mysql-host 127.0.0.1 --mysql-port 3306 --mysql-user root --mysql-database leaf_features")

    doc.add_heading("7.4. Tìm kiếm qua CLI", level=2)
    add_code_block(doc, 'python faiss_leaf_search.py --query-image "test\\test\\Mango\\0001_0001.JPG" --top-k 5 --nprobe 3')

    doc.add_heading("7.5. Mở giao diện web Streamlit", level=2)
    add_code_block(doc, "streamlit run streamlit_leaf_app.py")

    doc.add_page_break()

    # ── 8. Tổng kết ───────────────────────────────────────────────────────────
    h = doc.add_heading("8. Tổng Kết", level=1)
    set_heading_color(h, GREEN)

    doc.add_paragraph(
        "Dự án đã xây dựng thành công hệ thống tìm kiếm ảnh lá cây dựa trên đặc trưng, "
        "tích hợp pipeline hoàn chỉnh từ tiền xử lý ảnh đến lưu trữ và tìm kiếm hiệu quả."
    )

    achievements = [
        "Trích xuất vector đặc trưng 349 chiều kết hợp màu sắc, hình dạng, texture và HOG.",
        "Chuẩn hóa z-score đảm bảo các đặc trưng có cùng tầm quan trọng.",
        "Chỉ mục FAISS IVF cho phép tìm kiếm gần đúng nhanh trên tập train 4 274 ảnh.",
        "Weighted voting giúp dự đoán nhãn chính xác và có thể giải thích được.",
        "Giao diện Streamlit trực quan, dễ sử dụng.",
        "Tích hợp MySQL để lưu và truy vấn metadata chi tiết.",
    ]
    for a in achievements:
        doc.add_paragraph(a, style="List Bullet")

    doc.add_paragraph()
    doc.add_paragraph(
        "Hướng phát triển: mở rộng số lớp, tích hợp deep learning embedding (ResNet/EfficientNet) "
        "thay thế hand-crafted features, triển khai FAISS HNSW cho tập dữ liệu lớn hơn."
    )


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.2)
        section.right_margin  = Inches(1.2)

    # Default font
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(12)

    build(doc)
    doc.save(str(OUTPUT))
    print(f"✓ Đã tạo file: {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
