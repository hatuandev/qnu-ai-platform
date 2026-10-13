# Phiên417 — Đối soát câu hỏi độc lập

Đã thử 8/8 lượt cho 4 câu qua dag, rag; nhận 8 phản hồi HTTP (kể cả lỗi). Lỗi kết nối không phải đáp án sai.

Đáp án tham chiếu chỉ để chấm, không đưa vào prompt/evidence. Status supported/answered không tự chứng minh đáp án đúng. Không công bố Ragas từ bảng này.

Runtime: {'answered': 5, 'failed': 1, 'insufficient_context': 2}. Quyết định: {'supported': 5, 'none': 1, 'missing': 2}.

Kiểm tra digest/revision/quote/numeric: 5/5 quyết định supported/partial đạt contract; chưa thay thế kiểm chứng ngữ nghĩa.

Config/publication/code không đổi: True/True/True.

## Câu 1: Trường Đại học Quy Nhơn có mã trường là gì?

Tham chiếu: Mã cơ sở đào tạo của Trường Đại học Quy Nhơn trong tuyển sinh là DQN.

Thực tế: Đối chiếu năm 2026:

Mã cơ sở đào tạo trong tuyển sinh của Trường Đại học Quy Nhơn: DQN (năm 2026).

Status: answered; decision: supported; reason: VERIFIED_CLAIM_COVERAGE; error: None; thời gian: 24.08s.

Nguồn: Thông tin TSĐH cập nhật, trang 1, ks_rev_6280c8de7f46

Mô hình thực: custom/gpt-6-luna (fallback=False)

## Câu 1: Trường Đại học Quy Nhơn có mã trường là gì?

Tham chiếu: Mã cơ sở đào tạo của Trường Đại học Quy Nhơn trong tuyển sinh là DQN.

Thực tế: Đối chiếu năm 2026:

Mã cơ sở đào tạo trong tuyển sinh của Trường Đại học Quy Nhơn là DQN.

Status: answered; decision: supported; reason: VERIFIED_CLAIM_COVERAGE; error: None; thời gian: 13.39s.

Nguồn: Thông tin TSĐH cập nhật, trang 1, ks_rev_6280c8de7f46

Mô hình thực: custom/gpt-6-luna (fallback=False)

## Câu 5: Năm 2026 Trường Đại học Quy Nhơn tuyển bao nhiêu chỉ tiêu?

Tham chiếu: Tổng số lượng tuyển sinh đại học chính quy là 5.173.

Thực tế: Đối chiếu năm 2026:

Năm 2026, Trường Đại học Quy Nhơn tuyển 5.173 chỉ tiêu.

Status: answered; decision: supported; reason: VERIFIED_CLAIM_COVERAGE; error: None; thời gian: 15.06s.

Nguồn: Thông tin TSĐH cập nhật, trang 1, ks_rev_6280c8de7f46; Thông tin TSĐH cập nhật, trang 2, ks_rev_6280c8de7f46

Mô hình thực: custom/gpt-6-luna (fallback=False)

## Câu 5: Năm 2026 Trường Đại học Quy Nhơn tuyển bao nhiêu chỉ tiêu?

Tham chiếu: Tổng số lượng tuyển sinh đại học chính quy là 5.173.

Thực tế: Đối chiếu năm 2026:

Năm 2026, Trường Đại học Quy Nhơn tuyển 5.173 chỉ tiêu.

Status: answered; decision: supported; reason: VERIFIED_CLAIM_COVERAGE; error: None; thời gian: 20.72s.

Nguồn: Thông tin TSĐH cập nhật, trang 1, ks_rev_6280c8de7f46; Thông tin TSĐH cập nhật, trang 2, ks_rev_6280c8de7f46

Mô hình thực: custom/gpt-6-luna (fallback=False)

## Câu 13: Ngành sư phạm có xét ĐGNL Trường ĐHSP Hà Nội không?

Tham chiếu: Có, các ngành đào tạo giáo viên phù hợp có thể xét PT4; riêng Giáo dục Mầm non và Giáo dục Thể chất sử dụng phương thức có năng khiếu theo thông báo của Trường.

Thực tế: Hệ thống chưa thể hoàn tất yêu cầu do lỗi trong quy trình xử lý. Node 'knowledge_answer' thực thi không thành công: Đối soát chứng cứ vượt thời gian xử lý.

- **Mã xử lý:** `da3530de-1443-4618-b72b-9ce01419eca7`

Vui lòng kiểm tra lịch sử thực thi hoặc thử lại sau khi cấu hình được cập nhật.

Status: failed; decision: None; reason: None; error: EVIDENCE_TIMEOUT; thời gian: 94.64s.

Nguồn: 

Mô hình thực: custom/gpt-6-luna (fallback=False)

## Câu 13: Ngành sư phạm có xét ĐGNL Trường ĐHSP Hà Nội không?

Tham chiếu: Có, các ngành đào tạo giáo viên phù hợp có thể xét PT4; riêng Giáo dục Mầm non và Giáo dục Thể chất sử dụng phương thức có năng khiếu theo thông báo của Trường.

Thực tế: Đối chiếu năm 2026:

Chưa đủ căn cứ cho: Xác nhận PT4 (402B) có áp dụng cho ngành sư phạm/ngành đào tạo giáo viên hay không.

Trong nguồn đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho phần thông tin bạn hỏi. Bạn có thể liên hệ tư vấn tuyển sinh QNU qua 1800.55.88.49 để được xác nhận.

Status: insufficient_context; decision: missing; reason: PARTIAL_OR_MISSING_COVERAGE; error: None; thời gian: 32.88s.

Nguồn: 

Mô hình thực: custom/gpt-6-luna (fallback=False)

## Câu 42: Điểm sàn Giáo dục Mầm non năm 2026 là bao nhiêu?

Tham chiếu: Theo Thông báo 121/TB-HĐTS ngày 09/07/2026, ngưỡng theo phương thức điểm thi THPT của Giáo dục Mầm non là 20 điểm; đồng thời tổng điểm 2 môn văn hóa cộng 2/3 điểm ưu tiên phải đạt ít nhất 13,34.

Thực tế: Đối chiếu năm 2026:

Ngưỡng đầu vào ngành Giáo dục Mầm non năm 2026 tại Trường Đại học Quy Nhơn: 20 điểm theo phương thức thi TN. THPT và 20 điểm theo phương thức thi ĐGNL ĐHSP HN.

Status: answered; decision: supported; reason: VERIFIED_CLAIM_COVERAGE; error: None; thời gian: 28.97s.

Nguồn: TB điểm sàn 26, trang 1, ks_rev_cf1863148443

Mô hình thực: custom/gpt-6-luna (fallback=False)

## Câu 42: Điểm sàn Giáo dục Mầm non năm 2026 là bao nhiêu?

Tham chiếu: Theo Thông báo 121/TB-HĐTS ngày 09/07/2026, ngưỡng theo phương thức điểm thi THPT của Giáo dục Mầm non là 20 điểm; đồng thời tổng điểm 2 môn văn hóa cộng 2/3 điểm ưu tiên phải đạt ít nhất 13,34.

Thực tế: Đối chiếu năm 2026:

Chưa đủ căn cứ cho: Mức điểm sàn ngành Giáo dục Mầm non năm 2026 chưa có trong bằng chứng được cung cấp.

Trong nguồn đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho phần thông tin bạn hỏi. Bạn có thể liên hệ tư vấn tuyển sinh QNU qua 1800.55.88.49 để được xác nhận.

Status: insufficient_context; decision: missing; reason: EVIDENCE_NOT_SUPPORTED; error: None; thời gian: 9.05s.

Nguồn: 

Mô hình thực: custom/gpt-6-luna (fallback=False)
