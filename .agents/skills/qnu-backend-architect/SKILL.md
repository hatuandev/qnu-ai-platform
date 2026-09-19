---
name: qnu-backend-architect
description: >-
  Use this skill when developing, refactoring, or extending Backend modules on QNU AI Platform (FastAPI, Modular Monolith 4-file structure, SQLAlchemy async, RFC 7807 exceptions, Pytest). Do NOT use for pure frontend UI tasks or document parsing logic.
---

# Hướng Dẫn Kiến Trúc & Quy Chuẩn Phát Triển Backend QNU AI Platform

Tài liệu này là cẩm nang bắt buộc cho mọi kỹ sư Backend phát triển trên nền tảng **`qnu-ai-platform`**.

---

## 1. Cấu Trúc Module Chuẩn Hóa (Quy Tắc 4 Tệp Tin)

Mỗi tính năng/domain nghiệp vụ phải là một module khép kín nằm trong `app/modules/<module_name>/`, tuyệt đối không viết file "quái vật" nghìn dòng:

```text
app/modules/<module_name>/
├── __init__.py      # Export router và service
├── models.py        # SQLAlchemy ORM Models (Khai báo bảng CSDL PostgreSQL)
├── schemas.py       # Pydantic v2 DTOs (Request / Response validation)
├── service.py       # Domain Logic & Business Rules (Thin Controller, Fat Service)
└── router.py        # FastAPI Router (Chỉ tiếp nhận HTTP request & gọi service)
```

Nếu module có các logic phức tạp chuyên biệt, tách thành các file chiến lược phụ (ví dụ: `parsers/`, `chunker.py`, `retriever.py`, `fusion.py`).

---

## 2. Các Design Patterns Bắt Buộc Áp Dụng

1. **Strategy Pattern**:
   - Dùng khi có nhiều thuật toán hoặc định dạng khác nhau giải quyết cùng một mục tiêu.
   - Ví dụ: `BaseDocumentParser` với các chiến lược `PdfParser`, `DocxParser`, `ExcelParser`, `PlainTextParser`.
   - Ví dụ: `BaseChunker` với `ClauseBasedChunker` (cắt theo Điều/Khoản) và `SemanticChunker`.
2. **Pipeline Pattern**:
   - Dùng khi một luồng xử lý trải qua chuỗi các bước tuần tự rõ ràng.
   - Ví dụ Ingestion Pipeline: `Upload -> Checksum SHA-256 -> Storage -> Parse -> Clean -> Chunk -> DB & Facts -> Vector Index`.
   - Ví dụ RAG Pipeline: `Input Guardrail -> Semantic Cache -> Hybrid Retrieve -> Fact Lookup -> Format Planning -> Synthesis -> Output Guardrail`.
3. **Adapter Pattern**:
   - Dùng để trừu tượng hóa dịch vụ bên ngoài, cho phép hoán đổi nhà cung cấp mà không sửa core code.
   - Ví dụ: `StorageDriver` (chuyển đổi giữa `LocalStorageDriver` và `S3StorageDriver`).
   - Ví dụ: `BaseLLMAdapter` (chuẩn hóa `OpenAIAdapter`, `GeminiAdapter`, `LocalVLLMAdapter`).
4. **Thin Controller / Controller-Service Pattern**:
   - Router tuyệt đối **không** chứa câu truy vấn SQL trực tiếp, không chứa logic nghiệp vụ phức tạp. Router chỉ nhận request, gọi hàm tương ứng trong service và trả về Response Model.

---

## 3. Quy Chuẩn Kỹ Thuật Bắt Buộc (Production Guidelines)

1. **100% Asynchronous I/O**:
   - Toàn bộ kết nối Database phải dùng `AsyncSession` qua `asyncpg`.
   - Gọi Redis, Qdrant, S3, hoặc HTTP API bên thứ 3 phải dùng `await` (sử dụng `httpx.AsyncClient` hoặc async client của thư viện).
2. **Mã Lỗi Chuẩn Hóa RFC 7807 (Problem Details)**:
   - Khi có lỗi nghiệp vụ, ném ra các exception kế thừa từ `AppException` trong `app.core.exceptions`.
   - Định dạng trả về client:
     ```json
     {
       "type": "https://errors.qnu.edu.vn/document_not_found",
       "title": "Tài liệu không tồn tại",
       "status": 404,
       "detail": "Không tìm thấy tài liệu với mã doc_123 trong bộ sưu tập.",
       "instance": "/platform/v1alpha1/knowledge/documents/doc_123",
       "code": "DOCUMENT_NOT_FOUND",
       "correlation_id": "req-9a8b7c6d"
     }
     ```
3. **Structured JSON Logging & Correlation ID**:
   - Luôn sử dụng logger từ `app.core.logging`.
   - Luôn truyền `correlation_id` vào log context để dễ dàng trace request trên hệ thống giám sát tập trung.
4. **Kiểm Thử & Đảm Bảo Chất Lượng**:
   - Trước khi tạo commit hoặc kết thúc task, bắt buộc phải chạy thành công 100%:
     ```bash
     uv run ruff check .
     uv run --extra dev pytest -v
     ```
