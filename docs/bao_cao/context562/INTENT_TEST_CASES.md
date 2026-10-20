# Context562 — Corpus và kịch bản hội thoại

Corpus có 116 thông điệp riêng biệt, nhãn đặt trong test data độc lập. Bảng dưới được sinh từ cùng bộ gold đang chạy để đối chiếu; runtime không đọc corpus này. Không coi kết quả rule corpus là độ chính xác AI trên dữ liệu ngoài mẫu.

| ID | Thông điệp | Expected intent | RAG |
|---|---|---|---|
| U001 | Xin chào | SOCIAL | Không |
| U002 | xin chào! | SOCIAL | Không |
| U003 |   Xin   Chào   | SOCIAL | Không |
| U004 | chào bạn | SOCIAL | Không |
| U005 | chao ban | SOCIAL | Không |
| U006 | Xin chào bạn nhé. | SOCIAL | Không |
| U007 | Chào anh | SOCIAL | Không |
| U008 | chào chị ạ | SOCIAL | Không |
| U009 | chào thầy | SOCIAL | Không |
| U010 | chào cô | SOCIAL | Không |
| U011 | Hello | SOCIAL | Không |
| U012 | HELLO! | SOCIAL | Không |
| U013 | hi | SOCIAL | Không |
| U014 | Hi bạn | SOCIAL | Không |
| U015 | hey | SOCIAL | Không |
| U016 | Good morning! | SOCIAL | Không |
| U017 | good afternoon | SOCIAL | Không |
| U018 | Good evening | SOCIAL | Không |
| U019 | chào buổi sáng | SOCIAL | Không |
| U020 | Chào buổi tối | SOCIAL | Không |
| U021 | Cảm ơn | SOCIAL | Không |
| U022 | cam on | SOCIAL | Không |
| U023 | Cảm ơn bạn nhiều nhé | SOCIAL | Không |
| U024 | Xin cảm ơn! | SOCIAL | Không |
| U025 | Cảm ơn rất nhiều | SOCIAL | Không |
| U026 | Cảm ơn anh ạ | SOCIAL | Không |
| U027 | Thank you | SOCIAL | Không |
| U028 | Thanks | SOCIAL | Không |
| U029 | Thanks a lot | SOCIAL | Không |
| U030 | Tạm biệt | SOCIAL | Không |
| U031 | tam biet nhe | SOCIAL | Không |
| U032 | bye | SOCIAL | Không |
| U033 | Bye bye! | SOCIAL | Không |
| U034 | Goodbye | SOCIAL | Không |
| U035 | Hẹn gặp lại | SOCIAL | Không |
| U036 | See you | SOCIAL | Không |
| U037 | xin chào | SOCIAL | Không |
| U038 | Bạn là ai? | ASSISTANT_META | Không |
| U039 | ban la ai | ASSISTANT_META | Không |
| U040 | Bạn tên gì? | ASSISTANT_META | Không |
| U041 | Bạn tên là gì | ASSISTANT_META | Không |
| U042 | Bạn giúp được gì? | ASSISTANT_META | Không |
| U043 | Bạn có thể làm gì? | ASSISTANT_META | Không |
| U044 | Bạn hỗ trợ những gì? | ASSISTANT_META | Không |
| U045 | Who are you? | ASSISTANT_META | Không |
| U046 | What can you do? | ASSISTANT_META | Không |
| U047 | Bạn có thể tư vấn tuyển sinh không? | ASSISTANT_META | Không |
| U048 | Xin chào, bạn là ai? | ASSISTANT_META | Không |
| U049 | Chào bạn, bạn là ai? | ASSISTANT_META | Không |
| U050 | Học phí CNTT năm 2026? | KNOWLEDGE | Có |
| U051 | Điểm chuẩn Sư phạm Toán? | KNOWLEDGE | Có |
| U052 | Điều kiện xét tuyển học bạ là gì? | KNOWLEDGE | Có |
| U053 | Danh sách ngành tuyển sinh? | KNOWLEDGE | Có |
| U054 | Trường nhận hồ sơ từ ngày nào? | KNOWLEDGE | Có |
| U055 | Mã chương trình 00127? | KNOWLEDGE | Có |
| U056 | Học bổng dành cho đối tượng nào? | KNOWLEDGE | Có |
| U057 | Chương trình Alpha học mấy năm? | KNOWLEDGE | Có |
| U058 | Ngành Beta có những môn học nào? | KNOWLEDGE | Có |
| U059 | Điều kiện miễn học phí? | KNOWLEDGE | Có |
| U060 | Tra cứu học phí năm 2025. | KNOWLEDGE | Có |
| U061 | Đối chiếu dữ liệu 2025 và 2026. | KNOWLEDGE | Có |
| U062 | Năm học 2026–2027 có bao nhiêu tín chỉ? | KNOWLEDGE | Có |
| U063 | Học phần bắt buộc của chương trình Gamma? | KNOWLEDGE | Có |
| U064 | Các phương thức tuyển sinh được công bố? | KNOWLEDGE | Có |
| U065 | Trường Đại học Delta có ngành tiếng Nhật không? | KNOWLEDGE | Có |
| U066 | Thời gian nhận hồ sơ hệ sau đại học? | KNOWLEDGE | Có |
| U067 | Đăng ký thi ở địa chỉ nào? | KNOWLEDGE | Có |
| U068 | Số hiệu quyết định mới được công bố? | KNOWLEDGE | Có |
| U069 | Hạn đăng ký ký túc xá? | KNOWLEDGE | Có |
| U070 | Yêu cầu đầu vào ngoại ngữ? | KNOWLEDGE | Có |
| U071 | Học phí có bao gồm lệ phí thi không? | KNOWLEDGE | Có |
| U072 | Môn học mang tên Hello có bao nhiêu tín chỉ? | KNOWLEDGE | Có |
| U073 | Từ “cảm ơn” xuất hiện ở trang nào? | KNOWLEDGE | Có |
| U074 | Hiến pháp quy định thế nào về giáo dục? | KNOWLEDGE | Có |
| U075 | Danh sách tổ hợp xét tuyển của mã 0123456? | KNOWLEDGE | Có |
| U076 | Mức phí áp dụng cho nhóm B, không áp dụng cho nhóm A? | KNOWLEDGE | Có |
| U077 | Phạm vi của phụ lục IV? | KNOWLEDGE | Có |
| U078 | Điều kiện chuyển ngành được quy định ở đâu? | KNOWLEDGE | Có |
| U079 | So sánh chương trình Alpha và Beta năm 2026. | KNOWLEDGE | Có |
| U080 | Chương trình chất lượng cao yêu cầu những gì? | KNOWLEDGE | Có |
| U081 | Có bao nhiêu phương thức tuyển sinh năm 2027? | KNOWLEDGE | Có |
| U082 | Xin chào, học phí CNTT năm 2026 bao nhiêu? | MIXED | Có |
| U083 | Cảm ơn, cho tôi hỏi điểm chuẩn năm 2026. | MIXED | Có |
| U084 | Hi, cho mình biết phương thức xét tuyển. | MIXED | Có |
| U085 | Hello, trường có bao nhiêu ngành? | MIXED | Có |
| U086 | Chào bạn, cho tôi danh sách ngành tuyển sinh. | MIXED | Có |
| U087 | Cam on, hoc phi CNTT 2026? | MIXED | Có |
| U088 | Xin chào! Tôi muốn tra cứu mã ngành 00123. | MIXED | Có |
| U089 | Cảm ơn anh, ngành Alpha học mấy năm? | MIXED | Có |
| U090 | Chào chị, điều kiện miễn học phí là gì? | MIXED | Có |
| U091 | Thanks, what are the admission requirements? | MIXED | Có |
| U092 | Thank you, học phí ngành Beta bao nhiêu? | MIXED | Có |
| U093 | Chào cô, trường có học bổng không? | MIXED | Có |
| U094 | Tạm biệt, nhưng cho tôi hỏi hạn nộp hồ sơ. | MIXED | Có |
| U095 | Hi, năm học 2026–2027 có mấy học kỳ? | MIXED | Có |
| U096 | Chào buổi sáng, các môn bắt buộc là gì? | MIXED | Có |
| U097 | Xin chào, không tính nhóm A thì có bao nhiêu? | MIXED | Có |
| U098 | Chào bạn, ngành X và ngành Y khác nhau thế nào? | MIXED | Có |
| U099 | Cảm ơn nhé, giúp tôi so sánh hai phương thức. | MIXED | Có |
| U100 | Xin chào, thông tin liên hệ trong tài liệu là gì? | MIXED | Có |
| U101 | Hello, chương trình 00007 có yêu cầu gì? | MIXED | Có |
| U102 | Tư vấn giúp tôi | CLARIFICATION | Không |
| U103 | tư vấn giúp mình | CLARIFICATION | Không |
| U104 | Ngành nào tốt? | CLARIFICATION | Không |
| U105 | giúp tôi | CLARIFICATION | Không |
| U106 | help | CLARIFICATION | Không |
| U107 | Help me | CLARIFICATION | Không |
| U108 | Còn môn tự chọn? | CLARIFICATION | Không |
| U109 | Ngành đó học mấy năm? | CLARIFICATION | Không |
| U110 | Còn năm 2025? | CLARIFICATION | Không |
| U111 | Cảm ơn, còn học phí? | CLARIFICATION | Không |
| U112 | Có | CLARIFICATION | Không |
| U113 | Không | CLARIFICATION | Không |
| U114 | Ok | CLARIFICATION | Không |
| U115 | Không, tôi hỏi năm 2026 | CLARIFICATION | Không |
| U116 | Cho tôi danh sách môn học gì đó | CLARIFICATION | Không |

## 20 kịch bản nhiều lượt

Structured model output của nhóm gold được stub để kiểm validator, số lần gọi và query downstream; không phải 20 lượt provider thật. Lịch sử assistant trong test có khẳng định sai cố ý để chứng minh không thành dữ kiện nguồn.

| Test ID suffix | Hiện tại | Expected standalone |
|---|---|---|
| `knowledge_thanks_followup` | Còn môn tự chọn? | Môn tự chọn ngành Alpha năm 2026? |
| `knowledge_greeting_followup` | Ngành đó học mấy năm? | Thời gian học ngành Alpha năm 2026? |
| `switch_program` | Còn môn tự chọn? | Môn tự chọn ngành Beta năm 2026? |
| `switch_year` | Còn năm 2026? | Học phí ngành Alpha năm 2026? |
| `academic_not_calendar` | Còn học phí? | Học phí ngành Alpha năm học 2026-2027? |
| `leading_zero_code` | Còn môn tự chọn? | Môn tự chọn mã 00123 năm 2026? |
| `institution` | Còn môn tự chọn? | Môn tự chọn ngành Alpha trường Zeta năm 2026? |
| `assistant_prose_not_truth` | Còn học phí? | Học phí ngành Alpha năm 2026? |
| `user_correction` | Không, tôi hỏi năm 2026 | Học phí ngành Alpha năm 2026? |
| `mixed_thanks` | Cảm ơn, còn môn tự chọn? | Môn tự chọn ngành Alpha năm 2026? |
| `mixed_hello` | Xin chào, còn học phí? | Học phí ngành Alpha năm 2026? |
| `repeated_social` | Còn môn tự chọn? | Môn tự chọn ngành Alpha năm 2026? |
| `topic_change_same_subject` | Ngành đó học mấy năm? | Thời gian đào tạo ngành Alpha năm 2026? |
| `negation_preserved` | Còn học phí, không tính nhóm A? | Học phí ngành Alpha năm 2026, không tính nhóm A? |
| `condition_preserved` | Còn học phí nếu thuộc nhóm B? | Học phí ngành Alpha năm 2026 nếu thuộc nhóm B? |
| `explicit_current_program` | Còn ngành Beta? | Học phí ngành Beta năm 2026? |
| `unknown_year_stays_unknown` | Còn môn tự chọn? | Môn tự chọn ngành Alpha? |
| `english_followup` | What about duration? | Duration for program Omega in 2026? |
| `earlier_year_override` | Còn năm 2025? | Học phí ngành Alpha năm 2025? |
| `correction_then_social_then_followup` | Còn môn tự chọn? | Môn tự chọn ngành Alpha năm 2026? |

## Negative cases và tích hợp

- Mock timeout, schema hỏng, số/mã mới không có căn cứ, sai năm, mất năm học/phủ định, lấy ngành cũ sau khi đổi ngành: làm rõ hoặc từ chối rewrite.
- Hai mươi request đồng thời tách context; history DB đúng trợ lý/cấu hình; nhiều social không đẩy mất chủ đề; DB lỗi phải trả lỗi.
- JSON/SSE, quyền debug, capability sai phiên/sai trợ lý, ID đoán được, token không thành access token, phiên đã xóa, không nhận client-chosen ID chung.
- Frontend: URL mặc định không debug, encode path; restore đúng session A/B, lịch sử cũ/cross-assistant không mượn session.
- Ba probe Qwen thật: cảm ơn→môn tự chọn, đổi năm 2026→2025, hai ngành→tham chiếu mơ hồ. Kết quả và giới hạn ở VALIDATION_REPORT.
