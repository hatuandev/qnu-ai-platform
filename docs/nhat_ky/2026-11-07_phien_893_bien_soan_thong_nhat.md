# Phiên 893 — Biên soạn thống nhất, bổ sung AI có chọn lọc

## Phạm vi

Người dùng yêu cầu hợp nhất biên soạn nhanh và phần AI hữu ích thành một thao tác trên tài liệu đang mở. Kết quả live phiên 892 cho thấy bản nền giữ đủ nguồn nhưng các đoạn AI đều chép lại nguồn; không tiếp tục gửi toàn văn qua AI chỉ để dựng lại bản đã có. Sau khi người dùng mở Docker, tiếp tục kiểm chứng trên DB tạm, không reset hoặc thay dữ liệu ứng dụng.

## Thực hiện

- Hộp thoại từ tài liệu ghim đúng run và bản văn đã lưu, dùng tên nguồn, gửi `selective_supplement=true`, `auto_review=false`. Bỏ lựa chọn chế độ, model, token và thêm nguồn ở lối này; giữ API/chức năng nâng cao ở bộ sưu tập.
- Dựng bản nền nguyên văn với bảng/citation trước. API cho đọc bản xem trước đã nhóm, UI không cho đăng ký hoặc sửa khi lượt còn chạy. Cache bản xem trước riêng với bản cuối, chỉ poll tới khi có bản nền và tiếp tục theo dõi trạng thái nhẹ.
- Chọn các nhóm văn xuôi liền nhau chưa có heading và trường định danh văn bản tường minh chưa được quy tắc giải quyết. Không gọi AI nếu không có nhóm phù hợp; không khẳng định selector bao phủ mọi metadata. Gợi ý phải có dẫn chứng thuộc nguồn được ghim và được lưu tách biệt.
- Dùng planner, ModelOps, concurrency, idempotency và chia lỗi token hiện hành. Không gán trần output mới. Phần AI lỗi xác định/không chắc chắn được báo `incomplete`, giữ bản nền và gợi ý con hoàn tất đúng một lần. Không tự gửi lại request lỗi. Lỗi source/storage/quyền/đổi cấu hình không được đổi thành kết quả AI thành công.
- Phản hồi bị cắt lưu mã provider trên nhóm, đồng thời giữ mã dừng chia nhỏ ở báo cáo tổng hợp. Loại gợi ý chép lại nguyên văn hoặc tiêu đề đã có. Metadata vẫn cần người dùng xác nhận khi đăng ký; review toàn văn là thao tác chủ động từ trang kết quả.
- Không migration, không đổi mặc định model/reasoning đang chạy, không publish/reindex/push. Giữ các thay đổi UI chưa commit của người dùng.

## Kiểm chứng

- **PASS** Ruff có phạm vi trong `backendV1` trên 11 file mã/test liên quan, exit 0.
- **PASS** `npm exec -- biome check` trên 8 file FE liên quan; exit 0, không warning.
- **PASS** `npm exec -- vitest run tests/compilation-dialog-state-809.test.tsx tests/compilation-tabs-849.test.tsx tests/ocr-original-preview.test.tsx` tại `frontendV1`: 21/21, exit 0.
- **PASS** `npm run build` tại `frontendV1`: TypeScript và build đạt, exit 0. Còn cảnh báo bundle lớn hơn 500 kB.
- **PASS** harness DB tạm: `backendV1/.venv/Scripts/python.exe -X utf8 backendV1/scripts/run_isolated_tests.py tests/integration/test_compiler_selective_893.py tests/unit/test_compiler_selective_893.py -q --tb=short`, với Selector loop cho TestClient Windows và namespace test riêng: 22/22, exit 0. Receipt xác nhận DB thử đã xóa và sentinel legacy giữ nguyên. Provider là HTTP fake loopback; không chứng minh model thật mới đã đạt.
- Regression bổ sung cho đổi model/capacity stale/sai cấu hình tái hiện 5 lỗi trước sửa classifier; sau sửa 17/17 unit đạt, exit 0.
- **PASS** Chromium cô lập bằng component thật, API bị chặn ghi: 390 và 1280 px, không tràn hộp thoại, không hiện nút/cấu hình thừa, mỗi lần nhấn gửi đúng một POST với phiên bản v6, cờ mới và idempotency key; không có pageerror. Đã xem cả hai ảnh. Fixture frontend và Vite cổng riêng đã dừng/dọn; ảnh/receipt giữ trong `tmp/check-893-dialog-*`.
- **PASS sau sửa fixture**: 24 ca (`test_review_empty_blocks_736.py`, `test_compiler_selective_893.py` integration và unit), 5 ca (`test_contextual_scope_790.py`, `test_review_literal_751.py`), exit 0. Full gate đã phát hiện helper mở rộng đóng băng `TABLE_RESPONSE` ở default argument, làm mất monkeypatch của bốn ca cũ. Sửa default thành `None` và resolve mẫu lúc gọi; không đổi assertion. Các lần kiểm lại này xác nhận sửa helper, không phải retry model thật để làm xanh.
- **Full backend FAIL**: từ root chạy `backendV1/.venv/Scripts/python.exe -X utf8 tmp/check-893-backend.py`, collect 1.489 ca, chia bốn nhóm file không trùng qua harness DB riêng; **1.477 pass / 9 fail / 3 skip**, exit 1, 1.446,91 giây. Tất cả DB nhóm đã xóa và sentinel giữ nguyên. Mã phân loại lỗi model/capacity được bổ sung negative cases sau khi full gate khởi động; bộ 24 ca cuối kiểm trên mã sau sửa.
- Trong 9 failure: bốn ca do default argument helper vừa nêu đã kiểm lại đạt; ba ca do runner thiếu `TEST_REDIS_URL` (`test_integration_gateway_pipeline.py::test_external_key_calls_real_rag_and_preserves_assistant_config[128/None]`, `test_readiness_666.py::test_worker_heartbeat_is_queue_scoped_and_removed_on_shutdown`) đã đạt 2 + 1 ca sau khi cấp Redis test riêng, exit 0. Không sửa mã app cho lỗi môi trường này.
- **Hai lỗi còn lại ngoài batch**, mã và test khớp nguyên HEAD: `tests/unit/test_table_grounding_770.py::test_ingestion_quality_and_dependencies_are_derived_not_source_rewrites` còn chờ `qnu.published-chunks/v4` trong khi chunker là v5; `tests/unit/test_rag_modelops_budgets_767.py::test_window_zero_records_bounded_bytes_and_keeps_whole_evidence` truyền actor/db `None` vào bước kiểm quyền, gây AttributeError. Không sửa chúng trong đợt Compiler và không báo full suite PASS.
- **PASS** ba ca từng skip khi thiếu Redis test: limiter thật, giao nhận Compiler qua ARQ và giao nhận OCR qua ARQ. Kiểm riêng với `TEST_REDIS_URL` ở DB Redis thử, namespace/queue thuộc test: 3/3, exit 0; DB PostgreSQL thử đã xóa và sentinel giữ nguyên. Tổng các nhóm kiểm lại trên mã cuối: 35 ca đạt, không thay thế kết quả FAIL của full gate đã chạy.
- `git diff --check` đạt tại lúc kiểm.

## Giới hạn và vận hành

Selector ưu tiên bảo toàn nguồn và tránh gọi thừa; không thay thế kiểm tra chất lượng OCR hay đánh giá ngữ nghĩa. AI không tự sửa, duyệt hoặc xuất bản. Bản cuối giữ đủ nguồn không đồng nghĩa mọi gợi ý AI đã hoàn tất. Lượt và dữ liệu cũ không được chuyển đổi tự động. Chưa chạy lại model thật cho phiên bản selective; số đo live 38,84 giây/80.926 token của phiên 892 là luồng cũ.

Khởi động app bằng `./make.ps1 dev`, mở tài liệu đã bóc tách và nhấn **Biên soạn** để tạo lượt mới. Không cần upload/bóc tách lại nguồn cũ chỉ để dùng luồng mới.
