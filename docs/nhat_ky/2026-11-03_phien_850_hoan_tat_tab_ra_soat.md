# Phiên 850 — Hoàn tất trạng thái và tiến độ rà soát biên soạn

## Nguyên nhân và phạm vi

Người dùng yêu cầu hoàn tất tab Rà soát & Đánh giá. Đối chiếu DB và sự
kiện thực thi: compiler đã hoàn tất; review có 11 nhóm: 1 completed,
1 uncertain, 9 pending. Nhóm không xác định dừng sau 300,089 giây với
`chat_provider_uncertain`, không có HTTP upstream hay usage được xác nhận.
Qwen lúc đó `wait_for_completion=false`, timeout 300. Đây là thời hạn chờ
phản hồi; không có bằng chứng lỗi output token.

## Thay đổi

- Seed local thêm helper cho đúng endpoint/model Qwen. Giữ reasoning off,
  bật `wait_for_completion` qua service ModelOps có quyền/audit, giữ policy
  resilience khác. Chạy lặp không ghi khi đã đúng; không đổi model khác.
- Đã áp dụng helper trên DB development loopback và đọc lại false → true.
  Không seed lại toàn bộ/key. Giữ timeout connect/write; read và outer
  generation không dùng deadline đó khi policy chờ hoàn tất bật. Không
  đổi capacity, token, đồng thời, worker hay dịch vụ đang chạy.
- Frontend thêm client/type/query cho GET progress đã có; key đủ session,
  workspace, collection, run, review. Poll queued/running, dừng terminal
  hoặc lỗi đọc. Không POST AI từ polling/nút tải lại.
- Panel tiến độ hiện nhóm thực và trạng thái từng nhóm, giải thích lỗi/
  chưa xác định và phạm vi chưa chạy. Không gọi report đầy đủ khi chưa
  completed, không biến lỗi thành báo cáo rỗng thành công.
- Tab phân biệt lỗi đọc và lượt chưa hoàn tất; tạo thủ công chọn deep link
  mới thay vì giữ auto-review cũ. Key idempotency đổi sau tạo thành công,
  giữ nguyên khi lỗi. Dropdown dùng nhãn trạng thái thay ID nội bộ.
- Nhóm thao tác đầu trang compiler được xuống dòng ở màn hình hẹp. Giữ
  toàn bộ tối ưu tab và bản nháp phiên849, không sửa ngoài phạm vi này.

Không tự tạo review AI mới/gửi lại uncertain, sửa kết quả/history, OCR,
nguồn, xuất bản hoặc index. Không restart, commit/push.

## Kiểm chứng

- BE trọng tâm từ root: `uv run --project backendV1 --frozen --no-sync
  python backendV1/scripts/run_isolated_tests.py
  tests/unit/test_seed_qwen_wait_850.py tests/unit/test_chat_wait_760.py
  tests/integration/test_chat_wait_760.py -q`: exit0, 12 PASS, 8,06s;
  DB test đã xóa, sentinel legacy giữ. Bao phủ wait/cancel/transport,
  idempotency seed, scope endpoint/model và giữ policy khác. Ruff2file exit0.
- FE trọng tâm lần đầu 43 PASS/2 FAIL: thiếu ResizeObserver fixture và
  chưa đợi notify async trong test polling. Sau sửa fixture/đợi state:
  45/45 PASS. Không bỏ assertion nghiệp vụ.
- Full FE `npm exec -- vitest run --maxWorkers=2` trong frontendV1:
  exit0, 91 suites, 764/764 PASS, 150,84s. Build bắt variant Alert `default`
  sai contract; sửa `info`, build gồm TypeScript sau sửa exit0. Biome9file
  exit0. Regression cuối progress/query/tab15/15 PASS. Cảnh báo chunk lớn
  và Vite native config vẫn còn, không tắt warning để che.
- Chrome thật local: GET progress đúng 1/11, 1 uncertain, 9 pending;
  0 JSerror/mutation/GET report chưa sẵn sàng. Khối progress không tràn
  390px; shared app header còn overflow khi thu viewport, ngoài phạm vi
  panel review, không coi toàn trang mobile đạt. Artifact trong tmp/ignore.
- Full BE tuần tự đầu dừng có kiểm soát sau500,20s để chuyển harness nhóm
  Windows/queue/cache riêng theo hướng chạy lịch sử. Trước dừng có2FAIL,
  không tính PASS. DB test đã xóa/sentinel giữ. Kết quả đầy đủ bên dưới.

### Backend toàn phần và cấu hình Redis kiểm thử

- Chạy toàn bộ 1.329 ca qua bốn nhóm file không giao nhau. Mỗi nhóm dùng
  DB, storage, cache namespace, queue riêng và chặn egress model. Windows
  Selector cho các nhóm HTTP/Redis, Proactor riêng cho recovery subprocess.
  Đối chiếu JUnit đủ số ca theo từng file, không thiếu hoặc trùng.
- `uv run --project backendV1 --frozen --no-sync python
  tmp/full-backend-850.py`: exit 1, 1.322 PASS / 4 FAIL / 3 SKIP,
  1.161,00 giây. Full gate vẫn FAIL, không thay assertion để báo xanh.
- Ba FAIL là cấu hình harness thiếu `TEST_REDIS_URL`, chưa phải lỗi ứng dụng:
  `test_readiness_666.py::test_worker_heartbeat_is_queue_scoped_and_removed_on_shutdown`
  và hai tham số `[128]`, `[None]` của
  `test_integration_gateway_pipeline.py::test_external_key_calls_real_rag_and_preserves_assistant_config`.
  Ba SKIP còn lại là limiter Redis, OCR queue và compiler reconcile queue
  cũng thiếu biến kiểm thử này.
- Tạo Redis Docker tạm riêng, chỉ bind loopback; đặt cả REDIS_URL và
  TEST_REDIS_URL vào container đó, giữ nguyên code/assertion. Kiểm tra đúng
  sáu ca trên: 6/6 PASS, exit 0, 31,06 giây; DB test đã xóa, sentinel giữ,
  container kiểm thử đã dừng. Không gọi model thật; fake HTTP local theo
  fixture hiện hành. Không gộp lượt này để đổi nhãn full gate thành PASS.
- FAIL còn lại:
  `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`
  tại dòng109: không có cell `header=true`. Nhánh parser không thuộc thay
  đổi review/seed, không sửa trong phiên này. Lỗi cùng test đã ghi ở839;
  chưa chạy baseline HEAD riêng để khẳng định nguyên nhân hiện tại giống hệt.
- Dọn đúng prefix Redis của lượt full: 0 key còn; đọc lại 4 DB test còn0.
  Giữ mọi log/JUnit/receipt trong tmp hoặc storage test bị ignore; không
  xóa dữ liệu app, tệp nguồn hay kết quả review hiện tại.

## Vận hành và giới hạn

F5 trang biên soạn rồi mở Rà soát & Đánh giá. Lượt cũ vẫn chưa hoàn tất:
đổi policy không khôi phục phản hồi đã mất. Muốn chạy mới chọn Yêu cầu
Review thủ công → Bắt đầu Review. Không cần OCR/compiler lại, cleanup/init
hay restart chỉ để nhận policy này. Chưa chạy review toàn tài liệu bằng
model thật sau đổi cấu hình; không báo lượt cũ đã thành công. Không kết luận
toàn bộ V1 đã PASS khi ca DOCX trên còn FAIL.
