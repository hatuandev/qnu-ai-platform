# NHẬT KÝ PHIÊN LÀM VIỆC — TÍCH HỢP MISTRAL OCR & CƠ CHẾ ĐIỀU PHỐI BÓC TÁCH ĐA TẦNG

**Ngày**: 2026-09-17 23:28:00 (GMT+7)  
**Mục tiêu**: Chuẩn hóa luồng bóc tách tài liệu Kho Tri thức theo đúng kiến trúc `qnu-ai-core`: Tích hợp Mistral OCR (`mistral-ocr-latest`), điều phối thông minh định dạng file (Fast-path text cho PDF số hóa, Mistral OCR cho PDF scan & ảnh với graceful fallback sang Local OCR khi thiếu key, Docling cho Office).

---

## 1. Vấn Đề Kỹ Thuật Ban Đầu
1. **CPU Chạy Nặng Do Docling Trên Bản Scan PDF**: Khi người dùng tải lên tài liệu PDF dạng scan (`4740-qd-bgddt-bo-chi-so-cds-dai-hoc.pdf`), Platform tự động gọi Docling TableFormer trên CPU, dẫn đến tải mô hình Heron Object Detection 770MB và chạy suy luận mất hàng chục giây.
2. **Thiếu Mistral OCR Adapter**: Bên `qnu-ai-core` đã có Mistral OCR Cloud API xử lý các trang scan cực nhanh (1-2s), nhưng `qnu-ai-platform` chưa tích hợp adapter này.
3. **Cơ Chế Phân Định Cần Thiết**:
   - PDF có text layer: Dùng PyMuPDF fast-path (10-30ms).
   - PDF scan & Ảnh: Dùng Mistral OCR khi có `MISTRAL_API_KEY`, nếu không có key hoặc lỗi mạng thì tự động rơi về Local OCR (`easyocr` / `docling` / `pymupdf_ocr`).
   - Word / Excel: Dùng Docling TableFormer / openpyxl để giữ cấu trúc bảng.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết
| Tệp Tin | Hành Động | Lý Do Kỹ Thuật |
| :--- | :--- | :--- |
| [`backend/app/modules/ocr/adapters/mistral_adapter.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/adapters/mistral_adapter.py) | Tạo mới | Kế thừa `BaseOCRAdapter`, gọi API `https://api.mistral.ai/v1/ocr` với model `mistral-ocr-latest`, tự động kiểm tra availability từ `settings.MISTRAL_API_KEY`. |
| [`backend/app/modules/ocr/adapters/__init__.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/adapters/__init__.py) | Chỉnh sửa | Export `MistralOCRAdapter`. |
| [`backend/app/modules/ocr/adapters/easyocr_adapter.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/adapters/easyocr_adapter.py) | Chỉnh sửa | Sửa lỗi `reader.readtext` nhận 1D numpy buffer bằng cách truyền trực tiếp `image_bytes`. |
| [`backend/app/modules/ocr/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/ocr/service.py) | Chỉnh sửa | Đăng ký `mistral_ocr` trong catalog; trong `extract_document`, nếu người dùng chọn Mistral nhưng thiếu key, ghi log cảnh báo và fallback mượt mà sang Local OCR; trong `_extract_auto`, phân luồng ưu tiên theo định dạng file. |
| [`backend/app/modules/knowledge/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/service.py) | Chỉnh sửa | Điều phối trong `prepare_ingestion` và `parse_preview`: ảnh và PDF scan tự động chuyển OCR rescue qua `MistralOCRAdapter` (có local fallback). |
| [`backend/tests/test_ocr.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_ocr.py) | Chỉnh sửa | Cập nhật catalog 5 engines, bổ sung unit test `test_mistral_adapter_without_key_falls_back_to_local` và `test_auto_routing_uses_mistral_when_key_present`. |
| [`frontend/src/lib/file-inspector.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/lib/file-inspector.ts) | Chỉnh sửa | Cập nhật gợi ý bóc tách: PDF hiển thị "Fast-path + Mistral OCR", ảnh hiển thị "Vision OCR • Mistral". |
| [`frontend/src/pages/document-ingest-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/document-ingest-page.tsx) | Chỉnh sửa | Bổ sung option `mistral: "mistral_ocr"` ("Mistral OCR (Cloud Vision 1-2s)") vào danh sách lựa chọn bộ máy OCR. |

---

## 3. Kết Quả Kiểm Thử Toàn Diện
- **Backend Linter**: `uv run ruff check .` $\rightarrow$ All checks passed (0 lỗi).
- **Backend OCR Tests**: `uv run --extra dev pytest tests/test_ocr.py -v` $\rightarrow$ 13/13 passed (100%).
- **Backend Knowledge Tests**: `uv run --extra dev pytest tests/test_knowledge.py -v` $\rightarrow$ 25/25 passed (100%).
- **Frontend Linter**: `npm run lint` $\rightarrow$ Checked 90 files, 0 lỗi.
- **Frontend TypeScript**: `npm run typecheck` $\rightarrow$ 0 lỗi.
- **Frontend Build**: `npm run build` $\rightarrow$ Vite production build thành công (15.95s).
