# Phiên 969 — 2026-11-14 — Xử lý ca trọng điểm G3

- Phạm vi gồm Q2, Q24, Q41, Q44, Q53, Q99 và các ca đối chứng. Người dùng yêu cầu bỏ lượt 100 câu.
- Q2 bị chặn trước tra cứu. Backend nay đưa câu gốc của lượt đầu đi tìm trong kho khi model yêu cầu làm rõ tham chiếu. Nhiều tài liệu trong kết quả vẫn yêu cầu chọn nguồn; câu nối tiếp mơ hồ giữ hành vi hỏi làm rõ.
- Q24 có dòng ACCA trong chỉ mục và phạm vi truy xuất. Bộ tạo danh mục từng nhận mã chữ-số xuống dòng làm tên, làm mất dòng đúng khi lọc theo tên. Nhãn đã sửa, ô mã và chỉ tiêu lấy từ nguồn.
- Q41 được cấp mã chọn tên, mở phần tiếp theo của danh mục có bằng chứng, giữ tên theo phiên bản phát hành và gộp mục trùng. Lượt sửa có thể giới hạn vào tên khi danh mục chính chọn được; với bảng chưa chọn được ô, vẫn cho chép nguyên văn tên có dẫn chứng. Q44 ghép hai phần của ô danh sách có liên kết hàng/cột đã được xác minh, sau khi lọc phạm vi. Khi có năm tường minh, cả hai ô phải có bằng chứng năm phù hợp.
- Q53 có cả đoạn mở đầu và đoạn ngày trong ngữ cảnh G3; đoạn nối mang hai dẫn chứng làm rõ ngày đăng ký. Q99 được đính chính giữ cùng trạng thái thiếu căn cứ giữa baseline và G3 gốc. Báo cáo lịch sử ghi 7 ca lệch đã xác định, so baseline lượt đầu 10/100 với G3 8/100 lỗi kiểm tra đầu ra, tách khỏi số liệu thử lại.
- Đợt đo v34: năm câu trọng điểm đều HTTP 200 trên cùng Qwen và chỉ mục. Q2 trả chính quy, Q24 7340301AC và 30 chỉ tiêu, Q41 chọn 15 tên có dẫn chứng sau một lượt sửa, Q44 có đủ năm tổ hợp, Q53 đúng khoảng 20/5–15/6/2026. Q45 đạt. Q73 và Q99 ở đợt v34 còn lỗi đầu ra; đợt xử lý sau ghi Q73 trả đủ bốn ngành của Phụ lục 1 và Q99 giải thích chưa thể dự đoán năm 2026 từ điểm cũ, có dẫn chứng.
- 109 unit trọng điểm và 6 API cô lập đã đạt trước lần rà cuối. Full suite và bộ benchmark 100 câu chưa được nghiệm thu trong phiên này. Bản thử dùng API cổng 8017; cổng 8002 vẫn là tiến trình dev gốc. Không sửa cấu hình model, không lập lại chỉ mục.

## Xác nhận cuối

- Q41 sau chỉnh chỉ dẫn cuối trả đủ 15 ngành có căn cứ, không đưa Quản lý giáo dục vào. Q99 qua một lượt sửa đầu ra và giải thích trực tiếp rằng điểm cao hơn mốc cũ chưa đủ để khẳng định trúng tuyển. Kết quả tạm: qnu_g3_target_v35_ae4ad4ca.json. Đợt trước đó có Q2, Q24, Q41, Q44, Q53, Q73, Q99 cùng HTTP 200 nhưng Q41 thừa một mục và Q99 chưa trả lời thẳng; hai ca này được xác nhận ở lượt cuối.
- 109 unit phạm vi đạt trên mã cuối. 6 API cô lập đạt trước thay đổi chỉ dẫn cuối; DB đã được dọn. Không chạy lại bộ 100 câu và không kết luận G3 PASS. API 8017 là tiến trình kiểm thử tạm.
