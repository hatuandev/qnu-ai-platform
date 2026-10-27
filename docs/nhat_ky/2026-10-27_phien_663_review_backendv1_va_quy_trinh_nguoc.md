# Context663 — Rà soát backendV1 và quy trình ngược

Người dùng yêu cầu kiểm tra các chức năng BE còn cần xử lý và độ ổn của quy trình
ngược. Chỉ review và chạy probe độc lập, không sửa app hoặc DB phục vụ.

Đọc mã lifecycle, assistants/conversations, checkpoint worker, publication,
operations/backup và client FE đang gọi API. Chạy lại 23 ca lifecycle đạt; thêm
hai probe API độc lập tái hiện dừng/bật chatbot và archive/mở lại hội thoại khi
model đang trả lời. Hai API PUT không hủy turn bền vững; đều nhận HTTP 200,
turn completed, có kết quả. Luồng lifecycle mới đã hủy đúng.

Probe assistant đầu lỗi dựng request do trường thừa; sửa probe về đúng config,
không đổi assertion, chạy lại cả hai nhánh đều FAIL đúng hành vi cần sửa. Lượt
cuối 23 PASS regression / 2 FAIL độc lập, không kết luận backend hoàn toàn ổn.
Full suite không chạy lại; 565 PASS Context662 là lịch sử.

Giới hạn còn lại: soft delete giữ nguồn; purge/GC orphan/full DR chưa có;
Compiler review chưa thành publish gate; thay thế nhóm nguồn dùng chung chưa có.
Ưu tiên sửa hai đường trạng thái rồi dọn dữ liệu dẫn xuất và phục hồi vận hành.

Ba DB thử đã dọn và sentinel/version legacy giữ; không còn vector v1 quan sát.
Model HTTP tổng hợp, hạ tầng loopback thật. Chưa AI thật, quality, thay schema,
restart, deploy hoặc sửa code. Chi tiết phạm vi, lệnh/exit code, số test và bằng
chứng trong [báo cáo](../bao_cao/context663/REVIEW.md) và
[receipt](../bao_cao/context663/verification.json).
