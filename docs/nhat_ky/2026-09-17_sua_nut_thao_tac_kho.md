# Nhật Ký Làm Việc — 17/09/2026

## Tiêu đề: Sửa Dứt Điểm Nút Thao Tác Kho Tri Thức — Download/Xóa/Reindex/Cấu Hình/Sandbox Thật

### 1. Bối cảnh & Nguyên nhân (báo lỗi người dùng + ảnh chụp)
Trên trang chi tiết kho, cột THAO TÁC có 2/4 nút chết (Download, Xóa không có `onClick`), Reindex/Sandbox giả lập `setTimeout`, badge "Hiệu lực" gán cứng, "0 chunks" vì `DocumentResponse.chunk_count` luôn là default Pydantic (service không đếm), nút "Cấu hình" không handler.

### 2. Các Thay Đổi Kỹ Thuật Đã Thực Hiện
**Backend:**
1. `knowledge/service.py`: `_chunk_counts_by_document` (GROUP BY) + `_attach_collection_stats` → counts thật cho list/get; `download_document` (bytes gốc + media-type + 404 trung thực); `delete_document` dọn thêm vectors Qdrant chống trích dẫn ma.
2. `rag/vector_indexer.py`: thêm `delete_by_document` (FilterSelector theo document_id).
3. `knowledge/router.py`: endpoint `GET /documents/{id}/download`.
4. Tests +4: download happy/404, reindex enqueue, retrieval test thật.

**Frontend (`collection-detail-page.tsx` + `api-client.ts`):**
5. Download (blob save), Xóa (ConfirmDialog + DELETE + invalidate), Reindex thật (POST reindex → banner job + refresh tab tasks), Cấu hình (dialog sửa tên/mô tả → PUT), Sandbox thật (`POST test`, map kết quả + banner khi trống/lỗi).
6. Badge trạng thái thật cho tài liệu (Chờ duyệt/Đã duyệt/Đang xử lý/Lưu trữ/Lỗi) và tasks (Hoàn tất/Đang xử lý/Thất bại); nút retry/cancel job theo trạng thái; mở rộng options bộ lọc trạng thái.

### 3. Kết Quả Kiểm Thử (Verification)
- **Verify live trên backend + DB đang chạy của người dùng** (tài liệu thử tạo/xóa sạch, không đụng dữ liệu thật): upload 201 → chunk_count=1/status pending thật; download 200 đúng bytes + disposition; reindex → job queued; retrieval `found=1`; delete 204 → 404 sau xóa.
- `uv run ruff check .`: 0 lỗi; **pytest 113/113**; FE biome lint 0, typecheck 0, build ✓.
