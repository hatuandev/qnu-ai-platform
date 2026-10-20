# Phiên 561 — Dọn toàn kho tuyển sinh, nạp lại DOCX đến xuất bản

Người dùng duyệt dọn toàn `col_admissions`, tải lại đúng DOCX phức tạp và test đến xuất bản. Chỉ Knowledge dẫn xuất được xóa; Repository, bytes nguồn và các collection khác giữ nguyên.

Bảy purge job completed; 318 vector cũ về 0; 15 revisions cũ bị xóa, 22 tombstone lịch sử vẫn không phục vụ. Dọn thêm 33 sidecar không tham chiếu, 22390544 bytes, không bypass Storage.

Nguồn mới `bnd_fa71a57c9cf1`, revision `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`. 233 khối / 10 bảng / 368 facts; 262 chunks và 262 điểm retrievable sau HTTP publish 200. Xác nhận Hình 1 tái sử dụng đúng source/image hash. Không áp semantic proposal chưa được duyệt. Native unknown/footnote page unknown giữ nguyên.

Sửa identity theo provenance cuối ở nguồn mới; không bỏ parity field. Full đầu phát hiện 3 regression header/association: giữ diagnostic literal_only và match nguồn duy nhất trước role; bump extraction v21. Không sửa nguồn đã publish; kiểm tra lại bằng guard mới đạt.

Focused identity 50 PASS; focused sau sửa 87 PASS; Ruff PASS. Full cuối 2494 PASS / 18 FAIL / 17 SKIP +23 subtests; exit 1. 18 lỗi nền khớp từng ID và nguyên nhân với Context558, không regression mới. Full vẫn FAIL. Không chạy frontend/browser E2E/chat LLM; import/reparse là official inline worker, vector qua broker thật.

Không commit/push/deploy/restart phiên 561. DB test dọn theo nonce sau các lượt chạy. Runtime test không xóa được: kiểm duyệt tự động `blocked by policy`; không bypass. Lượt full Context560 bị ngắt không được tính PASS. [Báo cáo và kiểm thử](../bao_cao/context561/REPORT.md), [từng test ID](../bao_cao/context561/REGRESSION_IDS.md). Evidence riêng: `backend/storage/context561/`.
