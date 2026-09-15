# Phân Tích Chuyên Sâu Công Nghệ Hạ Tầng Triển Khai

Tài liệu này đi sâu vào chi tiết kỹ thuật của từng thành phần trong ngăn xếp công nghệ (Tech Stack) phục vụ triển khai nền tảng **QNU AI Platform**.

---

## 1. Nền Tảng Điều Phối PaaS — Dokploy & Traefik Proxy

### 1.1. Vai Trò của Dokploy
Dokploy được lựa chọn làm nền tảng điều phối ứng dụng (Application Orchestrator) đặt trực tiếp trên máy chủ VPS hoặc máy chủ vật lý của Trường Đại học Quy Nhơn:
- **Tự quản trị (Self-Hosted)**: Toàn bộ dữ liệu sinh viên, tài liệu quy chế và vector nằm 100% trong hạ tầng của trường, không bị phụ thuộc vào dịch vụ bên thứ ba.
- **Quản lý dạng Stack (Docker Compose Support)**: Dokploy cho phép khai báo toàn bộ hệ thống gồm 7 containers trong một file compose duy nhất, quản lý biến môi trường tập trung và kiểm soát trạng thái của từng container.
- **Git Integration & Webhooks**: Kết nối trực tiếp với kho mã nguồn (GitLab/GitHub), tự động kích hoạt tiến trình đóng gói và triển khai khi có bản phát hành mới.

### 1.2. Vai Trò của Traefik Reverse Proxy
Traefik được nhúng sẵn trong Dokploy và đóng vai trò là **Bộ định tuyến biên L7 (Edge Router)**:
- **Tự động hóa SSL/TLS**: Tích hợp giao thức ACME với Let's Encrypt. Khi phát hiện cấu hình domain mới (ví dụ: `api.ai.qnu.edu.vn`), Traefik tự động thực hiện xác thực HTTP-01 / DNS-01 để cấp phát và tự gia hạn chứng chỉ SSL hợp lệ.
- **Hỗ trợ Streaming RAG (Server-Sent Events)**: Điểm đặc thù của trợ lý ảo AI là phản hồi sinh chữ theo thời gian thực (Token Streaming). Traefik được cấu hình bộ đệm mở rộng (Buffering Middleware) để ngăn chặn hiện tượng ngắt kết nối giữa chừng (504 Gateway Timeout) khi LLM đang xử lý câu trả lời dài.

---

## 2. Tầng Ứng Dụng & Tính Toán Bất Đồng Bộ

### 2.1. QNU Platform API (`qnu_backend`)
- **Khung ứng dụng**: FastAPI (Python 3.12+), tận dụng tối đa cơ chế `asyncio` để đạt thông lượng hàng nghìn requests đồng thời với mức tiêu thụ tài nguyên tối thiểu.
- **Quản lý phụ thuộc bằng UV**: Sử dụng binary `uv` (từ Astral) thay vì `pip` truyền thống, giúp thời gian build Docker image rút ngắn từ 5 phút xuống còn dưới 45 giây.
- **Bảo mật Container**:
  - Không chạy bằng quyền `root`, chuyển sang người dùng hệ thống đặc quyền thấp `qnu` (UID 10001).
  - Tích hợp sẵn font chữ `Liberation Serif` (tương đương Times New Roman) phục vụ xuất văn bản hành chính theo đúng thể thức chuẩn.
- **Healthcheck Probe**: Tích hợp sẵn probe `/health/live` và `/health/ready` kiểm tra liveness và readiness của toàn bộ các kết nối phụ thuộc.

### 2.2. ARQ Background Worker (`qnu_worker`)
- **Khung hàng đợi**: ARQ (Async Redis Queue), giải pháp hàng đợi tác vụ thuần `asyncio` viết riêng cho Python hiện đại, nhẹ hơn Celery gấp nhiều lần và không cần cấu hình phức tạp.
- **Nhiệm vụ phân công**:
  - Bóc tách tệp tải lên dung lượng lớn (PDF hàng trăm trang).
  - Làm sạch văn bản tiếng Việt và phân loại Điều/Khoản (`ClauseBasedChunker`).
  - Gọi mô hình tạo nhúng vector và đẩy hàng loạt vào Qdrant.
  - Sinh báo cáo nghiệm thu hoặc xuất ma trận đề thi Excel Bloom.

---

## 3. Bộ Tứ Lưu Trữ Dữ Liệu Chuyên Trách (Data Tier)

```
                            ┌────────────────────────────────┐
                            │    TẦNG DỮ LIỆU ĐA MÔ HÌNH     │
                            └────────────────┬───────────────┘
                                             │
      ┌──────────────────────┬───────────────┴───────────────┬──────────────────────┐
      ▼                      ▼                               ▼                      ▼
┌──────────────┐      ┌──────────────┐                ┌──────────────┐      ┌──────────────┐
│  PostgreSQL  │      │    Qdrant    │                │    Redis     │      │    MinIO     │
│  (Relational │      │  (Vector DB  │                │  (In-Memory  │      │ (S3 Storage  │
│  + FTS vi)   │      │   Dense BGE) │                │  Cache & Q)  │      │  Raw Files)  │
└──────────────┘      └──────────────┘                └──────────────┘      └──────────────┘
```

### 3.1. PostgreSQL 16 (CSDL Quan Hệ & Bảng Sự Thật)
- **Lưu trữ nghiệp vụ**: Thông tin định danh Trợ lý, phân quyền người dùng, lịch sử tương tác, cấu hình DAG Workflows và kết quả kiểm định chất lượng Ragas.
- **Structured Fact Layer**: Lưu trữ bảng số liệu sự thật (Điểm chuẩn từng năm, mã tổ hợp môn, chỉ tiêu, biểu phí). Khi người học hỏi số liệu, bot truy vấn thẳng vào đây thay vì suy diễn từ vector, đảm bảo độ chính xác 100%.
- **Vietnamese Full-Text Search (FTS)**: Đóng vai trò là nhánh tìm kiếm từ khóa chính xác (Lexical Search) trong thuật toán lai **Hybrid RAG**, kết hợp cùng nhánh vector qua công thức Reciprocal Rank Fusion ($k=60$).

### 3.2. Qdrant Vector Database (Lưu Trữ Ngữ Nghĩa)
- **Mô hình Vector**: Lưu trữ các vector 1024 chiều từ mô hình `BAAI/bge-m3`.
- **Hiệu năng & Khả năng mở rộng**: Viết bằng Rust, tối ưu hóa bộ nhớ và hỗ trợ bộ lọc Payload đa người thuê (`tenant_id`, `collection_id`, `is_active`) với độ trễ truy vấn dưới 10ms.

### 3.3. Redis 7 (Bộ Nhớ Đệm & Hàng Đợi)
- **Semantic Cache**: Lưu trữ tạm thời các câu trả lời của những câu hỏi phổ biến (ví dụ: *"Hạn nộp hồ sơ xét tuyển khi nào?"*). Nếu câu hỏi mới trùng khớp ngữ nghĩa $\ge 0.95$, hệ thống trả về ngay kết quả từ Redis trong 5ms mà không cần gọi LLM, tiết kiệm tối đa chi phí API.
- **Hàng đợi thông điệp**: Quản lý các jobs nạp tri thức bất đồng bộ cho Worker.

### 3.4. MinIO (Lưu Trữ Đối Tượng S3-Compatible)
- **Chuẩn S3 tương thích**: Lưu trữ các tệp thô ban đầu (PDF tuyển sinh, Word quyết định đào tạo, ảnh scan văn bằng) và các tệp thành phẩm xuất ra.
- **Toàn vẹn dữ liệu**: Tính toán và kiểm tra mã băm `sha256` của mọi tệp tin trước khi nạp vào hệ thống để loại bỏ hoàn toàn việc tải trùng lặp tài liệu.

---

## 4. Công Cụ Hỗ Trợ Chuyên Biệt — Gotenberg 8

- **Mục đích sử dụng**: Gotenberg là microservice chuyên trách chạy LibreOffice và Chromium headless.
- **Nghiệp vụ thực tế**: Khi Trợ lý Soạn thảo Văn bản (`drafting_assistant`) sinh xong văn bản Word theo chuẩn Nghị định 30/2020/NĐ-CP, Gotenberg chịu trách nhiệm render và xuất ra bản PDF hoàn chỉnh có đầy đủ canh lề chuẩn quy phạm (trái 30mm, phải 15mm, trên/dưới 20mm), sẵn sàng in ấn hoặc ký số.

---

## 5. Bảng Khuyến Nghị Cấu Hình Máy Chủ (Sizing Guide)

| Môi Trường | Số Người Dùng Đồng Thời | vCPU | RAM | Dung Lượng Ổ Cứng (NVMe) | Ghi Chú |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Thử nghiệm / Demo** | 10 – 30 | 2 – 4 cores | 4 – 8 GB | 30 – 50 GB | Đủ chạy trọn bộ 7 containers trên 1 VPS nhỏ. |
| **Production Đề Tài** | 50 – 200 | 4 – 8 cores | 8 – 16 GB | 80 – 120 GB | Mức khuyến nghị chính thức phục vụ nghiệm thu và chạy thử toàn trường. |
| **Mở Rộng Toàn Trường**| 500+ | 8 – 16 cores| 16 – 32 GB| 200 – 500 GB | Có thể bổ sung thêm container Worker và nâng cấp RAM cho Qdrant/PostgreSQL. |
