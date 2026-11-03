# Phiên 837 — Rà soát phục hồi lỗi token

Hai màn hình OCR dùng chung bộ chia nhóm. Tắt retry ở mutation kiểm tra chính tả để chỉ bộ chia nhóm quyết định gửi thêm yêu cầu. Báo cáo lưu số nhóm đã chia và thông tin chẩn đoán an toàn trong JSON, kể cả khi các phần con đều hoàn tất.

AGENTS.md ghi nguyên tắc ngân sách từ ModelOps, chia theo cấu trúc, giữ phần đã hoàn tất, dừng ở đơn vị nhỏ nhất, phân biệt token đo được và ước tính. Không sửa compiler hay thay cấu hình model.

Vitest OCR tập trung đạt 36 ca, bao gồm lỗi token đến đơn vị nhỏ nhất. Chưa gọi model thật.
