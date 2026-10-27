# Phiên609 — Thử GPT-OSS và ngân sách đầu ra

Ngày 23/10/2026. Theo yêu cầu thử ollama/gpt-oss:120b, giữ gh/gpt-6-luna làm primary. Chỉ override route cho thí nghiệm qua ModelOps/9router, không sửa cấu hình mặc định/danh mục model, mã ứng dụng, nguồn hoặc Quality Gate.

Probe JSON tổng hợp PASS 1,56s/109 output. Compiler ba DOCX ghim nguồn, dùng lại 381 proof: lựa chọn đầu tiên JSON hợp lệ/1.950 output, bước chọn thứ hai lỗi MODEL_OUTPUT_BUDGET_EXHAUSTED, API503 sau13,96s; uncertain/bundle null, toàn compiler FAIL. Không gọi lại job uncertain hoặc coi usage lượt lỗi bằng0. Chưa đủ dữ liệu đánh giá toàn diện chất lượng GPT-OSS.

Điều tra tiếp xác định 2.500 là default WikiPolicy riêng của compiler; schema request cho tối đa8.192. Finish_reason=length kích hoạt lỗi, không chứng minh thiếu context. Thinking_budget=0 hiện không gửi tắt suy luận đến upstream; lượng reasoning thực chưa đo. Tăng output cần đồng bộ packing/preflight/cache/request và giữ workflow24K; bound input19.197 của draft preflight vừa4.096 nhưng không vừa8.192. Chưa đổi cap/chưa gọi model thêm trong phần phân tích.

[Báo cáo kết quả và phương án](../bao_cao/context609/MODEL_AND_OUTPUT_BUDGET_REPORT.md) ghi IDs PASS/FAIL/NOT RUN, artifact và tài liệu chính thức đã đối chiếu. DB609 local có ownership đã dọn; Storage giữ theo chính sách bảo vệ, không thử vượt chặn. Model/defaults/nguồn/index/full vector payload2.943points/0retrievable và457app files khớp. Không full test mới vì không sửa app; full608 vẫn FAIL18baseline, không relabel PASS. Không benchmark64/reindex/publish/restart/commit/push.
