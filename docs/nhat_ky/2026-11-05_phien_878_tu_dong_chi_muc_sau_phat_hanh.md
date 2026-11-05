# Context878 — Tự cập nhật chỉ mục sau phát hành và dọn vector cũ

## Yêu cầu và phạm vi

Người dùng giao bước 1–2: tự đưa bản phát hành vào tìm kiếm và quản lý vector cũ;
không còn dùng thao tác Tìm kiếm & Chỉ mục trong luồng thường. Không triển khai
trích metadata JSON/AI hay đổi Compiler trong đợt này. Giữ nguyên các diff OCR,
PDF Inspector, Docling và thay đổi FE đồng thời từ IDE khác.

Áp dụng skill clean-code, backend architect, knowledge ingestion và frontend
architect; theo verification chung. Đã tái hiện đỏ endpoint readiness 404 trước
khi thêm contract (DB thử qnu_v1_test_995e8e1083b043f6, đã xóa).

## Thay đổi

- Migration0014 thêm outbox `kb_index_sync`, mốc deactivation và retirement cho
  IndexRun; cập nhật schema head/ownership/test fixture. Ý định ghi cùng transaction
  publish/withdraw; archive/delete/restore nguồn/tài liệu/collection cũng yêu cầu sync.
- Worker nhận index_sync, reconcile mỗi phút và lúc khởi động. Gom theo collection,
  dùng khóa workspace và hàng outbox, snapshot publication, ModelOps default embedding,
  idempotency từng lượt. Không gọi embedding trong HTTP publish. Mất delivery có thể
  giao lại; provider uncertain không tự inference lại. Retry chủ động có quyền và audit,
  giữ các receipt cũ để phát lại cùng khóa không tạo thêm việc.
- Generation mới chỉ active khi hoàn tất, cùng source/hash/state hiện hành. Nguồn
  thu hồi không lọt eligibility; bản cũ đang phục vụ được giữ trong khi dựng bản mới.
- Retirement chỉ completed inactive đúng target, có active mới hơn, giữ 1 inactive
  gần nhất và chờ24h từ deactivation. Lọc eligibility trước batch để các bản được giữ
  không chặn hàng đợi dọn. Kiểm lại dưới khóa workspace trước xóa Qdrant và SQL vector;
  giữ chunk text/cấu trúc/citations/manifests/source/receipt. Không xóa lịch sử nghiệp vụ.
- Bỏ menu Tìm kiếm thử & Chỉ mục và nút tạo index ở trang tài liệu/phiên bản. FE hiển thị
  đang cập nhật/sẵn sàng/lỗi; ready phải khớp version/state/bundle. Read error có refresh;
  failed/uncertain có nút yêu cầu cập nhật mới cho người có quyền. API/route cũ giữ
  tương thích, không gỡ backend retrieval cần cho trợ lý.

Các file chính: `index/sync.py`, `index/retirement.py`, `index/models.py`,
`index/router.py`, `index/execution.py`, publication decisions/router,
lifecycle effects, worker indexing/settings, schema/config/ownership,
`0014_publication_index_sync.py`, `search-availability.tsx`, hai trang tài liệu/phiên bản,
publication query invalidation, knowledge detail menu và hai test878.
Chi tiết luồng: [quy trình24](../quy_trinh/24_index_va_tim_kiem_dense_backendv1.md).

## Kiểm chứng thực chạy

Backend chạy từ root qua `uv run --project backendV1 --frozen --extra dev python
backendV1/scripts/run_isolated_tests.py ...`, bật selector loop Windows. Harness tạo
DB qnu_v1_test_* riêng, storage riêng và chặn egress không loopback; model giả lập,
PostgreSQL/Qdrant thật. Không dùng DB app để pytest.

- `tests/integration/test_publication_index_sync_878.py tests/unit/test_migration_baseline_661.py -q --tb=short`:
  **13 PASS / 0 FAIL**, exit0,105,70s. Trong đó11 integration và2 migration. Receipt
  qnu_v1_test_fe75dc6565ec4106 xác nhận db_dropped=true, legacy_sentinel_preserved=true.
  Bao gồm transaction rollback, replay publication, coalescing, concurrent delivery,
  queue outage, startup maintenance, uncertainty, auth boundaries, withdrawal và retirement.
- `test_publication_646.py test_index_api_647.py test_index_readiness_819.py test_lifecycle_659.py test_source_purge_716.py`
  trong tests/integration: **48 PASS / 0 FAIL**, exit0,285,23s. DB
  qnu_v1_test_7ee962da45eb4cce đã xóa, legacy sentinel giữ nguyên.
- Full backend `tests -x --failed-first --tb=short -q`: **FAIL**, exit1, dừng ca nền
  `test_chat_shared_admission_751.py::test_real_redis_enforces_shared_limit_and_releases_own_leases`.
  Test yêu cầu CACHE_NAMESPACE bắt đầu qnu:test: nhưng môi trường qnu:v1:cache:.
  DB qnu_v1_test_05a861287b55439c đã xóa. Không thay namespace/assertion để làm xanh.
- Sau bổ sung guard lỗi delivery không ghi đè binding mới, chạy lại3 ca
  missing_provider/concurrent_delivery/uncertain: **3 PASS**, exit0,20,69s,
  8 deselected; DB qnu_v1_test_738a5b8762ca4043 đã xóa. Đây là kiểm lại sau đổi code,
  không phải retry để làm xanh câu hỏi model thật.
- Ruff check các file backend sửa trong phạm vi **PASS**, exit0.
- Trong frontendV1, `npm run build`: **PASS**, exit0 (Vite + TypeScript).
  Còn warning Vite config native loader và bundle lớn; không chứng minh visual QA.
- `npm exec -- vitest run tests/search-availability-878.test.tsx tests/regression-677-index-scope.test.tsx`:
  **17 PASS / 0 FAIL**, exit0,7,92s. Biome6 file FE phạm vi **PASS**.
- Lượt FE mở rộng trước đó gồm thêm `tests/v1-publication.test.ts`: **38 PASS / 1 FAIL**;
  ca `createDecisionPreview, draft, review-gate and history transport properly` còn
  regex /draft$/ trong khi request hiện hành dùng /draft?group_by_source=true. File
  request/test đó không sửa trong đợt này. Không đổi expectation để báo xanh.

## Vận hành và giới hạn

Chưa migrate DB app, restart, publish, reindex corpus thật hoặc push. Chưa chạy model
thật/benchmark chất lượng RAG hay visual browser; fake provider chứng minh luồng và quyền.
Sau khi dừng dev: `./make.ps1 v1-migrate`, rồi `./make.ps1 dev`. Không clear/reset, không
cần upload lại. Bản phát hành mới tự sync; bản cũ chưa có outbox không tự backfill lúc mở
trang, dùng Thử cập nhật khi cần. Chưa biết mốc deactivation thì giữ vector, không đoán.

`git diff --check` và kiểm UTF-8 không BOM/LF của các file mới/ghi nhật ký: PASS.
