# Phiên 823 — MinerU làm OCR mặc định trong V1

## Yêu cầu và phạm vi

Người dùng yêu cầu đổi OCR mặc định sang MinerU sau benchmark GPU822. MinerU trước
đây chỉ có trong script đo thử. Phiên này nối dịch vụ vào ứng dụng V1, cấu hình qua
ModelOps rồi kiểm tra một lượt OCR thật. Giữ Nemotron, nguồn và lịch sử cũ. Không
compiler/publish/index lại tài liệu cũ; không restart dịch vụ đang mở, commit hoặc push.

Áp dụng skill ModelOps resilience, knowledge ingestion, backend, frontend và clean code.

## Cách triển khai

- Transport `mineru_tasks/v1`: gửi cả PDF một lượt (`standard`, `auto`, `default`).
  DOCX dùng PDF cố định đã lưu; nguồn có chữ vẫn chạy native-first. Không biến mỗi
  trang thành một tác vụ PDF riêng.
- Checkpoint ghi trước POST/PUT, giữ task/file ID và hash đầu vào. Sau khi có task ID
  chỉ thăm dò tác vụ cũ; PUT mơ hồ không gửi lại. POST mơ hồ không có ID kết thúc
  uncertain. Chờ hoàn tất theo policy ModelOps; timeout của một kết nối không phải
  trần thời gian xử lý PDF. Worker vẫn có giới hạn vận hành cấu hình được.
- Mỗi vòng poll kiểm lại quyền, lease, revision/hash và provider đã ghim. Không theo
  redirect hoặc URL kết quả tùy ý; chỉ tải endpoint file thuộc base URL đã cấp phép.
- ZIP gốc lưu bất biến qua BlobStore (`provider_document`); từng raw page liên kết
  SHA256 ZIP. Chuyển `middle_json` sang canonical hiện có: thứ tự trang/block, bbox,
  chữ nguyên văn, bảng HTML/rowspan/colspan/ô rỗng. Không đoán header hoặc sửa chữ.
  Từ chối thiếu/trùng trang, bbox sai, archive path traversal/symlink/ZIP quá lớn.
  Bảng không tái dựng được giữ raw và cảnh báo.
- MinerU không báo LLM token: ledger vẫn ghi request/model/quyền, `total_tokens` và
  `cost_usd` là NULL, status unknown. Chỉ OCR MinerU được reserve 0 token nội bộ;
  provider khác vẫn cần ngân sách dương. Workspace bị khóa vẫn bị chặn. Không gán
  giới hạn context giả cho MinerU. Cần khai báo quota tháng theo cơ chế hiện có.
- Migration0011 thêm loại provider/artifact và cho reservation tokenless; không xóa
  dữ liệu. Downgrade bị từ chối nếu còn bằng chứng MinerU/usage tokenless.
- UI có giao thức MinerU, capability OCR khi thêm model, loại bỏ nhánh đổi port
  Nemotron cho kết nối MinerU. Catalog gửi provider_type để giao diện không chặn
  MinerU vì thiếu ngân sách ảnh LLM. Chỉnh sửa chính tả và xác nhận người dùng giữ nguyên.

## Cấu hình thực tế đã áp

- Profile app `.env` root: DB `qnu_ai_platform`, schema cũ0007 được nâng theo chuỗi
  đến0011; mặc định hệ thống và2 workspace active đã có đổi OCR sang provider MinerU
  `prv_507040a208b2`. Khóa nạp một lần từ tệp REST đã được cho phép vào ModelOps mã hóa.
  Không thêm key vào env. Chat/embedding/rerank mặc định giữ nguyên.
- Profile E2E93faa11f0caf: schema0010→0011, provider MinerU
  `prv_76bcb55987bd`, mặc định hệ thống và workspace `ws_6a1f64c24d44` đã đổi.
  Không reset E2E, không sửa lịch sử/checkpoint OCR cũ. Runner provider-setup vẫn có
  cấu hình kiểm từng model riêng; chạy lại setup sẽ áp cấu hình của runner.
- Workspace thử mới `ws_179b39abe7fa` và collection riêng chứa bản363 đã OCR, chưa
  xuất bản hoặc lập chỉ mục. Các workspace mới về sau vẫn cần cấp model/mặc định
  qua ModelOps; không tự vượt allowlist hoặc lấy global default làm bằng chứng quyền.

## Lượt thật qua ứng dụng

- Source363 SHA256 `59444d277a5e904808537ce70544c1fc83c0bf0a2f2653b78af362af59d5cccc`.
- Run `ocr_765c2329e654`:32/32 completed,36,89s tính cả native/render/store/provider/
  assembly. Đây là lượt warm/cache chưa kiểm soát, không dùng để khẳng định mọi file.
- MinerU task `job_fe4ae5d541d630fb941127d3`,1 lượt dispatch; checkpoint uploaded,
  không retry inference.18 kiểm tra live đạt; nguồn trước/sau giữ hash.
- Canonical441 blocks (gồm native image evidence),8/8 bảng parsed,600 review units,
  Text Version0,131 artifacts. Technical validation0errors/0warnings. Không đồng nghĩa
  toàn bộ chữ OCR chính xác hoặc người dùng đã duyệt. Bản raw/ảnh/canonical còn nguyên.
- Artifact local `tmp/mineru823/live-363.{json,md,zip}`, manifest và live-review.json;
  bản bền vững đồng thời ở BlobStore app. Không đưa corpus hoặc ZIP vào Git.

## Kiểm chứng

- Unit mới16PASS; integration API/DB mới5PASS; kiểm provider/key/grant/default/ledger,
  forbidden/disabled/quota, checksum, parse, chặn duplicate, POST/PUT mơ hồ, redirect.
- Đọc offline output thật822:32+29trang,409+106blocks (bao gồm2caption bảng),
  34/34bảng parsed; không gọi lại. Caption/footnote là block riêng để không mất
  khi xuất Markdown. Regression cuối16unit+5API đạt trên mã parser cuối; exit0.
- Build đầu sau khi thêm provider_type phát hiện nullable TypeScript; đã sửa kiểu
  và chạy lại build/typecheck đạt, không bỏ kiểm kiểu.
- FE scoped25PASS/5suites, full701PASS/80suites, exit0; build đã kiểm lại exit0.
  Catalog MinerU không bị chặn bởi image-token bound; Nemotron vẫn giữ guard đó.
  Biome6file đạt; chưa browser QA trực quan. Ruff scoped đạt, diff whitespace đạt.
- Lượt full1306 đầu bị ngắt theo phiên làm việc trước khi ghi JUnit đủ; NOT COMPLETE.
  Không biến log PASS từng phần thành full PASS. Ba DB thuộc lượt ngắt đã dọn sau
  khi xác nhận không còn kết nối.
- Full lần cuối:1306 nodes,1304PASS/2FAIL/0ERROR/0SKIP,exit1,1224,72s
  (20phút24,72s),4nhóm DB riêng. Hai ca FAIL:
  `tests/unit/test_migration_baseline_661.py::test_single_initial_revision_has_no_dependencies`
  và `::test_initial_schema_offline_sql_creates_v1_without_touching_legacy` còn
  cố định10migration/head0010. Đã cập nhật11migration/head0011, bổ sung assert
  down_revision, SQL MinerU/rawZIP/tokenless; giữ toàn bộ guard không đụng legacy.
- Sau sửa2test: chạy riêng `tests/unit/test_migration_baseline_661.py` và
  `tests/unit/test_mineru_823.py`:18PASS/0FAIL,exit0,1,67s. Không chạy full thêm
  lần nữa; báo cáo full lịch sử vẫn FAIL, không đổi màu hoặc bỏ assertion.
- JUnit đủ1306ca, không trùng/thiếu theo class/function;6case ZIP có ID chứa DOS
  timestamp biến đổi giữa collect/run nên đối chiếu thứ tự6case riêng,1300ID khác
  khớp exact. Đã đặt6ID ổn định trong fixture mới để tránh biến động này. Nội dung
  case không thay. Tất cả DB test phiên823 đãdọn0; sentinel legacy mỗi DB giữ nguyên.
- Ruff cuối7file PASS; whitespace diff PASS; so bí mật MinerU với mọi file
  sửa/thêm không có key; tài liệu mới UTF8khôngBOM/LF và link local đạt.
- Bằng chứng: `tmp/mineru823/final/summary.json` (giữFAIL),
  `final-focused.xml/log`, `frontend-full.log`, `frontend-build-verified.log`,
  `focused-final-console.log`, `root-live.json` và `e2e-live.json`.

## Vận hành tiếp

Mở lại API/worker bằng lệnh V1 hiện có để nạp mã mới rồi upload tài liệu mới.
Chọn tự động hoặc OCR mặc định: MinerU. Nếu chọn tường minh Nemotron thì giữ lựa
chọn đó. Các nguồn cũ giữ provider/config/parser đã ghim, không tự xử lý lại.
Chưa triển khai demo/server; chưa đo chính tả toàn61trang hoặc chạy lại53câuRAG.
