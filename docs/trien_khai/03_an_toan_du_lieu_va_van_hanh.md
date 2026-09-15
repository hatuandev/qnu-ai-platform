# An Toàn Dữ Liệu, Sao Lưu & Xử Lý Sự Cố Vận Hành

Tài liệu này cung cấp các nguyên tắc an toàn dữ liệu, phương án sao lưu dự phòng và hướng dẫn xử lý các sự cố kỹ thuật phổ biến khi vận hành hệ thống **QNU AI Platform** trên nền tảng Dokploy.

---

## 🛡️ 1. Cơ Chế Lưu Trữ Bền Vững (Data Persistence)

Khi triển khai trên Docker/Dokploy, một trong những nỗi lo lớn nhất của đội ngũ là: *"Liệu khi cập nhật hoặc restart container, dữ liệu có bị mất không?"*

Hệ thống được thiết kế với **5 Named Volumes độc lập với vòng đời của container**:

| Tên Volume | Thành Phần Gắn Kết | Dữ Liệu Chứa Bên Trong | Khả Năng Bảo Toàn |
| :--- | :--- | :--- | :---: |
| **`postgres_data`** | PostgreSQL 16 | Toàn bộ dữ liệu quan hệ, bảng sự thật số liệu, người dùng, nhật ký chi phí LLM. | **Bền vững 100%** |
| **`qdrant_data`** | Qdrant Vector DB | Các vector embedding 1024D từ mô hình BGE-M3 và chỉ mục payload. | **Bền vững 100%** |
| **`minio_data`** | MinIO Object Storage | Các tệp gốc PDF, DOCX, XLSX và văn bản xuất chuẩn Nghị định 30. | **Bền vững 100%** |
| **`redis_data`** | Redis 7 | Dữ liệu bộ đệm ngữ nghĩa Semantic Cache và trạng thái hàng đợi jobs. | **Bền vững 100%** |
| **`backend_storage`**| Backend & Worker | Các tệp xử lý tạm thời và bản sao lưu snapshot cục bộ. | **Bền vững 100%** |

> **Quy tắc vàng**: Việc Re-build image, Restart container, hoặc Deploy phiên bản mới trên Dokploy **chỉ thay đổi mã nguồn tầng ứng dụng**, toàn bộ dữ liệu nằm trong các volume trên hoàn toàn không bị ảnh hưởng.

---

## 💾 2. Quy Trình Sao Lưu Dữ Liệu (Backup & Disaster Recovery)

### 2.1. Sao lưu Cơ sở dữ liệu PostgreSQL
Có thể thực hiện trực tiếp từ máy chủ VPS bằng lệnh `pg_dump`:
```bash
# Tạo bản sao lưu CSDL nén gzip kèm dấu thời gian
docker exec qnu_postgres pg_dump -U qnu -d qnu_ai_platform | gzip > /backup/qnu_db_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 2.2. Phục hồi Cơ sở dữ liệu (Restore)
Khi cần khôi phục lại dữ liệu từ tệp sao lưu:
```bash
gunzip -c /backup/qnu_db_xxxx.sql.gz | docker exec -i qnu_postgres psql -U qnu -d qnu_ai_platform
```

### 2.3. Sao lưu Kho tệp tin MinIO
Dữ liệu tệp tin trong MinIO có thể được đồng bộ sang ổ cứng gắn ngoài hoặc dịch vụ lưu trữ phụ bằng công cụ `mc` (MinIO Client):
```bash
mc alias set local http://localhost:9000 qnu_minio_admin <SECRET_KEY>
mc mirror local/qnu-ai-documents /backup/minio_documents/
```

---

## 🚨 3. Bảng Xử Lý Các Sự Cố Phổ Biến (Troubleshooting Runbook)

### Sự cố 1: Lỗi 504 Gateway Timeout khi hỏi đáp câu hỏi dài
- **Hiện tượng**: Người dùng hỏi một câu hỏi phức tạp hoặc yêu cầu soạn thảo văn bản dài, sau 30-60 giây trình duyệt báo lỗi `504 Gateway Time-out`.
- **Nguyên nhân**: Traefik Proxy mặc định đóng kết nối nếu thời gian phản hồi quá ngưỡng timeout.
- **Cách khắc phục**:
  - Kiểm tra trong cấu hình Traefik labels của `backend` đã có các nhãn đệm stream chưa:
    ```yaml
    - "traefik.http.middlewares.qnu-backend-stream.buffering.maxRequestBodyBytes=52428800"
    - "traefik.http.middlewares.qnu-backend-stream.buffering.memRequestBodyBytes=52428800"
    ```

---

### Sự cố 2: Trợ lý AI trả lời "Hệ thống tạm thời quá tải" (Circuit Breaker kích hoạt)
- **Hiện tượng**: Người dùng hỏi và nhận được thông báo lỗi kèm mã `QUOTA_EXCEEDED` hoặc `PROVIDER_TEMPORARILY_UNAVAILABLE`.
- **Nguyên nhân**:
  1. Khóa API OpenAI hết tiền (Quota Exceeded) hoặc bị Rate Limit (HTTP 429).
  2. Circuit Breaker của module `modelops` đã chuyển từ trạng thái `CLOSED` sang `OPEN` để bảo vệ hệ thống không bị treo.
- **Cách khắc phục**:
  - Kiểm tra số dư tài khoản trên OpenAI Platform Dashboard.
  - Kiểm tra biến môi trường `GEMINI_API_KEY` đã được điền chưa. Nếu có Gemini, hệ thống sẽ tự động fallback sang mô hình phụ `gemini-1.5-flash` mà không làm gián đoạn người dùng.
  - Xem bảng `llm_usage_logs` trong PostgreSQL để tra cứu chi tiết thông điệp lỗi:
    ```sql
    SELECT provider, model_name, status, error_message, created_at 
    FROM llm_usage_logs 
    WHERE status = 'error' 
    ORDER BY created_at DESC LIMIT 10;
    ```

---

### Sự cố 3: Tải file lên báo lỗi "MinIO Connection Refused"
- **Hiện tượng**: Bấm upload tài liệu trên giao diện bị báo lỗi không thể kết nối đến kho lưu trữ.
- **Nguyên nhân**: Container `qnu_minio` chưa đạt trạng thái `healthy` hoặc bucket `qnu-ai-documents` chưa được tạo.
- **Cách khắc phục**:
  - Kiểm tra log của container minio: `docker logs qnu_minio`.
  - Backend của hệ thống đã có cơ chế tự động tạo bucket (`check_or_create_bucket`) khi khởi động. Nếu chưa có, có thể đăng nhập vào MinIO Console (cổng 9001) để tạo bucket có tên `qnu-ai-documents`.

---

### Sự cố 4: Container Backend báo trạng thái `unhealthy`
- **Hiện tượng**: Dokploy hiển thị container `backend` màu đỏ hoặc liên tục restart.
- **Nguyên nhân**: Probe `/health/live` thất bại hoặc kết nối đến PostgreSQL/Redis bị từ chối do sai mật khẩu.
- **Cách khắc phục**:
  - Chạy lệnh xem log chi tiết: `docker logs qnu_backend --tail 100`.
  - Kiểm tra lại các biến môi trường `DATABASE_URL`, `REDIS_URL`, `POSTGRES_PASSWORD` trong tab Environment trên Dokploy đảm bảo trùng khớp giữa các dịch vụ.
