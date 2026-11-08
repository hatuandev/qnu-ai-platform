# Phiên898 — Read model nguồn–chuẩn bị–xuất bản và trang tài liệu

## Yêu cầu và phạm vi

Triển khai tiếp kế hoạch
[15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md)
trên nhánh `feat/v1-user-workflow`, sau khi người dùng xác nhận bỏ qua thư mục
mẫu `KTX` (chỉ là mã tham khảo FE). Phiên này gồm P1 (điều hướng, thuật ngữ,
thao tác theo vai trò) và P2 (read model summary, gắn vào trang nguồn và trang
tài liệu biên soạn).

Không deploy, migrate, reindex, gọi model thật, đổi cấu hình đang chạy hoặc
push. Mọi thay đổi nằm trong working tree; các thay đổi chưa commit của phiên
896–897 được giữ nguyên.

## Thay đổi

### P1 — Điều hướng, thuật ngữ, thao tác

- `frontendV1/src/navigation/workspace-features.ts`: thêm
  `workspaceFeatureBreadcrumb`, `resolveWorkspaceExperience` và
  `workspacePrimaryFeatures` để sidebar, command menu và breadcrumb cùng đọc
  một registry; thứ tự mục chính theo vai trò lấy từ membership server trả về,
  không suy từ tên role UI. Đổi nhãn hiển thị: OCR & chính tả → Đọc nội dung,
  Biên soạn → Chuẩn bị nội dung, Tìm kiếm → Đồng bộ cho trợ lý.
- `frontendV1/src/layouts/workspace-sidebar.tsx`,
  `frontendV1/src/layouts/qnu-command-menu.tsx`,
  `frontendV1/src/navigation/config.ts`, các route knowledge: dùng chung danh
  sách mục chính theo vai trò, giữ route trực tiếp hiện hành, một mục active.
- Nhóm thao tác phụ vào menu `⋯`, ẩn chi tiết kỹ thuật mặc định ở các trang
  nguồn/OCR/biên soạn/xuất bản; giữ khả năng chẩn đoán khi mở rộng. Cập nhật
  nhãn ngắn theo chuẩn microcopy; đồng bộ test hiện có với nhãn mới.

### P2 — Backend read-only summary

- `backendV1/qnu/domains/knowledge/sources/summary.py` (mới): summary theo
  source/revision. Chuỗi dẫn xuất lấy từ `CompilationInput` đã lưu (ghim đúng
  `OcrProcessingRun` và `TextVersion`), không suy từ generation hay "run mới
  nhất". Danh sách run/dẫn xuất giới hạn `limit + 1` để báo truncated.
  `active_run_id` chỉ từ trạng thái đang hoạt động thật.
- `backendV1/qnu/domains/knowledge/publication/summary.py` (mới): summary theo
  compiled document, phân trang version ở server; origins join
  `CompilationInput → OCR run → revision → source` và lọc `visible("source")`;
  tái sử dụng `index/readiness.py`, không viết thuật toán readiness thứ hai;
  `serving_matches_published` đối chiếu version/state/hash/bundle và
  `publication_decision_id`.
- `backendV1/qnu/domains/knowledge/policies/capabilities.py` (mới):
  `SummaryCapabilities` theo role đã được xác thực (admin/editor/reviewer/member).
- `backendV1/qnu/domains/workspaces/access.py`: thêm `caller_workspace_role`
  chỉ dùng cho read model sau `resolve_workspace_access`.
- DTO tại `sources/schemas.py`, `publication/schemas.py`; endpoint
  `GET /sources/{source_id}/summary` (revision_id, runs_limit ≤ 20,
  derivations_limit ≤ 50) và `GET /compiled-documents/{document_id}/summary`
  (page, page_size ≤ 100). GET thuần đọc, có `observed_at` và capabilities.
- `backendV1/tests/integration/test_knowledge_summary_api.py` (mới): 9 ca phủ
  một nguồn nhiều run, bản tổng hợp nhiều nguồn, nhiều phiên bản, không index,
  sync lỗi, nguồn archived, mất membership giữa hai lần đọc, không vượt
  workspace/collection, và GET không đổi trạng thái.

### P2 — Frontend

- `frontendV1/src/features/knowledge/summary-types.ts`,
  `summary-requests.ts`, `summary-schemas.ts`, `summary-queries.ts` (mới):
  transport typed, nhãn readiness, query key gồm session/workspace/collection/
  resource/tham số; poll 3 giây chỉ khi có tác vụ thật đang hoạt động;
  `isSourceSummaryKey` + `invalidateSourceSummaries` cho invalidate theo phạm vi.
- `frontendV1/src/features/knowledge/source-lineage-panel.tsx` (mới): panel
  "Dòng dẫn xuất" trong trang chi tiết nguồn, hiển thị lần đọc nội dung, bản văn
  bản, lần chuẩn bị, phiên bản đích, trạng thái readiness và "Đang phục vụ";
  loading/error/empty riêng, "Tải thêm" tới giới hạn 50, footer `observed_at`.
- `frontendV1/src/features/knowledge/compiled-document-detail-page.tsx`: dùng
  summary thay truy vấn version rời; phân trang server theo `meta.total`; cột
  nguồn dẫn xuất; badge readiness/serving ở dòng đã xuất bản; poll theo
  `useSearchAvailability().isUpdating` và refetch một lần khi về terminal.
- Invalidation sau mutation: `ocr-queries.ts`, `queries.ts`,
  `publication-queries.ts`, `compilation-queries.ts` làm mới summary nguồn/tài
  liệu liên quan.
- `frontendV1/src/app/api/v1/endpoints.ts`: thêm path source summary và document
  summary.
- `frontendV1/tests/summary-query-isolation.test.ts` (mới): 5 ca key isolation,
  terminal idle và tín hiệu poll; cập nhật các test cũ theo nhãn P1 và mock
  summary/role cần thiết.

## Kiểm chứng thực chạy

Backend, từ root repo:

- `uv run --project backendV1 --frozen --extra dev python backendV1/scripts/run_isolated_tests.py tests/integration/test_knowledge_summary_api.py`: PASS 9/9, 79,93 giây.
- `uv run --project backendV1 --frozen --extra dev ruff check` và
  `ruff format --check` trên 9 tệp backend thuộc phạm vi: PASS, exit0 ("All
  checks passed!", "9 files already formatted").
- Full backend suite (`run_isolated_tests.py` không tham số): đã khởi chạy, CHƯA HOÀN TẤT tại thời điểm bàn giao — sau 11 phút mới ~5% (~941 test funcs), log trực tiếp ghi nhận `test_chat_shared_admission_751.py::test_real_redis_enforces_shared_limit_and_releases_own_leases` FAILED (lỗi nền Redis751 đã biết từ các phiên trước, ngoài phạm vi P2). Không có kết quả tổng để tuyên bố PASS/FAIL toàn bộ; xem `backendV1/storage/context636/qnu_v1_test_4a262de990814899/pytest.log` và `result.xml` khi chạy xong.

Frontend, trong `frontendV1/`:

- `npx biome check` trên 11 tệp P2 vừa sửa: PASS, exit0, không đề xuất sửa.
  `npm run typecheck`: PASS.
- `npm test` (Vitest): PASS 874/874 qua 105 tệp.
- `npm run build`: PASS (Vite + TypeScript).
- `npx biome check src tests` toàn bộ: exit1 với 35 lỗi/8 cảnh báo có sẵn ở các
  tệp không thuộc phạm vi phiên (compilation-draft-sections, breadcrumb,
  quick-prompts, folder-form-dialog, collection-card, file-upload,
  document-file-icon, page-breadcrumbs). Không sửa các tệp này; toàn bộ tệp
  phiên898 không có lỗi Biome.

## Rủi ro và bước sau

- P2 chỉ đọc; chưa kiểm chứng trên dữ liệu thật nhiều năm/bảng lớn ngoài fixture
  test. Chưa chạy trình duyệt cho panel mới; các trang dùng component/test hiện
  có, cần kiểm thị giác khi chạy app.
- P3–P7 chưa bắt đầu. Chưa commit/push; cần người dùng xác nhận trước khi tạo
  commit cho nhánh `feat/v1-user-workflow`.
- Full backend suite còn lỗi nền/không hoàn tất được ghi riêng bên trên; không
  tuyên bố toàn hệ thống PASS.
