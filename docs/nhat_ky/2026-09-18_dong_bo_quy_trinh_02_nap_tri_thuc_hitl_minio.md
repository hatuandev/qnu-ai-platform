# NHẬT KÝ LÀM VIỆC — ĐỒNG BỘ QUY TRÌNH 02 NẠP TRI THỨC, PHÂN NHÁNH OCR & ĐỐI SOÁT HITL

- **Thời gian**: 2026-09-18 08:18 (UTC+7)
- **Kỹ sư / Agent**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Đồng bộ toàn diện tệp tài liệu quy trình [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](../quy_trinh/02_nap_tri_thuc_minio.md) khớp 100% với kiến trúc và luồng dữ liệu thực tế trong codebase của QNU AI Platform.

---

## 1. Bối Cảnh & Phân Tích Hiện Trạng

Người dùng yêu cầu rà soát và đối chiếu tệp tài liệu [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](../quy_trinh/02_nap_tri_thuc_minio.md) với thực tế hoạt động của Kho tri thức.
Quá trình rà soát mã nguồn thực tế tại `backend/app/modules/knowledge/service.py`, `router.py`, `models.py`, `backend/app/core/storage.py`, `frontend/src/lib/file-inspector.ts` và `frontend/src/pages/document-verification-page.tsx` đã chỉ ra 5 khoảng cách trọng yếu trong bản quy trình cũ:
1. **Thiếu tầng Human-in-the-loop (HITL) Studio**: Bản cũ mô tả luồng nạp tự động đẩy thẳng vào Qdrant với `status = INDEXED`. Thực tế tài liệu sau bóc tách chỉ lưu tạm ở trạng thái `status = 'pending'`, chỉ khi cán bộ đối soát mắt trên Studio và bấm `[Xác nhận & Nạp vào Vector DB]` (`/approve`) thì mới nạp vector vào Qdrant.
2. **Sai lệch Document Status Lifecycle**: CSDL lưu `pending` $\rightarrow$ `approved` $\rightarrow$ `archived`, không phải `UPLOADED` $\rightarrow$ `INDEXED`.
3. **Thiếu cơ chế Smart Auto-Recommendation & System Defaults**: Hệ thống đã có tính năng tự động nhận diện loại file, tự map 37 loại văn bản NĐ 30 và tự nạp Active System Defaults cho Embedding Model (Cloudflare Edge vs Local CPU).
4. **Quy chuẩn lưu trữ Dual-driver**: Hệ thống hỗ trợ song song `S3StorageDriver` (MinIO S3 Production) và `LocalStorageDriver` (Development/Testing), đồng thời lưu ảnh render cache từng trang (`cache/{document_id}/page_{page_number}.png`).
5. **Thiếu cơ chế lưu trữ `page_markdowns` & bảo toàn bảng GFM**: Đã được phát triển ở các phiên #70, #75, #76, #77 để chống mất bảng biểu và tránh dồn chunks vào trang 1.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết

| Tệp Tin | Hành Động | Lý Do Kỹ Thuật |
| :--- | :---: | :--- |
| [`docs/quy_trinh/02_nap_tri_thuc_minio.md`](../quy_trinh/02_nap_tri_thuc_minio.md) | **Chỉnh sửa** | Viết lại toàn diện sơ đồ luồng luân chuyển dữ liệu Mermaid (2 pha: Pha 1 Bóc tách pending $\rightarrow$ Pha 2 Đối soát HITL Studio $\rightarrow$ Approve Qdrant), cập nhật 8 bước kỹ thuật chi tiết chuẩn hóa theo hiện trạng thực tế. |
| [`backend/app/modules/knowledge/chunker.py`](../../backend/app/modules/knowledge/chunker.py) | **Refactor** | Sửa cảnh báo Ruff `SIM114`: Gộp 2 nhánh `if` tương đồng gán `sec_start_page` theo luật Clean Code (Boy Scout Rule 8.1 & 8.8). |
| [`docs/WORK_LOG.md`](../WORK_LOG.md) | **Cập nhật** | Ghi nhận phiên làm việc vào Sổ mục lục tổng hợp tiến trình dự án. |

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Zero Mojibake Audit**:
   - Chạy `uv run python scripts/check_mojibake.py`: **225/225 tệp sạch 100%**, không có bất kỳ ký tự rác hay vỡ font tiếng Việt nào.
2. **Frontend Linter**:
   - Chạy `npm run lint` (Biome check): **0 lỗi** trên 91 files.
3. **Backend Linter**:
   - Chạy `uv run ruff check .`: **All checks passed! (0 lỗi)**.
