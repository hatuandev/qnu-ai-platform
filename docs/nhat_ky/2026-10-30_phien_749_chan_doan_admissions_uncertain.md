# Phiên 749 — Chẩn đoán admissions-compilation uncertain

- Yêu cầu: tìm nguyên nhân từ log người dùng, chưa sửa code/runtime.
- Report mới kết thúc2.1s, đọc lượt cũ cmp_10c51e267f1f ở checkpoint:6/15 completed, phần7 uncertain,8–15 pending. elapsed1003.4s là thời gian lượt cũ, không phải thời gian test mới.
- Worker log xác nhận phần6 trả HTTP200 lúc17:44:15; run kết thúc17:48:47 với chat_provider_uncertain, trước khi worker mới khởi động19:30:57. Phần7 bắt đầu17:44:15, sau271.2s chưa có kết quả được lưu, usage null. Mã lỗi này bao gồm timeout/lỗi truyền nhận sau connect; log hiện có chưa đủ phân biệt nguyên nhân upstream cụ thể. Không gán cho lần dừng tiến trình ở phiên748.
- Backend ghi compilation_request_interrupted cho phần running không có raw; không tự resend vì chưa biết provider đã xử lý/tính token hay chưa.
- admissions-publication.ts chỉ tạo recovery/replan khi run.status==failed; uncertain giữ nguyên và session.waitProgress ném lỗi ngay. Vì vậy chạy lại lệnh không tạo lượt v4, không kiểm chứng sửa747. concurrency=2 trong progress không chứng minh lượt15phần cũ đã chạy song song; timestamps1–6 nối tiếp.
- Hướng dẫn phiên748 còn thiếu cách xử lý run uncertain. Hướng tiếp: phục hồi có chủ đích/tạo run mới dùng nguồn OCR hiện có, giữ lịch sử/partial, không reset uncertain thành pending hay tự gọi lại request cũ. Không cần cleanup/init/upload/OCR lại.
- Đã đọc attachment, checkpoint chỉ phần publication, worker log sự kiện, E2E/helper và backend. Không chạy test/model, không đổi checkpoint/DB/source code/restart. Chưa kiểm chứng planner v4 hoặc tốc độ mới.
