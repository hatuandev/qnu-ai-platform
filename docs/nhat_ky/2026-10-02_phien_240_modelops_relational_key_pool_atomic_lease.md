# Phiên #240 — ModelOps Giai đoạn 2: Relational Key Pool & Atomic Lease

**Thời gian:** 2026-10-02 (UTC+7)  
**Phạm vi:** backend ModelOps, OCR, RAG embedding/reranker và migration PostgreSQL  
**Mục tiêu:** khi một API key hết quota hoặc gặp 429, request tự động chuyển sang key tiếp theo an toàn giữa nhiều Uvicorn workers.

## Nội dung đã triển khai

### 1. Key pool quan hệ

- Thêm model `ProviderApiKey` tại `backend/app/modules/modelops/models.py`.
- Thêm migration `20261002_provider_api_keys`.
- Backfill các key trong `extra_config.api_keys` sang bảng mới.
- Provider chỉ có `api_key_encrypted` được tạo một bản ghi primary tương thích.
- Lưu riêng quota, usage, cooldown, trạng thái, lỗi gần nhất và thông tin lease.

### 2. Lease nguyên tử

- Thêm `ProviderKeyRotationService` tại `backend/app/modules/modelops/services/provider_key_rotation_service.py`.
- Chọn khóa bằng `FOR UPDATE SKIP LOCKED`.
- Lease có `lease_token` và thời hạn tự giải phóng khi worker chết.
- Thành công: cộng token, cập nhật usage và reset lỗi.
- 429/quota/key invalid: cập nhật trạng thái và cooldown tương ứng.
- Lỗi không phân loại: giải phóng lease và cho phép thử khóa kế tiếp.

### 3. Nối các runtime

- `InferenceService.generate` và `generate_stream` dùng lease quan hệ, xoay key trước khi fallback provider.
- `ModelRuntimeResolver` truyền `key_id` và `lease_token` cho embedding/reranker.
- `VectorIndexer` và `RerankerClient` hoàn tất hoặc đánh dấu lỗi lease sau request cloud.
- `OCRService` dùng key pool cho Gemini/Mistral trong combo, auto-routing và engine cloud chỉ định.

### 4. Tương thích chuyển tiếp

- Nếu migration chưa chạy hoặc provider chưa có bản ghi quan hệ, runtime tiếp tục dùng JSONB cũ.
- CRUD Provider ghi song song relational table và JSONB trong giai đoạn chuyển đổi.
- Không thêm đường trả khóa API dạng plaintext; API quản trị chỉ trả masked value.

## Xác minh

- Test trọng điểm: **46/46 passed**.
- Full backend suite: **492 passed, 5 failed** ở các test admissions/fact/artifact đã tồn tại trước phiên.
- Ruff trên các file thay đổi: **0 lỗi**.
- `alembic heads`: `20261002_provider_api_keys`.

## Vận hành tiếp theo

Trước khi dùng pool quan hệ trên môi trường thật, chạy migration:

```text
alembic upgrade head
```

Sau migration cần kiểm tra số lượng bản ghi `provider_api_keys` theo từng provider và xác nhận các key có trạng thái `active`/`exhausted` đúng với JSONB cũ.

## Tồn đọng đã ghi nhận

- Full suite còn 5 lỗi admissions/fact/artifact không thuộc thay đổi Giai đoạn 2.
- Docling native trên Windows còn cảnh báo access violation khi chạy full suite; cần xử lý riêng ở pipeline OCR.
- Ruff toàn repo vẫn còn lỗi ở các script/scratch cũ ngoài phạm vi module vừa cập nhật.
