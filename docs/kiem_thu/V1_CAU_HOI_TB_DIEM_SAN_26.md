# Câu hỏi kiểm thử — TB điểm sàn 26

Nguồn: [TB điểm sàn 26.pdf](../tai_lieu/tuyen_sinh/TB%20điểm%20sàn%2026.pdf), 8 trang. SHA-256: `236ab3573d6d683a760ed227512022d6c21a03ba5c147c32d4ed7b042f7c6d45`.

Nhãn v1 do agent đọc PDF lập, chưa có người duyệt độc lập. Đáp án chỉ áp dụng snapshot file này, không chứng nhận văn bản là dữ liệu pháp lý đang hiệu lực. Không dùng đáp án hay rubric làm prompt cho model.

Kiểm tự động: trạng thái, số, một số điều kiện bằng pattern, citation đúng version/revision/hash/trang, ID bằng chứng của statement. PASS tự động không thay thế đánh giá toàn bộ ngữ nghĩa; báo cáo ghi semantic_review=NOT_RUN.

| ID | Câu hỏi | Đáp án đối chiếu | Trang |
|---|---|---|---|
| F01 | Theo thông báo ngưỡng đầu vào năm 2026, ngành Quản lý giáo dục xét điểm thi tốt nghiệp THPT cần tối thiểu bao nhiêu điểm? | 15 điểm, cột điểm thi TN THPT, dòng 1. | 1 |
| F02 | Ngưỡng học bạ THPT năm 2026 của ngành Quản lý giáo dục là bao nhiêu? | 18 điểm, dòng 1, cột kết quả học tập THPT. | 1 |
| F03 | Quản lý giáo dục năm 2026 yêu cầu tối thiểu bao nhiêu điểm đánh giá năng lực ĐHQG TP.HCM? | 600 điểm, dòng 1, cột ĐGNL ĐHQG TPHCM. | 1 |
| F04 | Ngành Sư phạm Toán học năm 2026 có ngưỡng điểm thi tốt nghiệp THPT là bao nhiêu? | 20 điểm, dòng 6. | 2 |
| F05 | Điểm sàn theo kết quả thi tốt nghiệp THPT năm 2026 của ngành Giáo dục Thể chất là bao nhiêu? | 19 điểm, dòng 5. | 1 |
| F06 | Ngành Ngôn ngữ Anh năm 2026 xét học bạ cần tối thiểu bao nhiêu điểm? | 19 điểm, dòng 17, cột học tập THPT. | 3 |
| F07 | Ngành Ngôn ngữ Trung Quốc năm 2026 có ngưỡng ĐGNL ĐHQG TP.HCM bao nhiêu? | 650 điểm, dòng 18. | 3 |
| F08 | Ngành Trí tuệ nhân tạo năm 2026 xét điểm thi tốt nghiệp THPT có ngưỡng bao nhiêu? | 16 điểm, dòng 37. | 5 |
| F09 | Ngành Luật năm 2026 có ngưỡng xét học bạ THPT bao nhiêu điểm? | 22 điểm, dòng 32. | 4 |
| F10 | Điểm sàn ĐGNL ĐHQG TP.HCM của ngành Luật năm 2026 là bao nhiêu? | 750 điểm, dòng 32. | 4 |
| F11 | Đối với Giáo dục Mầm non năm 2026, tổng hai môn văn hóa cộng hai phần ba điểm ưu tiên cần đạt ngưỡng bao nhiêu? | Tổng điểm 2 môn văn hóa + 2/3 điểm ưu tiên ≥ 13,34, ghi chú dòng 2. | 1 |
| F12 | Giáo dục Thể chất năm 2026 yêu cầu tổng hai môn văn hóa cộng hai phần ba điểm ưu tiên tối thiểu bao nhiêu? | Tổng điểm 2 môn văn hóa + 2/3 điểm ưu tiên ≥ 12,67, dòng 5 nối trang 1–2. | 1, 2 |
| F13 | Chú ý 1 quy định ngưỡng tổng ba môn thi THPT cho thí sinh tốt nghiệp năm 2026 bao nhiêu, và ngoại lệ là những nhóm ngành nào? | Tối thiểu 15,00/30; áp dụng thí sinh tốt nghiệp 2026, trừ các ngành đào tạo giáo viên và Luật theo ngưỡng Bộ. | 7, 8 |
| F14 | Xét ĐGNL SPHN vào các ngành đào tạo giáo viên năm 2026 (trừ Giáo dục Thể chất), ngoài ngưỡng bảng còn có điều kiện học lực và hai ngưỡng điểm nào? | Mức tốt/giỏi trở lên cả năm lớp 12 (hoặc tương đương), tổng ba môn THPT từ 18,00 hoặc điểm xét tốt nghiệp từ 8,50; xem chú ý 2a. | 8 |
| F15 | Với Giáo dục Thể chất năm 2026 xét theo phương thức không dùng kết quả thi THPT, điều kiện học lực và hai ngưỡng điểm bổ sung ở chú ý 2b là gì? | Mức khá trở lên cả năm lớp 12 (hoặc tương đương), tổng ba môn thi THPT từ 16,50 hoặc điểm xét tốt nghiệp từ 6,50. | 8 |
| F16 | Ký hiệu dấu gạch ngang trong các cột phương thức xét tuyển của thông báo năm 2026 có nghĩa là gì? | Trường không xét tuyển theo phương thức tương ứng đối với ngành này. | 8 |
| F17 | Chỉ dùng thông báo đã tải: điểm trúng tuyển chính thức ngành Luật năm 2026 là bao nhiêu? | Tài liệu chỉ công bố ngưỡng đầu vào, không cung cấp điểm trúng tuyển chính thức. | Ngoài phạm vi nguồn |
| F18 | Chỉ dùng thông báo đã tải: học phí ngành Luật năm học 2026–2027 bao nhiêu đồng? | Không có thông tin học phí trong snapshot PDF này. | Ngoài phạm vi nguồn |
| F19 | Chỉ dùng thông báo đã tải: điểm sàn ngành Luật theo học bạ năm 2025 là bao nhiêu? | Nguồn này là thông báo ngưỡng năm 2026; không có căn cứ năm 2025. | Ngoài phạm vi nguồn |

## Tiêu chí đọc tay bổ sung

- **F01**: Không lấy 18 học bạ hoặc 600 ĐGNL thay cho điểm THPT.
- **F02**: Giữ đúng phương thức học bạ.
- **F03**: Không gộp thang điểm THPT vào thang ĐGNL.
- **F04**: Không biến điểm sàn thành điểm trúng tuyển.
- **F05**: Phân biệt ngưỡng tổng 19 với ngưỡng 12,67 cho hai môn văn hóa và ưu tiên.
- **F06**: Không trả 16 của cột thi THPT hoặc 650 của ĐGNL.
- **F07**: Không nhầm ngành/ngôn ngữ/phương thức.
- **F08**: Không lấy 19 học bạ hay 650 ĐGNL.
- **F09**: Ngưỡng học bạ không thay thế điều kiện bổ sung ở chú ý 3 trang 8.
- **F10**: Không trả 20 hoặc 22 của phương thức khác.
- **F11**: Giữ hệ số 2/3, dấu tối thiểu và đúng phạm vi GDMN; không thay bằng 20 điểm tổng.
- **F12**: Phải nối đúng ghi chú dòng 5 qua trang, không lấy điều kiện GDMN 13,34.
- **F13**: Phải giữ năm tốt nghiệp, thang điểm và cả hai ngoại lệ; không áp dụng đại trà cho giáo viên/Luật.
- **F14**: Giữ quan hệ và/hoặc theo nguyên văn; không thay ngưỡng ngành riêng bằng các điểm này.
- **F15**: Giữ ngoại lệ GDTC, không dùng 18/8,50 hay ngưỡng 19 trong bảng để thay thế.
- **F16**: Không diễn giải dấu gạch thành điểm 0 hoặc điểm chưa công bố.
- **F17**: Không đổi điểm sàn thành điểm chuẩn/điểm trúng tuyển.
- **F18**: Không đoán giá hoặc dùng dữ liệu từ tài liệu khác.
- **F19**: Không trả 22 của năm 2026 cho năm 2025.

Câu hỏi mở để kiểm tra thêm (không thuộc 19 câu tự động): “Đạt điểm sàn ngành Luật có bảo đảm trúng tuyển không? Vì sao?” Cần giải thích rằng đạt ngưỡng chỉ là điều kiện đầu vào; không khẳng định chắc chắn trúng tuyển hoặc tự đặt điểm trúng tuyển.
