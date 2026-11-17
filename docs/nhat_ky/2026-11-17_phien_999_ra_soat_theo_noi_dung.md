# Phiên 999 — Đối chiếu bản nháp theo nội dung đã lưu

Người dùng yêu cầu tối ưu luồng xử lý tài liệu dùng chung. Điều kiện cũ chỉ đối chiếu văn xuôi nguyên văn khi lượt chuẩn bị đặt `source_first`. Bản đã có AI bổ sung vẫn có thể giữ nguyên các đoạn nguồn, như 5 mục của bản Word thử nghiệm.

`backendV1/qnu/domains/knowledge/compilation/review/service.py` cho lượt rà soát mặc định dựng lại các mục từ dữ liệu nguồn đã ghim và so với JSON bản nháp. Nếu khớp, planner áp dụng các phép đối chiếu cục bộ cho đoạn và ô bảng đủ điều kiện. Nội dung thiếu căn cứ hoặc cần đánh giá ngữ nghĩa vẫn đi qua quy trình hiện có. Kiểm tra hồi quy tại `backendV1/tests/integration/test_compiler_review_segments_750.py` đi qua API cho cả bản giữ nguồn và bản giữ nguồn có AI bổ sung thông tin. Lượt đã lưu tiếp tục dùng hợp đồng và phạm vi theo khóa yêu cầu cũ.

## Lượt thử Qwen

`cmp_2d2e9d39776d`, bản Word phức tạp của phiên 998, cùng tập nguồn, cùng cấu hình `qwen3.8-27b-q4`, JSON bản nháp khớp từng byte. Dùng API và worker backend trên kho thử nghiệm hiện có.

| Rà soát | Kết quả | Thời gian | Lượt gọi | Token provider |
| --- | --- | ---: | ---: | ---: |
| Trước sửa `rvw_c18b34c0c2c1` | Dừng ở 17/26 phần | 949,62 giây | 20 | 392.958 |
| Sau sửa `rvw_77d788329f36` | Hoàn tất 23/23 phần, có 2 mục cần đối chiếu | 118,55 giây | 5 | 102.050 |

Báo cáo gồm 840 mục nguồn và 862 mục bản nháp. Đối chiếu cục bộ 184 mục văn xuôi và 646 mục ô bảng. Hai mục cần xem lại là tên bản nháp và một đoạn dẫn cả bảng 326 ô vượt ngân sách của một lượt. Các ô nguồn của bảng có phần kiểm tra riêng. Gửi lại khóa của lượt mới hoặc khóa của lượt trước khi sửa đều trả đúng ID đã lưu. Chỉ đo rà soát, dùng lại bản nháp đã chuẩn bị. Lượt thử dừng trước phát hành và lập chỉ mục.

## Kiểm chứng

Chạy tại `backendV1`.

- `uv run ruff check` và `uv run ruff format --check` trên hai tệp Python sửa. Đạt, exit 0.
- `uv run pytest -q tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_compiler_review_budget_757.py`. Đạt 57, exit 0.
- `uv run --env-file ../.env python scripts/run_isolated_tests.py -q tests/integration/test_compiler_review_segments_750.py tests/integration/test_compiler_review_652.py tests/integration/test_compiler_selective_893.py`. Đạt 38, exit 0.
- `uv run --env-file ../.env python scripts/run_isolated_tests.py -q -x`. Exit 1 sau 8 ca đạt và 1 ca lỗi. Lặp ID lỗi nền `tests/integration/test_answer_review_p6.py::test_review_keeps_insufficient_evidence_truthful` với `KeyError: 'evidence'` trong fixture trả lời. Các ca sau dừng theo `-x`. Cả hai lượt integration dùng DB thử nghiệm tách riêng.
- `uv run --env-file ../.env python $qnuRunner` và `uv run --env-file ../.env python $qnuReplay`. Runner Qwen và phát lại lượt cũ đạt, exit 0.
