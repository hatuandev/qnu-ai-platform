# QUY TRÌNH 01: KHỞI ĐỘNG & VÒNG ĐỜI NỀN TẢNG (BOOT SEQUENCE & PLATFORM LIFECYCLE)

Tài liệu này mô tả chi tiết thứ tự điều phối nạp các container, kiểm tra tính sẵn sàng (Healthcheck Probes) và khởi tạo kết nối hạ tầng khi nền tảng khởi động.

---

## 1. Sơ Đồ Tuần Tự Khởi Động (Boot Sequence Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    participant DC as Docker Compose Engine
    participant DB as PostgreSQL 16 (Port 5432)
    participant QD as Qdrant DB (Port 6333)
    participant RD as Redis 7 (Port 6379)
    participant MN as MinIO S3 (Port 9000/9001)
    participant API as FastAPI Backend (Port 8001)
    participant WK as ARQ Worker Container

    Note over DC: 1. Khởi chạy cụm Cơ sở dữ liệu & Lưu trữ (Tầng 1)
    DC->>DB: docker run qnu_postgres (PostgreSQL 16 Alpine)
    DC->>QD: docker run qnu_qdrant (Qdrant v1.11.0)
    DC->>RD: docker run qnu_redis (Redis 7 Alpine)
    DC->>MN: docker run qnu_minio (MinIO Server)

    Note over DB,MN: 2. Thăm dò trạng thái sức khỏe (Healthchecks)
    loop Mỗi 5 giây
        DC->>DB: pg_isready -U qnu -d qnu_ai_platform
        DB-->>DC: Sẵn sàng nhận kết nối (healthy)
        DC->>QD: curl -f http://localhost:6333/readyz
        QD-->>DC: HTTP 200 OK (healthy)
        DC->>RD: redis-cli ping
        RD-->>DC: PONG (healthy)
        DC->>MN: curl -f http://localhost:9000/minio/health/live
        MN-->>DC: HTTP 200 OK (healthy)
    end

    Note over DC,API: 3. Khởi chạy Backend Application (Tầng 2)
    DC->>API: docker run qnu_backend (depends_on: DB, QD, RD, MN healthy)
    API->>API: FastAPI lifespan startup event
    API->>DB: Tạo Connection Pool SQLAlchemy Async (asyncpg, size=15)
    API->>QD: Kiểm tra collection 'qnu_knowledge_chunks' (1024 chiều)
    API->>MN: Kiểm tra / tự tạo bucket 'qnu-ai-documents'
    API->>API: Đăng ký Global RFC 7807 Error Handlers
    API->>API: Nạp danh mục 05 Trợ lý AI QNU vào RAM
    API-->>DC: Healthcheck probe /health/live OK (Port 8001)

    Note over DC,WK: 4. Khởi chạy Async Background Worker (Tầng 3)
    DC->>WK: docker run qnu_worker (depends_on: backend started, redis/minio healthy)
    WK->>RD: Kết nối ARQ Pool & lắng nghe tác vụ hàng đợi
    WK-->>DC: Worker sẵn sàng xử lý Ingestion, OCR & Export
```

---

## 2. Chi Tiết Các Bước Thực Thi

### Bước 1: Khởi động Hạ tầng Lưu trữ & CSDL (Tầng 1)
- **PostgreSQL 16**: Cấu hình bộ nhớ đệm `shared_buffers`, nạp extension tiếng Việt cho Full-Text Search.
- **Qdrant Vector DB**: Nạp engine lưu trữ vector trên ổ cứng tại volume `qnu_qdrant_data`.
- **Redis 7**: Nạp cơ chế semantic cache và lưu trữ hàng đợi tác vụ của ARQ.
- **MinIO S3**: Khởi tạo object storage server tại cổng `9000` (API) và `9001` (Console).

### Bước 2: Thăm Dò Sức Khỏe (Healthcheck Polling)
Để tránh hiện tượng `CrashLoopBackOff` khi Backend khởi động trước khi CSDL sẵn sàng:
- Lệnh kiểm tra PostgreSQL: `pg_isready -U qnu -d qnu_ai_platform`.
- Lệnh kiểm tra Qdrant: `curl -f http://localhost:6333/readyz || exit 1`.
- Lệnh kiểm tra Redis: `redis-cli ping`.
- Lệnh kiểm tra MinIO: `curl -f http://localhost:9000/minio/health/live || exit 1`.

### Bước 3: Vòng Đời Ứng Dụng FastAPI (`lifespan`)
Được quản lý trong hàm `lifespan(app: FastAPI)` tại [`app/main.py`](file:///d:/DuAnPhanMem/DeTaiAI/qnu-ai-platform/backend/app/main.py):
1. **Khởi tạo Logger có cấu trúc**: Đăng ký structlog định dạng JSON kèm `correlation_id`.
2. **Khởi tạo Connection Pool CSDL**: `asyncpg` mở sẵn 15 kết nối tới PostgreSQL.
3. **Đăng ký RFC 7807 Exception Handlers**: Bắt và chuẩn hóa toàn bộ lỗi ngoại lệ thành Problem Details.
4. **Graceful Shutdown**: Khi nhận tín hiệu `SIGTERM`, server ngưng nhận request mới, đợi các request đang chạy hoàn tất và đóng Connection Pool (`await engine.dispose()`).
