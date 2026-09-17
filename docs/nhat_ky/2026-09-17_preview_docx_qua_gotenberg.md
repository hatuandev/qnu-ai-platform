# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Preview Ảnh Cho File Word/Excel — Chuyển Đổi Qua Gotenberg LibreOffice

### 1. Bối cảnh & Nguyên nhân
Người dùng up file `.docx` (Kế hoạch HEMIS) thấy cột trái chỉ hiện placeholder "Tài liệu số hóa". Nguyên nhân: `render_page_image` chỉ render trực tiếp PDF/ảnh; Word/Excel/PowerPoint bị từ chối 404 có chủ đích. Đúng hướng nhưng dở dang — Gotenberg + LibreOffice đã chạy sẵn trong cụm docker mà chưa được dùng.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
1. `knowledge/service.py`: `_convert_office_to_pdf()` gọi `POST {GOTENBERG_URL}/forms/libreoffice/convert` (timeout 120s, lỗi rõ 503/422); `render_page_image` tự chuyển đổi nhóm `doc/docx/xls/xlsx/ppt/pptx/odt/ods/odp/rtf` rồi render như PDF; loại khác vẫn 404 trung thực.
2. `knowledge/schemas.py` + `get_studio_view`: bổ sung `file_size_bytes`, `total_chunks` — sửa luôn hiển thị "0 MB / ~0 Chunks" trên topbar studio.
3. `api-client.getStudioView`: đọc 2 trường mới thay vì hardcode 0.
4. Tests mới (`test_knowledge.py`, +3): render docx qua converter mock (assert magic PNG), Gotenberg lỗi → 422 đúng mã, studio-view mang size/chunks thật.

### 3. Kết Quả Kiểm Thử (Verification)
- **Verify live trên backend đang chạy của người dùng**: `studio-view` của `doc_17368a829751` trả đúng tiêu đề/engine/chunks; `pages/1/image` render PNG 260KB — ảnh quốc hiệu/tên trường/căn cứ/kế hoạch chuẩn, font Việt nguyên vẹn.
- `uv run ruff check .`: 0 lỗi.
- `uv run --extra dev pytest -q`: **108/108 passed**.
- FE `typecheck`: 0 lỗi.
