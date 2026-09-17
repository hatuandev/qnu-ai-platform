# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Fact Số Hóa Đúng Nghĩa — Entity/Attribute/Value Từ Bảng Tuyển Sinh (Việc 3/5)

### 1. Bối cảnh
Vòng lặp ingest cũ dump nguyên headers thành fact (`entity=headers[0]`, `attribute="headers"`) — Fact Layer RAG không thể trả lời số liệu. Mục tiêu: trích đúng Mã ngành / Chỉ tiêu / Điểm chuẩn (+năm) / Tổ hợp / Phương thức / Học phí.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. `knowledge/facts.py` (mới): `FactExtractor` — map header tiếng Việt sang vai trò cột (mã/tên/chỉ tiêu/điểm chuẩn/tổ hợp/phương thức/học phí, kèm năm regex), parse số Việt (`24,5`→24.5, `16.500.000`→16500000), giữ nguyên văn các cột danh sách (`1,4` không bao giờ thành số), bỏ qua ô trống/cột lạ, giữ 1 fact tóm tắt mỗi bảng, ghi vị trí nguồn (table/row/page) vào `raw_data`.
2. `knowledge/service.py`: thay vòng lặp dump headers bằng `fact_extractor.extract(...)`.
3. `tests/test_facts.py` (mới, 5 tests): parse số, map header + năm, bảng tuyển sinh 2 dòng, điểm chuẩn đa năm, bảng lạ chỉ còn summary.
4. Trong lúc làm phát hiện và sửa 2 lỗi nghiêm túc: `parse_vietnamese_int("1,4")` suýt trả 1 (đã siết: có dấu phẩy → None) và cột cùng vai trò lặp theo năm bị `setdefault` nuốt mất (chuyển sang giữ toàn bộ cột).

### 3. Kết Quả Kiểm Thử (Verification)
- Kiểm chứng thật trên Đề án 2026 (DocxParser → extractor): 5 bảng → **254 facts** (250 facts ngành: mã/phương thức/tổ hợp đúng từng ngành như `Sư phạm Toán học (7140209)`; ô chỉ tiêu trống bị bỏ qua trung thực).
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest -q`: **93/93 passed**.
