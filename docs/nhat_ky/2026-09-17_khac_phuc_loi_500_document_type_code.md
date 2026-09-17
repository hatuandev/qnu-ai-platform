# NHẬT KÝ LÀM VIỆC — Phiên #70
# Ngày: 2026-09-17 | Tiêu đề: Khắc Phục Lỗi TypeError document_type_code và Hoàn Thiện Studio Page Builder

## 1. Bối Cảnh & Nguyên Nhân
- **Sự cố**: Khi người dùng tải lên tệp tin `7.1.6 Kế hoạch triển khai 2 phần mềm của Nhà trường.docx` qua Studio Nạp Kho Tri thức, giao diện báo `Tải lên thất bại (HTTP 500). Vui lòng thử lại.`
- **Log Backend**:
  - `TypeError: KnowledgeService.list_documents() got an unexpected keyword argument 'document_type_code'`
  - `TypeError: KnowledgeService.ingest_document() got an unexpected keyword argument 'document_type_code'`
- **Nguyên nhân cốt lõi**:
  - Tệp `backend/app/modules/knowledge/service.py` trước đó bị revert về nhánh gốc khiến các tham số `document_type_code` (thuộc gói Taxonomy đồng bộ từ Core ở phiên #61) bị mất trong signature của `KnowledgeService.list_documents` và `KnowledgeService.ingest_document`, trong khi `router.py` vẫn truyền `document_type_code`.
  - Ngoài ra, `build_studio_pages` trong `KnowledgeService` chưa tiếp nhận `page_markdowns` và thiếu logic tổng hợp markdown từ layout blocks khi chunks bị dồn trang.

## 2. Thay Đổi Kỹ Thuật
| Tệp | Hành Động | Mô Tả |
| :--- | :--- | :--- |
| `backend/app/modules/knowledge/service.py` | MODIFY | 1. Import `document_types_service` từ `app.modules.document_types.service`.<br>2. Bổ sung tham số `document_type_code: str \| None = None` vào `list_documents` và query filter theo loại văn bản chuẩn.<br>3. Bổ sung tham số `document_type_code: str \| None = None` vào `ingest_document`, xác thực active code qua `document_types_service.validate_active_code` và lưu nhãn nguồn `document_type_source`.<br>4. Thêm tham số `page_markdowns` và hàm `_synthesize_page_markdown_from_blocks` trong `build_studio_pages` chống trang trắng khi chunks bị dồn. |

## 3. Kết Quả Kiểm Thử
- `uv run ruff check .`: 0 lỗi, 100% clean.
- `uv run --extra dev pytest tests/test_knowledge.py tests/test_document_types.py tests/test_jobs.py -v`: 47/47 tests passed (100%).
- Kiểm tra endpoint trực tiếp: `GET http://127.0.0.1:8001/platform/v1alpha1/knowledge/documents?collection_id=col_admissions` trả về `HTTP 200 OK`.
