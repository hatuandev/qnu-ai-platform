# Context664 — Sửa hủy lượt chat khi dừng và lưu trữ

## Yêu cầu và phạm vi

Người dùng đồng ý sửa hai lỗi trong review Context663: tắt/bật trợ lý và lưu trữ/
mở lại hội thoại qua API cập nhật có thể nhận phản hồi muộn của lượt cũ.
Chỉ backendV1, giữ API hiện hữu, workspace/membership/role và ownership ở server.
Không làm purge, GC, DR restore hoặc thay chính sách duyệt Compiler trong batch này.

## Thay đổi và phương pháp

- Thêm `cancel_related_jobs` vào lifecycle effects và tái dùng ở cả lifecycle,
  assistant PUT khi `is_active=false`, conversation PUT khi `status=archived`.
- Quyền và revision được kiểm trước khi hủy. Hủy giữ workspace lock, khóa turn;
  trạng thái dừng, cancelled/lease và audit commit cùng transaction. Không tạo
  job, không tự resend, không đổi revision cấu hình chỉ vì tắt/bật.
- Audit hiện hữu thêm `cancelled_turns` theo số lượt thật bị hủy. Bật/mở lại
  không hồi sinh turn đã hủy; key cũ vẫn báo cancelled, lượt mới dùng key/seq mới.
- Thêm 10 regression qua API/DB: phản hồi muộn và gửi lượt mới; phạm vi mọi owner
  của đúng trợ lý/chỉ hội thoại được sở hữu; giữ lịch sử completed và trợ lý khác;
  người thiếu quyền; cập nhật active; rollback khi audit lỗi.
- Cập nhật tài liệu API/lifecycle và quy trình hội thoại. Không đổi schema,
  dependency, cấu hình provider, frontend hoặc migration.

## Kiểm chứng đang hoàn tất

Cwd `backendV1`, Python `.venv/Scripts/python.exe`. Harness tạo DB sở hữu riêng,
chỉ mạng loopback, model HTTP tổng hợp; không gửi corpus/key AI thật.

Regression trước sửa:
`-X utf8 storage/context661/run_tests.py tests/integration/test_chat_stop_updates_664.py -k stop_and_resume -q`
exit 1: 2 FAIL đúng HTTP200/completed/có result, 8 deselected, 22,75 giây pytest.
Không nới assertion để sửa lỗi. Số cuối sau sửa và full gate bổ sung khi hoàn tất.

## Quan sát trình chạy focused

Pytest ghi 50 PASS sau 460,58 giây, nhưng launcher kết thúc chậm thêm khoảng
130 giây. Không coi summary là bằng chứng exit/cleanup khi chưa có receipt.
Sau đó launcher tự kết thúc exit 0, receipt xác nhận DB đã dọn và sentinel/version
legacy giữ. Kiểm tra bổ sung gặp DB đã được dọn; guard process cũng từ chối dừng
vì process đã thoát. Không có Stop-Process hoặc DROP thủ công nào được thực hiện.
Chưa xác định nguyên nhân chậm kết thúc trên Windows; không sửa hạ tầng trong task.

## Kết quả cuối

Focused: 50 PASS / 0 FAIL / 0 SKIP, exit 0. Full: 575 PASS / 0 FAIL / 0 SKIP,
10 mới và 0 mất so 565; bốn nhóm không trùng, mỗi nhóm DB thử riêng.
Ruff/format 4 file PASS; UTF-8/LF PASS; OpenAPI 96 path/123 operation giữ.
487 file legacy/migration khớp seal; head vẫn 0001_initial_schema.
Sáu DB thử dọn, sentinel/version giữ; 0 collection vector v1 quan sát.

Lệnh focused: `-X utf8 storage/context661/run_tests.py tests/integration/test_chat_stop_updates_664.py tests/integration/test_lifecycle_659.py tests/integration/test_lifecycle_runtime_659.py tests/integration/test_conversations_649.py -q`.
Lệnh full: `-X utf8 storage/context664/full_gate.py` (manifest 65 test file).
Chỉ test PostgreSQL/Redis/Qdrant cục bộ và HTTP model tổng hợp. Chưa AI thật,
quality benchmark, thay DB/schema/config phục vụ, restart/deploy hoặc frontend.

[Báo cáo](../bao_cao/context664/REVIEW.md) · [Receipt](../bao_cao/context664/verification.json).
