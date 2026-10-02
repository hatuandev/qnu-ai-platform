# Báo cáo kiểm thử chatbot tuyển sinh bằng 20 câu hỏi

- **Ngày kiểm thử:** 02/10/2026 (UTC+7)
- **Trợ lý:** `admissions` — Mô-đun trợ lý ảo tư vấn tuyển sinh
- **Kho tri thức:** `col_admissions`
- **Dữ liệu nguồn:** 7 PDF trong `docs/tai_lieu/tuyen_sinh/dai_hoc_chinh_quy`
- **Tình trạng dữ liệu:** 7/7 tài liệu `ready/indexed`, 132 chunks, 1.332 facts
- **Cách chạy:** gọi API chat thật, mỗi câu dùng một hội thoại mới, `stream=false`

## 1. Kết quả tổng hợp

| Chỉ số | Kết quả |
| --- | ---: |
| Tổng số câu | 20 |
| Đạt hoàn toàn | 14 (70%) |
| Đạt một phần | 3 (15%) |
| Không đạt | 3 (15%) |
| Điểm quy đổi (Đạt = 1; Một phần = 0,5) | **15,5/20 — 77,5%** |
| HTTP thành công | 20/20 |
| Có ít nhất một citation | 20/20 |
| Độ trễ trung bình | 5,685 giây |
| Trung vị | 5,489 giây |
| P95 | 7,628 giây |
| Nhanh nhất / chậm nhất | 3,872 / 7,817 giây |

**Đánh giá:** chatbot đã trả lời tốt các câu tra cứu trực tiếp và câu yêu cầu đối chiếu số liệu rõ ràng. Chất lượng chưa đạt mức sẵn sàng phát hành cao vì ba lỗi dữ liệu quan trọng và một số citation dư thừa. Điểm thực nghiệm 77,5% thấp hơn mục tiêu Answer Relevance 0,85 của dự án.

## 2. Kết quả từng câu

| ID | Câu hỏi rút gọn | Đáp án chuẩn | Kết quả | Nhận xét |
| --- | --- | --- | :---: | --- |
| Q01 | Mã tuyển sinh của trường | DQN | Đạt | Trả lời đúng, ngắn gọn. |
| Q02 | Địa chỉ và hotline | 170 An Dương Vương…; 1800.55.88.49 | Đạt | Đúng và có thêm website chính thức. |
| Q03 | Điều kiện dự tuyển | Tốt nghiệp THPT hoặc tương đương | Đạt | Đúng; phần diễn giải thêm không làm đổi nghĩa. |
| Q04 | Các phương thức và mã | 100, 200, 402A, 402B, 405; xét tuyển thẳng | Đạt | Liệt kê đúng, đủ. |
| Q05 | Ngành giáo viên có dùng PT2/PT3? | Không dùng cả PT2 và PT3 | Đạt | Đúng và diễn giải rõ. |
| Q06 | PT5 mã 405 áp dụng thế nào? | Thi THPT + năng khiếu QNU; GDMN/GDTC | **Không đạt** | Trả lời sai rằng PT5 áp dụng cho nhiều ngành sư phạm, còn ghi nhầm năm 2024. |
| Q07 | Tổng chỉ tiêu dự kiến | 4.800 | Đạt | Đúng; câu trả lời dài hơn cần thiết. |
| Q08 | IELTS 6.5 quy đổi và dùng ở đâu | 9,5; PT1 và PT2 | Một phần | Đúng 9,5 nhưng diễn đạt mơ hồ về PT1/PT2 dù nguồn có thông tin rõ. |
| Q09 | Lịch đăng ký và thi năng khiếu | ĐK 20/5–15/6; thi 19–21/6/2026 | **Không đạt** | Trả lời chung chung “tháng 4–5” và “tháng 5–6”, sai mốc cụ thể. |
| Q10 | Chiều cao/cân nặng GDTC | Nam 1,65 m/45 kg; nữ 1,55 m/40 kg | Đạt | Đúng đầy đủ các số liệu được hỏi. |
| Q11 | Học phí toàn khóa | Cử nhân 83–97 triệu; kỹ sư 112,3 triệu | Đạt | Đúng cả mức tiền và thời gian khóa học. |
| Q12 | Ưu tiên giải nhất HSGQG | +3 điểm; không quá 3 năm | Đạt | Đúng, súc tích. |
| Q13 | Xử lý thí sinh bằng điểm | Điểm cộng thấp hơn, rồi nguyện vọng cao hơn | Một phần | Kết luận đúng nhưng tự tạo bảng điểm 2024/2025 không liên quan, làm giảm groundedness. |
| Q14 | 7 tổ hợp gốc | A00, A01, B00, C00, C01, D01, D07 | Đạt | Đúng, đủ. |
| Q15 | Thuật toán quy đổi và làm tròn | Nội suy tuyến tính; làm tròn cuối cùng 2 số | Đạt | Đúng cả công thức và quy tắc làm tròn. |
| Q16 | Chỉ tiêu AI/KTPM/CNTT 2026 | 53 / 60 / 182 | **Không đạt** | Trả 20 / 41 / 222; nhầm dữ liệu điều kiện/năng lực với chỉ tiêu đăng ký. |
| Q17 | Điểm chuẩn quy đổi AI/KTPM/CNTT | 17,50 / 16,00 / 18,20 | Đạt | Đúng cả ba ngành. |
| Q18 | Quyết định mở ngành AI | 1203/QĐ-ĐHQN, 17/05/2022, từ 2022 | Đạt | Đúng hoàn toàn. |
| Q19 | Thực hiện chỉ tiêu AI năm 2025 | 55 / 50 / 90,9% | Đạt | Đúng hoàn toàn. |
| Q20 | Phí ký túc xá chưa có trong nguồn | Không bịa; hướng dẫn kênh chính thức | Một phần | Không bịa số tiền, nhưng chưa cung cấp hotline/email/phòng ban để người dùng hỏi tiếp. |

## 3. Nhận xét theo năng lực

### Điểm tốt

1. Các câu tra cứu định danh, điều kiện, học phí, điểm chuẩn và số liệu năm 2025 có độ chính xác tốt.
2. Câu quy đổi điểm nêu đúng thuật toán nội suy tuyến tính, công thức và quy tắc làm tròn.
3. Câu không có dữ liệu không bịa mức phí ký túc xá.
4. 20/20 phản hồi có HTTP 200 và thời gian đều dưới 8 giây trong lần chạy sạch.

### Vấn đề cần ưu tiên

1. **P0 — Semantic cache lưu phản hồi suy giảm:** khi tất cả provider mất kết nối, hệ thống tạo câu trả lời bằng cách ghép context thô rồi lưu vào semantic cache. Khi provider hoạt động trở lại, cache tiếp tục phát các câu trả lời kém chất lượng. Lần kiểm thử sạch chỉ hợp lệ sau khi xóa 25 cache của `col_admissions`.
2. **P0 — Sai số liệu do trộn loại báo cáo:** Q16 lấy số liệu từ báo cáo điều kiện/năng lực thay cho bảng đăng ký chỉ tiêu. Retrieval cần ưu tiên loại tài liệu theo ý định và năm dữ liệu.
3. **P0 — Sai phạm vi PT5 và lịch năng khiếu:** Q06 và Q09 cho thấy reranker/fact layer chưa giữ đúng câu và thuộc tính cần trả lời.
4. **P1 — Citation quá rộng:** nhiều câu có 5–8 citation, gồm tài liệu không trực tiếp chứng minh đáp án. Nên giới hạn 1–3 nguồn mạnh nhất và đối soát claim–citation.
5. **P1 — Trả lời dư dữ liệu:** Q07 và một số câu đơn giản kèm bảng dài. Cần AnswerFormatPlanner chọn câu trả lời ngắn cho truy vấn một dữ kiện.
6. **P1 — No-Answer chưa điều hướng:** Q20 an toàn về số liệu nhưng cần hướng người dùng tới hotline tuyển sinh `1800.55.88.49` hoặc website chính thức thay vì hứa “sẽ cập nhật”.

## 4. Quan sát ModelOps và xoay khóa

- Trong quá trình chạy, khóa Gemini hiện có nhận HTTP 429 và được chuyển sang trạng thái `rate_limited`; log xác nhận runtime bỏ qua khóa đó và tiếp tục sang fallback provider.
- Luồng chatbot không bị gián đoạn: bộ chạy sạch vẫn hoàn thành 20/20 request sau khi circuit breaker được khởi động lại.
- Provider Gemini hiện chỉ có một khóa khả dụng tại thời điểm kiểm thử, nên kịch bản thật **Key 1 → Key 2 → Key 3** chưa thể đo bằng bộ câu hỏi này. Muốn xác nhận đúng chuỗi xoay khóa production cần cấu hình tối thiểu ba khóa hợp lệ cho cùng provider và chạy kịch bản ép 429 có kiểm soát.
- Primary và fallback của trợ lý đều thuộc Google Gemini. Nếu pool Gemini hết khóa, khả năng tiếp tục phụ thuộc fallback provider toàn cục; nên cấu hình fallback model thuộc provider khác để tránh cùng điểm lỗi.

## 5. Đề xuất tiêu chí chạy lại

Chạy lại đúng 20 câu sau khi xử lý P0 và chỉ chấp nhận phát hành khi:

- Đạt hoàn toàn ít nhất 18/20 câu.
- Không còn câu sai số liệu hoặc sai ngày.
- No-Answer có kênh liên hệ chính thức.
- Mỗi câu tối đa 3 citation trực tiếp.
- Phản hồi suy giảm do provider lỗi không được ghi vào semantic cache.
- Cấu hình ba khóa Gemini và xác nhận lịch sử sự kiện thể hiện Key 1 (429) → Key 2 (429) → Key 3 (success).

