# NHẬT KÝ PHIÊN LÀM VIỆC SỐ 325
**Ngày thực hiện**: 2026-10-10
**Kỹ sư thực hiện**: Senior Full-Stack Architect & Enterprise AI Systems Specialist
**Mục tiêu chính**:
1. Khắc phục triệt để lỗi SQLAlchemy Mapper Initialization (`expression 'DocumentGroup' failed to locate a name ('DocumentGroup')`) và circular dependency giữa mô-đun `knowledge` và `documents`.
2. Rà soát toàn diện và chuẩn hóa đồng bộ 4 task runner files (`Makefile`, `make.ps1`, `make.bat`, `make` bash script).
3. Bổ sung các lệnh quản trị CSDL & Migration (`migrate`, `db-check`, `db-ready`), chất lượng mã nguồn (`lint`, `lint-fix`, `typecheck`, `build`), và kiểm thử chuẩn (`test`, `test-be`, `test-fe`).
4. Triệt tiêu các lỗi command không tồn tại (`npm run test:e2e`, thiếu `uv` trong PATH) và loại bỏ hoàn toàn các ghi chú lỗi thời (port 3001).

---

## 1. Bối Cảnh & Vấn Đề Phát Sinh

1. **Lỗi SQLAlchemy Mapper khi khởi động ứng dụng (`make dev` / `db ensure-ready`)**:
   - Khi chạy `python -m app.cli db ensure-ready`, SQLAlchemy ném lỗi:
     `InvalidRequestError: When initializing mapper Mapper[KnowledgeGroupSource(knowledge_group_sources)], expression 'DocumentGroup' failed to locate a name ('DocumentGroup').`
   - Nguyên nhân: Trong `app/modules/knowledge/models.py`, quan hệ `document_group` trỏ tới `'DocumentGroup'`, nhưng `DocumentGroup` chưa được nạp vào registry metadata của SQLAlchemy trước đó do circular dependency khi `documents.service` import từ `knowledge.models`.
2. **Lỗi khi chạy Alembic Migration ở thư mục gốc**:
   - Chạy `uv run alembic upgrade head` từ thư mục gốc bị lỗi: `FAILED: No 'script_location' key found in configuration.` do `alembic.ini` nằm trong thư mục `backend/`. Dev thiếu một lệnh tiện ích như `make migrate`.
3. **Lỗi trong lệnh kiểm thử `make test`**:
   - Cả 4 runner file cũ đều chạy `cd frontend && npm run test:e2e`. Trong `frontend/package.json` **hoàn toàn không có script `test:e2e`**, khiến lệnh test bị vỡ (`npm error Missing script: "test:e2e"`).
   - Lệnh backend chạy `uv run --extra dev pytest`, nhưng máy dev Windows không có `uv` trong biến môi trường PATH (`uv : The term 'uv' is not recognized`), trong khi virtualenv `.\.venv\Scripts\python.exe -m pytest` hoạt động hoàn hảo 100%.
4. **Thiếu lệnh kiểm soát chất lượng & CSDL thiết yếu**:
   - Thiếu `migrate`, `db-check`, `db-ready`, `lint`, `lint-fix`, `typecheck`, `build`, `reconcile`, `reindex`.
   - Các file `make.bat` và `make` còn chứa thông tin lỗi thời về `Port 3001` (tàn dư từ đợt tách frontend cũ).

---

## 2. Chi Tiết Các Thay Đổi & Giải Pháp Kỹ Thuật

### 2.1. Khắc Phục Triệt Để SQLAlchemy Mapper & Circular Dependency
- **`backend/app/modules/knowledge/models.py`**:
  - Import `DocumentGroup` từ `app.modules.documents.models`.
  - Khai báo kiểu relationship rõ ràng: `document_group: Mapped[DocumentGroup] = relationship("DocumentGroup", foreign_keys=[document_group_id], lazy="joined")`.
- **`backend/app/modules/documents/__init__.py`**:
  - Chuyển sang lazy loading qua `__getattr__` cho `documents_router` và `document_repository_service`, giúp phá vỡ vòng lặp nạp module.
- **`backend/app/modules/documents/service.py`**:
  - Xóa bỏ import `KnowledgeDocument` ở top-level (nguyên nhân gây circular import).
  - Bổ sung import cục bộ `from app.modules.knowledge.models import KnowledgeDocument` bên trong các hàm thực sự truy vấn (`list_repository_documents`, `get_document_usages`, `get_repository_stats`).
  - Đảm bảo 0 lỗi Ruff linter (`All checks passed!`).

### 2.2. Chuẩn Hóa Toàn Bộ 4 Task Runner Files
Đồng bộ 100% các targets và chức năng giữa 4 files:
- **`Makefile`**: Tương thích GNU Make, hỗ trợ biến và targets chuẩn.
- **`make.ps1`**: PowerShell script hiện đại, hỗ trợ tham số `ValidateSet`, tự nhận diện Python venv, phân nhóm màu sắc trực quan.
- **`make.bat`**: Windows CMD batch file dành cho command prompt truyền thống.
- **`make`**: Bash script cho Git Bash, WSL và Unix environments.

### 2.3. Bảng Danh Mục Lệnh Chuẩn Hóa Mới

| Nhóm | Lệnh | Mô tả chi tiết |
| :--- | :--- | :--- |
| **Hạ tầng Docker** | `infra-up` | Khởi động toàn bộ container hạ tầng (Postgres, Qdrant, Redis, MinIO, Gotenberg) |
| | `infra-down` | Dừng hạ tầng Docker |
| | `infra-status` | Kiểm tra trạng thái các container Docker (`docker compose ps`) |
| | `infra-logs` | Theo dõi logs của cụm Docker |
| **Phát triển (Dev)** | `dev` | Kiểm tra CSDL (`db ensure-ready`) và khởi chạy đồng thời Backend (8001) & Frontend (3000) |
| | `be` | Khởi chạy riêng Backend API (Port 8001) sau khi kiểm tra CSDL |
| | `fe` | Khởi chạy riêng Frontend Studio (Port 3000) |
| **CSDL & Migration** | `migrate` | Chạy migration CSDL lên Alembic HEAD (`python -m app.cli db migrate`) *(Mới)* |
| | `db-check` | Kiểm tra kết nối, schema và các bảng cốt lõi CSDL (`python -m app.cli db check`) *(Mới)* |
| | `db-ready` | Kiểm tra và tự động khởi tạo CSDL/seed nếu còn thiếu (`python -m app.cli db ensure-ready`) *(Mới)* |
| | `seed` | Khởi tạo CSDL và seed toàn bộ dữ liệu mặc định QNU AI Platform |
| | `reset-db` / `reseed` | Xóa sạch toàn bộ CSDL PostgreSQL & Qdrant, sau đó seed lại toàn bộ 5 mô-đun |
| **Kiểm thử tự động** | `test` | Chạy toàn bộ kiểm thử Backend (`pytest`) và Frontend (`npm test`) |
| | `test-be` | Chạy riêng kiểm thử Backend với Pytest *(Mới)* |
| | `test-fe` | Chạy riêng kiểm thử Frontend với Node native runner *(Mới)* |
| **Chất lượng mã nguồn** | `lint` | Kiểm tra linter Backend (Ruff) và Frontend (Biome) *(Mới)* |
| | `lint-fix` | Tự động sửa lỗi linter cả Backend và Frontend *(Mới)* |
| | `typecheck` | Kiểm tra kiểu dữ liệu TypeScript Frontend (`tsc --noEmit`) *(Mới)* |
| | `build` | Kiểm tra đóng gói build Frontend bundle (`vite build`) *(Mới)* |
| **Kho tri thức** | `reconcile` | Kiểm tra đối soát 4 tầng (Postgres, Qdrant, MinIO, Redis) *(Mới)* |
| | `reindex` | Đánh lại toàn bộ chỉ mục vector Qdrant *(Mới)* |
| **Trợ giúp** | `help` | Hiển thị bảng hướng dẫn sử dụng chuyên nghiệp, phân nhóm trực quan |

---

## 3. Kết Quả Kiểm Thử & Xác Minh (Verification)

1. **Khởi tạo và kiểm tra CSDL (`db ensure-ready`)**:
   - Chạy: `.\backend\.venv\Scripts\python.exe -m app.cli db ensure-ready`
   - Kết quả: `Exit Code 0`, `Database va du lieu nen tang QNU AI Platform: SAN SANG.`
2. **Kiểm tra Linter Backend (Ruff)**:
   - Chạy: `.\backend\.venv\Scripts\python.exe -m ruff check backend/app/modules/documents/service.py backend/app/modules/knowledge/models.py`
   - Kết quả: `All checks passed!` (0 lỗi).
3. **Kiểm tra Test Suite Nguồn Nhóm Tri Thức**:
   - Chạy: `.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_knowledge_group_sources.py`
   - Kết quả: `32 passed, 1 skipped in 3.07s` (100% test pass).
4. **Kiểm tra Thực Thi Trực Tiếp Các Task Runners**:
   - `powershell -ExecutionPolicy Bypass -File .\make.ps1 help`: Hoàn thành với mã 0, hiển thị đầy đủ bảng nhóm lệnh màu sắc.
   - `cmd /c make.bat help`: Hoàn thành với mã 0, hiển thị đầy đủ thông tin chuẩn hóa.
   - `Makefile`: Cú pháp tab chuẩn (`\t`), định nghĩa đầy đủ 25 `.PHONY` targets.

---

## 4. Trạng Thái & Bàn Giao

- **Trạng thái phiên**: **HOÀN THÀNH 100%**.
- **Tính sẵn sàng**: Các lập trình viên có thể sử dụng bất kỳ công cụ nào (`make`, `make.bat`, `make.ps1`, hoặc `./make`) với cú pháp hoàn toàn thống nhất.
