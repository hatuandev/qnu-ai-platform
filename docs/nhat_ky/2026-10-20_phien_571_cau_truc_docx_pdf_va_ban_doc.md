# Phiên571 — Cấu trúc DOCX/PDF và bản đọc

Ngày 20/10/2026. Người dùng cho triển khai A–E và năm điểm bổ sung trước benchmark bước 3. Đã dùng clean-code, ingestion, backend/frontend và admin frontend design. Giữ source/index/model, không commit/push/deploy, không restart hay inference ngoài.

PDF 42 khối/5 mục; DOCX 233 khối/10 bảng/53 list items/3 note, 517 fields giữ; reader 61.760 bytes; focused172/FE36/Ruff/Biome/build PASS; full 2837 PASS/18 FAIL/17 SKIP, 0 lỗi mới theo ID.

Source metadata, raw notes/ô/locator/hash giữ; parser mới v22/PDF v2/list v1, reader v1. Mục PDF dựa trên nhiều tín hiệu; source unknown/complex note còn cảnh báo. Ba đầu ra có vai trò rõ; reader GET từ verified pair, không thành nguồn index. Source revision cũ không tự sửa.

172 focused +23 subtests; 36 FE; full exit1 và 18 baseline errors đối chiếu ID/cause. Full đầu INTERRUPTED sau turn gián đoạn, không tính hoàn tất. Actual local browser/ASGI/download/AST verified; 375px tab overflow đã sửa, chưa dark-mode đủ. DB/Storage test đã dọn, evidence ignored giữ. 68 RAG files/14 benchmark inputs giữ; không 64-case model benchmark.

[Triển khai](../bao_cao/context571/IMPLEMENTATION_REPORT.md) · [Lệnh, bằng chứng và giới hạn](../bao_cao/context571/VALIDATION_REPORT.md). Muốn nguồn thật nhận parser mới cần revision và quy trình nạp/xuất bản riêng; bước 3 vẫn giữ nguồn cũ để đo riêng RAG.
