# NHẬT KÝ LÀM VIỆC — PHIÊN #201
**Ngày thực hiện**: 2026-09-22 23:59 (UTC+7)  
**Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Mục tiêu chính**: Hoàn thiện bóc tách & Reconstruct bảng đa trang cho 3 PDF nghiệp vụ (Kế hoạch 2214 Bán dẫn-AI-ANM, Kế hoạch 2781 Học liệu E-learning, Kế hoạch 4053 BĐCLGD).

---

## 1. Bối Cảnh & Vấn Đề Kỹ Thuật

Người dùng gửi 3 tài liệu PDF thực tế của Trường Đại học Quy Nhơn để kiểm thử tính năng bóc tách tự động:
1. `QNU_Ke hoach THUC HIEN DE AN DAO TAO NHAN LUC BAN DAN_AI_AT va ANM-signed.pdf` (12 trang, Số 2214/KH-ĐHQN).
2. `KH2781 XAY DUNG HOC LIEU E-LEARNING 2025-2026.pdf` (3 trang, Số 2781/KH-ĐHQN).
3. `KH4053 BDCLGD nam hoc 2025-2026 (Final)-signed.pdf` (7 trang, Số 4053/KH-ĐHQN).

Qua phân tích tự động end-to-end trên toàn bộ 3 tệp, hệ thống phát hiện 4 vấn đề kỹ thuật tại các tầng bóc tách và tái cấu trúc bảng:
- **Vấn đề 1 (File 1 Trang 5)**: Hộp tiêu đề phụ lục `PHỤ LỤC (Ban hành kèm theo Kế hoạch...)` do có màu nền trắng nên `find_tables()` của PyMuPDF gom luôn vào làm hàng 0 của bảng. Hàng 0 chiếm mất vị trí của Header 8 cột, đẩy các hàng tiêu đề thực tế xuống dòng 1..3, làm sai lệch `schema_key` và khiến bảng phụ lục từ Trang 6..12 không thể stitch với Trang 5.
- **Vấn đề 2 (File 2 Trang 1)**: Bảng công việc tại Trang 1 có 4 cột nhưng trích xuất PyMuPDF xen kẽ các cột rỗng (spacer columns), thành 8 cột. Bộ chuẩn hóa `_normalize_spacer_columns` có điều kiện cứng `len(semantic_indices) >= 5`, dẫn tới bảng 4 cột bị bỏ qua không dọn spacer. Khi chuyển sang `markdown_renderer.py`, chốt chặn từ chối render bảng có header rỗng làm biến mất hoàn toàn 2 dòng nhiệm vụ (Row 1 và Row 2).
- **Vấn đề 3 (File 3 Trang 6)**: Bộ lọc anti-leakage trong `pdf_parser.py` vô tình bắt nhầm các gạch đầu dòng hành chính tại mục `III. Tổ chức thực hiện` ("- Phòng ĐBCL&KT: + Là đầu mối triển khai...", "- Các đơn vị...") vì các câu này chứa từ khóa trùng với bảng và có số năm học `2025-2026`.
- **Vấn đề 4 (File 1 Trang 6..12)**: Hàm `_has_semantic_headers` kiểm tra substring `"tt" in normalize_header(h)`. Cụm từ chuyên môn `Khoa CNTT` chứa chuỗi `tt`, khiến dòng dữ liệu nối tiếp ở đỉnh Trang 6 bị nhận nhầm thành Header mới thay vì dữ liệu tiếp nối, làm đứt gãy bảng phụ lục.

---

## 2. Giải Pháp Kỹ Thuật Chi Tiết

### 2.1. Tách Tiêu Đề Phụ Lục & Gộp Header Nhiều Tầng (`pdf_parser.py`)
- Xây dựng hàm `_normalize_raw_table_rows`:
  - Phát hiện hàng 0 có duy nhất 1 ô dữ liệu bắt đầu bằng `PHỤ LỤC`, `BẢNG`, `DANH MỤC` $\rightarrow$ tách thành `CanonicalBlock(type=BlockType.HEADING)` đặt ngay trước bảng.
  - Nhận diện các hàng tiêu đề kế tiếp (hỗ trợ header 2-3 tầng) và gộp lại thành 1 hàng header chuẩn 8 cột.
  - Bảo vệ dữ liệu: Loại trừ tuyệt đối các hàng có ô đầu tiên là số nguyên (STT 1, 2, 3), mã số 7 chữ số, chữ số La Mã, hoặc ô có độ dài > 50 ký tự khỏi header detection.

### 2.2. Chống Nuốt Gạch Đầu Dòng Hành Chính (`pdf_parser.py`)
- Bổ sung kiểm tra `is_admin_bullet = txt.startswith(("- ", "+ ", "• "))`.
- Các khối văn bản là gạch đầu dòng phân công nhiệm vụ/tổ chức thực hiện được bảo vệ 100%, không bị bộ lọc anti-leakage của bảng nuốt chửng.

### 2.3. Nâng Cấp Chuẩn Hóa Cột Spacer & Ghép Nối Bảng 4 Cột (`table_reconstructor.py`)
- Hạ ngưỡng `has_interspersed_spacers` từ `>= 5` xuống `>= 3` để bao quát các bảng 3 và 4 cột.
- Bổ sung cơ chế direct remapping: Khi số ô dữ liệu thực tế `len(row_non_empty) == len(semantic_headers)`, tự động ánh xạ trực tiếp các ô vào danh sách cột ngữ nghĩa, khắc phục triệt để hiện tượng dữ liệu nhảy cột trong PDF.
- Bảng tại Kế hoạch 2781 khôi phục trọn vẹn Row 1 & Row 2 và nối liền 7 dòng nhiệm vụ của Trang 1 & 2 thành 1 bảng master duy nhất.

### 2.4. Khử False Positive `tt` Bằng Regex Word Boundaries (`table_reconstructor.py`)
- Thay thế substring match bằng regex word boundaries: `r"\b(stt|tt|mã|tên|công việc|ngành|nhiệm vụ|chủ trì|đơn vị|thời gian|sản phẩm|kết quả|điểm|chỉ tiêu|tổ hợp|phương thức)\b"`.
- Thêm điều kiện độ dài mỗi header $\le 40$ ký tự và yêu cầu khớp ít nhất 2 khái niệm ngữ nghĩa độc lập.
- Ngăn chặn triệt để hiện tượng `Khoa CNTT` bị nhận nhầm thành header `tt`, giúp bảng Phụ lục 284 dòng Trang 5-12 của Kế hoạch 2214 nối liền mạch.

### 2.5. Fallback An Toàn Khi Render Markdown (`markdown_renderer.py`)
- Khi một bảng có cột header rỗng, tự động gọi `clean_table_columns` để dọn dẹp các cột thừa trước khi quyết định từ chối render, bảo đảm dữ liệu người dùng không bao giờ bị mất mát.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Unit & Integration Tests**:
   - `tests/test_table_stitching_and_page_partition.py` & `tests/test_table_reconstructor.py`: 31/31 passed in 0.97s.
   - Bổ sung 3 unit tests mới: `test_normalize_spacer_columns_four_columns`, `test_normalize_raw_table_rows_extracts_title_and_merges`, `test_has_semantic_headers_word_boundaries`.
2. **Code Quality**:
   - `uv run ruff check .`: 0 lỗi.
   - `frontend/`: Biome check 170 files (0 errors), `tsc --noEmit` (0 errors).
3. **Kiểm Thử Thực Tế Trên 3 PDF Nghiệp Vụ**:
   - **File 1 (2214/KH-ĐHQN)**: 12 trang, 0 số trang rác, toàn bộ 284 dòng Phụ lục nối thành 1 bảng master 8 cột đầy đủ 6 phần La Mã I..VI.
   - **File 2 (2781/KH-ĐHQN)**: 3 trang, 0 số trang rác, khôi phục trọn vẹn Row 1 & Row 2, bảng nối từ Trang 1 sang Trang 2 thành 1 bảng master 4 cột gồm 7 dòng nhiệm vụ.
   - **File 3 (4053/KH-ĐHQN)**: 7 trang, 0 số trang rác, 20 nhiệm vụ nối thành 1 bảng master 6 cột từ Trang 2..6, bảo toàn 100% các gạch đầu dòng hành chính tại Trang 6.
