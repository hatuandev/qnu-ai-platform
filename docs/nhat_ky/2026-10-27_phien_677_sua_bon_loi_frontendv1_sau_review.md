# Phiên677 — Sửa 4 lỗi frontendV1 sau review676

Người dùng yêu cầu xử lý cả4lỗi. Đã áp dụng skill clean-code/frontend; đọc lại
PROJECT_CONTEXT, Git và mã thực tế, xác nhận ứng dụng chưa đổi từ review676.
Phạm vi6tệp FE source,5tệp test mới và tài liệu; giữ BE/KTX/config runtime.

R1 giữ căn cứ nháp OCR, chặn lưu khi version trôi kể cả modal đang mở, chỉ rebase
khi có xác nhận và ngăn callback phiên cũ sửa nháp mới. R2 lỗi năm hiện cạnh ô,
chặn tìm/chat bằng nút hoặc Enter, không bỏ filter và giữ câu hỏi. R3 ghim state
index/search theo session/workspace/collection, bỏ kết quả muộn hoặc cũ hơn.
R4 hủy ticket dev-login khi SSO tiếp quản, không để pending vô hạn hoặc nhận
token cũ sau callback, chặn retry bridge trong callback. Auth server vẫn giữ.

Baseline8ca:6FAIL/2PASS. Sau sửa: trọng tâm30PASS; full211PASS/0FAIL/0SKIP,
giữ190ID+21mới; lint494tệp0/0/0; build+tsc PASS; probe6768PASS, probe67411PASS,
bundle/template sau build11PASS. Snapshot774tệp chỉ đổi đúng6source, BE/test
cũ giữ nguyên. Lint ban đầu1warning import test, bỏ import rồi lint lại0.

Chưa live API/SSO/model hoặc browser đa thiết bị; không migrate/reindex,
restart/deploy/commit/push. [Báo cáo](../bao_cao/context677/REPORT.md),
[verification](../bao_cao/context677/verification.json). Artifacts ignored tại
`storage/artifacts/context677-fe-fixes`. Luồng hiện có được sửa lỗi, không thêm
quy trình hoặc chức năng BE mới.
