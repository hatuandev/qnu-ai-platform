# Phiên638 — Review kho tri thức backendV1

Đọc prompt, mã, test và báo cáo637; rà độc lập phạm vi collection/source/revision/storage/migration. Không sửa mã ứng dụng hoặc test suite chính.

Suite hiện có104PASS/31,24s/exit0, Ruff PASS. Ba probe độc lập trong storage/context638 đều FAIL đúng lỗi: writer local đồng thời thất bại có thể cắt file đã commit (P1), idempotency bỏ title (P2), downgrade0005 rỗng khiến upgrade sau bị chặn (P2). Chưa nghiệm thu batch để nối OCR.

Hai database review dọn đúng ownership; sentinel legacy giữ. Không xóa database test khác đang tồn tại.141file app/migration hash khớp; không migrate DB phục vụ/restart/commit/push. Lưu probe/log/receipt Git ignored; file tổng hợp, không corpus hoặc key.

[Phát hiện, vị trí, cách tái hiện và hướng sửa](../bao_cao/context638/REVIEW.md). Bước tiếp theo: sửa F1–F3, chuyển probe thành regression chính và chạy gate phù hợp.
