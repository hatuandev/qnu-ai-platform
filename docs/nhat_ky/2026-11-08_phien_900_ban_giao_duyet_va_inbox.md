# Nhật ký phiên 900 — Bàn giao duyệt và danh sách “Cần xử lý”

- Ngày: 2026-11-08.
- Nhánh: `feat/v1-user-workflow`, baseline `09a173a2`.
- Kế hoạch nguồn: [15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md), gói P4.
- Trạng thái: P4 đã triển khai, kiểm chứng trong phạm vi; P5–P7 chưa bắt đầu. Không commit/push.

## 1. Yêu cầu và giả định

Yêu cầu của người dùng: “tiếp tục giai đoạn 4” — bàn giao review có bản ghi riêng, hàng chờ duyệt và trang “Cần xử lý” đúng dữ liệu server.

Giả định đã dùng, bám theo P4 trong kế hoạch 15:

- Giữ nguyên enum xuất bản hiện có (`draft/approved/published/superseded/withdrawn`); submission chỉ là bản ghi bàn giao, không thay trạng thái xuất bản.
- Submission dùng trạng thái `pending`, `changes_requested`, `resolved`, `cancelled`; không backfill bản nháp cũ thành `pending`.
- Quyền: gửi duyệt admin/editor; yêu cầu sửa và duyệt theo gate hiện hành (admin/reviewer); rút yêu cầu admin hoặc chính người gửi; reviewer không cần quyền editor.
- Duyệt xong không tự xuất bản; approved không tự hiện “sẵn sàng tra cứu”.
- Inbox chỉ tổng hợp trạng thái thật của tài nguyên/submission; không có nút dismiss giả xử lý; không coi mọi job lỗi cũ là việc còn mở.

## 2. Thay đổi Backend

### 2.1. Domain review submission (mới)

`backendV1/qnu/domains/knowledge/review/` gồm `models.py`, `schemas.py`, `service.py`, `router.py`:

- Bảng ghim `document_id`, `version_id`, action (`submit/request_changes/cancel`), bundle hash và hash nội dung tại thời điểm preview; preview có hạn dùng và bị vô hiệu khi nội dung/phiên bản thay đổi.
- Endpoint scoped theo workspace/collection:
  - `POST /workspaces/{ws}/collections/{col}/review-submissions/previews` — xem trước hành động.
  - `POST /workspaces/{ws}/collections/{col}/review-submissions` — commit kèm `Idempotency-Key`.
  - `GET /workspaces/{ws}/collections/{col}/review-submissions` và `GET .../{submission_id}` — lịch sử/chi tiết.
- Chỉ phiên bản ở `draft`, `superseded`, `withdrawn` mới gửi duyệt (`SUBMITTABLE_STATUSES`); yêu cầu sửa bắt buộc có lý do; nội dung phiên bản bất biến, muốn sửa phải tạo phiên bản mới rồi gửi lại.
- Rút yêu cầu: admin hoặc đúng người gửi; trạng thái không còn `pending` thì bị từ chối.
- Chống trùng và cạnh tranh: khóa/sequence + idempotency; hai quyết định đồng thời không tạo trạng thái cuối mâu thuẫn.
- `resolve_on_approval` trong `service.py`: khi quyết định xuất bản hiện hành được áp dụng, submission đang mở của phiên bản được đóng trong cùng transaction, tránh hàng chờ ma.
- Mã lỗi RFC 7807 dùng chung: `review_submission_duplicate`, `changes_required`, `stale`, `forbidden`, `not_found`, `not_pending`, `version_invalid`, `review_preview_consumed/expired/mismatch/stale/not_found`, `idempotency_conflict`.

Migration `backendV1/alembic/versions/0016_review_submission.py` (down revision `0015_preparation_intent`); `qnu/platform/schema.py` cập nhật `SCHEMA_HEAD = "0016_review_submission"`. Cập nhật kèm: `alembic/env.py`, `docs/migration-ownership.yaml`, `lifecycle/purge_graph.py`, `workspaces/access.py`, `platform/ownership.py`, truncate trong `tests/integration/conftest.py`, baseline test migration.

### 2.2. Domain inbox (mới)

`backendV1/qnu/domains/knowledge/inbox/`:

- `GET /workspaces/{ws}/inbox?collection_id=&kind=&page=&page_size=` trả `InboxPage {items, meta, counts}`; chỉ đọc, không tạo run/job.
- Nguồn dữ liệu hợp nhất bằng SQL `UNION ALL` từ trạng thái thật:
  - `review_pending`: submission `pending`.
  - `changes_requested`: submission `changes_requested` chưa được thay thế.
  - `awaiting_publish`: phiên bản đã duyệt nhưng chưa xuất bản.
  - `preparation_failed`: chỉ lần chuẩn bị mới nhất thất bại (không coi job lỗi cũ).
  - `sync_incomplete`: collection chưa đồng bộ xong theo trạng thái hiện tại.
- `counts` tôn trọng bộ lọc collection nhưng không phụ thuộc bộ lọc kind; loại trừ lifecycle đã xóa/lưu trữ; quyền đọc theo `READ_ROLES`.
- Mỗi dòng có `document_id/version_id/submission_id/source_id`, `allowed_roles` và `deep_path`; không gán người phụ trách giả.

## 3. Thay đổi Frontend

- `src/app/api/v1/endpoints.ts`: thêm `reviewSubmissionPaths` và `inboxPaths`.
- `src/features/knowledge/review-types.ts`, `review-requests.ts`, `review-schemas.ts`, `review-queries.ts`: contract submission, mapping lỗi sang thông điệp hành động, query key `["v1", sessionId, "workspaces", workspaceId, ...]`, invalidate review + inbox sau mutation.
- `src/features/knowledge/review-submission-dialog.tsx`: hộp thoại hai bước xem trước → xác nhận, khóa idempotency, lý do tối thiểu (`request_changes` 10 ký tự, `cancel` 3 ký tự), reset khi đổi hành động bằng `key` ở trang cha.
- `src/features/knowledge/compiled-version-detail-page.tsx`:
  - Badge “Chờ người duyệt” khi có submission `pending`; “Đã yêu cầu sửa” khi yêu cầu sửa chưa được thay thế.
  - Nút chính “Gửi duyệt” cho editor/admin khi phiên bản hợp lệ và không có yêu cầu mở; “Yêu cầu sửa” cho reviewer/admin khi đang chờ duyệt.
  - Menu `⋯` giữ thao tác phụ: gửi duyệt (admin), rút yêu cầu (admin/người gửi), duyệt nhanh, thu hồi — không rải nút vào từng khối.
  - Panel trạng thái submission (người gửi, thời điểm, ghi chú, kết quả) và gợi ý “Bước tiếp theo” theo trạng thái thật; chặn gửi lại khi còn yêu cầu sửa để khớp lỗi 409 của server.
- `src/features/knowledge/publication-queries.ts`: sau quyết định duyệt/xuất bản, invalidate cả submission và inbox (duyệt đóng submission cùng transaction).
- `src/features/inbox/`: types/schemas/requests/queries/page. Trang “Cần xử lý” có lọc kind + collection, phân trang server, `counts` từ server, bảng cuộn ngang nội bộ, hiển thị nhóm được phép xử lý (“Chờ người duyệt” khi trống), deep link tới đúng phiên bản/nguồn/collection; loading/error/empty riêng; không có nút dismiss.
- `src/routes/workspaces.$workspaceId.inbox.tsx`: search params `page/pageSize/kind/collectionId`, đổi bộ lọc quay về trang 1. `routeTree.gen.ts` do plugin sinh, không sửa tay.
- `src/navigation/workspace-features.ts`: mục “Cần xử lý” nhóm “Điều phối”, hiển thị theo membership server.
- Test hợp đồng `tests/review-inbox-contract.test.ts` (11 ca) và cập nhật `tests/template-boundary.test.ts` cho phép `features/inbox/` gọi client V1.
- Tài liệu: thêm quy trình [45 — Gửi duyệt, yêu cầu sửa và danh sách “Cần xử lý”](../quy_trinh/45_ban_giao_duyet_va_can_xu_ly_v1.md) và mục lục; cập nhật trạng thái kế hoạch 15/README kế hoạch, mục lục nhật ký, WORK_LOG, PROJECT_CONTEXT và snapshot 900.

## 4. Phương pháp và lệnh thật

### 4.1. Backend

Từ `backendV1`, dùng harness DB cô lập (không chạy trên DB ứng dụng):

```bash
export DATABASE_URL="$(grep -m1 '^DATABASE_URL=' ../.env | cut -d= -f2-)"
uv run python scripts/run_isolated_tests.py \
  tests/integration/test_review_handoff.py \
  tests/integration/test_publication_646.py \
  tests/integration/test_review_gate_666.py \
  tests/integration/test_fast_publication_779.py \
  tests/migrations/test_workspace_model_schema.py \
  tests/unit/test_migration_baseline_661.py
```

Kết quả: `43 passed, 5 warnings in 196.12s`; receipt `qnu_v1_test_3d5f57455400453a`, `db_dropped: true`, `legacy_sentinel_preserved: true`, `pytest_exit: 0`, `seconds: 208.02`. Không chạy trên DB ứng dụng.

Ruff scoped:

```bash
uv run ruff check qnu/domains/knowledge/review qnu/domains/knowledge/inbox \
  tests/integration/test_review_handoff.py alembic/versions/0016_review_submission.py \
  qnu/domains/knowledge/publication/decisions.py qnu/domains/knowledge/publication/router.py \
  qnu/domains/knowledge/publication/schemas.py qnu/domains/knowledge/sources/router.py \
  qnu/domains/knowledge/sources/schemas.py qnu/domains/lifecycle/purge_graph.py \
  qnu/domains/workspaces/access.py qnu/platform/ownership.py qnu/platform/schema.py \
  qnu/api/routes.py tests/integration/conftest.py \
  tests/migrations/test_workspace_model_schema.py tests/unit/test_migration_baseline_661.py \
  alembic/env.py
```

Kết quả: `All checks passed!`.

Full backend suite: đã khởi chạy harness cô lập, thu thập `1533 items`; sau khoảng 4 phút mới chạy xong 29 test, tất cả PASSED, 0 FAILED (≈7 test/phút) nên không thể hoàn tất trong phiên và đã dừng có kiểm soát. Đây là **NOT COMPLETED**, không phải PASS. Các phiên trước ghi nhận lỗi nền Redis751 trên bộ đầy đủ.

### 4.2. Frontend

Từ `frontendV1`:

```bash
npm run test   # 107 passed (107), 895 passed (895), 52.07s
npm run build  # ✓ built in 3.74s; còn cảnh báo chunk >500 kB có sẵn
npx biome check <18 file P4>   # Checked 18 files. No fixes applied.
```

Build sinh route mới `/workspaces/$workspaceId/inbox` qua plugin TanStack Router; không sửa `routeTree.gen.ts` bằng tay.

Biome toàn repo (`npm run lint`) chưa đạt vì còn 42 lỗi có sẵn ngoài phạm vi P4 (ghi nhận từ lần chạy trong phiên); không sửa các file ngoài phạm vi.

### 4.3. NOT RUN

- Kiểm thị giác/tương tác trình duyệt cho luồng gửi duyệt và trang “Cần xử lý”: **NOT RUN** — không có dev server API/web trong phiên; DB ứng dụng đang ở `0014_publication_index_sync`, migration `0015/0016` chưa áp dụng, và việc migrate DB ứng dụng nằm ngoài phạm vi được giao.
- Không deploy, không migrate DB ứng dụng, không reindex, không gọi model thật, không restart dịch vụ.

## 5. Rủi ro và bước sau

- Trước khi nghiệm thu đầu-cuối cần áp migration `0016` ở môi trường phát triển được phép, chạy API/web và kiểm 8 tổ hợp desktop/mobile, sáng/tối cho: gửi duyệt, yêu cầu sửa, rút yêu cầu, duyệt (không tự publish), inbox lọc/phân trang/deep link.
- Full backend suite cần được chạy lại ở môi trường đủ nhanh; lỗi nền Redis751 vẫn phải xử lý riêng, không gộp vào kết quả P4.
- P5 (xuất bản/đồng bộ trung thực), P6 (trợ lý dễ cấu hình) và P7 (pilot) chưa bắt đầu.
