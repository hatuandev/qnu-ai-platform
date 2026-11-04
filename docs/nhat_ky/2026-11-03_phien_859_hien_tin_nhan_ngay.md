# Phiên 859 — Hiện tin nhắn ngay khi gửi

Khung chat trước đây chỉ dựng tin nhắn từ lịch sử máy chủ, nên tin người dùng xuất hiện cùng câu trả lời. Giao diện giờ dựng tin tạm từ yêu cầu đang gửi, thông báo đang chờ và thay bằng kết quả API. Lịch sử từ máy chủ được ưu tiên khi có cùng lượt. Bộ đếm chi tiết lấy số lượt đã xác nhận để chuẩn bị yêu cầu kế tiếp.

Test lịch sử dùng phản hồi trì hoãn có kiểm soát để xác nhận tin tạm có mặt trước phản hồi và chỉ hiện một lượt sau khi đồng bộ. Vitest trọng tâm đạt 16/16, Biome và `npm run build` đạt. Chưa chạy trình duyệt live.
