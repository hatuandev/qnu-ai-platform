# Kiểm thử 20 câu đầu RAG/DAG — GPT-OSS, không quota nội bộ

## Kết luận

Đã gửi đủ 20 câu trên cả DAG và RAG trực tiếp, tổng 40 lượt, với cấu hình primary `ollama/gpt-oss:120b`, fallback `ollama/gemma4:31b`. **Không còn QUOTA_EXCEEDED. Chưa nghiệm thu chất lượng RAG/DAG.** Có đáp án liệt kê thiếu dù runtime đánh dấu supported, có no-answer bỏ sót dữ kiện và khác biệt giữa hai route.

- Lượt mới độc lập: 00:01:48–00:12:52 ngày 14/10/2026, UTC+7.
- [JSON đầy đủ: câu hỏi, tham chiếu, câu trả lời, citations, traces, usage](../../backend/storage/admissions_eval428_first20.json).
- [Nhật ký triển khai bỏ quota](../nhat_ky/2026-10-14_phien_428_bo_quota_noi_bo_va_test_20_cau.md).
- Câu hỏi gốc và thứ tự giữ nguyên. Expected answers không gửi vào request hoặc nạp vào evidence. Không gộp với lượt 427 bị quota.

## Số liệu vận hành (không phải accuracy)

| Chỉ số | DAG | RAG trực tiếp |
| --- | --- | --- |
| Lượt gửi | 20 | 20 |
| answered | 10 | 8 |
| insufficient_context | 10 | 11 |
| Lỗi kiểm chứng ưu tiên nguồn | 0 | 1 (HTTP502, câu 1) |
| Trung vị thời gian | 16,48 giây | 13,28 giây |
| Thời gian cao nhất | 34,78 giây | 32,16 giây |
| Lỗi quota nội bộ | 0 | 0 |

120 inference usage logs, 1.130.701 prompt+completion tokens, tất cả served model `gpt-oss:120b`, provider custom, fallback=false. **Gemma chưa được kiểm chứng trong batch này**, không ép primary lỗi để thử fallback ngoài yêu cầu. Con số model calls lấy từ logs có conversation_id của lượt test, không tự coi là toàn bộ traffic/usage của đơn vị.

23/23 quyết định supported/partial đạt kiểm tra digest, identity revision, quote, numeric và entity binding. Kiểm tra này không chứng minh completeness hoặc entailment ngữ nghĩa; câu 9 là phản ví dụ. Chưa chạy Ragas, không công bố tỷ lệ accuracy từ runtime statuses.

Assistant config, publication fingerprint và fingerprint các file evidence/workflow mà harness theo dõi không thay đổi giữa lượt. Kho giữ 19 bindings/epoch3/generation `vg_21324678abcf`, nguồn TB1906 ưu tiên cùng ngữ cảnh như người dùng đã chọn; không reset/publish/reembed hoặc sửa runtime trong lượt.

## Đối soát từng câu

“Đúng trọng tâm” dưới đây là đối soát thủ công câu trả lời với câu hỏi/tham chiếu và quotes có trong report, không phải full independent document audit cho mọi điều kiện.

| Câu | DAG | RAG trực tiếp | Nhận xét |
| --- | --- | --- | --- |
| 1. Mã trường | missing / INVALID_OR_EMPTY_CLAIMS | HTTP502 EVIDENCE_PRECEDENCE_INVALID | Nguồn cập nhật có dòng DQN; chưa trả được. |
| 2. Địa chỉ | supported, 170 An Dương Vương, P. Quy Nhơn Nam, Gia Lai | supported, cùng địa chỉ | Đúng trọng tâm, đúng quote trang 1 nguồn cập nhật. |
| 3. Hotline | supported, 1800.55.88.49 | partial, cùng số rồi thêm no-answer | Nội dung chính đúng; RAG phủ định khả năng trả lời sau khi đã trả lời. |
| 4. Website | partial, tuyensinh.qnu.edu.vn | missing | Chưa phủ đủ câu hỏi; nguồn có thông tin website, cần kiểm tra chọn/bind quote. |
| 5. Chỉ tiêu 2026 | supported, 5.173 | missing | DAG đúng số tham chiếu; không ổn định giữa hai route. |
| 6. Số ngành/chương trình | partial, liệt kê vài ngành nhưng thiếu tổng | missing | Chưa trả tổng số; cần phân biệt ngành/chương trình/mã xét tuyển và hiệu lực nguồn, không đếm vài row top-k thành toàn kho. |
| 7. Đối tượng dự tuyển | supported, tốt nghiệp THPT/tương đương | supported, cùng nội dung | Đúng điều kiện cơ bản; chưa nhắc điều kiện riêng của ngành/phương thức. |
| 8. Tuyển thẳng | supported, có | supported, có, mã 301 | Đúng trọng tâm và có quote chính sách. |
| 9. Các phương thức 2026 | supported nhưng nói chỉ có 4 (PT1–PT4) | supported nhưng nói chỉ có 4 | **Sai/thiếu nghiêm trọng:** bỏ PT5/mã405, không nhắc tuyển thẳng; nguồn xuất bản có cả PT5 và mã301. |
| 10. Nhiều phương thức cùng ngành | missing | supported nhưng chỉ nói một chương trình có thể có nhiều phương thức | Chưa trả quyền/điều kiện đăng ký của thí sinh; related evidence không tương đương direct answer. |
| 11. Ngành không xét học bạ | supported, ngành đào tạo giáo viên không xét PT2 | supported, cùng nội dung | Đúng trọng tâm, quote phủ định chính sách trực tiếp. |
| 12. Sư phạm xét ĐGNL TP.HCM | supported, không xét PT3 | partial, không xét PT3 rồi no-answer | Nội dung chính đúng; RAG đánh giá completeness/presentation chưa nhất quán. |
| 13. Sư phạm xét ĐGNL ĐHSP Hà Nội | missing; yêu cầu major | missing; chuyển câu hỏi thành ĐHSP Hà Nội xét tuyển | Chưa trả; có dấu hiệu nhầm trường tổ chức kỳ thi với trường đích QNU. |
| 14. Phương thức GDMN | missing | missing | Rejection nêu reviewed row/claim không giữ exact entity name; nguồn có row GDMN/phương thức5. |
| 15. Phương thức GDTC | missing | missing | DAG quote không khớp block; RAG row entity name không khớp. Không nên hardcode PT5 để che lỗi binding. |
| 16. Chọn học bạ hay THPT | missing, hiểu thành kết hợp hai điểm | partial, chỉ giải thích PT2 | Chưa tư vấn lựa chọn theo các phương thức được phép; planning đổi ý nghĩa câu hỏi. |
| 17. Học bạ mấy năm | supported, 3 năm THPT | supported, 3 năm THPT | Đúng trọng tâm, quote PT2. |
| 18. Học bạ lớp nào | supported, chỉ nói 3 năm THPT | supported, lớp10/11/12 | RAG trả rõ lớp; DAG thiếu chi tiết lớp, cả hai cần giữ điều kiện điểm trung bình cả năm/các môn trong tổ hợp khi giải thích đầy đủ. |
| 19. Ngưỡng nguồn học bạ | missing, còn lộ missing constraint tiếng Anh | missing | Chưa phân biệt ngưỡng nguồn theo quy chế với ngưỡng ngành/phương thức. |
| 20. Mọi ngành sàn học bạ15? | missing | missing | Chưa trả được sự phân biệt 15/30 điều kiện nguồn và ngưỡng riêng. |

## Bằng chứng lỗi và hướng giải quyết đề xuất

### 1. Độ đầy đủ của liệt kê — ưu tiên cao nhất

Câu9 cả hai route nêu “4 phương thức” với quotes PT1, PT2, PT3, PT4. Đọc trực tiếp source `ks_rev_6280c8de7f46` đã xuất bản xác nhận tiếp theo có:

> + Phương thức 5 (PT5 - mã 405): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

Và câu “Ngoài ra, thực hiện Xét tuyển thẳng (mã 301) ...”. Cả source span có PT5 nhưng câu trả lời và verifier vẫn coi bốn mục là complete.

Đề xuất kiểm tra cấu trúc liệt kê tổng quát: liên kết các block cùng section/list across page, thu toàn bộ nhóm trước khi kết luận số lượng, kiểm tra tập mục được chứng minh với tập đã trả lời. Không dùng số thứ tự mục làm bằng chứng cho số lượng toàn nhóm; không hardcode “luôn 5” hoặc câu trả lời benchmark. Thiếu coverage phải partial/clarify, không complete=true.

### 2. Quote/entity binding và ưu tiên nguồn

Câu1 nguồn có DQN nhưng RAG EVIDENCE_PRECEDENCE_INVALID; câu14/15 có nguồn nhưng claim/quote mapping bị từ chối. Cần quan sát proposal/verifier output có kiểm soát, tạo regression với source spans thật, làm rõ authoritative entity identifier và display text, bind bằng source/block/span thay vì sửa chuỗi theo từ điển. Giữ xác thực hash/revision/exact quotes và không chấp nhận tham chiếu giả. Quy tắc ưu tiên TB1906 chỉ cho claim thực sự thuộc nguồn cũ và cùng applicability tuple, không vô hiệu hóa claim đúng từ chính nguồn ưu tiên.

### 3. Bảo toàn ý định và cách trả partial

Các ca10/13/16 cần kiểm tra subject institution, exam organizer, phương thức, lựa chọn so với kết hợp, rồi so khớp câu trả lời với yêu cầu nguyên gốc. Thiếu year dùng năm hiện tại như user chọn; không hỏi năm lại vô ích. Partial chỉ nêu phần còn thiếu, không gắn footer “chưa tìm thấy” chung sau dữ kiện đã trả đủ; missing_constraints phải tiếng Việt. Không suy từ bốn bảng row hoặc một câu điều kiện thành kết luận cho mọi ngành.

**Chưa triển khai các sửa RAG/DAG trên.** Phiên này chỉ bỏ quota và kiểm thử; cần được xác nhận đề xuất trước sửa các cấu trúc evidence/coverage phức tạp. Nên sửa và thử lại những ca ưu tiên trong 20 trước khi chạy đủ 82.
