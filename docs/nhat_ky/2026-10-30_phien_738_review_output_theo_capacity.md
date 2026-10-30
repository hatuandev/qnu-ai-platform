# Phiên 738 — Ngân sách output review theo ModelOps

- Yêu cầu: sửa nhanh lỗi review bị cắt output; người dùng yêu cầu không tự chạy test. Phạm vi ngoại lệ kiểm chứng chỉ áp dụng phiên sửa này.
- Căn cứ đọc ở lượt chẩn đoán trước: compiler completed, review Qwen trả `finish_reason=length`, completion 8192 token, JSON chưa hoàn chỉnh; model được cấu hình output 16384. Lỗi ở ngân sách review cố định, không phải thứ tự chạy test hay timeout.
- Sửa: review thủ công và tự động mặc định để ModelOps tính output từ capacity và phần context còn lại. Người dùng vẫn được nhập giới hạn riêng. Giữ ngân sách compiler 8192 theo yêu cầu trước đó; không đổi DB/cấu hình provider.
- File backend: review/schemas.py, compilation/schemas.py, workflow/edits.py, modelops/inference/service.py. Tận dụng planner hiện có vốn hỗ trợ requested_output_tokens=None; adapter vẫn từ chối phản hồi bị cắt.
- File frontend: compilation-dialog.tsx, compilation-review-tab.tsx, compilation-schemas.ts, compilation-types.ts. Để trống output review tương ứng null/omitted; điều chỉnh assertion contract hiện có, chưa chạy.
- E2E workflow.spec.ts: bỏ ép 8192 cho review; đọc lại review đã lưu trước khi tạo. Khi người dùng chủ động chạy lại chặng, chỉ tạo lượt phục hồi cho lỗi chat_output_truncated trên cùng provider nếu output model lớn hơn ngân sách cũ, với khóa idempotency riêng theo giới hạn. Giữ review cũ và các lượt uncertain/lỗi cùng ngân sách; không retry vòng lặp.
- Hướng dẫn test lại đã ghi cách restart riêng serve rồi chạy compilation trong phiên hiện tại; không cleanup/init nếu tiếp tục.
- Kiểm chứng: NOT RUN toàn bộ test, build, lint, typecheck và live inference theo yêu cầu người dùng. Chỉ đọc mã/diff và sửa file. Không restart dịch vụ, gọi model hay ghi trạng thái E2E trong phiên này. Không coi kết quả lịch sử là PASS cho bản sửa này.
- Giới hạn: tăng ngân sách không bảo đảm model luôn hoàn thành JSON; nếu tiếp tục bị cắt ở giới hạn mới, lỗi vẫn được báo và cần xem trace mới. Các lỗi gate rộng của phiên 737 vẫn giữ nguyên trạng thái lịch sử.
