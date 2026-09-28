# Nhật Ký Phiên Làm Việc #228 — Tự Động Migration & Seed Khi Chạy `make dev1` & Khắc Phục Lỗi Index Chunks Lớn Trên Cloudflare BGE-M3

- **Thời gian**: 2026-09-28 23:45 (UTC+7)
- **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Tiêu đề**: Tự Động Hóa Vòng Đời CSDL & Seed Khi Chạy `make dev1`, Khắc Phục Lỗi Tràn Token Cloudflare Workers AI BGE-M3 (HTTP 400 Code 3030)

---

## 1. Bối Cảnh & Các Vấn Đề Kỹ Thuật Tiếp Nhận

1. **Khởi động hạ tầng Docker cục bộ bị lỗi Dokploy env**:
   - Khi chạy `./make infra-up`, lệnh đọc nhầm file gốc `docker-compose.yml` (dành riêng cho Dokploy production) khiến Docker báo lỗi thiếu biến môi trường `DEV_ACCESS_PASSWORD` và `PROVIDER_ENCRYPTION_KEY`.
2. **Nhu cầu tự động hóa CSDL khi chạy `make dev1`**:
   - Người dùng mong muốn khi chạy `make dev1`, nếu CSDL chưa tồn tại hoặc vừa xóa volume/container, hệ thống phải tự động nhận diện, tự tạo database PostgreSQL, tự chạy Alembic migration và tự nạp toàn bộ seed data mà không cần người dùng phải chạy thủ công lệnh seed.
3. **Hiện tượng lỗi chỉ mục ("Lỗi index") khi nạp tệp tài liệu tuyển sinh**:
   - Người dùng tải lên tệp DOCX `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1)` gồm 14 trang với 23 chunks. Tệp thứ 2 (6 chunks) thì `Đã index` thành công, nhưng tệp tuyển sinh báo lỗi `Lỗi index` (đỏ).

---

## 2. Nguyên Nhân Gốc Rễ & Giải Pháp Triển Khai

### 2.1. Tách Biệt Hạ Tầng Docker Local (`docker-compose.infra.yml`)
- **Nguyên nhân**: `docker-compose.yml` ở root chứa cấu hình các service production của Dokploy (`frontend`, `backend`, `worker`, `bootstrap`).
- **Giải pháp**:
  - Tạo tệp `docker-compose.infra.yml` dành riêng cho 5 dịch vụ phát triển cục bộ: PostgreSQL 16 (5432), Qdrant (6333-6334), Redis (6379), MinIO (9000-9001), Gotenberg (3005).
  - Cập nhật toàn bộ task runners (`make.ps1`, `make.bat`, `make`, `run.ps1`, `Makefile`) trỏ chuẩn xác vào `-f docker-compose.infra.yml`.
  - Khai báo bổ sung `DEV_ACCESS_PASSWORD=QNU@2026` và `PROVIDER_ENCRYPTION_KEY` đồng nhất với nút "Điền mặc định" trên giao diện `sign-in.tsx`.

### 2.2. Cơ Chế Tự Động Migration & Seed Cho `make dev1` (`app.cli db ensure-ready`)
- **Triển khai tại backend (`backend/app/cli.py`)**:
  - Bổ sung hàm `ensure_db_ready(*, auto_seed=True) -> bool`:
    1. Kiểm tra kết nối PostgreSQL (báo lỗi thân thiện nhắc bật Docker nếu chưa chạy).
    2. Tự động kiểm tra và tạo database `qnu_ai_platform` qua maintenance connection nếu chưa có.
    3. Kiểm tra schema (`check_db_schema`), nếu thiếu bảng tự động chạy Alembic migration (`alembic upgrade head`).
    4. Kiểm tra dữ liệu mẫu (`verify_core_seed_data`), nếu thiếu tự động kích hoạt `run_db_seed(seed_all=True)`.
  - Đăng ký lệnh CLI: `python -m app.cli db ensure-ready`.
- **Tích hợp vào FastAPI Lifespan (`backend/app/main.py`)**:
  - Tự động gọi `ensure_db_ready` khi backend khởi động ở môi trường development hoặc khi `DEV_AUTO_MIGRATE=true` / `DEV_AUTO_SEED=true`.
- **Tích hợp vào các Task Runners**:
  - Cập nhật các lệnh `dev`, `dev1`, `dev2`, `be` trong `make.ps1`, `make.bat`, `make`, `run.ps1`, `Makefile`: tự động chạy `app.cli db ensure-ready` trước khi mở cửa sổ Backend và Frontend. Nếu đã có dữ liệu, chỉ mất <0.5s để xác nhận.

### 2.3. Khắc Phục Lỗi Tràn Token Cloudflare Workers AI BGE-M3 (HTTP 400 Code 3030)
- **Nguyên nhân**:
  - Truy vấn CSDL cho thấy lỗi:
    ```
    Cloudflare Workers AI không khả dụng: Cloudflare embedding error (HTTP 400):
    {"errors":[{"message":"AiError: Max context reached 82800 tokens but model supports only 60000","code":3030}],"success":false}
    ```
  - Trong `backend/app/modules/rag/vector_indexer.py`, hàm `_embed_texts_cloudflare` gán cứng `batch_size = 16`.
  - Với tệp tuyển sinh chứa bảng biểu lớn (52 ngành x 9 cột điểm chuẩn 2 năm), 16 chunks đầu tiên đạt tới **82.800 tokens**, vượt ngưỡng tối đa 60.000 tokens/request của Cloudflare Workers AI.
- **Giải pháp**:
  - **Dynamic Token & Character Budgeting**: Phân bổ batch động với `MAX_BATCH_ITEMS = 6` và `MAX_BATCH_CHARS = 16000` (khoảng ~8.000 - 10.000 tokens), luôn nằm trong vùng an toàn (< 20% giới hạn Cloudflare).
  - **Adaptive Recursive Sub-batching Fallback**: Nếu gặp lỗi `Max context reached` hoặc code `3030`, hệ thống tự động chia đôi batch thành 2 nửa và gửi lại đệ quy; nếu 1 chunk đơn lẻ quá dài sẽ tự động cắt ngắn an toàn về 6.000 ký tự.
  - **Tái lập chỉ mục ngay**: Kích hoạt `reindex_document` cho tài liệu `doc_18253b3d02d3`, toàn bộ 23/23 chunks đã được sinh vector 1024-dim và lưu thành công vào Qdrant DB. Trạng thái chuyển thành `ready` / `indexed`.

### 2.4. Phân Tích Kiến Trúc Gemini Embedding 1 & 2
- Đối chiếu chi tiết kiến trúc giữa `gemini-embedding-001` (Text-only, 3072 dims MRL, 2k context) và `gemini-embedding-2` (Native Multimodal: Text, Images, Video, Audio, PDF; 8k context) cho định hướng mở rộng hệ thống RAG đa phương tiện tương lai của ĐH Quy Nhơn.
- Thống nhất tiếp tục duy trì **BAAI BGE-M3 (`@cf/baai/bge-m3`)** làm mô hình embedding chính nhờ độ chính xác tiếng Việt vượt trội và chi phí vận hành tối ưu.

---

## 3. Các Tệp Mã Nguồn Đã Chỉnh Sửa

| Tệp | Thay đổi |
| :--- | :--- |
| `docker-compose.infra.yml` | Tạo mới file compose cô lập 5 container hạ tầng local |
| `backend/app/cli.py` | Bổ sung hàm `ensure_db_ready` và lệnh CLI `db ensure-ready` |
| `backend/app/main.py` | Tích hợp `ensure_db_ready` vào `lifespan` FastAPI Backend |
| `backend/app/modules/rag/vector_indexer.py` | Nâng cấp `_embed_texts_cloudflare` với dynamic character budgeting & adaptive fallback |
| `.env` & `backend/.env` | Thêm `DEV_AUTO_MIGRATE=true`, `DEV_AUTO_SEED=true`, `DEV_ACCESS_PASSWORD=QNU@2026` |
| `make.ps1`, `run.ps1`, `make.bat`, `make`, `Makefile` | Cập nhật lệnh `dev`, `dev1`, `seed` tự động kiểm tra CSDL |

---

## 4. Kết Quả Xác Minh (Verification)

1. **Kiểm tra CSDL & Trạng thái tài liệu**:
   - `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1)`: `status = "ready"`, `index_status = "indexed"`, `23 chunks`.
   - `Quy định Xây dựng Ngân hàng câu hỏi...`: `status = "ready"`, `index_status = "indexed"`, `6 chunks`.
   - Tổng số tài liệu bị lỗi trong toàn bộ CSDL: **0 tài liệu**.
2. **Bộ kiểm thử Backend**:
   - `pytest tests/test_knowledge.py -k "test_approve_document"` $\rightarrow$ **3/3 passed (100%)**.
   - `pytest tests/test_rag.py tests/test_revision_safe_qdrant_and_retrieval.py` $\rightarrow$ **34/34 passed (100%)**.
   - `pytest tests/test_rag_data_truth_and_lifecycle.py` $\rightarrow$ **9/9 passed (100%)**.
