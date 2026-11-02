# Phiên 801 — Ngữ cảnh và hàng rào cho gợi ý chính tả OCR

## Phạm vi và ranh giới vận hành

Người dùng giao cải thiện bước sửa chính tả và hỏi ảnh hưởng đến compiler đang
chạy. Giữ nguyên luồng gợi ý → người dùng xác nhận/lưu → compiler; không đổi sang
MinerU, không restart, đổi ModelOps, sửa nguồn/bản chữ, xuất bản hoặc lập chỉ mục.
Đã kiểm tra tiến trình API không có cờ auto-reload. Truy vấn SELECT read-only xác
nhận `cmp_5b8a2375d0d9` đã completed, attempt_count=1, input text version=29,
canonical hash `102a200441d5c986fc5dd7194ff37e0b1a5945ae1f0374282a61468600670876`.
Không coi tài liệu phiên800 là bằng chứng thay cho kiểm tra này.

## Thay đổi

- Prompt `qnu.ocr.spelling/v4`, context recipe `qnu.ocr.spelling-context/v1`.
- Context từ canonical đúng version/hash: title gần nhất, block lân cận và ô
  header/cùng hàng của chính bảng. Ngữ cảnh chỉ đọc; enum evidence ID chỉ cho target.
  Ranh giới trang được đánh dấu candidate; không tự ghép. Giới hạn context 8.000
  ký tự, mỗi mục 1.500, cờ truncation; target giữ nguyên. ModelOps kiểm toàn request.
- Schema mới yêu cầu trích cụm trước/sau. Kiểm chuỗi nguồn, anchor, overlap, số và
  chỉ thay đúng đoạn được đề xuất. Giữ literal validator cũ cho công cụ đọc raw v3,
  runtime mới dùng validator contextual bắt buộc, không fallback nhận response cũ.
- So sánh cấu trúc chữ Unicode sau tách dấu để giữ các thay đổi sang từ khác/dấu
  câu/khoảng trắng trong `withheld_suggestions`. Ví dụ `bán → huyên` cần đối chiếu
  ảnh, `bán → bản` được đưa vào danh sách đề xuất để con người xem xét. Không có
  mapping theo từ hoặc câu test. Guard này không chứng minh đúng nghĩa; có thể giữ
  cả sửa OCR hợp lệ để con người xác nhận khi chữ cơ sở khác.
- Lưu context/recipe/withheld trong trace của lượt kiểm tra; GET/idempotency replay
  trả lại đúng kết quả mà không gọi model lần nữa. Không tự áp dụng hoặc tạo TextVersion.
- UI hiển thị cụm sau sửa và danh sách cần đối chiếu ảnh không có nút áp dụng; toast
  không báo "không có gợi ý" nếu còn mục cần đối chiếu. Hợp đồng đọc lượt cũ được giữ.

File ứng dụng: `backendV1/qnu/domains/ocr/review/{context,detection,schemas}.py`,
`frontendV1/src/features/knowledge/{ocr-types.ts,ocr-text-review-panel.tsx,spelling-result-panel.tsx}`.
Regression: unit/API/frontend `*context_review_801*` / `ocr-context-review-801.test.tsx`;
FakeSpeller651 thêm đúng hai trường quote của protocol mới, không giảm assertion.
Giữ mọi thay đổi797 và các thay đổi người dùng có sẵn. Phiên800 đã tồn tại do công
việc compiler của người dùng nên chọn801; không ghi đè nhật ký/snapshot cũ.

## Kiểm chứng thực chạy

- Regression đầu tiên chưa có module mới: collection ERROR do thiếu module; chưa
  phải benchmark hay tái hiện semantic bằng model. Sau triển khai: unit 28 PASS
  gồm17 mới và11 literal anchors797, exit0.
- Backend full `python -m pytest -q --basetemp=../tmp/ocr801-pytest`:
  **693 PASS / 1 FAIL / 76 SKIP**, exit1. Exact lỗi nền716:
  `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge`
  actor fixture401; không sửa hay bỏ test. Tổng gate vẫn FAIL.
- API qua FastAPI/loopback provider/Postgres riêng: **38 PASS / 1 FAIL**, exit1,
  169.98s. Toàn31 test OCR/context/review đạt. Bảy test compiler đạt; còn
  `test_compiler_source_versions_654.py::test_exact_saved_text_is_pinned_despite_newer_saved_text`
  thất bại KeyError `incoming['text_version']` trong prompt projection. Assertion
  ngay trước đó xác nhận model nhận đúng text version đã chọn. Các file compiler
  và test654 không có diff; chưa chạy baseline riêng nên không tuyên bố gate đã xanh
  hoặc lỗi này đã được sửa. Database test tự sở hữu đã drop, remaining=0.
- Frontend Vitest `ocr-context-review-801` + `knowledge-completion-681`: 27 PASS,
  exit0. `npm run build` (Vite + TypeScript): exit0, có warning chunk size.
- Ruff6 file và format5 file: exit0. Biome4 file: exit0. Diff/UTF8/LF/link kiểm cuối.
- Log: `tmp/ocr801-be-full.log`, `tmp/ocr801-schema-api.log`,
  `tmp/ocr801-fe-build.log`. Runner test DB: `tmp/ocr801-api-runner.py`.
- Quét mọi liên kết lịch sử trong PROJECT_CONTEXT gặp link phiên298 cũ không tồn
  tại; giữ nguyên ngoài phạm vi. Kiểm cuối chỉ xác minh các liên kết mới801 và
  guide được sửa, đồng thời kiểm UTF-8/LF toàn bộ16 file trong phạm vi.

## Giới hạn và tiếp tục

Chưa inference model thật bằng v4, chưa kiểm UI qua browser/screenshot. Port chat
hiện là text-only; chưa thêm visual model/crop inference, không giả ảnh đã được
xác minh. Bản v4 tăng thông tin và chặn suy đoán đổi từ, không cam kết sửa hết lỗi.
API/worker hiện chưa reload mã mới; phiên29 và compiler cũ không bị thay đổi. Chỉ
khởi động lại serve khi người dùng sẵn sàng dùng bước kiểm tra mới; không cần tạo
lại compiler29 vì thay đổi này.
