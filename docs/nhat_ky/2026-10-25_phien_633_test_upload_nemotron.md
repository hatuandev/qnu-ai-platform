# Phiên633 — Kiểm thử kho tài liệu → kho tri thức → Nemotron

Ngày: 2026-10-25. Người dùng yêu cầu test upload, chuyển kho tri thức, bóc tách DOCX/PDF với endpoint/model Nemotron đã cung cấp. Dùng fixture tổng hợp 1 DOCX, 1 PDF native, 1 PDF scan, bảng tiếng Việt 16 ô. Skill áp dụng: qnu-knowledge-ingestion và qnu-modelops-resilience; giữ nguồn/hash và key qua ModelOps.

Kết quả: upload/download/hash/idempotency PASS; import native 2/2 succeeded; OCR trực tiếp PNG/PDF scan PASS 16/16 ô, không fallback; regression29 PASS. Reparse PDF review_required/TABLES_NOT_MATERIALIZED; DOCX failed/DOCX_LAYOUT_ALIGNMENT_FAILED. Tổng thể chưa nghiệm thu đầu-cuối. Replay xác nhận HTML OCR làm lệch đối chiếu DOCX dù phần chữ đúng; PDF raw/JSON đủ ô nhưng phép kiểm Markdown và header còn giới hạn.

API chặn artifact v1 kế thừa trong revision DOCX failed bằng HTTP409. Active sources vẫn là v1; 0 index revision, chưa publish/vector/Compiler. Import batch chưa có engine riêng; scan→initial knowledge với Nemotron NOT RUN. Không ép qua default toàn cục: auto-review chặn thao tác đó trước khi chạy, đã dùng per-source request an toàn.

Thay đổi phiên này: tạo provider/key pool bằng ModelOps, group/collection CTX633 và ba tài liệu thử; cấu hình OCR riêng collection, defaults toàn cục không đổi. Fixture/runtime receipts trong backend/storage/context633 bị Git ignore. Chỉ thêm báo cáo/journal/snapshot/index; không sửa mã app, không restart hay đụng diff có sẵn.

Lệnh thực chạy từ backend: pytest test_nemotron_ocr_631.py -vv -o faulthandler_timeout=30 (29pass/exit0/3,20s); prepare_and_probe.py, e2e_upload_import.py, e2e_nemotron_reparse.py, verify_results.py, final_checks.py (exit0). Full suite/UI/publish/vector NOT RUN theo phạm vi; lần pytest hạn chế mạng treo Redis không được tính PASS.

Chi tiết nguyên nhân, IDs, giới hạn và việc tiếp: [REVIEW](../bao_cao/context633/REVIEW.md), [receipt](../bao_cao/context633/result.json). Snapshot: [session633](../memory/snapshots/2026-10-25_session_633.md). Không lưu key, Base64 hay corpus nghiệp vụ trong tài liệu.

Kiểm tra tài liệu: 7 tệp UTF-8 không BOM/LF, JSON hợp lệ, không khớp mẫu credential/Base64; liên kết local của bộ tài liệu633 tồn tại. `git diff --check` trên ba index exit0. Git cảnh báo cấu hình checkout CRLF, byte tệp hiện tại vẫn LF.
