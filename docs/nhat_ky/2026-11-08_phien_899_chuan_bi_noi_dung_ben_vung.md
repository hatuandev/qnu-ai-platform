# Phiên899 — Chuẩn bị nội dung bền vững sau khi lưu nguồn

## Yêu cầu và phạm vi

Triển khai P3 trong
[15 — Trải nghiệm người dùng QNU V1](../ke_hoach/15_ke_hoach_trai_nghiem_nguoi_dung_qnu_v1.md)
trên nhánh `feat/v1-user-workflow`, tiếp sau P1/P2 của phiên898. Mục tiêu: sau
khi lưu nguồn, người dùng có một yêu cầu rõ ràng “Chuẩn bị nội dung”; yêu cầu
được ghi bền vững trên máy chủ và tự chạy tiếp qua đọc nội dung rồi biên soạn
đến bản nháp chờ kiểm tra, kể cả khi đóng tab hoặc worker khởi động lại. Không
tự đăng ký/duyệt/xuất bản chỉ vì worker hoàn tất.

Không deploy, migrate dữ liệu thật, reindex, gọi model thật, đổi cấu hình đang
chạy hoặc push. Mọi thay đổi nằm trong working tree; các thay đổi chưa commit
của phiên896–898 được giữ nguyên.

## Thay đổi

### Backend — preparation intent

- `backendV1/qnu/domains/knowledge/preparation/` (mới):
  - `models.py`: bảng `kb_preparation_intents` ghim
    `source/revision/revision_no/revision_sha256`, `requested_by`,
    `idempotency_key`, `request_hash`, mode/status, text version + hash, provider,
    `ocr_run_id`, `compilation_run_id`, lease/worker và timestamps. FK ghép
    `(source_id, collection_id, workspace_id)` và
    `(revision_id, source_id, collection_id, workspace_id)`; unique
    `(workspace_id, requested_by, idempotency_key)`; check status/mode/hash/
    text_version; index theo source/thời gian và status/lease.
  - `service.py`: accept intent trong một transaction, tính request hash từ
    scope + mode + run/text + topic; cùng key/body trả bản ghi cũ, cùng key khác
    body trả `409 idempotency_conflict`. Mỗi bước đọc lại authority
    (`resolve_workspace_access`), lifecycle nguồn/revision và hash đã ghim từ DB;
    queue delivery chỉ là gợi ý. Bước đọc nội dung tái dùng
    `processing_service`, chỉ dùng lại artifact hoàn tất khi revision/hash/cấu
    hình khớp; chờ OCR xong mới chuyển compiler. Compiler tạo/reuse
    `CompilationRun` theo khóa idempotency riêng, dừng ở `ready` với
    `compilation_run_id`. Hủy chỉ chặn bước kế tiếp; không hứa abort request
    upstream đã gửi; usage chưa rõ giữ `uncertain`, không tự gửi lại.
  - `schemas.py`: `PreparationRequest` (mode mặc định `source`; `revision_id`,
    `ocr_run_id`, `text_version >= 0`, `topic <= 2000`, `provider_id`,
    `max_output_tokens > 0`; source mode từ chối tùy chọn AI; text version > 0
    bắt buộc có OCR run) và `PreparationResponse`/`PreparationCreated`.
  - `router.py`: POST tạo intent (header `Idempotency-Key`, 201/200 theo
    `created`), GET danh sách giới hạn, GET chi tiết, POST cancel; router mỏng,
    kiểm quyền trong service.
- `backendV1/qnu/workers/tasks/preparation.py` (mới) + `workers/settings.py`:
  đăng ký task ARQ `preparation_job`, claim theo lease và gọi bước kế tiếp.
  `workers/tasks/ocr.py`, `workers/tasks/compilation.py`: sau khi run nguồn kết
  thúc, đánh thức intent đang chờ đúng run đó; không tạo scheduler mới.
- `backendV1/qnu/api/routes.py`, `alembic/env.py`, `qnu/platform/ownership.py`,
  `qnu/domains/lifecycle/purge_graph.py`: gắn router, metadata migration và đồ
  thị purge/xóa theo scope.
- `backendV1/alembic/versions/0015_preparation_intent.py` (mới): tạo bảng và
  index/constraint tương ứng.
- `backendV1/tests/integration/test_preparation_intents.py` (mới, 11 ca):
  golden path nguồn→OCR→compiler dừng ở ready; replay/conflict theo key; queue
  lỗi vẫn durable và reconcile; duplicate delivery không gọi model lần hai;
  cancel và thu hồi membership chặn bước kế tiếp; revision mới không đổi intent
  đã ghim; hash lệch bị từ chối; tái dùng artifact tương thích; validate text
  version; AI mode qua ModelOps; outsider nhận 404. `conftest.py` dọn bảng mới
  giữa các ca.

### Frontend — hộp thoại và trạng thái chuẩn bị

- `src/features/knowledge/preparation-types.ts`, `preparation-schemas.ts`,
  `preparation-requests.ts`, `preparation-queries.ts` (mới): transport typed,
  nhãn/status variant, thông điệp lỗi theo mã, query key theo
  session/workspace/collection/source, poll 2,5 giây chỉ khi status đang hoạt
  động; mutation tạo/cancel cập nhật cache chi tiết, invalidate danh sách và
  summary nguồn.
- `src/features/knowledge/preparation-dialog.tsx` (mới): xem trước đúng nguồn,
  `Tệp vN · hash rút gọn`, bản văn bản đã lưu (hoặc “Chưa đọc — hệ thống sẽ đọc
  trước”); chọn “Giữ nguyên nguồn” (mặc định) hoặc “Bổ sung bằng AI” (ModelOps,
  quota, giữ nguồn); mô tả điểm dừng trước khi xác nhận. Sau khi gửi, hiển thị
  trạng thái thật, cho hủy yêu cầu đang chạy, “Chuẩn bị lại” khi failed/
  uncertain/cancelled, và “Mở bản nháp” khi ready. Khóa idempotency đổi khi đổi
  mode/provider/token và sau thành công/hủy; lỗi gửi giữ nguyên khóa để replay
  bền vững.
- `src/features/knowledge/preparation-status-bar.tsx` (mới): dải trạng thái
  trên trang nguồn cho yêu cầu mới nhất — đang chạy, sẵn sàng, lỗi/không chắc
  chắn; ẩn được; không hiện cho yêu cầu đã hủy.
- `src/features/knowledge/source-studio-header.tsx`: CTA chính đổi thành “Chuẩn
  bị nội dung” cho mọi trạng thái xử lý; “Chuẩn bị nâng cao” (biên soạn nhiều
  tài liệu) chuyển vào menu `⋯`.
- `src/features/knowledge/source-detail-page.tsx`: mở hộp thoại chuẩn bị với
  revision/hash và text version đang chọn trên server; chặn mở khi còn hiệu
  đính nháp chưa lưu và yêu cầu lưu/bỏ trước; giữ dialog biên soạn nâng cao
  nullable cho nguồn chưa xử lý.
- `src/app/api/v1/endpoints.ts`, `index.ts`: thêm `preparationPaths` và export.

### Kiểm thử frontend

- `tests/preparation-intent-contract.test.ts` (mới, 9 ca): path tạo/list theo
  source và chi tiết/cancel theo collection; POST kèm `Idempotency-Key` và body
  ghim; list `?limit=`; GET/cancel đúng method/URL/body; query key tách session/
  source/limit và không trùng khóa chi tiết; chỉ ba status hoạt động mới poll;
  nhãn/variant semantic; map mã lỗi và fallback; `shortHash` không bịa hash.
- `tests/ocr-review-ux-806.test.tsx`, `tests/ocr-original-preview.test.tsx`: mock
  `preparation-queries` inert cho các ca dựng `SourceDetailPage`; ca “phiên bản
  vừa lưu” nay kiểm tra hộp thoại chuẩn bị nhận v2, và ca chặn khi còn nháp
  kiểm tra cả hai hộp thoại đều không mở.

## Kiểm chứng thực chạy

Backend, từ root repo (DB test tách rời do `run_isolated_tests.py` tạo):

- `tests/integration/test_preparation_intents.py`: PASS 11/11, 33,52 giây
  (`qnu_v1_test_38f04f74a98f4bf0`).
- Nhóm regression liên quan summary/OCR/compiler trong cùng runner: PASS 41/41,
  126,51 giây (`qnu_v1_test_0f009196da5f4570`).
- Ruff lint/format trên các tệp backend thuộc phạm vi: PASS.
- Full backend suite: NOT PASS trong phiên này — lần chạy đầy đủ trước đó dừng
  giữa chừng và có lỗi nền Redis751 đã biết (Redis không sẵn sàng), ngoài phạm
  vi P3. Không dùng kết quả này để tuyên bố toàn hệ thống đạt.

Frontend, trong `frontendV1/`:

- `npx vitest run tests/preparation-intent-contract.test.ts`: PASS 9/9.
- `npx vitest run tests/ocr-review-ux-806.test.tsx tests/ocr-original-preview.test.tsx`:
  PASS 27/27.
- `npm test` (Vitest toàn bộ): PASS 883/883 qua 106 tệp.
- `npm run build` (Vite + `tsc --noEmit`): PASS; còn cảnh báo chunk > 500 kB có
  sẵn, không phát sinh lỗi mới.
- `npx biome check` trên 13 tệp P3 vừa sửa/tạo: PASS, không đề xuất sửa.
- Kiểm thị giác trên trình duyệt: NOT RUN — backendV1 cổng 8002 và web 5173
  không chạy trong phiên; không khởi động lại dịch vụ theo giới hạn.

## Rủi ro và bước sau

- Chưa kiểm chứng đầu-cuối với OCR/compiler thật và model thật; các ca tích hợp
  dùng fixture/hạ tầng test. Cần chạy thử trên môi trường phát triển có
  Redis/worker/ModelOps trước khi nghiệm thu P7.
- Chưa có màn hình “Cần xử lý” hay luồng duyệt/xuất bản sau bản nháp; P4–P7
  chưa bắt đầu.
- Chưa commit/push; cần người dùng xác nhận trước khi tạo commit cho nhánh
  `feat/v1-user-workflow`.
- Full backend suite vẫn còn lỗi nền Redis751; không tuyên bố toàn hệ thống PASS.
