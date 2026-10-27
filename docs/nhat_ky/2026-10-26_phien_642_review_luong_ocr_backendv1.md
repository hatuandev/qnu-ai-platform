# Phiên642 — Review độc lập luồng OCR backendV1

Người dùng yêu cầu xem lại prompt640 đã chạy xong. Đọc Git/source/context và skill
backend/clean-code/ingestion/ModelOps; không sửa app hoặc test suite để làm xanh.

Kết luận CHANGES REQUESTED:6probe cuối đều FAIL đúng lỗi, không fixture error:
ARQstartup thiếu ctx.settings; OCR không áp capacity; retry cùng provider_id trộn
endpoint/model; cron không phục hồi running hết lease; DOCX mất header không báo;
parse lỗi bỏ raw_response. Header OpenXML đủ declaration/relationship tái kiểm FAIL.

Full v1 hiện tại248PASS/1FAIL/0SKIP/83,42s/exit1. Lỗi local writer WinError5/read
PermissionError vẫn tái hiện trong harness trên D, nên chưa thể đóng như báo cáo640.
Ruff PASS. Source/migration640file và475legacy giữ hash;4DBtest dọn/sentinel giữ,
DB chính chưa version v1. Probe/log/receipt Git ignored; chưa gọi Nemotron thật.

Lượt probe đầu có lỗi báo pytest.fail qua portal; đã sửa probe và chạy lại đủ6ca.
Không tính6fixture error đó như lỗi app. Không migrate/restart/deploy/Git/sourcefix.

[Báo cáo, vị trí và bằng chứng642](../bao_cao/context642/REVIEW.md).
Bước tiếp: sửa F1–F6 và lỗi writer cũ, port probe vào regression chính trước live/Compiler.
