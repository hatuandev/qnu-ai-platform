# Phiên 929 — Hoàn tất luồng xử lý ngược, migration 0022 và khởi động lại dev

## Phạm vi và nguyên nhân

Tiếp nối các phiên 914–928, phiên này đóng bốn điểm nghẽn còn lại của luồng ngược
OCR/soát chính tả trong `backendV1`:

- Một ảnh nhúng lỗi làm hỏng cả lượt OCR dù trang vẫn còn text nền.
- Soát chính tả chạy tuần tự một lô lớn, dễ vượt ngân sách token và chậm.
- OCR ảnh nhúng gọi lại model cho cùng một ảnh và thiếu checkpoint theo ảnh.
- Kích thước lô soát chính tả cố định, không theo capacity của ModelOps.

Không reset/seed/reindex, không sửa `0020_reverse_flow`, không đổi dữ liệu hay lượt
cũ. F13 (chất lượng RAG) nằm ngoài phạm vi và giữ nguyên trạng thái mở.

## Thay đổi

- P1 — cách ly lỗi ảnh:
  - Ảnh nhúng lỗi trên trang còn text nền không còn làm lượt OCR thất bại; lượt kết
    thúc `completed_with_warnings` và ghi danh sách lỗi canonical `image_ocr_failures`.
  - Tài liệu chỉ có ảnh (không có text nền) vẫn thất bại toàn lượt, không hạ cấp.
  - Xuất bản lượt có cảnh báo cần admin xác nhận; thiếu xác nhận trả
    `publication_evidence_incomplete`. Cờ cảnh báo không thay thế quyết định duyệt.
  - `backendV1/alembic/versions/0022_ocr_warning_status.py` mở rộng cột trạng thái
    `ocr_processing_runs.status` từ `String(16)` lên `String(32)` và cập nhật check
    constraint; downgrade ánh xạ cảnh báo về `completed`.
- P3 — soát chính tả song song có giới hạn:
  - `plan_batches` xếp lô liền mạch theo `BATCH_SIZE=25` và ngân sách input của
    ModelOps; upper bound tính cả system prompt, JSON đơn vị và schema đầu ra.
  - Mỗi lô có idempotency key riêng `auto:spl:batch:{parent_id}:{offset}:{len}`;
    chạy tối đa `SPELLING_BATCH_CONCURRENCY=3`, không vượt
    `MODEL_CHAT_CONCURRENCY=4`; session và commit theo từng lô.
  - Lỗi token xác định được thì chia nhỏ đúng lô lỗi; lỗi quyền/quota/đổi nguồn/
    hạ tầng dừng lượt; không hủy các lô đang gọi provider. Kết quả gộp theo offset,
    lượt cha chỉ hoàn tất khi mọi đơn vị đã được kiểm tra.
- P5 — OCR ảnh nhúng song song và khử trùng:
  - `OCR_IMAGE_CONCURRENCY=3`; ảnh trùng SHA-256 trong cùng lượt chỉ gọi provider
    một lần qua `run.config["mineru_image_aliases"]`.
  - Mỗi ảnh vẫn có artifact `provider_document` và block riêng; checkpoint theo
    ảnh ghi dưới row lock để tiếp tục đúng ảnh sau lỗi.
- P6 — kích thước lô thích ứng:
  - Kích thước lô tính từ capacity input còn lại của ModelOps (system prompt +
    ngữ cảnh đơn vị + schema đầu ra), `BATCH_SIZE` chỉ là trần.
  - Chưa có giới hạn công bố thì dùng lát cắt cố định; một đơn vị quá lớn vẫn được
    giữ riêng thay vì cắt mất bằng chứng.
- Frontend V2: hiển thị trạng thái `completed_with_warnings`, cảnh báo ảnh lỗi và
  liên kết rà soát theo đúng lượt; không ẩn cảnh báo sau khi hoàn tất.
- Công cụ khởi động:
  - `backendV1/qnu/platform/schema.py` cập nhật `SCHEMA_HEAD` lên
    `0022_ocr_warning_status` để khớp migration đã áp.
  - `scripts/check_v1_runtime.py` báo cả revision DB và revision mà bản code hỗ trợ,
    phân biệt DB chậm hơn code (cần migrate) với code chậm hơn DB (cần cập nhật
    `SCHEMA_HEAD`).
  - Probe Qdrant dùng `trust_env=False` như adapter thật; tránh httpx đọc proxy hệ
    thống Windows có danh sách bypass chứa `[::1]` và báo `Invalid port`. Không tắt
    hay nới bất kỳ kiểm tra an toàn nào.

## Kiểm chứng

- Ruff trên các tệp backend/công cụ đã sửa: PASS.
- Nhóm trọng tâm P1/P3/P5/P6 trên DB cô lập: **63 ca PASS** trong 183,69 giây và
  **87 ca PASS** trong 174,85 giây; DB cô lập đã dọn sau mỗi nhóm.
- Smoke trên tệp scan thật 32 trang với OCR/chat giả lập: **1 ca PASS** trong 26,84
  giây; đúng một lời gọi OCR cho cả 32 trang, 32/32 trang hoàn tất, lượt soát cha
  `completed`, hai lô 25 + 7, phủ 32/32 đơn vị, 2 gợi ý cùng hình chữ được áp dụng.
  Tệp test chỉ dùng một lần và đã xóa. Đây chỉ là kiểm tra nối luồng, không phải
  nghiệm thu chất lượng OCR/chính tả.
- Test công cụ khởi động: **11 ca PASS** trong 3,78 giây, gồm ca mới kiểm tra thông
  điệp nêu đủ hai revision khi lệch schema.
- Test baseline migration: **2 ca PASS** trong 2,27 giây, xác nhận head của Alembic
  khớp `SCHEMA_HEAD`.
- Migration: đã chạy `0021_index_system_embedding -> 0022_ocr_warning_status` trên DB
  dev và đọc lại `alembic_version_backendv1` xác nhận đúng revision.
- Khởi động lại dev: cả 5 kiểm tra redis/postgres/qdrant/storage/frontend đạt; API
  `http://127.0.0.1:8002/health` trả 200; worker nạp 25 hàm và chạy cron
  `index_maintenance`; Vite `http://127.0.0.1:3002` sẵn sàng.
- Dọn rác test: xóa **756** thư mục `backendV1/storage/context636/qnu_v1_test_*` sau
  khi xác minh cấu trúc `guard/`, `pytest.log`, `objects/` và không có thư mục mới
  trong 2 giờ. Giữ nguyên log và `session917-suite`; không đụng dữ liệu ứng dụng.
- Full Pytest cô lập: **NOT RUN** — lượt chạy được khởi động nhưng người dùng chủ
  động dừng ở khoảng 2%; không có kết quả để báo PASS. Baseline lịch sử vẫn là
  **FAIL 4/1627** của phiên 928 (2 lỗi gateway RAG fixture, 1 lifecycle xóa nguồn,
  1 chat provider 504), giữ riêng và không chạy lại để làm xanh.

### E2E upload tệp scan thật qua giao diện V2

Người dùng yêu cầu chạy end-to-end thật qua giao diện, có chi phí token provider
thật và được phép tạo nguồn/lượt mới. Đã thực hiện trên stack dev đang chạy, không
reset/seed lại dữ liệu.

- Tệp: `docs/tai_lieu/quy_che_quy_dinh/quy che dao tao _QNU_2021.pdf`, 12.090,9 KB,
  23 trang scan, không có ký tự text trích xuất được. Tải qua hộp thoại "Tải tài
  liệu vào kho" của frontendV2; tạo nguồn `src_c0321a0193f9`, revision
  `rev_f5d625e93635`.
- OCR thật: lượt `ocr_df5b32587294` **completed**, 23/23 trang `completed`, 0 trang
  lỗi, 43,6 giây. Artefact: 23 `page_image`, 23 `native_page`, 23 `raw_response`,
  1 `provider_document`, 1 `canonical_json`, 1 `markdown`, 1 `manifest`.
- Chuẩn bị nội dung tự động: thẻ tác vụ đạt 100% "Đã sẵn sàng duyệt và hỏi đáp";
  nguồn hiển thị "Đã bóc tách"; trang chi tiết mở được nội dung đã chuẩn bị của
  text version 0. Không xuất bản.
- Soát chính tả tự động: lượt cha `spl_9079c95ebcee` **completed** với 16 lô con
  (P3, tối đa 3 lô song song), phủ 396 đơn vị bằng chứng, 0 đơn vị bị cắt ngữ cảnh.
  Kết quả: 15 gợi ý + 2 gợi ý bị giữ lại (withheld), 0 bị từ chối; giao diện rà
  soát hiển thị **15 "Chờ duyệt" + 2 "Cần dò"**, dải trạng thái báo "Có 17 vị trí
  cần xem". Model `qwen3.8-27b-q4`, prompt `qnu.ocr.spelling/v5`, provider
  `prv_abbb7c28cad5`; 16 bản ghi usage, 45.711 token, chi phí ghi nhận 0 USD;
  cửa sổ gọi model 20,7 giây.
- Không bấm duyệt/áp dụng/bỏ qua gợi ý, không xuất bản, không sửa nội dung; chỉ
  đọc và quan sát trạng thái. Đây là một lượt chạy thật, không phải nghiệm thu chất
  lượng OCR/chính tả.

### E2E phê duyệt gợi ý chính tả trên giao diện

Tiếp tục trên nguồn `src_c0321a0193f9`, người dùng yêu cầu test luôn luồng phê
duyệt gợi ý chính tả.

- Thao tác: áp dụng 1 gợi ý, bỏ qua 1 gợi ý, rồi "Lưu thay đổi". UI chuyển đúng
  từ 15 chờ duyệt / 0 đã nhận / 0 bỏ qua sang 13 chờ duyệt / 1 đã nhận / 1 bỏ qua,
  nút Lưu bật khi có thay đổi.
- Kết quả lưu: tạo text version **1** với đúng **1 change** do `act_dev_admin`;
  backend ghi blob JSON/Markdown mới và kiểm hash trước khi trả về. Sau lưu, UI
  chuyển về chi tiết nguồn, tạo preparation intent `prep_db726303a097` (mode auto,
  text version 1), compilation `cmp_940c0e87fa3c` hoàn tất với artefact
  `draft_json`/`input_snapshot`/`markdown`; thẻ tác vụ đạt 100% "Đã sẵn sàng duyệt
  và hỏi đáp". Không xuất bản.
- Phát hiện cần xử lý tiếp:
  - Sau khi lưu, liên kết rà soát trên trang nguồn đi theo text version mới (1).
    Version này chưa có kết quả soát, nên 13 gợi ý còn chờ và 2 gợi ý "Cần dò" của
    version 0 không còn truy cập được từ giao diện; mở route với `textVersion=1`
    hiển thị 0/0/0/0 và "Chưa có kết quả".
  - "Bỏ qua" chỉ là quyết định cục bộ trên phiên UI, không được gửi lên server
    (payload lưu chỉ chứa các thay đổi applied/custom), nên tải lại trang các gợi ý
    đã bỏ qua sẽ quay lại trạng thái chờ.
  - Chưa có nút soát lại toàn văn cho text version mới, cũng chưa có cách gộp các
    gợi ý chưa xử lý sang version mới. Cần chọn hướng: chặn lưu khi còn gợi ý chưa
    xử lý, giữ liên kết rà soát về version cũ, hay chạy lại soát chính tả cho
    version mới (có chi phí token).
- Không bấm "Duyệt", không xuất bản, không sửa tay; dữ liệu dev của nguồn test có
  thêm text version 1 và preparation intent mới.

## Giới hạn và vận hành

- F13 (RAG, phiên 908) vẫn mở: refactor, test mock và đợt OCR/chính tả này không sửa
  chất lượng câu trả lời hay rubric của bộ chấm.
- Đã có một lượt soát chính tả thật end-to-end (16 lô, 45.711 token, cửa sổ gọi
  20,7 giây) nhưng chưa phải benchmark: chưa có CER/WER, tỷ lệ từ chối trên bộ đo
  chuẩn và đối chiếu ảnh gốc để nghiệm thu chất lượng.
- Luồng `completed_with_warnings` chưa test end-to-end bằng tệp thật có ảnh lỗi và
  xác nhận admin trước xuất bản.
- Quy trình migration từ nay: thêm migration thì cập nhật `SCHEMA_HEAD` cùng lúc,
  chạy `make v1-migrate`, rồi `make v2-check` trước khi `make dev`. `make dev` không
  tự migrate.
- Stack dev đang chạy nền trong phiên này; dừng background task là dừng cả API,
  worker và frontend. Không chạy thêm `make dev` lần hai.
- Working tree vẫn chưa commit theo yêu cầu; không push hay deploy.
