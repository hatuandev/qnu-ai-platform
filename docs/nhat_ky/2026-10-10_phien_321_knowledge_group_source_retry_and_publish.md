# NHẬT KÝ LÀM VIỆC — PHIÊN #321 (2026-10-10)
## Hoàn Thiện Triệt Để 7 Vấn Đề Quy Trình Nguồn Nhóm Kho Tri Thức: Phân Loại Diff, Tái Sử Dụng Staging, Cấm Xuất Bản Revision Cũ, Frontend Retry Decision & Safe Test Persistence

> **Thời gian**: 2026-10-10 17:35 (UTC+7)  
> **Người thực hiện**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
> **Phạm vi thực hiện**: `backend/app/modules/knowledge/services/`, `backend/tests/`, `frontend/src/features/knowledge/`  
> **Trạng thái**: **HOÀN THÀNH 100% — PRODUCTION-READY & ZERO TEST FAILURES**

---

### 1. Bối Cảnh & Mục Tiêu Cốt Lõi

Sau phiên #320, quy trình đồng bộ và xuất bản từ Nhóm tài liệu vào Kho tri thức (`Document Group → KnowledgeGroupSource → Staging Index → Promote Active Index → Active RAG`) đã có nền tảng phân loại cơ bản. Tuy nhiên, qua rà soát chi tiết còn tồn đọng 7 khiếm khuyết ảnh hưởng đến tính toàn vẹn trạng thái và trải nghiệm người dùng:

1. **Không đánh dấu `ready` khi mới xuất bản một phần**: `publish_group_source` còn nhánh `elif published_count > 0: source.status = "ready"` vi phạm Single Source of Truth; cần dùng `resolve_group_source_state` với `eligible_doc_count = len(desired_pairs)`.
2. **Binding cũ chưa gắn nguồn (`group_source_id=None`)**: Bị đếm nhầm vào `unchanged_docs` khiến hệ thống bỏ sót không adopt vào nguồn nhóm.
3. **Tái sử dụng staging ready khi retry promote**: Khi đã có staging index `ready` cho target revision, `sync_group_source(auto_publish=True)` cần promote trực tiếp mà không build lại; khi `auto_publish=False` giữ `review_required`.
4. **Cấm xuất bản staging của revision cũ**: Tránh promote nhầm staging revision cũ nếu tài liệu đã có target revision mới hơn trong nhóm.
5. **Nút "Thử lại" trên frontend mơ hồ**: Không biết nên gọi API `publish` hay `sync`; chưa tách bạch giữa cờ cần build chỉ mục (`needsBuild`) và trạng thái tổng thể.
6. **Test retry promote dùng chuỗi SQL mơ hồ**: Dễ vỡ khi thay đổi câu lệnh SELECT/UPDATE; cần kiểm tra trực tiếp qua hàm `promote_index_revision` và `build_staging_index`.
7. **Test PostgreSQL persistence hardcode CSDL dev**: Nguy cơ ghi đè dữ liệu phát triển; cần đọc qua `TEST_DATABASE_URL`, kiểm tra database name chứa `test`, skip an toàn khi thiếu biến.

---

### 2. Chi Tiết Thay Đổi & Giải Pháp Kỹ Thuật

#### 2.1. Backend: Phân Loại Diff & State Resolver (`group_source_diff_service.py`)
- **Single Source of Truth cho trạng thái nguồn**: Cập nhật `resolve_group_source_state` nhận `eligible_doc_count: int` (tổng số tài liệu có revision hợp lệ trong nhóm) làm mẫu số đối chiếu.
  - Chỉ khi `active_count == eligible_doc_count` mới chuyển sang `ready`.
  - Nếu `failed_count > 0` và có staging chờ duyệt: ưu tiên `review_required` để người dùng kiểm tra hoặc `failed` nếu không có staging nào.
- **Phân loại `adoptable_docs`**: Khi binding đã trỏ đúng `repository_document_id` và `source_revision_id == target_revision.id` nhưng `group_source_id is None`, đưa vào danh sách `adoptable_docs`. Các binding này sẽ được cập nhật `group_source_id = source.id` trong transaction mà không cần build lại staging, và **không tính vào `unchanged_docs`** để số liệu diff phản ánh chính xác.
- **Phân loại `awaiting_publish_docs`**: Khi binding đã có index revision `ready` khớp đúng `target_revision.id` nhưng chưa `active`, xếp vào `awaiting_publish_docs`. Khi `sync` với `auto_publish=True`, service sẽ promote trực tiếp staging này mà không cần build lại.

#### 2.2. Backend: Tái Sử Dụng Staging Khi Sync & Retry (`group_source_sync_service.py`)
- Adopt các `adoptable_docs` bằng cách cập nhật `binding.group_source_id = source.id` ngay đầu quy trình.
- Duyệt qua `awaiting_publish_docs`: nếu `auto_publish=True`, gọi `_binding_service.promote_index_revision(target_ready_rev.id)` trực tiếp; nếu `auto_publish=False`, đánh dấu là staging chờ xuất bản mà không trigger `build_staging_index`.
- Tính toán chính xác `active_bindings_count` sau khi sync/promote để truyền vào `resolve_group_source_state(source_status="pending", ...)`.

#### 2.3. Backend: Cấm Xuất Bản Staging Revision Cũ (`group_source_publish_service.py`)
- Xây dựng bản đồ `target_rev_by_doc = {doc_id: rev.id for doc_id, rev in desired_pairs}`.
- Khi lọc các `publishable_revisions`, kiểm tra nghiêm ngặt `rev.source_revision_id == target_rev_by_doc.get(binding.repository_document_id)`. Bỏ qua bất kỳ staging revision nào thuộc về phiên bản cũ hơn.
- Xóa bỏ triệt để nhánh `elif published_count > 0: source.status = "ready"`. Trạng thái sau xuất bản được xác định 100% qua `resolve_group_source_state`.

#### 2.4. Backend: Độc Lập Service Instance Trong Facade (`group_source_service.py`)
- Khởi tạo `self._diff_service = diff_service or GroupSourceDiffService()` trong `__init__` thay vì chia sẻ module-level instance.
- Triệt tiêu hoàn toàn rò rỉ mock state giữa các test case trong Pytest suite (`StopAsyncIteration` do mock exhaustion).
- Dọn dẹp các import không sử dụng (`select`, `distinct`, `IndexBuildService`, `BindingService`).

#### 2.5. Backend: Sửa Test Retry Promote & Safe Persistence (`test_knowledge_group_sources.py`)
- **Test Retry Promote**: Mock `promote_index_revision` và `build_staging_index`, chứng minh:
  - `build_staging_index.assert_not_called()` (không tốn tài nguyên build lặp lại).
  - `promote_index_revision.assert_called_once()` (promote staging có sẵn thành công).
- **Test PostgreSQL Persistence**:
  - Đọc `test_db_url = os.getenv("TEST_DATABASE_URL")`.
  - Bỏ qua an toàn (`pytest.skip`) nếu không có biến môi trường hoặc URL không chứa `test`.
  - Khởi tạo engine tạm thời với `echo=False`, kiểm tra ràng buộc `nullable=False` trên bảng `knowledge_bindings` thật.

#### 2.6. Frontend: Thuật Toán Ra Quyết Định Retry (`retry-decision.ts`)
- Tạo module chuyên biệt `@/features/knowledge/utils/retry-decision.ts` xuất hàm thuần túy `resolveRetryAction(source)`:
  - Ưu tiên 1: Nếu `(source.publishable_count ?? 0) > 0` hoặc `(source.awaiting_publish_count ?? 0) > 0`, hành động là `'publish'`.
  - Ưu tiên 2: Ngược lại, hành động là `'sync'` với payload `{ auto_publish: false }`.
- Viết 4 unit tests toàn diện trong `retry-decision.test.ts` kiểm chứng mọi nhánh điều kiện:
  1. Có `publishable_count > 0` → trả về `publish`.
  2. Có `awaiting_publish_count > 0` nhưng `publishable_count = 0` → trả về `publish`.
  3. Có lỗi và `needs_build_count > 0` nhưng không có staging → trả về `sync`.
  4. Trạng thái bình thường/rỗng → fallback về `sync`.

#### 2.7. Frontend: Cập Nhật Trang Chi Tiết Nguồn (`source-detail-page.tsx`)
- Tích hợp `handleRetry` sử dụng `resolveRetryAction(source)`.
- Tách derived state `needsBuild = (source.needs_build_count ?? 0) > 0` độc lập với nút Thử lại.
- Dọn dẹp các biến không sử dụng (`hasChanges`, `isPublishing`) thỏa mãn 100% linter và compiler.

---

### 3. Tệp Tin Thay Đổi (Changelog)

| Phân Hệ | Tệp Tin | Mô Tả Thay Đổi |
| :--- | :--- | :--- |
| **Backend** | `backend/app/modules/knowledge/services/group_source_diff_service.py` | Bổ sung `adoptable_docs`, `awaiting_publish_docs`; chuẩn hóa `resolve_group_source_state` với `eligible_doc_count`. |
| **Backend** | `backend/app/modules/knowledge/services/group_source_sync_service.py` | Xử lý adopt binding cũ và promote staging chờ; dùng `resolve_group_source_state`. |
| **Backend** | `backend/app/modules/knowledge/services/group_source_publish_service.py` | Lọc staging theo target revision hiện tại; xóa bỏ gán `ready` một phần; chuẩn hóa state. |
| **Backend** | `backend/app/modules/knowledge/services/group_source_service.py` | Instance-level `diff_service` chống mock leak; dọn dẹp unused imports. |
| **Backend Tests** | `backend/tests/test_knowledge_group_sources.py` | Hoàn thiện 18 test cases; kiểm tra staging reuse qua call assertion; an toàn persistence test. |
| **Frontend** | `frontend/src/features/knowledge/utils/retry-decision.ts` | Thuật toán `resolveRetryAction` phân loại hành động `publish` vs `sync`. |
| **Frontend Tests**| `frontend/src/features/knowledge/utils/retry-decision.test.ts` | 4 test cases cho Node native test runner. |
| **Frontend** | `frontend/src/features/knowledge/source-detail-page.tsx` | Tích hợp `handleRetry`, `needsBuild`; dọn dẹp unused state. |

---

### 4. Kết Quả Kiểm Thử & Quality Gates

#### 4.1. Backend Ruff Linter
```bash
uv run ruff check app/modules/knowledge tests/test_knowledge_group_sources.py
```
- **Kết quả**: `All checks passed!` (0 cảnh báo, 0 lỗi).

#### 4.2. Pytest Unit & Regression Suites
```bash
uv run --extra dev pytest tests/test_knowledge_group_sources.py
```
- **Kết quả**: `17 passed, 1 skipped in 2.85s` (100% passed). Test persistence tự động skip an toàn do không có `TEST_DATABASE_URL` chứa `test`.

```bash
uv run --extra dev pytest tests/test_document_repository_workflow.py tests/test_rag.py tests/test_knowledge_publishing_v2.py
```
- **Kết quả**: `58 passed in 8.12s` (100% passed, 0 regressions).

#### 4.3. Frontend Unit Tests (Node 24 Native Test Runner)
```bash
node --experimental-strip-types --import ./src/app/auth/test-loader.mjs --test src/features/knowledge/utils/retry-decision.test.ts
```
- **Kết quả**: `✔ resolveRetryAction suite (4 tests) (passed 100%)`.

#### 4.4. Frontend Build & Typecheck
```bash
npm run build
```
- **Kết quả**: Vite v6 + TypeScript typecheck thành công trong 3.12s (Exit code 0, 0 lỗi).

---

### 5. Bài Học Kinh Nghiệm & Khuyến Nghị Vận Hành

1. **Mock Isolation trong Python Tests**: Tránh sử dụng module-level singleton services trong các lớp facade khi các service đó có thể bị mock `side_effect` trong unit test. Luôn khởi tạo instance riêng trong constructor để mỗi unit test hoàn toàn độc lập.
2. **Deterministic State Resolution**: Trạng thái của một aggregate phức tạp (`KnowledgeGroupSource`) phải luôn được tính toán dựa trên tập hợp số lượng thực tế (`eligible_doc_count`, `active_count`, `staging_ready_count`, `failed_count`), tuyệt đối không dựa vào các cờ tạm thời trong luồng chạy.
3. **Frontend Test Module Extension**: Khi dự án cấu hình `allowImportingTsExtensions: false`, các file test chạy bằng Node native test runner nên import không kèm đuôi `.ts` và dựa vào ESM loader hook để tương thích đồng thời cả `tsc` và Node runner.
