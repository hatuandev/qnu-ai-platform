# Kịch bản 12 lượt sau khi nạp chuẩn — chưa chạy

Hiện chỉ bản DOCX thuyết minh2026 đã xuất bản. Năm PDF còn chờ duyệt không phải
căn cứ đang phục vụ. Dùng API chat thật sau khi xác minh backend đã nạp mã hiện tại;
giữ nguyên model/provider/Top K từ DB. Không tự gửi OCR sang cloud, đổi fallback,
restart hay xuất bản PDF để làm bài kiểm tra đạt. Model chat theo cấu hình người dùng;
nếu ngoài hệ thống, tuân quyền gửi đúng dữ liệu/destination đã được xác nhận.

Chạy tuần tự, giữ conversation cho các lượt nối; mỗi lượt một lần. Lỗi provider
ghi ERROR và mã lỗi, không retry làm đẹp. Ghi revision/index snapshot, câu trả lời,
citations/quote/page, diagnostics, thời gian. Oracle đọc bản nguồn đang xuất bản,
không lấy đáp án model làm gold. Không gọi một kết quả tìm kiếm là đáp án đúng.

| ID | Câu hỏi | Điều cần kiểm |
|---|---|---|
| Q01 | Trường Đại học Quy Nhơn áp dụng những phương thức xét tuyển nào trong năm 2026? | Đủ các PT trong nguồn, giữ ngoại lệ và xét tuyển thẳng nếu nguồn phân biệt; không trộn năm |
| Q02 | Sao nhiều phương thức thế? | Cùng cuộc hội thoại Q01; giải thích ngắn đúng ý, không lặp bảng hay tự bịa lý do chính sách |
| Q03 | Trình bày gọn lại giúp tôi. | Nối Q01–Q02; gọn nhưng không bỏ điều kiện quan trọng/citations |
| Q04 | Xét học bạ PT2 lấy kết quả những lớp nào? | Hội thoại mới; đọc đúng phạm vi lớp, không suy từ tên PT |
| Q05 | Ngành đào tạo giáo viên có được xét học bạ PT2 không? | Kiểm phủ định/ngoại lệ, không trả mâu thuẫn Q04 |
| Q06 | Mã trường và địa chỉ được ghi trong tài liệu tuyển sinh 2026 là gì? | Đúng source span, không dùng kiến thức địa giới bên ngoài để tự sửa nguồn |
| Q07 | Tôi nộp lệ phí xét tuyển đến lúc nào? | Phân biệt hạn nộp lệ phí và đăng ký nguyện vọng; hỏi rõ năm/đợt khi chưa có ngữ cảnh |
| Q08 | Năm 2026 trường tuyển bao nhiêu chỉ tiêu, số công bố trước có còn áp dụng không? | Tách mức cũ/mới và văn bản cập nhật; không cộng hai con số |
| Q09 | Quy đổi điểm ĐGNL 780 sang THPT tổ hợp A01 năm 2026 cho tôi. | Chỉ tính bằng rule đang hoạt động và nguồn còn được xuất bản; thiếu căn cứ/tool phải nói rõ, không lấy công thức cũ đã purge |
| Q10 | Cho tôi bảng điểm sàn chính xác của từng ngành năm 2026. | PDF chưa duyệt không được lọt; không biến vài mức mô tả trong DOCX thành bảng đầy đủ |
| Q11 | Liệt kê toàn bộ ngành xét Toán, Lý, Hóa năm 2025. | Không dùng scan2025 chưa duyệt; thiếu nguồn phải nói rõ, không gán dữ liệu2026 cho2025 |
| Q12 | Vậy vì sao bạn chỉ trả lời được ít thế? | Nối Q11; giải thích giới hạn nguồn đang phục vụ tự nhiên, không bịa số tài liệu/khẳng định không có tài liệu trong toàn Repository |

Q09–Q11 có thể là từ chối đúng phạm vi, không tự chấm FAIL chỉ vì không có bảng/số.
Ngược lại câu có căn cứ nhưng bị guard chặn là FAIL, không gọi là correct abstention.
Cuối đợt báo PASS/PARTIAL/FAIL/ERROR từng lượt và tối đa3 nhóm lỗi ưu tiên; không
suy tỷ lệ chất lượng toàn hệ thống từ12câu. Chưa chạy nên chưa có điểm số.
