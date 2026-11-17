# Phiên 990 — Rà soát và metadata trong lượt chạy lại tài liệu tuyển sinh

Phạm vi gồm rà soát sau biên dịch, năm và lịch có căn cứ, đề xuất metadata sai kiểu ở phần AI bổ sung. Đối chiếu trên collection thử `col_7a022d5331bf` và tái dùng nguồn đã ghim của các tệp 01–05.

## Thay đổi

- `compilation/review` giữ phản hồi gốc và ghi riêng đánh giá đã kiểm tra. Nhận xét cần dẫn chứng nhưng để trống chuyển sang `uncertain`. Mã dẫn chứng ngoài phần và thiếu đơn vị đánh giá vẫn thử chia nhỏ trước. Khi phần đã tới giới hạn xử lý lỗi hợp đồng, phản hồi `stop` đã lưu có thể cung cấp đánh giá còn dùng được và mục cần đối chiếu cho một đơn vị bị bỏ sót. ID đánh giá lạ, bị lặp hoặc thiếu nhiều mục vẫn bị chặn. Mã dừng của phần được ghi lại kể cả khi dọn trạng thái gặp lỗi.
- `event_schedule.py`, `metadata.py` và `compilation/supplement.py` phân biệt hạn nộp lệ phí, đăng ký dự thi, ngày thi và xác nhận nhập học. Danh sách ngày giữ từng ngày, hạn ghi “trước” giữ dấu loại trừ. Năm trong câu giả định bị loại cả ở quy tắc tự động và đề xuất AI trích ngắn. Trường lịch rỗng được bỏ khi tuần tự hóa bộ lọc cũ.
- `compilation/segments.py` xử lý riêng mục metadata sai kiểu, bảo toàn phần nội dung và kiểm tra dẫn chứng. Bộ đếm mục bị loại nằm trong bản biên dịch bổ sung. Lược đồ request của lượt structured giữ hình dạng cũ để tái dựng đúng fingerprint. FE V2 hiển thị danh sách ngày và dấu “trước” trên thông tin lịch.

## Kiểm chứng

| Hạng mục | Kết quả |
| --- | --- |
| Tệp 01, API xem trước đăng ký | 4 sự kiện có nguồn, gồm hạn lệ phí, ngày thi 19–21/06, hạn đăng ký thi và hạn xác nhận trước 17:00 ngày 21/08. 18 gắn nhãn năm dữ liệu 2026. |
| Tệp 02, 03, 04, phát lại phản hồi đã lưu | Đối chiếu 11 phản hồi từng lỗi hợp đồng. Thiếu dẫn chứng tạo mục cần đối chiếu. Các phản hồi còn lại cho thấy mã dẫn sai phạm vi và một đơn vị bị bỏ sót. Cơ chế chia nhỏ trước và đọc raw khi cạn khả năng phục hồi được kiểm bằng regression có trường hợp âm. |
| Tệp 02, rà soát Qwen thật | `rvw_582a89bd333d` hoàn tất 14 phần, `needs_attention`. Báo cáo gồm 631 mục nguồn và 637 mục bản nháp, 3 mục cần đối chiếu. Lượt chạy bắt đầu trước lúc siết thứ tự phục hồi ở bản cuối. |
| Tệp 03, rà soát Qwen thật | `rvw_c9a6650f5e21` hoàn tất, `needs_attention`, 74 mục nguồn đã kiểm, 76 mục bản nháp gồm 1 mục chưa kiểm chứng. API xem trước đăng ký chỉ trả năm dữ liệu 2026. |
| Tệp 04, rà soát Qwen thật | `rvw_9134bbf35327` hoàn tất 13/13 phần, `needs_attention`. Báo cáo gồm 1.402 mục nguồn, 1.418 mục bản nháp và 11 phát hiện. Khoảng 55 phút 38 giây, 633.682 token tổng theo provider. Lượt chạy bắt đầu trước lúc siết thứ tự phục hồi. |
| Tệp 05, biên dịch Qwen thật | `cmp_7b5d064278b8` hoàn tất phần bổ sung. JSON nguồn giữ nguyên 5 mục, 10 bảng và 850 dẫn chứng. Phát lại phản hồi từng lỗi xác nhận giữ 2 đề xuất và loại đúng 1 đề xuất sai kiểu. |
| Regression trọng tâm | 127 unit đạt. Kiểm tra bao gồm chia phần, đọc phản hồi khi đã cạn khả năng chia, điều kiện năm/lịch và serialization cũ. |
| Integration | 31 đạt trên DB cô lập, gồm báo cáo thiếu dẫn chứng, kiểm tra phạm vi, chia phần và cơ chế giữ mã dừng khi dọn trạng thái lỗi. Harness đã dọn DB thử. |
| Toàn bộ unit | 1.280 đạt, 3 lỗi ở `test_legacy_source_deletion_718.py` và `test_migration_baseline_661.py`. |
| Full Pytest | `make.ps1 test-be` đã chạy trên snapshot giữa chặng và đã có lỗi. Bản cuối được kiểm lại bằng 127 unit và 31 integration. Ngoài phạm vi này, kiểm tra độc lập `test_revoked_provider_fails_only_review_before_http` vẫn thất bại ở điều kiện chặn trước khi gọi provider. |
| Frontend | Biome trên 2 tệp sửa và `npm run build` đạt. Vite báo cảnh báo kích thước bundle. |

Lệnh Backend chạy từ `backendV1` với `uv run ruff check` trên các tệp đã thay đổi và `uv run pytest -q --basetemp <temp>` với các bộ unit về review, compilation, metadata và scope. Integration dùng `uv run --project backendV1 --env-file .env python backendV1/scripts/run_isolated_tests.py tests/integration/test_compiler_review_652.py tests/integration/test_compiler_review_segments_750.py tests/integration/test_compiler_segments_api_744.py -q` từ root. Harness tạo và dọn riêng cơ sở dữ liệu `qnu_v1_test_*`.

Với bộ kiểm tra cuối, phát lại 21 phản hồi mới của tệp 02 và 04 trên đúng phạm vi đã ghim. Có 17 qua kiểm tra ngay và 4 có thể tạo phát hiện sau khi cạn khả năng chia. Hai lượt Qwen dài dùng bản giữa chặng. Chi phí và thời gian của thứ tự chia ở bản cuối chưa được đo với Qwen thật.

Chưa phát hành hoặc lập chỉ mục lại bản thử cho phiên này. Tệp 05 được kiểm lại khâu biên dịch, lượt rà soát trước đó đã bị người dùng dừng. Tệp 06–24 và bộ câu hỏi benchmark nằm ngoài lượt kiểm tra lại lỗi đã thấy ở tệp 01–05.
