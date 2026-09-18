# Nhật Ký Phiên #96 — 2026-09-18
## Mục Tiêu
Sửa 1 test fail còn lại từ phiên #95 và đồng bộ tài liệu quy trình với các thay đổi kỹ thuật đã thực hiện trong WP2-WP4.

## Key Changes

### 1. Sửa test_seed_preserves_existing_user_configuration
- **Tệp**: `backend/app/modules/assistants/seeder.py`
- **Nguyên nhân lỗi**: Logic `update_stmt` được thêm bởi phiên session song song (#95) đã gây `StopAsyncIteration` vì Mock `db.execute.side_effect` cạn phần tử.
- **Fix**: Loại bỏ toàn bộ `update_stmt`, `existing_assistant = ...`, 3 dòng gán overwrite. Khi `code in existing_codes` → `continue` ngay, không thêm execute nào.
- **Ý nghĩa**: Seeder bảo toàn 100% cấu hình trợ lý do cán bộ/admin tùy chỉnh qua UI — không bị ghi đè mỗi lần khởi động.

### 2. Cập nhật docs/quy_trinh/02_nap_tri_thuc_minio.md
- Thêm **Bước 9**: Fact Reconciliation & Cascading Cleanup chống Ghost Vector.
- Mô tả chi tiết 4 tầng xóa đồng bộ: MinIO Storage, Qdrant Vectors, PostgreSQL (facts+chunks+docs), Redis Semantic Cache.

### 3. Cập nhật docs/quy_trinh/03_hybrid_rag_truy_xuat.md
- **Bước 4-5**: Nêu rõ `asyncio.gather` song song phi phong tỏa.
- **Bước 7-8**: Đổi tên thành "Evidence-Based Citation Filtering", mô tả `filter_evidence_citations` — xóa citation khi No-Answer, lọc false-positive khi có trả lời.
- **Bước 9 (mới)**: Model-Partitioned Semantic Cache — key format `rag:cache:{collection_id}:{model}:{hash(query)}`.
- **Bước 10**: Đổi số từ 9 → 10 (Answer Format Planner).

### 4. Cập nhật docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md
- Thêm **Mục 8**: Bảo Toàn Tính Toàn Vẹn Thực Thi.
  - 8.1: Immutable Version Resolution — bắt buộc đọc `dag_spec` từ `workflow_versions`, từ chối nếu không tìm thấy.
  - 8.2: Server-Side Approval Flag — KHÔNG tin client `is_approved`, chỉ đọc DB.
  - 8.3: Concurrent Execution Context Isolation — `AssistantRuntimeProfile` bất biến theo execution_id.

## Verification
- Ruff: 0 lỗi
- Pytest: 174/174 passed (100%)
- npm lint: 0 lỗi (124 files)
- npm typecheck: 0 lỗi
- npm build: OK 0 warnings (9.09s)
- Mojibake: 267/267 files sạch
