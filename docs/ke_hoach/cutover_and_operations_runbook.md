# Sổ Tay Vận Hành & Hướng Dẫn Cắt Chuyển (Operations & Cutover Runbook)
### Quy trình "Tiếp Nhận Một Lần – Xuất Bản Tri Thức An Toàn" (ADR-011 / Kế Hoạch 11)

Tài liệu này cung cấp hướng dẫn vận hành chuẩn (SOP), các kịch bản kiểm soát rủi ro, và quy trình xử lý sự cố trong quá trình vận hành hệ thống xuất bản tri thức V2 trên QNU AI Platform.

---

## 1. Tổng Quan Kiến Trúc V2 & Trạng Thái Cắt Chuyển (Cutover Status)

Theo kiến trúc [ADR-011](../adr/ADR-011-immutable-document-revisions-and-safe-knowledge-publishing.md):
- **Kho Tài Liệu Tập Trung (Document Repository)**: Là Nguồn Sự Thật Duy Nhất (Single Source of Truth), quản lý các tệp gốc và chuỗi phiên bản bất biến (`DocumentRevision` v1, v2,...).
- **Kho Tri Thức (Knowledge Base)**: Không sở hữu tệp trực tiếp, chỉ liên kết qua `KnowledgeBinding` và phát hành các bản chỉ mục Staging (`KnowledgeIndexRevision`).
- **Cơ Chế Phục Vụ (Serving Mechanism)**: Hoán đổi con trỏ nguyên tử (Atomic Pointer Swap CAS) và cố định phiên truy vấn `RetrievalSnapshot` dùng chung cho Dense, Sparse FTS, Facts và Citations.
- **Trạng thái Cutover (Pha 7)**:
  * Biến môi trường: `RAG_REVISION_READ_MODE=revisioned` (Kích hoạt 100% Snapshot Isolation).
  * Biến môi trường: `KNOWLEDGE_REVISION_WRITES_ENABLED=true`.
  * Biến môi trường: `KNOWLEDGE_GC_RETENTION_REVISIONS=2` (Bảo lưu 2 bản lịch sử cho Instant Rollback).
  * Các API Legacy (`/collections/{id}/upload`, `/collections/{id}/reindex`, `/documents/{id}/reindex`) được đánh dấu `Deprecated: @2026-10-07`.

---

## 2. Quy Trình Vận Hành Thường Nhật (Daily Operations SOP)

### 2.1. Nạp Tài Liệu Nguồn Mới
1. Người dùng tải tệp lên qua giao diện **Kho Tài Liệu** (`POST /platform/v1alpha1/documents/intake`).
2. Hệ thống kiểm tra trùng lặp mã băm SHA-256 (`file_hash`):
   - Nếu tệp đã có: tạo phiên bản tiếp theo `v(N+1)` của tài liệu đó.
   - Nếu tệp mới: tạo bản ghi `RepositoryDocument` và phiên bản `v1`.
3. Worker ARQ bóc tách nội dung Markdown sạch, trích xuất siêu dữ liệu thể thức hành chính theo NĐ 30/2020/NĐ-CP.
4. Động cơ **Quality Gate** tự động thẩm định:
   - Mật độ ký tự văn bản $\ge 0.5$.
   - Bảng biểu được bảo toàn (bảo tồn cú pháp Markdown table).
   - Kiểm tra sạch mã font UTF-8 NFC (không có ký tự Mojibake `\ufffd`).
5. Cán bộ thẩm định duyệt phiên bản sang trạng thái `ready`.

### 2.2. Xuất Bản Vào Kho Tri Thức
1. Tại Kho Tri Thức, cán bộ mở Tab **Liên kết V2 (ADR-011)**.
2. Nhấn **"+ Liên Kết Tài Liệu Từ Kho"**, chọn các tài liệu có trạng thái `ready`.
3. Nhấn **"Dựng Index Staging"** (`POST /knowledge/bindings/{id}/build-staging-index`):
   - Chunks và Facts được sinh trong không gian cô lập `index_revision_id` nháp.
   - Cổng kiểm định Parity Gate so khớp 100% số lượng (`expected_chunks == vector_count == lexical_count`).
4. Nhấn **"Kích Hoạt Nguyên Tử (Promote)"** (`POST /knowledge/bindings/{id}/promote`):
   - Con trỏ `active_index_revision_id` chuyển sang bản mới trong $O(1)$.
   - `active_epoch` tăng lên, vô hiệu hóa tự động toàn bộ cache cũ.
   - Truy vấn người dùng chuyển sang dữ liệu mới với Zero Downtime.

---

## 3. Kịch Bản Xử Lý Sự Cố (Incident Response Runbooks)

### Kịch Bản 1: Phát Hiện Dữ Liệu Lỗi Sau Khi Kích Hoạt (Cần Rollback Tức Thì)
- **Triệu chứng**: Trợ lý AI trả lời sai do văn bản mới có thông tin chưa chuẩn hoặc bảng bị lỗi.
- **Hành động khắc phục**: Sử dụng tính năng **Instant Zero-Reindex Rollback** ($O(1)$):
  1. Gọi API:
     ```bash
     POST /platform/v1alpha1/knowledge/bindings/{binding_id}/rollback
     Content-Type: application/json

     {
       "target_index_revision_id": "<id_cua_revision_lich_su>",
       "expected_epoch": <epoch_hien_tai>,
       "reason": "Hoàn tác khẩn cấp do văn bản mới bị lỗi thông tin"
     }
     ```
  2. Hệ thống sẽ hoán đổi con trỏ `active_index_revision_id` về revision lịch sử, tăng `active_epoch`, và kích hoạt lại payload points trong Qdrant.
  3. **Thời gian phục hồi**: `< 1 giây`, hoàn toàn không cần tính toán embedding lại.

---

### Kịch Bản 2: Parity Gate Không Đạt (Count Mismatch)
- **Triệu chứng**: Khi dựng staging index, `parity_report.passed == false`.
- **Nguyên nhân**: Mạng gián đoạn trong lúc nạp vector vào Qdrant, hoặc số chunks trong DB lệch với Qdrant points.
- **Biện pháp bảo vệ**: Hệ thống tự động **CHẶN HOÀN TOÀN** lệnh Kích Hoạt (`promote`). Revision hiện tại đang phục vụ người dùng vẫn hoạt động 100% bình thường (Zero Impact).
- **Hành động khắc phục**:
  1. Kiểm tra log chi tiết: `GET /platform/v1alpha1/knowledge/bindings/{binding_id}/revisions`.
  2. Bấm **"Thử lại dựng staging index"** để pipeline tính toán lại vector.

---

### Kịch Bản 3: Di Trú Kho Tri Thức Cũ Lên V2 (Legacy Backfill)
- **Mục tiêu**: Đưa các tài liệu nạp theo cách cũ vào quy trình quản lý V2.
- **Thực hiện**:
  1. **Bước 1 — Kiểm kê (Audit)**:
     ```bash
     POST /platform/v1alpha1/knowledge/collections/{collection_id}/canary/audit
     ```
     Xem tỷ lệ `active_parity_ok_count` vs `needs_rebuild_count`.
  2. **Bước 2 — Di trú an toàn (Idempotent Backfill)**:
     ```bash
     POST /platform/v1alpha1/knowledge/collections/{collection_id}/canary/backfill
     Content-Type: application/json

     {
       "force_rebuild": false,
       "default_chunk_strategy": "ClauseBasedChunker"
     }
     ```
  3. **Bước 3 — Đối soát Shadow Retrieval**:
     ```bash
     POST /platform/v1alpha1/knowledge/collections/{collection_id}/canary/shadow-test
     Content-Type: application/json

     {
       "query": "Học phí và tiêu chuẩn xét tuyển 2026",
       "top_k": 5
     }
     ```
     Xác nhận `retrieval_revision_leak_total == 0` và Jaccard similarity $\ge 0.8$.

---

### Kịch Bản 4: Dọn Dẹp Chỉ Mục Cũ (Artifact Garbage Collection)
- **Mục tiêu**: Thu hồi dung lượng đĩa PostgreSQL và RAM của vector database Qdrant mà vẫn đảm bảo an toàn cho tính năng Rollback.
- **Nguyên tắc bảo vệ Rollback**: Luôn giữ lại revision `active` và $N=2$ bản lịch sử `superseded` gần nhất cho mỗi tài liệu. Chỉ các bản cũ hơn $N$ và bản `failed` mới bị dọn.
- **Thực hiện**:
  1. **Chạy mô phỏng trước (Dry-run)**:
     ```bash
     POST /platform/v1alpha1/knowledge/collections/{collection_id}/gc
     Content-Type: application/json

     {
       "keep_revisions": 2,
       "dry_run": true
     }
     ```
     Kiểm tra số lượng chunks/facts/points dự kiến sẽ được giải phóng trong `GarbageCollectionReport`.
  2. **Thực thi dọn dẹp thật**:
     ```bash
     POST /platform/v1alpha1/knowledge/collections/{collection_id}/gc
     Content-Type: application/json

     {
       "keep_revisions": 2,
       "dry_run": false
     }
     ```
  3. Hoặc nhấn nút **"Dọn Chỉ Mục Cũ (GC)"** ngay trên thanh công cụ của Tab Liên kết V2 trên giao diện quản trị.

---

## 4. Bảng Tra Cứu Mã Lỗi Chuẩn RFC 7807

| Mã Lỗi (`code`) | HTTP Status | Mô Tả & Cách Xử Lý |
|---|:---:|---|
| `CAS_EPOCH_CONFLICT` | **409** | Xung đột phiên bản con trỏ (Race Condition). Có người khác vừa kích hoạt revision mới. Cần F5 làm mới giao diện và thử lại. |
| `PARITY_GATE_FAILED` | **422** | Số vector trong Qdrant không khớp với số chunks trong PostgreSQL. Bị chặn kích hoạt để chống mất mát dữ liệu. Cần rebuild lại staging index. |
| `REVISION_ALREADY_PRUNED` | **400** | Cố gắng rollback về một revision đã bị dọn dẹp an toàn theo chính sách lưu trữ. Cần tạo staging index mới từ source revision thay vì rollback trực tiếp. |
| `INVALID_ROLLBACK_TARGET` | **400** | Revision mục tiêu đang ở trạng thái `failed` hoặc `building`, không thể chọn làm điểm phục hồi. |
| `REVISION_NOT_READY` | **400** | Tài liệu nguồn chưa được thẩm định chất lượng sang trạng thái `ready`. Cần duyệt qua Quality Gate trước khi liên kết. |

---

## 5. Danh Mục Chỉ Số Giám Sát (Key Health Metrics)

- `retrieval_revision_leak_total`: Bắt buộc luôn bằng **0**. Nếu $> 0$, kích hoạt cảnh báo đỏ (P0 Alert) vì có rò rỉ tri thức staging.
- `index_activation_total`: Số lượt kích hoạt nguyên tử thành công.
- `index_rollback_total`: Số lượt hoàn tác khẩn cấp.
- `parity_gate_failure_total`: Số lần kiểm định parity không khớp.
- `qdrant_point_count_delta`: Độ chênh lệch giữa số vector thực tế và số lượng chunks được ghi nhận trong CSDL.
