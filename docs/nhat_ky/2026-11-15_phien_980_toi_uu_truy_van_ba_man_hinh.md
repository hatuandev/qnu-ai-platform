# Phiên 980 — Tối ưu truy vấn trang chủ, chính tả và tác vụ

## Phạm vi

Xử lý ba điểm mức vừa trong review. Kiểm thử bằng dữ liệu tạo cho bộ test, cơ sở dữ liệu PostgreSQL cô lập và model giả lập.

## Thay đổi

- Trang chủ chatbot đọc thông tin công khai và đối chiếu nhóm phiên bản tài liệu đã phát hành với chỉ mục đang phục vụ. Các bộ thuộc nhiều đơn vị được so theo cặp đơn vị và kho. Chỉ mục phải hoàn tất, đang hoạt động và có thông tin manifest. Luồng trả lời tiếp tục áp dụng kiểm tra căn cứ của RAG.
- Trang chi tiết tài liệu tải bản tóm tắt soát chính tả theo lượt OCR và phiên bản. Bản tóm tắt trả trạng thái, tiến độ, số gợi ý và số vị trí bỏ qua. Mở màn rà soát mới tải gợi ý đầy đủ. Lượt kiểm tra và kết quả duyệt được ghép theo nhóm. Giao diện cập nhật định kỳ khi còn tác vụ đã quan sát được, đồng thời kiểm tra thêm một lần nếu bước chuẩn bị vừa kết thúc mà chưa có kết quả soát.
- Trang Tác vụ nạp bản ghi theo nhóm loại. Tiến độ lập chỉ mục lấy từ một phép đếm theo lượt chạy cho trang hiện tại. Chỉ đoạn đã có mảng vector được tính. Ca kiểm thử phát hiện JSON `null` trước đó bị đếm nhầm dù đoạn đang chờ xử lý.

## Kiểm chứng

- Backend V1: Ruff cho file đổi đạt. `python scripts/run_isolated_tests.py -q tests/integration/test_publication_channel.py tests/integration/test_ocr_text_review_651.py tests/integration/test_operations_655.py --maxfail=2` có 61 đạt và ca tiến độ mới phát hiện lỗi JSON `null`. Sau khi sửa điều kiện đếm, chạy lại `python scripts/run_isolated_tests.py -q tests/integration/test_operations_655.py` đạt 5/5. Hai DB kiểm thử đều đã được dọn.
- Cổng kiểm thử toàn bộ dùng `python scripts/run_isolated_tests.py -q --maxfail=2 tests/unit tests/contract tests/invariants tests/migrations tests/parity tests/integration tests/live`. Kết quả 552 đạt, 2 lỗi nền và dừng ở ngưỡng đã đặt. Hai ca lỗi trùng phiên 978 là `test_legacy_source_deletion_718.py::test_deleted_source_can_request_new_permanent_preview_but_other_deletes_stay_blocked` và `test_migration_baseline_661.py::test_initial_schema_offline_sql_creates_v1_without_touching_legacy`.
- Frontend V2: Biome sáu tệp và `npm run build` đạt. Chrome với phản hồi API giả lập xác nhận đúng phiên bản yêu cầu, gọi tiếp khi soát đang chạy và dừng sau khi nhận hoàn tất.
- OpenAPI thêm đường dẫn tóm tắt và hai schema phản hồi. Không có migration.

## Giới hạn

- Trạng thái thẻ công khai là kết quả đối chiếu từ PostgreSQL. Việc đọc nội dung đã ghim vẫn diễn ra qua luồng trả lời. Chưa đo thời gian phản hồi với tải production hoặc chạy G3.
- Khi tác vụ soát tự động còn trong hàng đợi sau khi bước chuẩn bị đã kết thúc, nó chỉ xuất hiện ở lần đọc từ lúc worker tạo bản ghi. Có thể thấy trạng thái mới khi mở lại trang hoặc quay lại cửa sổ.
