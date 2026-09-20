# NHẬT KÝ PHIÊN LÀM VIỆC #159
**Ngày**: 2026-09-20 | **Thời gian**: 18:05 (UTC+7)
**Mục tiêu**: Khắc phục triệt để lỗi `asyncpg.exceptions.StringDataRightTruncationError: value too long for type character varying(512)` khi tải lên và bóc tách tài liệu vào `knowledge_facts`.

---

## 1. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)
- **Triệu chứng**: Khi người dùng tải lên tài liệu Kế hoạch triển khai nhiệm vụ năm học (hoặc tài liệu có bảng phức tạp) qua endpoint `POST /platform/v1alpha1/knowledge/collections/{id}/upload`, hệ thống quăng lỗi HTTP 500:
  ```
  asyncpg.exceptions.StringDataRightTruncationError: value too long for type character varying(512)
  [SQL: INSERT INTO knowledge_facts (id, collection_id, document_id, entity_name, entity_type, attribute_name, attribute_value, confidence, raw_data, created_at) VALUES ...]
  ```
- **Nguyên nhân**:
  1. Trong [`backend/app/modules/knowledge/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/models.py), cột `attribute_value` của bảng `knowledge_facts` được định nghĩa giới hạn cứng là `String(512)`.
  2. Trong các văn bản kế hoạch hoặc thông báo tuyển sinh, các trường như "Sản phẩm kết quả", "Nội dung nhiệm vụ" (`ImplementationTaskRecord.deliverables`) chứa danh sách nhiều quyết định, quy chế, đề án hoặc chuỗi mô tả dài vượt quá 512 ký tự.
  3. CSDL PostgreSQL thực tế cũng bị giới hạn `VARCHAR(512)` trên cột `attribute_value`.
  4. Ngoài ra, trong [`backend/app/modules/knowledge/facts.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/facts.py), 2 methods `extract_facts_from_domain_records` và `extract_from_verified_markdown_pages` đã bị thiếu do ghi đè trước đó.

---

## 2. Các Giải Pháp Kỹ Thuật Đã Triển Khai

| Tệp | Hành Động | Mô Tả Kỹ Thuật |
| :--- | :--- | :--- |
| [`backend/app/modules/knowledge/models.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/models.py) | MODIFY | Chuyển `attribute_value` từ `String(512)` sang `Text` (chứa văn bản không giới hạn); Mở rộng `entity_name` sang `String(512)` và `attribute_name` sang `String(255)`. |
| [`backend/alembic/versions/20260920_expand_facts_text.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/alembic/versions/20260920_expand_facts_text.py) | NEW | Tạo migration Alembic `20260920_expand_facts_text` (Revises: `20260919_approval_payload_hash`) thực hiện `ALTER TABLE knowledge_facts ALTER COLUMN attribute_value TYPE TEXT`, mở rộng `attribute_name` lên `VARCHAR(255)` và `entity_name` lên `VARCHAR(512)`. Đã apply thành công vào database qua `alembic upgrade head`. |
| [`backend/app/modules/knowledge/facts.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/facts.py) | MODIFY | Bổ sung đầy đủ 2 methods `extract_facts_from_domain_records` và `extract_from_verified_markdown_pages` vào `FactExtractor`; Làm sạch khoảng trắng (`clean_deliv = "; ".join(d.strip() ...)`) và bảo đảm dữ liệu đầu vào sạch. |

---

## 3. Kết Quả Kiểm Thử Toàn Diện
- **Alembic Check**: `uv run alembic check` $\rightarrow$ `No new upgrade operations detected.` (Schema hoàn toàn sạch 0 diff).
- **Backend Lint**: `uv run ruff check .` $\rightarrow$ `All checks passed! (0 lỗi)`.
- **Backend Test Suite**:
  - `tests/test_domain_records_and_quality_gate.py`: **12/12 passed (100%)**.
  - `tests/test_table_reconstructor.py`: **12/12 passed (100%)**.
  - Toàn bộ suite Knowledge, RAG, Revision-Safe Qdrant và Golden Benchmark: **100% Passed**.
