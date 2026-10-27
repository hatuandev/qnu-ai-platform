# Phiên644 — Theo dõi và nghiệm thu luồng OCR

Người dùng giao triển khai cách kiểm chứng/theo dõi học từ Haystack trong phạm vi
upload→revision→job→render→ModelOps OCR→raw/canonical/Markdown→API. Compiler và
evaluation RAG nằm ngoài scope; dùng các skill backend/clean-code/ingestion/ModelOps.

Thêm trace content-free theo run/revision/generation/attempt, API đọc raw nguyên
bytes kể cả khi processing failed, reporter JUnit/receipt có đủ6nhóm kiểm tra và
tách live/quality NOT RUN. Không thêm framework/dependency hoặc schema.

Baseline hợp lệ2FAIL→focused21PASS→full286PASS/0FAIL/0SKIP,121,96s,exit0. Ruff/format
PASS; OpenAPI40path/55operation, chỉ thêm raw route. Test Redis/ARQ thực dùng queue
riêng; OCR HTTP giả lập loopback. So full643 không mất test,21ca mới.475legacyfile
giữ hash; DBtest do harness tạo đã dọn/sentinel giữ, Redis keys test đã dọn.

Live Nemotron/chất lượng ảnh nguồn NOT RUN vì runtime v1 chưa đủ cấu hình. Không
đổi config/provider/model, migrate DB phục vụ, gọi Compiler, index/pub/restart/Git.

[Báo cáo, lệnh, artifact và giới hạn](../bao_cao/context644/REVIEW.md).
