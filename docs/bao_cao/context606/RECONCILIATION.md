# Context606 — Đối soát ba coverage dispute và chiều quan hệ

Đối chiếu raw DOCX và canonical602; không sửa nguồn, không replay toàn tài liệu để giải quyết riêng ba mục. Evidence IDs dưới đây thuộc bundle604 lịch sử, không dùng thay ID của binding606.

| Mục | Nguồn/phạm vi đúng | Chủ đề tổng hợp cũ | Khi hỏi trực tiếp | Kết luận |
|---|---|---|---|---|
| `proof_3ce10d6e16bc2e5264872633` | Source1, qnu:p064, ghi chú sau Bảng3 trong phụ lục tuyển sinh vừa làm vừa học2024 | Không mặc định là điều kiện của tổng chính quy | Liên quan khi hỏi ký hiệu X/đăng ký đào tạo của bảng đó | Giữ riêng chế độ và association bảng; không lan sang toàn bộ tổng chỉ tiêu |
| `proof_79fd39c9639cb779bd2dc897` | Source2, qnu:r001, header có năm2025 nhưng bỏ trống ngày/tháng | Chưa chứng minh ngày ban hành đầy đủ | Bắt buộc giữ khi hỏi ngày đầy đủ/nguồn còn thiếu phần nào | Source limitation, null; không đoán ngày/tháng hoặc nói năm cũng trống |
| `proof_d550f8afe81037fe688a61c6` | Source3, qnu:p035, chỉ tiêu tuyển bổ sung2026,456 cho28ngành | Không cộng vào chỉ tiêu tổng5173 | Liên quan khi hỏi đợt bổ sung | Metric/round riêng, không lấy shared year/entity làm điều kiện của mọi tổng |

Hai lượt coverage Qwen của topic tổng hợp cũ đều coi cả ba không liên quan. Không dùng kết quả đó để khẳng định các đoạn luôn vô ích: khi đổi câu hỏi sang nội dung từng đoạn, trước sửa chỉ4/6phân loại đúng, hai lượt bỏ ngày trống sai. Sau hướng dẫn source limitation, kiểm soát cùng ba đoạn/câu hỏi đạt6/6 required_assertion. Đây là hai request phân loại riêng cùng Qwen, không phải hai model độc lập hoặc chứng nhận toàn tài liệu.

Raw DOCX Source1 cho thấy note thuộc phụ lục vừa làm vừa học; canonical vẫn giữ các nhãn cột trong nội dung nhưng header_context chưa được gán đầy đủ. Không sửa parser trong606, không tuyên bố toàn bộ cấu trúc DOCX được tái nghiệm thu.

## Chiều quan hệ

Probe mù không đưa chiều đề xuất cho Qwen. Witness dựng mới5173 → cũ4500 từ căn cứ thay thế; đúng hướng PASS và control đảo ngược bị chặn. Bundle604 giữ nguyên needs_attention, không tự duyệt hoặc sửa lại lịch sử.

Các căn cứ năm/tổng cần giữ: source1 dữ liệu2024 khác ngày văn bản2023; source2 có nhãn dự thảo riêng; source3 ngày cập nhật/version không tự là effective/publication. Các tỷ số hoặc số kế hoạch không tự chứng minh một metric tổng chỉ tiêu mới. Đã kiểm nguyên tắc và các đoạn tranh chấp; compiler ba nguồn chưa hoàn thành nên chưa có bundle606 để nghiệm thu đầy đủ các assertions này.

## Còn chặn

Lượt alias mới bóc tách đúng null/unknown khi persist, nhưng reviewer Qwen trả supported cùng temporal_roles=false và diễn giải sai rằng cả phần năm trống. Gate giữ complete=false. Probe empty draft vẫn nhận item check cho assertion không tồn tại, bị schema chặn sau một correction. Đây là lỗi tuân thủ/kiểm chứng đầu ra, không đủ căn cứ kết luận thiếu context32K hoặc lỗi parser.
