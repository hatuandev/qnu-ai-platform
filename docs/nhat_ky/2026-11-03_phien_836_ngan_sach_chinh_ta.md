# Phiên 836 — Ngân sách kiểm tra chính tả

Bỏ mặc định 4096 của tác vụ kiểm tra chính tả ở cả UI và API. Khi không truyền mức cụ thể, ModelOps tính trần đầu ra từ capacity và context còn lại. Giữ nguyên giới hạn vận hành của provider và quota.

Luồng kiểm tra chia đôi nhóm khi lỗi cắt đầu ra hoặc vượt ngân sách đầu vào/context. Các nhóm mới giữ phiên bản, hash và provider, có khóa riêng và dùng chung tối đa hai lượt song song. Nhóm một đoạn còn lỗi được báo lại. Chẩn đoán phân biệt số token đo được và phần vượt ước tính. Không suy ra độ dài đáp án chưa sinh.

Kiểm thử tập trung backend 34 ca đạt. Kiểm tra frontend theo phạm vi và build. Chưa gọi model thật cho thay đổi này.
