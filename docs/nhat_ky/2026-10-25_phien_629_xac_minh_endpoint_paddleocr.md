# Phiên629 — Xác minh endpoint PaddleOCR

Người dùng yêu cầu kiểm tra lại endpoint layout-parsing nội bộ sau câu hỏi vùng gửi/đích OCR của Context628. Chỉ gửi một PNG crop header trang1 PDF đã chọn tới http://100.105.13.53:8080/layout-parsing, không cloud fallback, qua adapter Paddle và Redis capacity thật. Không sửa app.

OCR629-HEADER-LIVE PASS/exit0: HTTP200/errorCode0,1,578s,1request/1page,788chars. OCR629-FIELDS-OFFLINE exit0: raw header có số123/TB-HĐTS, text có ngày11/7/2026; `_field_lines` trên Markdown thiếu số, trên raw block có cả2. Lỗi tích hợp là header rescue chỉ đọc extracted_text/Markdown trong khi server giữ số ở block header. Có lỗi chữ trong OCR, không coi crop PASS là toàn PDF PASS.

Lỗi628 là Redis cô lập trước dispatch, lượt live bị auto-review; không chứng minh OCR server hỏng. Lượt này endpoint được chỉ định rõ và live probe thành công. Không chạy lại toàn PDF/Compiler hoặc sửa bảng; nguồn628 vẫnNEEDS_ATTENTION. DBreadonly, không DBtestmới/usage/domain/configwrites, source/provider/app hashes giữ; Storage riêng giữ bằng chứng. Không index/pub/restart/modelchange/commit/push.

[Báo cáo](../bao_cao/context629/REVIEW.md). Helper ignored context629_ocr_probe.py/context629_field_audit.py; evidence backend/storage/context629 gồm safety/intent/result/http-response receipt/raw/crop/field-audit/postcheck. Lệnh và cwd/exit ghi ở báo cáo; full regression NOT RUN vì không appfix.
