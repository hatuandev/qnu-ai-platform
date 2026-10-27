# Phiên643 — Sửa sáu lỗi OCR backendV1

Người dùng gửi phản hồi OCR và giao sửa6phát hiện642. Áp dụng skill backend,
clean-code, ingestion và ModelOps; giữ thay đổi chưa commit ngoài phạm vi.

Sửa startup Settings, nối capacity/accounting ảnh với quota, ghim target/prompt và
kiểm reuse/resume, heartbeat/fencing + recovery job, chặn DOCX header/footer không
được converter giữ đầy đủ, lưu raw bytes trước parse và giữ raw lỗi/truncated.
Không dùng usage một mẫu làm ngân sách mọi trang, không tự sửa chính tả.

6regression trước sửa6FAIL/10,92s. Focused cuối76PASS/45,61s, full265PASS/0FAIL/
0SKIP/98,51s, replay riêng1PASS/4,26s; exit0 ở các gate cuối. Ruff toàn v1/format13file/
OpenAPI PASS.16ca mới. Mẫu giữ10block/bảng6x6/6header, raw khớp byte và usage4077;
chỉ replay với ảnh tổng hợp, chưa xác minh với ảnh nguồn hoặc gọi Nemotron thật.

8appfile v1 sửa +2helper mới;475legacy giữ.5DBtest dọn/sentinel giữ, DB chính chưa
migrate. Không restart/deploy/Git/default/key. Driver local giữ nguyên, full lượt
này PASS không chứng minh đã chữa nguyên nhân PermissionError chập chờn642.

DOCX header/footer hiện bị chặn rõ, có thể cung cấp PDF giữ bố cục. OCR thật cần
token_limits và ocr_page_input có căn cứ trong ModelOps; chưa Compiler/index/RAG.
Cập nhật hợp đồng OCR/capacity, quy trình21, report và memory/index.

[Bằng chứng, lệnh và giới hạn643](../bao_cao/context643/REVIEW.md).
