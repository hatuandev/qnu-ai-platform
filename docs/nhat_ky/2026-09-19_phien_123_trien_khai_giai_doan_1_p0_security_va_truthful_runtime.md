# Nhật Ký Phiên Làm Việc #123 — Triển Khai Giai Đoạn 1 (P0): Bảo Mật Fail-Fast & Truthful Runtime Toàn Diện

- **Thời gian**: 2026-09-19 20:25 (GMT+7)
- **Kỹ sư phụ trách**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu**: Thực thi toàn bộ Giai đoạn 1 (P0) theo [Kế hoạch Cải thiện Toàn diện Sau Code Review](file:///d:/DuAnPhanMem/qnu-ai-platform/docs/ke_hoach/07_ke_hoach_cai_thien_toan_dien_sau_code_review.md), bao gồm Đợt 1 (Bảo mật, Mã hóa Fernet, HITL Policy, Multi-tenant Isolation) và Đợt 2 (Truthful Runtime, triệt tiêu fake success, mock models và mock vectors).

---

## 1. Chi Tiết Các Thay Đổi Kỹ Thuật (Key Changes)

### 1.1. Khóa Chặt Bảo Mật Cấu Hình & Mã Hóa Khóa Provider (Fernet)
- [`backend/app/core/config.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/config.py):
  - Bổ sung biến môi trường `PROVIDER_ENCRYPTION_KEY: str | None = None`.
  - Thêm `@model_validator(mode="after") def validate_production_security`: phát hiện và ném lỗi `ValueError` (Fail-Fast) khi chạy trong môi trường `ENVIRONMENT="production"` nếu còn sử dụng default/dev secrets (`SECRET_KEY`, `INTERNAL_API_KEY`, `DEV_ACCESS_PASSWORD`, `DATABASE_URL`, `S3_SECRET_KEY`) hoặc thiếu `PROVIDER_ENCRYPTION_KEY`.
- [`backend/app/core/crypto.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/core/crypto.py):
  - Khởi tạo `Fernet` sử dụng `settings.PROVIDER_ENCRYPTION_KEY or settings.SECRET_KEY`.
  - Bổ sung hàm tiện ích `is_encrypted(value: str | None) -> bool` nhận diện tiền tố mã hóa `enc:v1:`.
- [`backend/app/modules/modelops/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/modelops/service.py):
  - Cập nhật `create_provider`, `update_provider`, `add_provider_key`: toàn bộ API keys được mã hóa bằng `encrypt_secret` trước khi ghi xuống CSDL PostgreSQL và mảng `extra_config["api_keys"]`.
  - Trong `_sync_runtime_credentials`, `_ping_provider_api`, `_ping_single_model`, `generate`, `generate_stream`: giải mã an toàn trong bộ nhớ bằng `decrypt_secret` trước khi kết nối API hoặc tiêm vào runtime settings.
  - Loại bỏ các mock keys và số token usage giả định (`124500`, `82000`) khỏi `_init_default_keys` và `STANDARD_QNU_PROVIDERS`.

### 1.2. Siết Chặt Human-in-the-Loop & Multi-Tenant Boundary
- [`backend/app/modules/tools/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/service.py):
  - Kiểm tra `tool.requires_approval`: bắt buộc phải có cả `is_approved=True` và danh tính người phê duyệt hợp lệ `approved_by` (không cho phép client bên ngoài bypass chỉ bằng boolean `is_approved: true` thô).
- [`backend/app/modules/workflows/nodes/api_caller_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/api_caller_node.py):
  - Fail-closed: từ chối thực thi và ném lỗi 500 nếu thiếu DB session trong môi trường live/production.
  - Đảm bảo kiểm tra `tool.requires_approval` với cả `is_approved` và `approved_by` trước khi gọi tool.
- [`backend/app/modules/rag/retriever.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/retriever.py):
  - Bổ sung tham số `workspace_id` vào `search_sparse_fts` và `retrieve`.
  - Cả luồng PostgreSQL FTS và nhánh ILIKE fallback đều thực hiện join `KnowledgeCollection` để cô lập dữ liệu theo cả `tenant_id` và `workspace_id`.
- [`backend/app/modules/rag/vector_indexer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py):
  - Trong môi trường live/production (`settings.ENVIRONMENT not in ("test", "testing")`), chặn hoàn toàn hành vi tự động sinh mock vectors khi embedding service bị lỗi, thay vào đó ném `AppException` (Fail-Closed) để bảo toàn sự toàn vẹn của CSDL Qdrant.

### 1.3. Triệt Tiêu Dữ Liệu Ảo & Chuẩn Hóa Truthful Runtime (Frontend)
- [`frontend/src/services/tools-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/tools-api.ts):
  - Xóa bỏ khối mã fallback tự ngụy tạo file DOCX Nghị định 30 và file XLSX Bloom Matrix cùng đường dẫn ảo `data/artifacts/...`.
  - Khi API thất bại hoặc mất kết nối, trả về `status: "failed"` kèm thông báo lỗi thực tế.
- [`frontend/src/components/admin/ingestion-progress-modal.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/admin/ingestion-progress-modal.tsx):
  - Loại bỏ chuỗi 4 `setTimeout` lồng nhau giả lập các bước bóc tách (128ms, 435ms, 172ms, 215ms).
  - Kết nối trực tiếp với props `activeStage` và `isComplete` từ tiến trình thực tế của hệ thống.
- [`frontend/src/services/system-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/system-api.ts):
  - Đổi endpoint kiểm tra sức khỏe từ `/health/live` sang `/health/ready` (đối soát trực tiếp trạng thái sống của PostgreSQL và Redis).
- [`frontend/src/pages/chat-studio-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/chat-studio-page.tsx):
  - Xóa bỏ hằng số `FALLBACK_STARTERS` chứa 5 trợ lý giả mạo.
  - Khi chưa có trợ lý nào được cấu hình, hiển thị `EmptyState` chuẩn kèm nút dẫn tới trang Quản lý Trợ lý AI.
- [`frontend/src/pages/assistant-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/assistant-detail-page.tsx) & [`frontend/src/components/assistants/sections/assistant-model-section.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/components/assistants/sections/assistant-model-section.tsx):
  - Xóa bỏ danh sách 7 models fallback giả mạo khi các provider đều offline.
  - Hiển thị cảnh báo rõ ràng khi không có Provider nào đang hoạt động.

---

## 2. Kết Quả Kiểm Thử Toàn Diện (Verification)

### 2.1. Backend Test Suite
```bash
uv run ruff check .
# Output: All checks passed!

uv run --extra dev pytest -v
# Output: 241 passed, 47 warnings in 54.16s (100% PASS)
```
- Số test cases tăng từ 239 lên 241 (bổ sung test xác thực production fail-fast và test kiểm soát HITL).

### 2.2. Frontend Test Suite
```bash
npm run lint
# Output: Checked 162 files in 149ms. No fixes applied (0 lỗi Biome).

npm run typecheck
# Output: tsc --noEmit (0 lỗi TypeScript).

npm run build
# Output: vite build thành công (2573 modules transformed, built in 7.17s).
```

---

## 3. Đánh Giá & Cam Kết Tuân Thủ
- **Bảo mật**: Khóa production fail-fast, API keys được mã hóa bằng Fernet an toàn chuẩn cấp doanh nghiệp.
- **Truthful Runtime**: Triệt tiêu 100% mock success, mock models, mock vector rác và timer giả lập trên toàn bộ Frontend và Backend.
- **Tính toàn vẹn**: 0 lỗi linter, 0 lỗi TypeScript, 0 lỗi ruff, test suite pass 100%.
