# Phiên 993 — Tinh gọn lượt rà soát bản biên soạn giữ nguyên nguồn

## Phạm vi

Triển khai bước rà soát đã thống nhất. Dùng dữ liệu giả lập để kiểm tra mã. Bộ bốn tệp tuyển sinh được dành cho đợt kiểm thử sau khi báo cáo.

## Thay đổi

- `review/service.py`, `review/parts.py` và `review/literal.py` dùng báo cáo có khóa theo từng đơn vị cho lượt rà soát mới của bản nháp giữ nguyên nguồn. QNU đối chiếu cục bộ tiêu đề phân đoạn khi dựng lại chính xác các mục từ nguồn đã ghim và tìm được dẫn chứng tương ứng. Nếu bản đang xem đã đổi, tiêu đề vẫn đi qua rà soát thông thường.
- `review/report.py` rút gọn hướng dẫn và giới hạn độ dài nhận xét trong schema. Các đơn vị thuộc phần và ngữ cảnh đối chiếu vẫn tách rõ. Phần đã lập theo phiên bản prompt cũ vẫn được dựng lại bằng phiên bản đó.
- `review/repair.py`, `review/execution.py` và `review/refinement.py` lưu các nhận xét hợp lệ từ phản hồi hoàn chỉnh. Lượt phục hồi có ngân sách riêng vẫn thuộc cùng phạm vi review và chỉ giao lại các mục thiếu hoặc sai. Khi không tách được phần hợp lệ một cách an toàn, worker đi theo cơ chế chia phần hiện có. Báo cáo cuối vẫn đối chiếu đủ mục và dẫn chứng thuộc phạm vi.

## Kiểm chứng

- PASS, exit 0. `uv run ruff check` trong thư mục review và hai tệp test sửa. `uv run ruff format --check` trên chín tệp Python của đợt này.
- PASS, exit 0. `uv run pytest -q tests/unit/test_compilation_review_parts_744.py tests/unit/test_compiler_review_refinement_755.py tests/unit/test_compiler_review_budget_757.py` đạt 49 ca.
- PASS, exit 0. `uv run --env-file ../.env python scripts/run_isolated_tests.py -q tests/integration/test_compiler_review_segments_750.py tests/integration/test_compiler_review_652.py` đạt 30 ca với dữ liệu và provider giả lập. Sau khi rút gọn prompt lần cuối, chạy lại riêng `test_source_first_review_repairs_only_missing_and_uncited_units`, đạt. Ca mới xác nhận chỉ gửi lại hai mục lỗi, lưu đúng nhận xét cũ và ghép báo cáo với dẫn chứng từ nguồn đã ghim. Cơ sở dữ liệu của hai lượt test đã được dọn.

Chưa chạy bộ bốn tệp, model thật và toàn bộ bộ kiểm thử Backend V1 trong phiên này. Hiệu quả trên tệp thật về thời gian, token và chất lượng báo cáo chưa được đo.
