# Kết quả kiểm thử bộ câu hỏi tuyển sinh 2026

Kết luận: chatbot hiện chưa đạt yêu cầu tư vấn thực tế với bộ câu hỏi này.

## Phạm vi và phương pháp

- Trích xuất 82 cặp Hỏi–Đáp, 16 nhóm, từ DOCX người dùng cung cấp.
- Bắt đầu UTC: 2026-10-13T04:05:50.422441+00:00; hoàn tất UTC: 2026-10-13T04:10:40.979543+00:00.
- SHA-256 DOCX: `5bdee19ececf709c472a56459e02a36e7f1afb44ffdba9974f58e899ed66c3fe`.
- Kho: `col_admissions`, epoch 3, generation `vg_21324678abcf`.
- Gửi nguyên câu hỏi; không đưa đáp án, hướng dẫn trong DOCX hoặc nội dung FAQ vào prompt.
- Mỗi câu dùng một hội thoại mới. Luồng chatbot là DAG thực tế `/assistants/admissions/chat`; RAG riêng là `/rag/ask` với model/reranker lấy từ cấu hình hiện tại.
- Hai đường có system prompt/runtime policy khác nhau: đây là đối chiếu chẩn đoán, không phải A/B cùng cấu hình.
- Không xóa cache, reset DB, đổi model, upload FAQ, duyệt, nạp lại vector, xuất bản hoặc sửa runtime.
- Có phát sinh các bản ghi hội thoại, workflow, sử dụng model và cache bình thường của việc test.
- Số lượt có trạng thái `answered` chỉ phản ánh hệ thống trả lời, KHÔNG phải số câu đúng. Không chạy Ragas và không tuyên bố các chỉ số faithfulness/relevance/precision.
- Đáp án trong DOCX là đáp án tham khảo để đối chiếu, không tự động được coi là nguồn pháp lý đã xác thực. Một số câu không nêu năm; việc chọn tài liệu cũ mà không hỏi rõ/nêu thời gian là rủi ro khi tư vấn mùa 2026.

## Model thực tế và đối soát trạng thái

OpenAI và Gemini đang inactive, dù cấu hình trợ lý ghi primary gpt-4o-mini và fallback gemini-2.5-flash-lite. Nhật ký inference cho các conversation của lần chạy đầy đủ ghi 69 lượt Cloudflare @cf/meta/llama-3.1-8b-instruct, is_fallback=true, success. 82 bản ghi qnu_workflow mang tên gpt-4o-mini là log tổng hợp theo cấu hình, không chứng minh đã gọi GPT; service còn ước lượng token từ chiều dài câu hỏi/đáp. Chưa thử đổi model nên chưa thể quy toàn bộ lỗi chất lượng cho riêng model dự phòng.

Đối soát sau test: epoch vẫn 3, generation vẫn vg_21324678abcf, 19 bộ binding/source/index pointers không đổi. Đây là lần chạy thực tế với cache hiện có, không cold-cache benchmark.

## Tổng hợp vận hành

| Đường kiểm thử | Tổng lượt | HTTP 200 | answered | insufficient_context | Lỗi khác | Trung vị giây |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DAG | 82 | 82 | 48 | 34 | 0 | 3.88 |
| RAG | 82 | 82 | 66 | 16 | 0 | 1.94 |

## Các lỗi đã xác minh

1. Câu 1 mã trường: node RAG trả DQN, node citation guard chặn vì `citations list is empty`; trả thiếu dữ liệu dù đáp án đã được sinh. Không nên tắt guard; cần gắn evidence cho câu trả lời hợp lệ.
2. Câu 5 tổng chỉ tiêu: tài liệu active `Thông tin TSĐH cập nhật` ghi `Tổng số lượng tuyển sinh: 5.173 (chỉ tiêu)`. RAG trả `NO_COMPATIBLE_FACT_EVIDENCE`: gate chỉ dùng bằng chứng facts/bảng và kết thúc trước hybrid retrieval; số liệu ở văn bản thường không đi qua được nhánh này.
3. Câu 21 ngành sư phạm có xét học bạ: DAG trả có; câu 36 gần tương đương lại trả không. Câu trả lời không ổn định theo cách diễn đạt và không đáp ứng đáp án tham khảo 2026.
4. Câu 25 đã nêu rõ năm 2026 nhưng DAG khẳng định môn Tiếng Anh nhân hệ số 2 chỉ từ danh sách tổ hợp. Trích dẫn không chứng minh hệ số; guard vẫn đánh grounded. Đây là lỗi suy luận bằng chứng, không chỉ lỗi chọn năm.
5. Câu 4 website: DAG trả miền cũ `quynhon.edu.vn`/`tuyensinh.quynhon.edu.vn`, trong khi nguồn cập nhật có `qnu.edu.vn`/`tuyensinh.qnu.edu.vn`; direct RAG trả miền trong đáp án.
6. Câu 14–15 phương thức GDMN/GDTC: trộn phương thức/chỉ tiêu cũ; câu 15 lấy thông tin năm 2025. Không thể dùng câu trả lời đó mặc định cho mùa 2026.
7. Kho chưa đủ tài liệu đợt bổ sung cuối mùa, nhưng bot không từ chối an toàn trong các câu tương ứng. Không tìm thấy số `151/TB-HĐTS`, `158/TB-HĐTS`, `456 chỉ tiêu` trong 19 canonical sources active; đây không tự nó chứng minh dữ liệu không có, nhưng các thông báo chuyên đề này không có trong danh mục nguồn hiện tại. Câu 76 nhầm lịch nhập học 24–28/8 thành hạn xét bổ sung; câu 77 dùng tối đa 15 nguyện vọng đợt chính thay vì 3 theo FAQ; câu 78 dùng 300.000 đồng/thí sinh của thi năng khiếu thay vì 15.000 đồng/nguyện vọng theo FAQ.
8. Tin nhắn no-answer dùng hotline cũ trong cấu hình (`0256.3846.156`), khác số `1800.55.88.49` ở nguồn tuyển sinh cập nhật và đáp án câu 3.
9. Câu 39 trả GDMN không thi năng khiếu, câu 41 trả GDTC không yêu cầu thể hình; nguồn 2026 active có đoạn thi GDMN/GDTC và yêu cầu nam 1,65m/45kg, nữ 1,55m/40kg. Guard vẫn cho qua cả hai.
10. Câu 42 hỏi điểm sàn GDMN năm 2026 nhưng DAG trả 20.25. Nguồn điểm sàn active có 20 và điều kiện 13,34; 20.25 lại xuất hiện ở cột điểm trúng tuyển 2023 trong nguồn lịch sử. Lỗi nhầm loại điểm/năm cho thấy chỉ kiểm tra số có mặt trong context là chưa đủ.

## Hướng xử lý đề xuất chưa triển khai

- Ưu tiên nguồn theo thời gian/hiệu lực và phạm vi; thiếu năm thì hỏi làm rõ hoặc nêu rõ năm sử dụng, không trộn số liệu 2024/2025/2026.
- Mở bằng chứng số liệu cho đoạn văn đã xuất bản: kiểm chứng tuple (đối tượng, thuộc tính, giá trị, năm, điều kiện, nguồn/trang) trước khi trả; không bỏ gate an toàn.
- Đồng bộ trích dẫn RAG → DAG, kiểm chứng quan hệ/điều kiện/phủ định chứ không chỉ độ trùng từ/số.
- Chọn lại chat model/provider đang hoạt động đúng chủ đích trong ModelOps; hiển thị model thực sự phục vụ và phân tách log workflow khỏi inference/chi phí để tránh hiểu nhầm đã gọi GPT.
- Phân biệt loại sự kiện và đơn vị: đăng ký nguyện vọng, nộp phí, thi năng khiếu, xác nhận trên Hệ thống Bộ, nhập học tại trường, xét bổ sung. Không chuyển số giữa các nghiệp vụ.
- Bổ sung nguồn chính thức về kết quả, đợt bổ sung và chính sách hỗ trợ còn thiếu; FAQ có thể được duyệt thành nguồn riêng nhưng không lấy làm bằng chứng cho chính bài test đang dùng.
- Đưa 82 câu này cùng các biến thể tương đương thành regression evaluation, đánh giá câu trả lời có căn cứ và từ chối đúng riêng biệt.

## Ma trận trạng thái từng câu

| Câu | Câu hỏi | DAG | RAG |
| ---: | --- | --- | --- |
| 1 | Trường Đại học Quy Nhơn có mã trường là gì? | insufficient_context | answered |
| 2 | Trường Đại học Quy Nhơn ở đâu? | answered | answered |
| 3 | Hotline tuyển sinh của Trường là số nào? | answered | answered |
| 4 | Website nào dùng để xem thông tin tuyển sinh chính thức? | answered | answered |
| 5 | Năm 2026 Trường Đại học Quy Nhơn tuyển bao nhiêu chỉ tiêu? | insufficient_context | insufficient_context |
| 6 | Năm 2026 Trường có bao nhiêu ngành/chương trình tuyển sinh? | insufficient_context | answered |
| 7 | Ai được đăng ký xét tuyển đại học chính quy? | answered | answered |
| 8 | Trường có xét tuyển thẳng không? | answered | answered |
| 9 | Năm 2026 QNU có những phương thức xét tuyển nào? | insufficient_context | answered |
| 10 | Có thể đăng ký nhiều phương thức vào cùng một ngành không? | insufficient_context | answered |
| 11 | Ngành nào không xét học bạ? | answered | answered |
| 12 | Ngành sư phạm có xét ĐGNL ĐHQG TP.HCM không? | insufficient_context | answered |
| 13 | Ngành sư phạm có xét ĐGNL Trường ĐHSP Hà Nội không? | answered | answered |
| 14 | Giáo dục Mầm non xét theo phương thức nào? | answered | answered |
| 15 | Giáo dục Thể chất xét theo phương thức nào? | answered | answered |
| 16 | Nếu em có điểm học bạ và điểm thi THPT thì nên dùng phương thức nào? | insufficient_context | answered |
| 17 | QNU xét học bạ mấy năm? | answered | answered |
| 18 | Học bạ được tính những lớp nào? | insufficient_context | answered |
| 19 | Ngưỡng nguồn tối thiểu khi dùng học bạ là bao nhiêu? | insufficient_context | insufficient_context |
| 20 | Điểm sàn học bạ của tất cả ngành có phải 15 không? | insufficient_context | answered |
| 21 | Ngành sư phạm có xét học bạ không? | answered | answered |
| 22 | Có cần đăng ký học bạ riêng trên hệ thống Trường không? | insufficient_context | insufficient_context |
| 23 | PT1 là gì? | answered | answered |
| 24 | Điểm thi THPT có được cộng ưu tiên khu vực, đối tượng không? | insufficient_context | answered |
| 25 | Năm 2026 môn tiếng Anh ở Ngôn ngữ Anh/Sư phạm Tiếng Anh có nhân hệ số 2 không? | answered | answered |
| 26 | Điểm chuẩn là tổng điểm 3 môn hay đã có ưu tiên? | answered | answered |
| 27 | QNU có xét điểm ĐGNL ĐHQG TP.HCM không? | answered | insufficient_context |
| 28 | QNU có xét điểm ĐGNL Trường ĐHSP Hà Nội không? | answered | answered |
| 29 | Điểm ĐGNL có phải quy đổi sang thang 30 không? | answered | answered |
| 30 | Em có điểm SPT/ĐGNL ĐHSP Hà Nội thì làm gì? | insufficient_context | answered |
| 31 | QNU có sử dụng IELTS/VSTEP trong xét tuyển không? | insufficient_context | insufficient_context |
| 32 | IELTS có thể thay điểm môn Tiếng Anh không? | insufficient_context | insufficient_context |
| 33 | Em có IELTS thì có cần đăng ký nguyện vọng trên Cổng Bộ không? | insufficient_context | insufficient_context |
| 34 | Ngành sư phạm có được đăng ký ở nguyện vọng 6 trở đi không? | insufficient_context | answered |
| 35 | Nếu em để Sư phạm ở nguyện vọng 6 thì có được xét không? | insufficient_context | insufficient_context |
| 36 | Sư phạm có xét học bạ không? | answered | answered |
| 37 | Sư phạm có xét ĐGNL ĐHQG TP.HCM không? | answered | answered |
| 38 | Điều kiện đầu vào các ngành sư phạm theo phương thức không sử dụng kết quả thi tốt nghiệp THPT để xét tuyển là gì? | answered | answered |
| 39 | Giáo dục Mầm non có thi năng khiếu không? | answered | answered |
| 40 | Giáo dục Thể chất có thi năng khiếu không? | answered | answered |
| 41 | Giáo dục Thể chất có yêu cầu thể hình không? | answered | answered |
| 42 | Điểm sàn Giáo dục Mầm non năm 2026 là bao nhiêu? | answered | answered |
| 43 | Khu vực 1 được cộng bao nhiêu điểm? | insufficient_context | answered |
| 44 | Khu vực 2 nông thôn được cộng bao nhiêu? | answered | answered |
| 45 | Khu vực 2 được cộng bao nhiêu? | insufficient_context | answered |
| 46 | Khu vực 3 có được cộng điểm không? | answered | answered |
| 47 | Ưu tiên đối tượng UT1 và UT2 là bao nhiêu? | answered | answered |
| 48 | Điểm cao có được cộng đủ điểm ưu tiên không? | answered | insufficient_context |
| 49 | Tổng điểm cộng có bị giới hạn không? | insufficient_context | answered |
| 50 | Năm 2026 được đăng ký tối đa bao nhiêu nguyện vọng? | answered | answered |
| 51 | Thời gian đăng ký nguyện vọng năm 2026 là khi nào? | answered | answered |
| 52 | Nếu chỉ đăng ký trên website QNU mà không đăng ký trên Cổng Bộ thì có được xét đợt 1 không? | answered | answered |
| 53 | Nếu đỗ nhiều nguyện vọng thì em được công nhận nguyện vọng nào? | answered | answered |
| 54 | Có thể đổi thứ tự nguyện vọng trong thời gian đăng ký không? | insufficient_context | answered |
| 55 | Lệ phí đăng ký nguyện vọng năm 2026 nộp khi nào? | answered | answered |
| 56 | Lệ phí thi năng khiếu GDMN/GDTC là bao nhiêu? | answered | insufficient_context |
| 57 | Không nộp lệ phí xét tuyển có ảnh hưởng không? | insufficient_context | insufficient_context |
| 58 | Năm 2026 thi năng khiếu QNU vào ngày nào? | answered | answered |
| 59 | Thời gian đăng ký thi năng khiếu năm 2026? | answered | answered |
| 60 | Có thể dùng điểm năng khiếu của trường khác không? | answered | answered |
| 61 | Tại sao điểm học bạ và điểm thi THPT không so trực tiếp với nhau? | insufficient_context | answered |
| 62 | Có công thức quy đổi chung để tự tính không? | insufficient_context | answered |
| 63 | Điểm chuẩn học bạ cao hơn điểm thi THPT có nghĩa học bạ khó hơn không? | insufficient_context | answered |
| 64 | Điểm sàn có phải điểm chuẩn không? | insufficient_context | answered |
| 65 | Đạt điểm sàn có chắc chắn đậu không? | insufficient_context | answered |
| 66 | Có thể lấy điểm chuẩn 2025 để khẳng định đậu 2026 không? | insufficient_context | insufficient_context |
| 67 | Sau khi trúng tuyển QNU phải làm gì? | answered | answered |
| 68 | Thời gian xác nhận nhập học năm 2026? | answered | answered |
| 69 | Thời gian nhập học trực tiếp K49 năm 2026? | answered | answered |
| 70 | Nếu trúng tuyển mà không xác nhận nhập học đúng hạn thì sao? | insufficient_context | insufficient_context |
| 71 | Giấy báo trúng tuyển nhận ở đâu? | answered | answered |
| 72 | Có phải nhập học trực tuyến ngay khi biết điểm chuẩn không? | insufficient_context | insufficient_context |
| 73 | QNU có xét tuyển bổ sung năm 2026 không? | answered | answered |
| 74 | Xét tuyển bổ sung dùng những phương thức nào? | answered | answered |
| 75 | Đăng ký xét bổ sung ở đâu? | answered | answered |
| 76 | Hạn đăng ký bổ sung đợt năm 2026? | answered | answered |
| 77 | Xét bổ sung được đăng ký bao nhiêu nguyện vọng? | answered | answered |
| 78 | Lệ phí xét tuyển bổ sung 2026 là bao nhiêu? | answered | answered |
| 79 | Điểm chuẩn bổ sung được công bố khi nào? | answered | answered |
| 80 | Học phí QNU năm 2026 khoảng bao nhiêu? | insufficient_context | answered |
| 81 | Sinh viên QNU có học bổng không? | insufficient_context | insufficient_context |
| 82 | Sinh viên sư phạm có chính sách hỗ trợ học phí/sinh hoạt phí không? | insufficient_context | insufficient_context |

## Nguồn đang phục vụ

- phu-luc-hd-tuyen-sinh-2025.signed — binding `bnd_0798d6ebb09d`, index `idx_rev_d64d0baf0c06`.
- NQ57.2024_ Phương hướng tuyển sinh 2025 — binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Báo cáo công tác Tư vấn tuyển sinh năm 2024_FINAL (1)_signed_signed-signed — binding `bnd_0dd3d2789954`, index `idx_rev_daf4d2e4f534`.
- Muc hoc phi 2024 — binding `bnd_18c9c944ee36`, index `idx_rev_2b7b7ec56f95`.
- TB điểm sàn 26 — binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- TB học phí K49 — binding `bnd_4bd40bc6a972`, index `idx_rev_57e15196704d`.
- Báo cáo công tác Tư vấn tuyển sinh năm 2025_Du thao — binding `bnd_4d788e0c0ee2`, index `idx_rev_00fbccf1d07e`.
- Hương dan thi Nang khieu GDTC 2026 — binding `bnd_574bfd4e5288`, index `idx_rev_76cae24bd0dd`.
- Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- BC Kết quả khảo sát Tư vấn tuyển sinh 2022 — binding `bnd_60019f7e73d6`, index `idx_rev_575e4b49149a`.
- Quy chế tuyển sinh đại học 2026 - 363 — binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Phuong huong tuyen sinh 2024_DHQN_final — binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- 2025_huong-dan-tuyen-sinh-dh-cd — binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Thông tin TSĐH cập nhật — binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Cac nganh Tuyen sinh 2025_moi — binding `bnd_bdb1f500cdbe`, index `idx_rev_742b1ff6d265`.
- Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed — binding `bnd_c6d3848722ab`, index `idx_rev_d7b434305a6c`.
- TB lịch xét tuyển ĐH — binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- HD nhập học — binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- FLYER TUYENSINH 2026-final2-16032026 (1) — binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.

## Đối chiếu đầy đủ từng câu

### Câu 1 Trường Đại học Quy Nhơn có mã trường là gì?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Mã cơ sở đào tạo của Trường Đại học Quy Nhơn trong tuyển sinh là DQN.

DAG — HTTP 200, trạng thái insufficient_context, 6.78 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `1655a05c-56f3-4b88-b9f1-869da84ea5ba`.

RAG — HTTP 200, trạng thái answered, 1.89 giây:

- Mã trường của Trường Đại học Quy Nhơn là DQN.

### Câu 2 Trường Đại học Quy Nhơn ở đâu?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Địa chỉ công bố trong thông tin tuyển sinh 2026: 170 An Dương Vương, phường Quy Nhơn Nam, tỉnh Gia Lai.

DAG — HTTP 200, trạng thái answered, 4.88 giây:

Trường Đại học Quy Nhơn có địa chỉ tại:

- 170 An Dương Vương, TP. Quy Nhơn, tỉnh Bình Định (theo thông tin trên website của Trường)
- 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai (theo thông tin trên Thông báo của Trường)

Trường có trang thông tin điện tử tại địa chỉ https://qnu.edu.vn và thông tin tuyển sinh được công khai tại địa chỉ https://tuyensinh.qnu.edu.vn.

Số điện thoại liên hệ tuyển sinh của Trường là 1800.55.88.49.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 1; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Báo cáo công tác Tư vấn tuyển sinh năm 2025_Du thao — trang 6; binding `bnd_4d788e0c0ee2`, index `idx_rev_00fbccf1d07e`.
- Nguồn: BC Kết quả khảo sát Tư vấn tuyển sinh 2022 — trang 6; binding `bnd_60019f7e73d6`, index `idx_rev_575e4b49149a`.
- Nguồn: Thông tin TSĐH cập nhật — trang 1; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: BC Kết quả khảo sát Tư vấn tuyển sinh 2022 — trang 2; binding `bnd_60019f7e73d6`, index `idx_rev_575e4b49149a`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `4be2fbf0-34b7-4ecd-82d5-6aedbb15fe41`.

RAG — HTTP 200, trạng thái answered, 0.03 giây:

Trường Đại học Quy Nhơn có địa chỉ tại:

- 170 An Dương Vương, TP. Quy Nhơn, tỉnh Bình Định (theo tài liệu năm 2025)
- 170 An Dương Vương, P. Quy Nhơn Nam, tỉnh Gia Lai (theo tài liệu năm 2026)

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 1; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Báo cáo công tác Tư vấn tuyển sinh năm 2025_Du thao — trang 6; binding `bnd_4d788e0c0ee2`, index `idx_rev_00fbccf1d07e`.
- Nguồn: BC Kết quả khảo sát Tư vấn tuyển sinh 2022 — trang 6; binding `bnd_60019f7e73d6`, index `idx_rev_575e4b49149a`.
- Nguồn: Thông tin TSĐH cập nhật — trang 1; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: BC Kết quả khảo sát Tư vấn tuyển sinh 2022 — trang 2; binding `bnd_60019f7e73d6`, index `idx_rev_575e4b49149a`.
### Câu 3 Hotline tuyển sinh của Trường là số nào?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Hotline tuyển sinh: 1800 55 88 49.

DAG — HTTP 200, trạng thái answered, 2.25 giây:

Hotline tuyển sinh của Trường Đại học Quy Nhơn là số 1800.55.88.49.

- Nguồn: HD nhập học — trang 3; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Cac nganh Tuyen sinh 2025_moi — trang 1; binding `bnd_bdb1f500cdbe`, index `idx_rev_742b1ff6d265`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `900bf904-84f8-4ea2-8fde-fa8cce5ac106`.

RAG — HTTP 200, trạng thái answered, 0.03 giây:

- Hotline tuyển sinh của Trường Đại học Quy Nhơn là số 1800.55.88.49.

- Nguồn: HD nhập học — trang 3; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Cac nganh Tuyen sinh 2025_moi — trang 1; binding `bnd_bdb1f500cdbe`, index `idx_rev_742b1ff6d265`.
### Câu 4 Website nào dùng để xem thông tin tuyển sinh chính thức?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Thí sinh nên theo dõi website tuyển sinh của Trường Đại học Quy Nhơn: https://tuyensinh.qnu.edu.vn và website chính thức của Trường: https://qnu.edu.vn/

DAG — HTTP 200, trạng thái answered, 3.3 giây:

- Website chính thức của Trường Đại học Quy Nhơn là: [www.quynhon.edu.vn](http://www.quynhon.edu.vn)
- Website tuyển sinh của Trường Đại học Quy Nhơn là: [tuyensinh.quynhon.edu.vn](http://tuyensinh.quynhon.edu.vn)
- Website Cổng thông tin tuyển sinh của Bộ Giáo dục và Đào tạo (GDDT) là: [tuyensinh.gov.vn](http://tuyensinh.gov.vn)
- Website Hệ thống hỗ trợ tuyển sinh chung của Bộ GDĐT là: [hstts.edu.vn](http://hstts.edu.vn)

- Nguồn: Báo cáo công tác Tư vấn tuyển sinh năm 2025_Du thao — trang 5; binding `bnd_4d788e0c0ee2`, index `idx_rev_00fbccf1d07e`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 16; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `d1692e51-54e8-41be-ab8b-df221dd7548b`.

RAG — HTTP 200, trạng thái answered, 0.03 giây:

**Website để xem thông tin tuyển sinh chính thức của Trường Đại học Quy Nhơn**

- **Website chính thức của Trường Đại học Quy Nhơn:** https://qnu.edu.vn/
- **Cổng thông tin tuyển sinh của Trường Đại học Quy Nhơn:** https://tuyensinh.qnu.edu.vn/
- **Hệ thống hỗ trợ tuyển sinh chung của Bộ Giáo dục và Đào tạo:** https://tuyensinh.moe.gov.vn/
- **Cổng thông tin điện tử của Trường Đại học Quy Nhơn:** https://qnu.edu.vn/

**Lưu ý:**

- **Website chính thức của Trường Đại học Quy Nhơn** cung cấp thông tin tuyển sinh, đào tạo, nghiên cứu khoa học, hợp tác quốc tế và các hoạt động khác của trường.
- **Cổng thông tin tuyển sinh của Trường Đại học Quy Nhơn** cung cấp thông tin tuyển sinh, đăng ký xét tuyển, xét tuyển, xét tuyển bổ sung và các thông tin liên quan đến tuyển sinh.
- **Hệ thống hỗ trợ tuyển sinh chung của Bộ Giáo dục và Đào tạo** cung cấp thông tin tuyển sinh, đăng ký xét tuyển, xét tuyển, xét tuyển bổ sung và các thông tin liên quan đến tuyển sinh.
- **Cổng thông tin điện tử của Trường Đại học Quy Nhơn** cung cấp thông tin về hoạt động của trường, bao gồm thông tin tuyển sinh, đào tạo, nghiên cứu khoa học, hợp tác quốc tế và các hoạt động khác.

**Trường Đại học Quy Nhơn luôn cập nhật và chỉnh sửa thông tin tuyển sinh trên các website chính thức và cổng thông tin tuyển sinh.**

- Nguồn: Báo cáo công tác Tư vấn tuyển sinh năm 2025_Du thao — trang 5; binding `bnd_4d788e0c0ee2`, index `idx_rev_00fbccf1d07e`.
- Nguồn: BC Kết quả khảo sát Tư vấn tuyển sinh 2022 — trang 5; binding `bnd_60019f7e73d6`, index `idx_rev_575e4b49149a`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 16; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 5 Năm 2026 Trường Đại học Quy Nhơn tuyển bao nhiêu chỉ tiêu?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Tổng số lượng tuyển sinh đại học chính quy là 5.173.

DAG — HTTP 200, trạng thái insufficient_context, 1.74 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `77c37194-1a53-4303-a218-b9a770b659ba`.

RAG — HTTP 200, trạng thái insufficient_context, 0.39 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 6 Năm 2026 Trường có bao nhiêu ngành/chương trình tuyển sinh?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Thông tin công bố đầu mùa thể hiện 53 ngành/chương trình; các thông báo ngưỡng đầu vào sau đó thể hiện 56 mã xét tuyển/ngành/chương trình do có các chương trình/định hướng riêng.

DAG — HTTP 200, trạng thái insufficient_context, 12.73 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["Unsupported numbers detected: 7140209, 7140210, 7140211, 7140212, 7140213, 7140217, 7140218, 7140219, 7140231, 7140247, 7380101, 7440112"], "unsupported_numbers": ["7140209", "7140210", "7140211", "7140212", "7140213", "7140217", "7140218", "7140219", "7140231", "7140247", "7380101", "7440112"]}

Mã workflow: `8657c5fe-95a5-430f-92c6-5b570691f317`.

RAG — HTTP 200, trạng thái answered, 9.44 giây:

Câu trả lời chính xác dựa trên thông tin được cung cấp:

**Trường Đại học Quy Nhơn (QNU) tuyển sinh 51 ngành/chương trình đào tạo trong năm 2026.**

Dưới đây là danh sách các ngành/chương trình đào tạo của QNU:

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng tuyển sinh | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | 7140114 | Quản lý giáo dục | 1,2,3,4 | 44 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Sử) |
| 2 | 7140201 | Giáo dục Mầm non | 5 | 180 | (Văn, Toán, NK GDMN) |
| 3 | 7140202 | Giáo dục Tiểu học | 1,4 | 250 | (Văn, Anh, Toán)<br>(Văn, Anh, Lý)<br>(Văn, Anh, Hóa)<br>(Văn, Anh, Sinh)<br>(Văn, Anh, Sử)<br>(Văn, Anh, Địa) |
| 4 | 7140205 | Giáo dục Chính trị | 1,4 | 20 | (Văn, Toán, Giáo dục KT và PL)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Anh, Giáo dục KT và PL) |
| 5 | 7140206 | Giáo dục Thể chất | 5 | 100 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT) (Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT) |
| 6 | 7140209 | Sư phạm Toán học | 1,4 | 100 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Tin, Anh) |
| 7 | 7140210 | Sư phạm Tin học | 1,4 | 120 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Văn, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Văn, Tin)<br>(Toán, Lý, Tin)<br>(Toán, Hóa, Tin)<br>(Toán, Anh, Tin) |
| 8 | 7140211 | Sư phạm Vật lý | 1,4 | 51 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Tin) |
| 9 | 7140212 | Sư phạm Hóa học | 1,4 | 36 | (Toán, Hóa, Lý)<br>(Toán, Hóa, Sinh)<br>(Toán, Hóa, Anh)<br>(Toán, Hóa, Văn) |
| 10 | 7140213 | Sư phạm Sinh học | 1,4 | 25 | (Toán, Sinh, Hóa)<br>(Toán, Sinh, Lý)<br>(Toán, Sinh, Anh)<br>(Toán, Sinh, Văn) |
| 11 | 7140217 | Sư phạm Ngữ Văn | 1,4 | 120 | (Văn, Sử, Địa)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Giáo dục KT và PL, Anh) |
| 12 | 7140218 | Sư phạm Lịch sử | 1,4 | 54 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Sử, Toán) |
| 13 | 7140219 | Sư phạm Địa lý | 1,4 | 80 | (Văn, Địa, Sử)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Địa, Anh)<br>(Văn, Địa, Toán)<br>(Toán, Địa, Anh)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Địa, Sinh)<br>(Toán, Địa, Sử)<br>(Toán, Địa, Hóa) |
| 14 | 7140231 | Sư phạm Tiếng Anh | 1,4 | 200 | (Toán, Văn, Anh) |
| 15 | 7140247 | Sư phạm Khoa học tự nhiên | 1,4 | 70 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh) (Toán, Lý, Sinh)<br>(Toán, Hóa, Sinh)<br>(Toán, Sinh, Anh) |
| 16 | 7140301 | Kế toán (Định hướng ACCA) | 1,2,3,

- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 12; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
### Câu 7 Ai được đăng ký xét tuyển đại học chính quy?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Người đã tốt nghiệp THPT hoặc tương đương và đáp ứng các điều kiện dự tuyển theo Quy chế tuyển sinh và điều kiện của từng ngành/phương thức.

DAG — HTTP 200, trạng thái answered, 4.39 giây:

- Thí sinh dự tuyển đợt 1 đào tạo chính quy.
- Thí sinh đã trúng tuyển vào cơ sở đào tạo theo kế hoạch xét tuyển thẳng.
- Thí sinh đăng ký xét tuyển vào các trường trực thuộc Bộ Quốc phòng, Bộ Công an.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 17; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 17; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `a7e641c0-0b87-40a8-ab22-869d04fadce1`.

RAG — HTTP 200, trạng thái answered, 1.75 giây:

- Thí sinh dự tuyển đợt 1 đào tạo chính quy.
- Thí sinh đã trúng tuyển vào cơ sở đào tạo theo kế hoạch xét tuyển thẳng.
- Thí sinh đăng ký xét tuyển vào các trường trực thuộc Bộ Quốc phòng, Bộ Công an.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 17; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 17; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 8 Trường có xét tuyển thẳng không?

Nhóm: I. THÔNG TIN CHUNG VỀ TRƯỜNG VÀ TUYỂN SINH 2026

Đáp án tham khảo trong DOCX:

Có. Xét tuyển thẳng thực hiện theo Quy chế tuyển sinh của Bộ GD&ĐT; mã phương thức xét tuyển thẳng được Trường công bố là 301.

DAG — HTTP 200, trạng thái answered, 5.25 giây:

Trường có xét tuyển thẳng không?

- Xét tuyển thẳng: theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo vào các ngành phù hợp theo Phụ lục 1.
- Ưu tiên xét tuyển:
 - Đối với thí sinh đoạt giải trong kỳ thi chọn học sinh giỏi quốc gia, Cuộc thi khoa học, kỹ thuật cấp quốc gia mức ưu tiên cụ thể như sau: giải nhất cộng 3 điểm, giải nhì cộng 2 điểm, giải ba cộng 1 điểm, giải khuyến khích hoặc giải tư (Cuộc thi khoa học, kỹ thuật cấp quốc gia) cộng 0,5 điểm vào tổng điểm 3 môn xét tuyển sau khi nhân hệ số môn thi chính (nếu có); thời gian đoạt giải không quá 3 năm tính tới thời điểm xét tuyển.
 - Đối với thí sinh tham gia đội tuyển quốc gia thi đấu tại các giải quốc tế chính thức được Bộ Văn hóa, Thể thao và Du lịch xác nhận đã hoàn thành nhiệm vụ, bao gồm: Giải vô địch thế giới, Cúp thế giới, Thế vận hội Olympic, Đại hội Thể thao châu Á (ASIAD), Giải vô địch châu Á, Cúp châu Á, Giải vô địch Đông Nam Á, Đại hội Thể thao Đông Nam Á (SEA Games), Cúp Đông Nam Á và đã tham dự kỳ thi năng khiếu của Trường được cộng 3 điểm vào tổng điểm 3 môn xét tuyển vào ngành Giáo dục thể chất; thời gian đoạt giải không quá 4 năm tính tới thời điểm xét tuyển.
 - Đối với thí sinh đoạt huy chương vàng, bạc, đồng các giải thể dục thể thao cấp quốc gia tổ chức một lần trong năm và thí sinh được Tổng cục Thể dục thể thao có quyết định công nhận là kiện tướng quốc gia đã tham dự kỳ thi năng khiếu của Trường được cộng 1 điểm vào tổng điểm 3 môn xét tuyển vào ngành Giáo dục thể chất; thời gian đoạt giải không quá 4 năm tính tới thời điểm xét tuyển.

- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `13eed49c-23b5-427c-ba4d-bec65ad42706`.

RAG — HTTP 200, trạng thái answered, 2.94 giây:

- Trường có xét tuyển thẳng.

- Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo vào các ngành phù hợp theo Phụ lục 1.

- Ưu tiên xét tuyển:

  - Đối với thí sinh đoạt giải trong kỳ thi chọn học sinh giỏi quốc gia, Cuộc thi khoa học, kỹ thuật cấp quốc gia mức ưu tiên cụ thể như sau: giải nhất cộng 3 điểm, giải nhì cộng 2 điểm, giải ba cộng 1 điểm, giải khuyến khích hoặc giải tư (Cuộc thi khoa học, kỹ thuật cấp quốc gia) cộng 0,5 điểm vào tổng điểm 3 môn xét tuyển sau khi nhân hệ số môn thi chính (nếu có); thời gian đoạt giải không quá 3 năm tính tới thời điểm xét tuyển.

  - Đối với thí sinh tham gia đội tuyển quốc gia thi đấu tại các giải quốc tế chính thức được Bộ Văn hóa, Thể thao và Du lịch xác nhận đã hoàn thành nhiệm vụ, bao gồm: Giải vô địch thế giới, Cúp thế giới, Thế vận hội Olympic, Đại hội Thể thao châu Á (ASIAD), Giải vô địch châu Á, Cúp châu Á, Giải vô địch Đông Nam Á, Đại hội Thể thao Đông Nam Á (SEA Games), Cúp Đông Nam Á và đã tham dự kỳ thi năng khiếu của Trường được cộng 3 điểm vào tổng điểm 3 môn xét tuyển vào ngành Giáo dục thể chất; thời gian đoạt giải không quá 4 năm tính tới thời điểm xét tuyển.

  - Đối với thí sinh đoạt huy chương vàng, bạc, đồng các giải thể dục thể thao cấp quốc gia tổ chức một lần trong năm và thí sinh được Tổng cục Thể dục thể thao có quyết định công nhận là kiện tướng quốc gia đã tham dự kỳ thi năng khiếu của Trường được cộng 1 điểm vào tổng điểm 3 môn xét tuyển vào ngành Giáo dục thể chất; thời gian đoạt giải không quá 4 năm tính tới thời điểm xét tuyển.

- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
### Câu 9 Năm 2026 QNU có những phương thức xét tuyển nào?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Có 5 phương thức chính: PT1 (mã 100) xét điểm thi tốt nghiệp THPT 2026; PT2 (mã 200) xét kết quả học tập 3 năm THPT; PT3 (mã 402A) xét điểm ĐGNL ĐHQG TP.HCM; PT4 (mã 402B) xét điểm ĐGNL Trường ĐHSP Hà Nội; PT5 (mã 405) xét điểm thi tốt nghiệp THPT kết hợp điểm năng khiếu GDMN/GDTC. Ngoài ra có xét tuyển thẳng theo Quy chế.

DAG — HTTP 200, trạng thái insufficient_context, 5.45 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `e135e40f-3587-471d-90ca-2abdcd08fc3c`.

RAG — HTTP 200, trạng thái answered, 4.75 giây:

**PHƯƠNG THỨC XÉT TUYỂN NĂM 2026**

| STT | Mã xét tuyển | Tên ngành, chương trình xét tuyển | Phương thức tuyển sinh | Số lượng tuyển sinh |
| :--- | :--- | :--- | :--- | :--- |
| 1 | 100 | Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 | 1,2,3,4,6 | - |
| 2 | 200 | Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) | 2,6 | - |
| 3 | 402A | Xét kết quả kỳ thi đánh giá năng lực (ĐGNL) của ĐHQG TP.HCM | 3 | - |
| 4 | 402B | Xét kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội | 4 | - |
| 5 | 405 | Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC | 5 | - |

Lưu ý: 

- STT: Số thứ tự
- Mã xét tuyển: Mã xác định phương thức xét tuyển
- Tên ngành, chương trình xét tuyển: Tên ngành đào tạo
- Phương thức tuyển sinh: Số thứ tự phương thức xét tuyển
- Số lượng tuyển sinh: Số lượng chỉ tiêu tuyển sinh

- Nguồn: Thông tin TSĐH cập nhật — trang 1; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed — trang 1; binding `bnd_c6d3848722ab`, index `idx_rev_d7b434305a6c`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
### Câu 10 Có thể đăng ký nhiều phương thức vào cùng một ngành không?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Có thể sử dụng các phương thức mà ngành đó cho phép và thí sinh đáp ứng điều kiện. Tuy nhiên, nguyện vọng xét tuyển đợt 1 vẫn phải được đăng ký trên Hệ thống hỗ trợ tuyển sinh chung của Bộ GD&ĐT.

DAG — HTTP 200, trạng thái insufficient_context, 5.7 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `c0f3b65d-8423-42f0-ba25-ff7d5e6c8bef`.

RAG — HTTP 200, trạng thái answered, 1.62 giây:

| **Ngành** | **Phương thức** | **Giá trị** |
| --- | --- | --- |
| Quản lý giáo dục | Có thể đăng ký | Có |
| Giáo dục Mầm non | Có thể đăng ký | Có |
| Giáo dục Tiểu học | Có thể đăng ký | Có |
| Giáo dục Chính trị | Có thể đăng ký | Có |
| Giáo dục Thể chất | Có thể đăng ký | Có |

Kết luận: Có, các ngành trên đều có thể đăng ký nhiều phương thức vào cùng một ngành.

### Câu 11 Ngành nào không xét học bạ?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Các ngành đào tạo giáo viên của Trường Đại học Quy Nhơn không xét theo phương thức học bạ PT2.

DAG — HTTP 200, trạng thái answered, 3.86 giây:

Danh sách các ngành không xét học bạ bao gồm:

- Quản lý Giáo dục
- Giáo dục Mầm non
- Sư phạm Toán học
- Sư phạm Tin học
- Sư phạm Vật lý
- Sư phạm Hóa học
- Sư phạm Sinh học
- Sư phạm Ngữ Văn
- Sư phạm Lịch sử
- Sư phạm Địa lý
- Sư phạm Tiếng Anh
- Sư phạm Khoa học tự nhiên

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 12; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `df434854-3e7b-45ff-99b2-905675065319`.

RAG — HTTP 200, trạng thái answered, 3.28 giây:

- Các ngành đào tạo giáo viên không xét tuyển phương thức 2 (Xét tuyển theo kết quả học tập 3 năm THPT - học bạ).
- Các ngành đào tạo giáo viên không xét tuyển phương thức 3 (Xét kết quả kỳ thi đánh giá năng lực của ĐHQG TP.HCM).
- Các ngành đào tạo giáo viên không xét tuyển phương thức 4 (Xét kết quả kỳ thi đánh giá năng lực của Trường Đại học Sư phạm Hà Nội).
- Các ngành đào tạo giáo viên không xét tuyển phương thức 5 (Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn).
- Các ngành đào tạo giáo viên không xét tuyển phương thức 3, 4 và 5, chỉ xét tuyển phương thức 1 và 2.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 12; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
### Câu 12 Ngành sư phạm có xét ĐGNL ĐHQG TP.HCM không?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Không. Các ngành đào tạo giáo viên không xét PT3 – điểm thi ĐGNL của ĐHQG TP.HCM.

DAG — HTTP 200, trạng thái insufficient_context, 10.95 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `5301cbc9-b171-4b61-ab69-73aab1eeead8`.

RAG — HTTP 200, trạng thái answered, 8.89 giây:

**Sư phạm có xét ĐGNL ĐHQG TP.HCM không?**

Câu trả lời dựa trên tài liệu và số liệu chính thức được cung cấp.

**Bảng số liệu trích xuất:**

| STT | Mã xét tuyển | Tên ngành/CTĐT xét tuyển | Phương thức xét điểm thi TN. THPT | Phương thức xét kết quả học tập THPT | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM | Phương thức xét điểm thi ĐGNL ĐHSP HN | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 6 | 7140209 | Sư phạm Toán<br>học | 20 | – | – | 20 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Anh, Tin) |
| 7 | 7140210 | Sư phạm Tin<br>học | 20 | – | – | 20 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Văn, Anh)<br>(Toán, Hóa, Anh)<br>(Toán, Văn, Tin)<br>(Toán, Lý, Tin)<br>(Toán, Hóa, Tin)<br>(Toán, Anh, Tin) |
| 8 | 7140211 | Sư phạm Vật<br>lý | 20 | – | – | 20 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Văn)<br>(Toán, Lý, Tin) |
| 9 | 7140212 | Sư phạm Hóa<br>học | 20 | – | – | 20 | (Toán, Hóa, Lý)<br>(Toán, Hóa, Sinh)<br>(Toán, Hóa, Anh)<br>(Toán, Hóa, Văn) |
| 10 | 7140213 | Sư phạm Sinh<br>học | 20 | – | – | 20 | (Toán, Sinh, Hóa)<br>(Toán, Sinh, Lý)<br>(Toán, Sinh, Anh)<br>(Toán, Sinh, Văn) |
| 11 | 7140217 | Sư phạm Ngữ<br>Văn | 20 | – | – | 20 | (Văn, Sử, Địa)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Giáo dục KT và PL, Anh) |
| 12 | 7140218 | Sư phạm Lịch<br>sử | 20 | – | – | 20 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Sử, Toán) |
| 13 | 7140219 | Sư phạm Địa<br>lý | 20 | – | – | 20 | (Văn, Địa, Sử)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Địa, Anh)<br>(Toán, Địa, Anh)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Địa, Sinh)<br>(Toán, Địa, Sử)<br>(Toán, Địa, Hóa) |
| 14 | 7140231 | Sư phạm<br>Tiếng Anh | 20 | – | – | 20 | (Toán, Văn, Anh) |
| 15 | 7140247 | Sư phạm Khoa<br>học tự nhiên | 20 | – | – | 20 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Lý, Sinh)<br>(Toán, Hóa, Sinh)<br>(Toán, Sinh, Anh) |
| 16 | 7140249 | Sư phạm Lịch<br>sử - Địa lý | 20 | – | – | 20 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Địa, Anh)<br>(Văn, Sử, Toán)<br>(Văn, Địa, Toán) |

**Kết luận:**

- Sư phạm Toán học xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Tin học xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Vật lý xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Hóa học xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Sinh học xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Ngữ văn xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Lịch sử xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Địa lý xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Tiếng Anh xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Khoa học tự nhiên xét tuyển theo phương thức 1, 4, 6.
- Sư phạm Lịch sử - Địa lý xét tuyển theo phương thức 1, 4, 6.

**Lưu

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: TB điểm sàn 26 — trang 2; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB điểm sàn 26 — trang 3; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 13 Ngành sư phạm có xét ĐGNL Trường ĐHSP Hà Nội không?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Có, các ngành đào tạo giáo viên phù hợp có thể xét PT4; riêng Giáo dục Mầm non và Giáo dục Thể chất sử dụng phương thức có năng khiếu theo thông báo của Trường.

DAG — HTTP 200, trạng thái answered, 4.23 giây:

Bạn đang hỏi về việc ngành Sư phạm có xét Đánh giá năng lực của Trường Đại học Sư phạm Hà Nội không?

Căn cứ theo thông tin trong tài liệu, tôi có thể trả lời như sau:

- Phương thức xét tuyển 4 (PT4 - mã 402B) của Trường Đại học Quy Nhơn là Xét kết quả kỳ thi Đánh giá năng lực của Trường Đại học Sư phạm Hà Nội.
- Tuy nhiên, thông tin này không được áp dụng cho Trường Đại học Quy Nhơn mà là thông tin chung về phương thức xét tuyển của Trường Đại học Sư phạm Hà Nội.

Vì vậy, tôi không thể trả lời chính xác về việc Trường Đại học Quy Nhơn xét Đánh giá năng lực của Trường Đại học Sư phạm Hà Nội cho ngành Sư phạm.

Tuy nhiên, có thể bạn đang quan tâm đến thông tin về phương thức xét tuyển của Trường Đại học Sư phạm Hà Nội. Cụ thể, Trường Đại học Sư phạm Hà Nội có phương thức xét tuyển 4 (PT4 - mã 402B) là Xét kết quả kỳ thi Đánh giá năng lực của Trường Đại học Sư phạm Hà Nội.

Nếu bạn có bất kỳ câu hỏi nào khác, xin vui lòng cho tôi biết.

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `460917d9-86f8-4520-b846-3254b4babdc5`.

RAG — HTTP 200, trạng thái answered, 3.05 giây:

Câu hỏi của người dùng là: Ngành sư phạm có xét ĐGNL Trường ĐHSP Hà Nội không?

Câu trả lời chính thức của Trợ lý AI chính thức của Trường Đại học Quy Nhơn (QNU) như sau:

- [Giáo dục Mầm non]: STT: 2 | Mã xét tuyển: 7140201 | Phương thức xét điểm thi TN. THPT: 20 | Phương thức xét kết quả học tập THPT: – | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM: – | Phương thức xét điểm thi ĐGNL ĐHSP HN: 20 | Tổ hợp môn xét tuyển: (Văn, Toán, NK GDMN)<br>Tổng điểm 2 môn văn hóa + 2/3 điểm ƯT ≥<br>13,34
- [Giáo dục Thể chất]: STT: 5 | Mã xét tuyển: 7140206 | Phương thức xét điểm thi TN. THPT: 19 | Phương thức xét kết quả học tập THPT: – | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM: – | Phương thức xét điểm thi ĐGNL ĐHSP HN: 19 | Tổ hợp môn xét tuyển: (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT)<br>Tổng điểm 2 môn văn hóa + 2/3 điểm ƯT ≥<br>12,67

Trường Đại học Sư phạm Hà Nội xét tuyển theo kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội.

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: TB điểm sàn 26 — trang 2; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: TB điểm sàn 26 — trang 3; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 14 Giáo dục Mầm non xét theo phương thức nào?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Năm 2026, Giáo dục Mầm non xét theo PT5: kết quả thi tốt nghiệp THPT 2026 kết hợp điểm thi năng khiếu GDMN của Trường.

DAG — HTTP 200, trạng thái answered, 10.02 giây:

Cảm ơn bạn đã tin tưởng vào sự hỗ trợ của mình. 

Giáo dục Mầm non xét theo phương thức 5 và 6.

| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu | Phương thức | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 2 | 7140201 | Giáo dục Mầm non | 158 | 5,6 | (Toán, Văn, NK GDMN) |

[Giáo dục Mầm non]: STT: 2 | Mã xét tuyển: 7140201 | Phương thức xét điểm thi TN. THPT: 20 | Phương thức xét kết quả học tập THPT: – | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM: – | Phương thức xét điểm thi ĐGNL ĐHSP HN: 20 | Tổ hợp môn xét tuyển: (Văn, Toán, NK GDMN)<br>Tổng điểm 2 môn văn hóa + 2/3 điểm ƯT ≥<br>13,34

[Giáo dục Thể chất]: STT: 5 | Mã xét tuyển: 7140206 | Phương thức xét điểm thi TN. THPT: 19 | Phương thức xét kết quả học tập THPT: – | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM: – | Phương thức xét điểm thi ĐGNL ĐHSP HN: 19 | Tổ hợp môn xét tuyển: (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT)<br>Tổng điểm 2 môn văn hóa + 2/3 điểm ƯT ≥<br>12,67

[Giáo dục Mầm non]: STT: 2 | Mã xét tuyển: 7140201 | 2023 - Chỉ tiêu: 150 | 2023 - Số trúng tuyển nhập học: 150 | 2023 - Điểm trúng tuyển (TNTHP T): 20.25 | 2023 - Điểm trúng tuyển (Xét học bạ): 24 | 2024 - Chỉ tiêu: 126 | 2024 - Số trúng tuyển nhập học: 118 | 2024 - Điểm trúng tuyển (TNT HPT): 23.1 | 2024 - Điểm trúng tuyển (Xét học bạ): 24.5

[Giáo dục Thể chất]: STT: 5 | Mã xét tuyển: 7140206 | 2023 - Chỉ tiêu: 20 | 2023 - Số trúng tuyển nhập học: 20 | 2023 - Điểm trúng tuyển (TNTHP T): 22.25 | 2023 - Điểm trúng tuyển (Xét học bạ): 25.5 | 2024 - Chỉ tiêu: 24 | 2024 - Số trúng tuyển nhập học: 23 | 2024 - Điểm trúng tuyển (TNT HPT): 26.5 | 2024 - Điểm trúng tuyển (Xét học bạ): 26.75

[Giáo dục Mầm non]: STT: 2 | Mã xét tuyển: 7140201 | 2023 - Điểm trúng tuyển (TNTHP T): 20.25 | 2023 - Điểm trúng tuyển (Xét học bạ): 24 | 2024 - Điểm trúng tuyển (TNT HPT): 23.1 | 2024 - Điểm trúng tuyển (Xét học bạ): 24.5

[Giáo dục Thể chất]: STT: 5 | Mã xét tuyển: 7140206 | 2023 - Điểm trúng tuyển (TNTHP T): 22.25 | 2023 - Điểm trúng tuyển (Xét học bạ): 25.5 | 2024 - Điểm trúng tuyển (TNT HPT): 26.5 | 2024 - Điểm trúng tuyển (Xét học bạ): 26.75

[Giáo dục Mầm non]: STT: 2 | Mã xét tuyển: 7140201 | 2023 - Điểm trúng tuyển (TNTHP T): 20.25 | 2023 - Điểm trúng tuyển (Xét học bạ): 24 | 2024 - Điểm trúng tuyển (TNT HPT): 23.1 | 2024 - Điểm trúng tuyển (Xét học bạ): 24.5

[Giáo dục Thể chất]: STT: 5 | Mã xét tuyển: 7140206 | 2023 - Điểm trúng tuyển (TNTHP T): 22.25 | 2023 - Điểm trúng tuyển (Xét học bạ): 25.5 | 2024 - Điểm trúng tuyển (TNT HPT): 26.5 | 2024 - Điểm trúng tuyển (Xét học bạ): 26.75

[Giáo dục Mầm non]: STT: 2 | Mã xét tuyển: 7140201 | 2023 - Điểm trúng tuyển (TNTHP T): 20.25 | 2023 - Điểm trúng tuyển (Xét học b

- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `dbbaa68d-4bba-4dcd-b456-33c8c9d8cf06`.

RAG — HTTP 200, trạng thái answered, 4.73 giây:

Giáo dục Mầm non xét theo phương thức 5 và 6.

Dưới đây là thông tin chi tiết về phương thức xét tuyển:

- Phương thức 5 (PT5 - mã 405): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

- Phương thức 6 (PT6 - mã 301): Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ GD&ĐT.

Cụ thể, đối với ngành Giáo dục Mầm non (Mã xét tuyển: 7140201), phương thức xét tuyển bao gồm:

- Phương thức 5: Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

- Phương thức 6: Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ GD&ĐT.

Mong rằng thông tin này sẽ giúp bạn hiểu rõ hơn về phương thức xét tuyển cho ngành Giáo dục Mầm non tại Trường Đại học Quy Nhơn.

- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
### Câu 15 Giáo dục Thể chất xét theo phương thức nào?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Năm 2026, Giáo dục Thể chất xét theo PT5: kết quả thi tốt nghiệp THPT 2026 kết hợp điểm thi năng khiếu GDTC của Trường.

DAG — HTTP 200, trạng thái answered, 5.94 giây:

Cảm ơn bạn đã đặt câu hỏi về phương thức xét tuyển của ngành Giáo dục Thể chất.

Dưới đây là thông tin về phương thức xét tuyển của ngành Giáo dục Thể chất:

| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu | Phương thức | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | 7140206 | Giáo dục Thể chất | 54 | 5,6 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT) |

Theo đó, ngành Giáo dục Thể chất sẽ xét tuyển theo phương thức 5 (Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2025 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn) và phương thức 6 (Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ GD&ĐT).

Tổ hợp môn xét tuyển cho ngành Giáo dục Thể chất bao gồm:

* (Toán, Sinh, NK TDTT)
* (Toán, Văn, NK TDTT)
* (Văn, Sinh, NK TDTT)
* (Toán, Lý, NK TDTT)
* (Văn, Giáo dục KT và PL, NK TDTT)

Hy vọng thông tin này sẽ giúp bạn hiểu rõ hơn về phương thức xét tuyển của ngành Giáo dục Thể chất.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `b5330052-1817-4f34-b318-62674fcc3813`.

RAG — HTTP 200, trạng thái answered, 3.95 giây:

Câu trả lời của Trợ lý AI chính thức của Trường Đại học Quy Nhơn:

Giáo dục Thể chất xét theo phương thức 5 (PT5 - mã 405) và phương thức 6 (PT6 - mã 301).

Cụ thể, phương thức 5 (PT5 - mã 405) xét tuyển theo kết quả thi tốt nghiệp THPT năm 2025 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

Phương thức 6 (PT6 - mã 301) xét tuyển thẳng theo Quy chế tuyển sinh của Bộ GD&ĐT.

Dưới đây là thông tin chi tiết về phương thức 5 (PT5 - mã 405) và phương thức 6 (PT6 - mã 301) xét tuyển vào ngành Giáo dục Thể chất:

| STT | Mã xét tuyển | Tên ngành xét tuyển | Phương thức | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- |
| 1 | 7140206 | Giáo dục Thể chất | 5 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT) |
| 2 | 7140206 | Giáo dục Thể chất | 6 | Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ GD&ĐT |

Lưu ý: Thông tin trên chỉ áp dụng cho ngành Giáo dục Thể chất và có thể có thay đổi trong quá trình tuyển sinh.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 16 Nếu em có điểm học bạ và điểm thi THPT thì nên dùng phương thức nào?

Nhóm: II. PHƯƠNG THỨC XÉT TUYỂN

Đáp án tham khảo trong DOCX:

Nếu ngành cho phép cả hai phương thức, em có thể sử dụng cả hai để tăng cơ hội xét tuyển.

DAG — HTTP 200, trạng thái insufficient_context, 4.84 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `df9cebd2-a80a-4b78-8b20-f5875a05dd4c`.

RAG — HTTP 200, trạng thái answered, 1.84 giây:

Nếu bạn có điểm học bạ và điểm thi THPT, bạn nên sử dụng điểm quy đổi VSTEP để xét tuyển. Theo bảng số liệu đã xác thực, điểm quy đổi VSTEP tương ứng với điểm 7.0 trở lên là **10**.

| | Điểm quy đổi VSTEP | Điểm quy đổi (IELTS) |
| --- | --- | --- |
| 7.0 trở lên | **10** |  |
| Mức điểm IELTS 5.0 |  | **8.0** |
| Mức điểm IELTS 5.5 |  | **9.0** |
| Mức điểm IELTS 6.0 |  | **10.0** |

Tuy nhiên, nếu bạn có điểm IELTS, bạn cũng có thể sử dụng điểm quy đổi IELTS để xét tuyển. Theo bảng số liệu đã xác thực, mức điểm IELTS 5.0 tương ứng với điểm quy đổi là **8.0**, mức điểm IELTS 5.5 tương ứng với điểm quy đổi là **9.0**, và mức điểm IELTS 6.0 tương ứng với điểm quy đổi là **10.0**.

### Câu 17 QNU xét học bạ mấy năm?

Nhóm: III. XÉT HỌC BẠ THPT

Đáp án tham khảo trong DOCX:

Năm 2026, phương thức học bạ sử dụng kết quả học tập của cả 3 năm THPT theo quy định hiện hành.

DAG — HTTP 200, trạng thái answered, 3.22 giây:

Trường Đại học Quy Nhơn xét học bạ các năm sau:

- Phương thức 2 (PT2 - mã 200): Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) theo quy định của Bộ Giáo dục và Đào tạo.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 1; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `15029852-197c-41c1-8cb8-4118100cde10`.

RAG — HTTP 200, trạng thái answered, 1.5 giây:

- QNU xét học bạ mấy năm?

Căn cứ vào thông tin tuyển sinh của Trường Đại học Quy Nhơn năm 2025, thí sinh xét tuyển theo kết quả học tập THPT (học bạ) của 3 năm.

- Danh sách các năm học được xét tuyển:

- 3 năm học THPT

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 1; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
### Câu 18 Học bạ được tính những lớp nào?

Nhóm: III. XÉT HỌC BẠ THPT

Đáp án tham khảo trong DOCX:

Sử dụng điểm trung bình cả năm lớp 10, lớp 11 và lớp 12 của các môn thuộc tổ hợp xét tuyển theo quy định.

DAG — HTTP 200, trạng thái insufficient_context, 4.44 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `7591e6f6-a5dd-4958-a163-9e8b1a39e855`.

RAG — HTTP 200, trạng thái answered, 1.81 giây:

Dựa trên thông tin được cung cấp, học bạ được tính ở các lớp sau:

| Lớp học | Giá trị dữ liệu |
| --- | --- |
| Giáo dục Mầm non | Học phí toàn khóa học (tạm tính): **83.074.000** |
| Giáo dục Mầm non | Mức học phí /tín chỉ (tạm tính): **554.000** |
| Giáo dục Tiểu học | Học phí toàn khóa học (tạm tính): **83.074.000** |

### Câu 19 Ngưỡng nguồn tối thiểu khi dùng học bạ là bao nhiêu?

Nhóm: III. XÉT HỌC BẠ THPT

Đáp án tham khảo trong DOCX:

Đối với thí sinh dự thi tốt nghiệp THPT từ năm 2026, Quy chế quy định tổng điểm 3 môn thi tốt nghiệp THPT theo tổ hợp xét tuyển hoặc Toán, Ngữ văn và một môn khác phải đạt tối thiểu 15/30, trừ các trường hợp được quy định ngoại lệ. Ngoài điều kiện nguồn này, từng ngành còn phải đạt ngưỡng đầu vào do Trường công bố.

DAG — HTTP 200, trạng thái insufficient_context, 1.84 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `09fcd9b2-32d7-4158-811f-76374d89e2f5`.

RAG — HTTP 200, trạng thái insufficient_context, 0.92 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 20 Điểm sàn học bạ của tất cả ngành có phải 15 không?

Nhóm: III. XÉT HỌC BẠ THPT

Đáp án tham khảo trong DOCX:

Không. Mốc 15/30 là điều kiện nguồn theo Quy chế đối với đối tượng áp dụng, không đồng nghĩa điểm sàn học bạ của mọi ngành đều là 15. Trường công bố ngưỡng đầu vào riêng theo từng ngành/phương thức.

DAG — HTTP 200, trạng thái insufficient_context, 5.95 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["Unsupported numbers detected: 7.0, 8.0, 9.0, 6.0, 10.0"], "unsupported_numbers": ["7.0", "8.0", "9.0", "6.0", "10.0"]}

Mã workflow: `0bddf586-15e2-4615-a085-bd996081ddfb`.

RAG — HTTP 200, trạng thái answered, 4.8 giây:

Dựa trên thông tin được cung cấp, điểm sàn học bạ của tất cả ngành không phải là 15.

Điểm sàn học bạ được quy định tại khoản 1 Điều 6 Quy chế tuyển sinh, điểm sàn học bạ là 18,00 điểm trở lên (trừ các ngành đào tạo giáo viên và ngành Luật thực hiện theo ngưỡng bảo đảm chất lượng đầu vào do Bộ Giáo dục và Đào tạo quy định).

Dưới đây là bảng thông tin về điểm sàn học bạ của một số ngành:

| STT | Mã xét tuyển | Tên ngành/CTĐT xét tuyển | Phương thức xét điểm thi TN. THPT | Phương thức xét kết quả học tập THPT | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM | Phương thức xét điểm thi ĐGNL ĐHSP HN | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 52 | 7760101 | Công tác xã hội | 15 | 18 | 600 | 15 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Sử, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Địa)<br>(Văn, Toán, Sử)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Giáo dục KT và PL, Anh)<br>(Văn, Địa, Giáo dục KT và PL) |
| 53 | 7810103 | Quản trị dịch vụ du lịch và lữ hành | 15 | 18 | 600 | 15 | (Toán, Văn, Giáo dục KT và PL)<br>(Toán, Văn, Anh)<br>(Toán, Văn, Sử)<br>(Toán, Văn, Địa)<br>(Toán, Văn, Hóa)<br>(Toán, Văn, Lý)<br>(Toán, Văn, Tin) |
| 54 | 7810201 | Quản trị khách sạn | 15 | 18 | 600 | 15 | (Toán, Văn, Giáo dục KT và PL)<br>(Toán, Văn, Anh)<br>(Toán, Văn, Sử)<br>(Toán, Văn, Địa)<br>(Toán, Văn, Hóa)<br>(Toán, Văn, Lý)<br>(Toán, Văn, Tin) |

Lưu ý rằng điểm sàn học bạ có thể thay đổi tùy thuộc vào từng trường hợp và yêu cầu cụ thể của từng ngành.

Nếu bạn muốn biết thêm thông tin về điểm sàn học bạ của một ngành cụ thể, vui lòng cho tôi biết mã xét tuyển hoặc tên ngành bạn muốn hỏi.

- Nguồn: TB điểm sàn 26 — trang 7; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: TB điểm sàn 26 — trang 6; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 12; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 12; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 21 Ngành sư phạm có xét học bạ không?

Nhóm: III. XÉT HỌC BẠ THPT

Đáp án tham khảo trong DOCX:

Không. QNU không sử dụng PT2 học bạ cho các ngành đào tạo giáo viên năm 2026.

DAG — HTTP 200, trạng thái answered, 6.61 giây:

Bạn đang hỏi về ngành Sư phạm có xét học bạ không? 

Theo thông tin mà mình đã tìm được, Trường Đại học Quy Nhơn có xét tuyển ngành Sư phạm theo học bạ. 

Cụ thể, theo bảng số liệu đã xác thực, ngành Sư phạm Toán học và Sư phạm Tin học đều có phương thức xét tuyển là 1, 4, 6 và tổ hợp môn xét tuyển bao gồm cả tổ hợp môn dựa trên học bạ.

Tuy nhiên, để biết thêm thông tin chính xác về phương thức xét tuyển và các yêu cầu cụ thể, bạn nên tham khảo trang web chính thức của Trường Đại học Quy Nhơn hoặc liên hệ trực tiếp với trường để được tư vấn cụ thể.

Mình hy vọng thông tin này sẽ giúp bạn!

- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `fde9bf17-af1b-4008-a4f7-1c6164293241`.

RAG — HTTP 200, trạng thái answered, 7.42 giây:

Câu trả lời của Trợ lý AI chính thức của Trường Đại học Quy Nhơn:

**Ngành Sư phạm có xét học bạ không?**

Câu trả lời dựa trên thông tin được trích xuất từ tài liệu chính thức:

- Trong Bảng Số Liệu được cung cấp, có thể thấy rằng các ngành Sư phạm đều có phương thức xét tuyển bằng học bạ.
- Cụ thể, các ngành Sư phạm như Sư phạm Toán học, Sư phạm Tin học, Sư phạm Vật lý, Sư phạm Sinh học, Sư phạm Ngữ văn, Sư phạm Lịch sử, Sư phạm Địa lý và Sư phạm Tiếng Anh đều có phương thức xét tuyển bằng học bạ.
- Điều này cho thấy rằng Trường Đại học Quy Nhơn đã công khai thông tin về phương thức xét tuyển cho các ngành Sư phạm, bao gồm cả xét tuyển bằng học bạ.

**Bảng thông tin về các ngành Sư phạm:**

| STT | Mã ngành | Tên ngành | 2023 - Chỉ tiêu | 2023 - Số trúng tuyển nhập học | 2023 - Điểm trúng tuyển (TNTHP T) | 2023 - Điểm trúng tuyển (Xét học bạ) | 2024 - Chỉ tiêu | 2024 - Số trúng tuyển nhập học | 2024 - Điểm trúng tuyển (TNT HPT) | 2024 - Điểm trúng tuyển (Xét học bạ) |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 7140209 | Sư phạm Toán học | 17 | 17 | 25.25 | 29.25 | 20 | 20 | 26.5 | 29.5 |
| 2 | 7140210 | Sư phạm Tin học | 63 | 62 | 19 | 21 | 100 | 106 | 22.85 | 23 |
| 3 | 7140211 | Sư phạm Vật lý | 18 | 18 | 23.5 | 28 | 20 | 19 | 25.75 | 28.5 |
| 4 | 7140213 | Sư phạm Sinh học | 17 | 16 | 20 | 26.5 | 20 | 21 | 23.9 | 28 |
| 5 | 7140217 | Sư phạm Ngữ văn | 20 | 20 | 25.25 | 28 | 30 | 32 | 27.35 | 28.5 |
| 6 | 7140218 | Sư phạm Lịch sử | 19 | 19 | 25.75 | 27 | 20 | 23 | 27.45 | 28.25 |
| 7 | 7140219 | Sư phạm Địa lý | 14 | 14 | 23.5 | 25.5 | 20 | 19 | 27.3 | 27.25 |
| 8 | 7140231 | Sư phạm Tiếng Anh | 80 | 80 | 24.75 | 28.5 | 84 | 87 | 25.92 | 28.75 |
| 9 | 7140247 | Sư phạm Khoa học tự nhiên | 164 | 164 | 19 | 21 | 20 | 17 | 25.65 | 28.5 |
| 10 | 7140249 | Sư phạm Lịch sử Địa lý | 80 | 79 | 24.25 | 23 | 27 | 32 | 27.15 | 27.25 |

**Lưu ý:**

- Thông tin trên chỉ áp dụng cho các ngành Sư phạm và không áp dụng cho các ngành khác.
- Trường Đại học Quy Nhơn có thể thay đổi phương thức xét tuyển cho các ngành Sư phạm mà không cần thông báo trước.

- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 22 Có cần đăng ký học bạ riêng trên hệ thống Trường không?

Nhóm: III. XÉT HỌC BẠ THPT

Đáp án tham khảo trong DOCX:

Tất cả thí sinh vẫn phải đăng ký nguyện vọng trên Hệ thống của Bộ trong thời gian quy định, không cần đăng kí trên cổng thông tin của Trường.

DAG — HTTP 200, trạng thái insufficient_context, 2.27 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `57c427a3-0155-48d9-9ec3-e30754231116`.

RAG — HTTP 200, trạng thái insufficient_context, 0.38 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 23 PT1 là gì?

Nhóm: IV. XÉT ĐIỂM THI TỐT NGHIỆP THPT

Đáp án tham khảo trong DOCX:

PT1, mã 100, là xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026.

DAG — HTTP 200, trạng thái answered, 6.3 giây:

- PT1 là Phương thức 1: Xét tuyển theo kết quả thi tốt nghiệp THPT.
- PT2 là Phương thức 2: Xét tuyển theo kết quả học tập THPT (học bạ).
- PT3 là Phương thức 3: Xét tuyển theo kết quả kỳ thi đánh giá năng lực của ĐHQG TP.HCM.
- PT4 là Phương thức 4: Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ GD&ĐT.
- PT5 là Phương thức 5: Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2025 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.
- PT6 là Phương thức 6: Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ GD&ĐT.

- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 1; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `26836842-852a-4c80-a04f-f86d09c148a8`.

RAG — HTTP 200, trạng thái answered, 1.88 giây:

- PT1 là phương thức tuyển sinh theo kết quả thi tốt nghiệp THPT.

- PT1 được sử dụng để xét tuyển vào các ngành đào tạo giáo viên theo quy định của Bộ Giáo dục và Đào tạo, và các ngành còn lại sẽ được xác định sau khi có kết quả thi tốt nghiệp THPT.

- PT1 được sử dụng trong trường hợp xét tuyển do Bộ Giáo dục và Đào tạo tổ chức, tham gia Nhóm lọc ảo Phía Nam.

- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 1; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
### Câu 24 Điểm thi THPT có được cộng ưu tiên khu vực, đối tượng không?

Nhóm: IV. XÉT ĐIỂM THI TỐT NGHIỆP THPT

Đáp án tham khảo trong DOCX:

Có, nếu thí sinh thuộc diện được hưởng ưu tiên và còn trong thời hạn hưởng ưu tiên theo Quy chế. Với tổng điểm từ 22,5/30 trở lên, điểm ưu tiên được giảm dần theo công thức của Bộ.

DAG — HTTP 200, trạng thái insufficient_context, 6.97 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["Unsupported numbers detected: 0,5, 1,5, 0,5, 1,5, 0,5, 1,5"], "unsupported_numbers": ["0,5", "1,5", "0,5", "1,5", "0,5", "1,5"]}

Mã workflow: `debe6216-194b-49a8-99b0-893217054cd6`.

RAG — HTTP 200, trạng thái answered, 3.45 giây:

Điểm thi THPT không được cộng ưu tiên khu vực, đối tượng.

Cụ thể, theo Quy chế tuyển sinh hiện hành, điểm xét tốt nghiệp THPT đã bao gồm cả điểm ưu tiên khu vực và ưu tiên đối tượng. Vì vậy, thí sinh không cần cộng thêm điểm ưu tiên khu vực, đối tượng vào điểm thi THPT.

Tuy nhiên, thí sinh cần khai báo và xác nhận thông tin để hưởng ưu tiên khu vực, đối tượng theo nơi thường trú trên Hệ thống đăng ký dự thi.

Dưới đây là thông tin chi tiết về quy trình khai báo và xác nhận thông tin để hưởng ưu tiên khu vực, đối tượng:

- Thí sinh cần đăng nhập vào Hệ thống tại địa chỉ: http://thisinh.thitotnghiepthpt.edu.vn theo tài khoản và mật khẩu đã được cấp.
- Thí sinh điền thông tin tại Mục 5: Nơi thường trú như sau:
 + Mã tỉnh/thành phố, mã huyện/quận và mã xã/phường chỉ đối với các xã/phường thuộc Khu vực 1 sẽ do Bộ GDĐT quy định.
 + Thí sinh cần tra cứu tại nơi đăng ký dự thi để ghi đúng mã tỉnh/thành phố, mã huyện/quận, mã xã/phường nơi thí sinh có nơi thường trú trong thời gian học THPT hoặc trung cấp.
 + Thí sinh không có nơi thường trú tại xã Khu vực 1 thì bỏ trống ô mã xã.
 + Sau khi điền đủ các mã đơn vị hành chính vào các ô, thí sinh ghi rõ tên xã/phường, huyện/quận, tỉnh/thành phố vào dòng trống.
- Thí sinh có nơi thường trú trên 18 tháng ở khu vực 1 (xã khó khăn hoặc xã đặc biệt khó khăn) trong thời gian học THPT hoặc trung cấp thì tích vào ô: "Nơi thường trú trên 18 tháng ở khu vực 1".
- Thí sinh có nơi thường trú trên 18 tháng ở xã đặc biệt khó khăn) trong thời gian học THPT hoặc trung cấp thì tích vào ô: "Nơi thường trú trên 18 tháng ở xã đặc biệt khó khăn".

Sau khi khai báo và xác nhận thông tin, thí sinh sẽ được hưởng ưu tiên khu vực, đối tượng theo quy định.

- Nguồn: phu-luc-hd-tuyen-sinh-2025.signed — trang 14; binding `bnd_0798d6ebb09d`, index `idx_rev_d64d0baf0c06`.
- Nguồn: phu-luc-hd-tuyen-sinh-2025.signed — trang 2; binding `bnd_0798d6ebb09d`, index `idx_rev_d64d0baf0c06`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 9; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: phu-luc-hd-tuyen-sinh-2025.signed — trang 2; binding `bnd_0798d6ebb09d`, index `idx_rev_d64d0baf0c06`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 1; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
### Câu 25 Năm 2026 môn tiếng Anh ở Ngôn ngữ Anh/Sư phạm Tiếng Anh có nhân hệ số 2 không?

Nhóm: IV. XÉT ĐIỂM THI TỐT NGHIỆP THPT

Đáp án tham khảo trong DOCX:

Trường không áp dụng cách nhân hệ số 2 môn Tiếng Anh.

DAG — HTTP 200, trạng thái answered, 4.81 giây:

Mình xin trả lời câu hỏi của bạn.

Môn tiếng Anh trong ngành Ngôn ngữ Anh/Sư phạm Tiếng Anh có nhân hệ số 2 không?

Câu trả lời là có. Trong bảng xét tuyển thẳng và ưu tiên xét tuyển, bạn có thể thấy rằng ngành Ngôn ngữ Anh (7220201) và ngành Sư phạm Tiếng Anh (7140231) đều có tổ hợp môn xét tuyển là (Toán, Văn, Anh) và (Toán, Văn, Anh) tương ứng.

Vậy, môn tiếng Anh trong ngành Ngôn ngữ Anh/Sư phạm Tiếng Anh có nhân hệ số 2.

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 13; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 13; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Cac nganh Tuyen sinh 2025_moi — trang 1; binding `bnd_bdb1f500cdbe`, index `idx_rev_742b1ff6d265`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 6; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `a6d76f31-c43d-4ecd-a578-117e2d96fc62`.

RAG — HTTP 200, trạng thái answered, 1.2 giây:

- (Toán, Tiếng Anh)

### Câu 26 Điểm chuẩn là tổng điểm 3 môn hay đã có ưu tiên?

Nhóm: IV. XÉT ĐIỂM THI TỐT NGHIỆP THPT

Đáp án tham khảo trong DOCX:

Điểm xét tuyển/điểm trúng tuyển được xác định theo quy định của từng phương thức và đã xử lý điểm ưu tiên, điểm cộng theo Quy chế. Khi so sánh điểm cá nhân với điểm chuẩn, cần tính đúng điểm xét tuyển của thí sinh.

DAG — HTTP 200, trạng thái answered, 8.05 giây:

Điểm chuẩn là tổng điểm 3 môn (trong tổ hợp xét tuyển) theo thang điểm 30 đối với từng môn (không nhân hệ số); trường hợp phương thức tuyển sinh sử dụng thang điểm khác thì mức điểm ưu tiên được quy đổi tương đương.

Dưới đây là danh sách các tổ hợp môn xét tuyển của Trường Đại học Quy Nhơn:

- Toán, Vật lý, Hóa học
- Toán, Vật lý, Tiếng Anh
- Toán, Hóa học, Tiếng Anh
- Ngữ văn, Lịch sử, Địa lý
- Ngữ văn, Địa lý, Giáo dục công dân
- Toán, Ngữ văn, Tiếng Anh
- Toán, Ngữ văn, Lịch sử
- Toán, Ngữ văn, Địa lý
- Ngữ văn, Toán, Tiếng Anh
- Ngữ văn, Toán, Lịch sử
- Ngữ văn, Toán, Địa lý
- Toán, Vật lý, Khoa học
- Toán, Vật lý, Tin học
- Toán, Vật lý, Công nghệ
- Toán, Hóa học, Vật lý
- Toán, Hóa học, Tin học
- Toán, Hóa học, Công nghệ
- Toán, Tiếng Anh, Vật lý
- Toán, Tiếng Anh, Hóa học
- Toán, Tiếng Anh, Tin học
- Toán, Tiếng Anh, Công nghệ
- Ngữ văn, Địa lý, Tiếng Anh
- Ngữ văn, Địa lý, Tin học
- Ngữ văn, Địa lý, Công nghệ
- Ngữ văn, Lịch sử, Giáo dục công dân
- Ngữ văn, Lịch sử, Tiếng Anh
- Ngữ văn, Lịch sử, Tin học
- Ngữ văn, Lịch sử, Công nghệ
- Ngữ văn, Tiếng Anh, Địa lý
- Ngữ văn, Tiếng Anh, Giáo dục công dân
- Ngữ văn, Tiếng Anh, Lịch sử
- Ngữ văn, Tiếng Anh, Tin học
- Ngữ văn, Tiếng Anh, Công nghệ
- Ngữ văn, Tin học, Địa lý
- Ngữ văn, Tin học, Giáo dục công dân
- Ngữ văn, Tin học, Lịch sử
- Ngữ văn, Tin học, Tiếng Anh
- Ngữ văn, Tin học, Công nghệ
- Ngữ văn, Công nghệ, Địa lý
- Ngữ văn, Công nghệ, Giáo dục công dân
- Ngữ văn, Công nghệ, Lịch sử
- Ngữ văn, Công nghệ, Tiếng Anh
- Ngữ văn, Công nghệ, Tin học
- Ngữ văn, Khoa học, Địa lý
- Ngữ văn, Khoa học, Giáo dục công dân
- Ngữ văn, Khoa học, Lịch sử
- Ngữ văn, Khoa học, Tiếng Anh
- Ngữ văn, Khoa học, Tin học
- Ngữ văn, Khoa học, Công nghệ
- Lịch sử, Địa lý, Giáo dục công dân
- Lịch sử, Địa lý, Tiếng Anh
- Lịch sử, Địa lý, Tin học
- Lịch sử, Địa lý, Công nghệ
- Lịch sử, Giáo dục công dân, Tiếng Anh
- Lịch sử, Giáo dục công dân, Tin học
- Lịch sử, Giáo dục công dân, Công nghệ
- Lịch sử, Tiếng Anh, Tin học
- Lịch sử, Tiếng Anh, Công nghệ
- Lịch sử, Tin học, Công nghệ
- Địa lý, Giáo dục công dân, Tiếng Anh
- Địa lý, Giáo dục công dân, Tin học
- Địa lý, Giáo dục công dân, Công nghệ
- Địa lý, Tiếng Anh, Tin học
- Địa lý, Tiếng Anh, Công nghệ
- Địa lý, Tin học, Công nghệ
- Giáo dục công dân, Tiếng Anh, Tin học
- Giáo dục công dân, Tiếng Anh, Công nghệ
- Giáo dục công dân, Tin học, Công nghệ
- Khoa học, Tiếng Anh, Tin học
- Khoa học, Tiếng Anh, Công nghệ
- Khoa học, Tin học, Công nghệ

Lưu ý rằng danh sách trên có thể thay đổi tùy thuộc vào từng phương thức tuyển sinh và tổ hợp môn xét tuyển.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 10; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 7; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 4; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `b43f61f3-dbea-4682-adbb-5c8b99405c14`.

RAG — HTTP 200, trạng thái answered, 2.52 giây:

Điểm chuẩn là tổng điểm 3 môn hay đã có ưu tiên?

Theo quy định tại Điều 4 của Quy chế tuyển sinh, điểm ưu tiên đối với thí sinh đạt tổng điểm từ 22,50 trở lên (khi quy đối về điểm theo thang 10 và theo thang tổng điểm 03 môn tối đa là 30) được làm tròn đến hàng phần trăm và xác định theo công thức sau:

Điểm ưu tiên = [(30 - Tổng điểm đạt được)/7,50] x Mức điểm ưu tiên quy định tại khoản 1, 2 Điều này

Tuy nhiên, không có thông tin cụ thể về mức điểm ưu tiên đối với từng tổ hợp môn xét tuyển trong quy định này.

Để biết thêm thông tin về tổ hợp môn xét tuyển và mức điểm ưu tiên, bạn có thể tham khảo thông tin chi tiết tại Phụ lục 1 của Quy chế tuyển sinh.

Dưới đây là một số tổ hợp môn xét tuyển tại Trường Đại học Quy Nhơn:

- Toán, Vật lý, Hóa học
- Toán, Vật lý, Tiếng Anh
- Ngữ văn, Lịch sử, Địa lý
- Ngữ văn, Địa lý, Giáo dục công dân
- Toán, Hóa học, Sinh học
- Toán, Vật lý, Sinh học
- Toán, Ngữ văn, Tiếng Anh
- Ngữ văn, Ngữ văn, Lịch sử
- Ngữ văn, Ngữ văn, Địa lý

Mức điểm ưu tiên đối với từng tổ hợp môn xét tuyển có thể được xác định theo công thức trên.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 10; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Phuong huong tuyen sinh 2024_DHQN_final — trang 1; binding `bnd_887623d8d318`, index `idx_rev_d39d623aef4e`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 7; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 4; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 27 QNU có xét điểm ĐGNL ĐHQG TP.HCM không?

Nhóm: V. ĐÁNH GIÁ NĂNG LỰC

Đáp án tham khảo trong DOCX:

Có. PT3 – mã 402A sử dụng kết quả kỳ thi ĐGNL của ĐHQG TP.HCM đối với các ngành được phép áp dụng; các ngành đào tạo giáo viên không xét phương thức này.

DAG — HTTP 200, trạng thái answered, 3.81 giây:

Trường Đại học Quy Nhơn (QNU) xét điểm Đánh giá năng lực ĐHQG TP.HCM không?

Câu trả lời của mình là **CÓ**. Theo thông tin trong tài liệu trích xuất, Trường Đại học Quy Nhơn xét tuyển theo kết quả Đánh giá năng lực của ĐHQG TP.HCM (trừ các ngành đào tạo giáo viên không xét tuyển PT3).

| Cột 1 | Cột 2 |
| --- | --- |
| Xét tuyển theo kết quả ĐGNL của ĐHQG TP.HCM | Trừ các ngành đào tạo giáo viên |

# GỢI Ý:

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `57e83d78-2b26-4ce8-a0d3-1d421a1b1191`.

RAG — HTTP 200, trạng thái insufficient_context, 7.66 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 28 QNU có xét điểm ĐGNL Trường ĐHSP Hà Nội không?

Nhóm: V. ĐÁNH GIÁ NĂNG LỰC

Đáp án tham khảo trong DOCX:

Có. PT4 – mã 402B sử dụng kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội theo ngành/tổ hợp được công bố.

DAG — HTTP 200, trạng thái answered, 4.83 giây:

Bạn đang tìm hiểu thông tin về phương thức xét tuyển của Trường Đại học Quy Nhơn (QNU). Câu trả lời của mình sẽ tập trung vào việc xác nhận liệu QNU có xét điểm Đánh giá năng lực (ĐGNL) của Trường Đại học Sư phạm Hà Nội hay không.

Căn cứ vào thông tin được cung cấp, mình thấy rằng QNU đã công bố thông tin về phương thức xét tuyển đại học chính quy năm 2026. Trong đó, có thể thấy rằng QNU đã quy định rõ ràng về các phương thức xét tuyển, bao gồm:

1. Xét tuyển dựa vào kết quả kỳ thi tốt nghiệp trung học phổ thông năm 2026 theo tổ hợp môn xét tuyển (THPT).
2. Xét tuyển dựa vào kết quả kỳ thi đánh giá năng lực của Đại học Quốc gia Thành phố Hồ Chí Minh (ĐNL).
3. Xét tuyển dựa vào kết quả học tập trung học phổ thông (HB), tính theo điểm trung bình các môn trong tổ hợp xét tuyển của cả năm lớp 10, 11 và 12.

Về việc xét điểm ĐGNL của Trường Đại học Sư phạm Hà Nội, mình không thấy có thông tin nào được đề cập trong tài liệu được cung cấp. Tuy nhiên, mình có thể kết luận rằng QNU có thể xét điểm ĐGNL của Trường Đại học Sư phạm Hà Nội, vì nó đã được đề cập trong thông tin về phương thức xét tuyển.

| Cột 1 | Cột 2 |
| --- | --- |
| QNU có xét điểm ĐGNL của Trường Đại học Sư phạm Hà Nội không? | Có |

Gợi ý: Bạn có muốn hỏi thêm thông tin về các phương thức xét tuyển của QNU không? Ví dụ như

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh thuc-signed — trang 1; binding `bnd_c6d3848722ab`, index `idx_rev_d7b434305a6c`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `20d6a557-2d24-48c4-8e64-cb3362811fd2`.

RAG — HTTP 200, trạng thái answered, 7.51 giây:

Xét tuyển theo kết quả kỳ thi đánh giá năng lực (ĐGNL) của Trường Đại học Sư phạm Hà Nội là phương thức xét tuyển của Trường Đại học Quy Nhơn.

| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu | Phương thức | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 3 | 7140204 | Giáo dục Chính trị | 43 | 1,4,6 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Toán, Văn, Anh)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Văn, Sử, Anh) |
| 4 | 7140206 | Giáo dục Thể chất | 54 | 5,6 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK<br>TDTT) |
| 5 | 7140211 | Sư phạm Toán học | 54 | 1,4,6 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Sử, Giáo dục KT và PL)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Sử, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Giáo dục KT và PL) |
| 6 | 7140212 | Sư phạm Vật lý | 49 | 1,4,6 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Sử, Giáo dục KT và PL)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Sử, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Giáo dục KT và PL) |
| 7 | 7140213 | Sư phạm Hóa học | 54 | 1,4,6 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Sử, Giáo dục KT và PL)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Sử, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Giáo dục KT và PL) |
| 8 | 7140214 | Sư phạm Sinh học | 54 | 1,4,6 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Sử, Giáo dục KT và PL)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Sử, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Giáo dục KT và PL) |
| 9 | 7140215 | Sư phạm Ngữ văn | 54 | 1,4,6 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Toán, Văn, Anh)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Văn, Sử, Anh) |
| 10 | 7140216 | Sư phạm Lịch sử | 49 | 1,4,6 | (Văn, Sử, Địa)<br>(Văn, Sử, Giáo dục KT và PL)<br>(Văn, Địa, Giáo dục KT và PL)<br>(Toán, Văn, Anh)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Toán, Anh, Giáo dục KT và PL)<br>(Văn, Sử, Anh) |
| 11 | 7140217 | Sư phạm Địa lý | 49 | 1,4,6 | (Toán, Lý, Hóa)<br>(Toán, Lý, Anh)<br>(Toán, Sử, Giáo dục KT và PL)<br>(Toán, Địa, Giáo dục KT và PL)<br>(Toán, Sử, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Giáo dục KT và PL) |
| 12 | 7140218 | Sư phạm Tiếng Anh | 54 | 1,4,6 | (Toán, Văn, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Toán, Tiếng Trung)<br>(Văn, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Giáo dục KT và PL) |
| 13 | 7140219 | Sư phạm tiếng Trung | 49 | 1,4,6 | (Toán, Văn, Anh)<br>(Văn, Toán, Anh)<br>(Văn, Toán, Giáo dục KT và PL)<br>(Văn, Toán, Tiếng Trung)<br>(Văn, Anh, Giáo dục KT và PL)<br>(Toán, Anh, Giáo dục KT và PL) |
| 14 | 7140220 | Sư

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
### Câu 29 Điểm ĐGNL có phải quy đổi sang thang 30 không?

Nhóm: V. ĐÁNH GIÁ NĂNG LỰC

Đáp án tham khảo trong DOCX:

Khi xét tuyển chung, Trường thực hiện quy tắc quy đổi tương đương ngưỡng đầu vào và điểm trúng tuyển giữa các phương thức theo thông báo chính thức. Không nên tự quy đổi bằng công thức không được Trường công bố.

DAG — HTTP 200, trạng thái answered, 2.99 giây:

Điểm Đánh giá năng lực có phải quy đổi sang thang 30 không?

Câu trả lời của mình là: Có, Điểm Đánh giá năng lực được quy đổi sang thang 30 điểm, trừ các ngành đào tạo giáo viên và ngành Luật thực hiện theo ngưỡng bảo đảm chất lượng đầu vào do Bộ Giáo dục và Đào tạo quy định.

- Nguồn: TB điểm sàn 26 — trang 8; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 4; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 10; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 7; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `a9228cfd-3484-473b-8442-322413c1025f`.

RAG — HTTP 200, trạng thái answered, 1.64 giây:

Câu trả lời của Trợ lý AI chính thức:

| **Thời gian áp dụng** | **Thể loại quy đổi** | **Giá trị dữ liệu** |
| --- | --- | --- |
| 2026 | Điểm ĐGNL quy đổi sang thang 30 | **Không có thông tin** |

Theo Bảng Số Liệu, không có thông tin về việc quy đổi điểm ĐGNL sang thang 30 trong năm 2026.

- Nguồn: TB lịch xét tuyển ĐH — trang 1; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
### Câu 30 Em có điểm SPT/ĐGNL ĐHSP Hà Nội thì làm gì?

Nhóm: V. ĐÁNH GIÁ NĂNG LỰC

Đáp án tham khảo trong DOCX:

Cần kiểm tra ngành có nhận PT4, bảo đảm kết quả thi được ghi nhận đúng trên hệ thống theo hướng dẫn của đơn vị tổ chức thi và của Trường, sau đó đăng ký nguyện vọng trên Hệ thống của Bộ trong thời gian quy định.

DAG — HTTP 200, trạng thái insufficient_context, 4.25 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `c6b3a12d-7960-400b-9dfa-dda3451954cb`.

RAG — HTTP 200, trạng thái answered, 1.45 giây:

Nếu bạn có điểm SPT/ĐGNL ĐHSP Hà Nội, bạn có thể tham khảo các thông tin sau:

- **Điểm quy đổi từ điểm SPT/ĐGNL ĐHSP Hà Nội:**

| | Điểm quy đổi |
| --- | --- |
| Điểm SPT/ĐGNL ĐHSP Hà Nội | **8.0** |

Lưu ý: Điểm quy đổi trên chỉ áp dụng cho điểm SPT/ĐGNL ĐHSP Hà Nội, không phải cho các loại điểm khác.

- **Lưu ý:** Để biết thông tin chi tiết và chính xác nhất về quy đổi điểm, bạn nên liên hệ trực tiếp với Trường Đại học Quy Nhơn (QNU) hoặc tham khảo trang web chính thức của trường.

### Câu 31 QNU có sử dụng IELTS/VSTEP trong xét tuyển không?

Nhóm: VI. CHỨNG CHỈ NGOẠI NGỮ IELTS/VSTEP

Đáp án tham khảo trong DOCX:

Có sử dụng chứng chỉ ngoại ngữ còn hiệu lực theo quy định và hướng dẫn công bố trong mùa tuyển sinh 2026, nhưng cách sử dụng phải tuân thủ Quy chế và bảng quy đổi chính thức.

DAG — HTTP 200, trạng thái insufficient_context, 1.09 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `3222dcb6-cdd5-4daa-9de1-00c392dc4d45`.

RAG — HTTP 200, trạng thái insufficient_context, 0.19 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 32 IELTS có thể thay điểm môn Tiếng Anh không?

Nhóm: VI. CHỨNG CHỈ NGOẠI NGỮ IELTS/VSTEP

Đáp án tham khảo trong DOCX:

Có. Chứng chỉ IELTS còn hiệu lực có thể được quy đổi thành điểm môn Tiếng Anh để thay thế điểm môn Tiếng Anh trong tổ hợp xét tuyển theo bảng quy đổi do Trường Đại học Quy Nhơn công bố. Tuy nhiên, điểm IELTS quy đổi không được dùng để thay thế điểm môn Tiếng Anh khi xác định điều kiện/ngưỡng đầu vào theo quy định. Thí sinh vẫn phải đáp ứng đầy đủ điều kiện về điểm thi tốt nghiệp THPT dùng để xác định ngưỡng đầu vào.

DAG — HTTP 200, trạng thái insufficient_context, 0.95 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `e7ff8590-5c31-4cbb-b9f5-6643519cd7b2`.

RAG — HTTP 200, trạng thái insufficient_context, 0.22 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 33 Em có IELTS thì có cần đăng ký nguyện vọng trên Cổng Bộ không?

Nhóm: VI. CHỨNG CHỈ NGOẠI NGỮ IELTS/VSTEP

Đáp án tham khảo trong DOCX:

Có. Chứng chỉ không thay thế việc đăng ký nguyện vọng xét tuyển đợt 1 trên Hệ thống của Bộ.

DAG — HTTP 200, trạng thái insufficient_context, 1.3 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `375f6fce-22be-4f5b-9520-08aedc0b3a3b`.

RAG — HTTP 200, trạng thái insufficient_context, 0.19 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 34 Ngành sư phạm có được đăng ký ở nguyện vọng 6 trở đi không?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Không. Theo Quy chế tuyển sinh 2026, các chương trình đào tạo giáo viên chỉ xét thí sinh đăng ký ở nguyện vọng từ 1 đến 5.

DAG — HTTP 200, trạng thái insufficient_context, 4.22 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `2d5ce3b1-a1d9-4824-8a1e-4ca29901b54e`.

RAG — HTTP 200, trạng thái answered, 1.5 giây:

Dựa trên bảng số liệu đã được xác thực, có thể kết luận như sau:

- Ngành Sư phạm Toán học có thể được đăng ký ở nguyện vọng 6 trở đi, vì phương thức xét tuyển của ngành này bao gồm cả nguyện vọng 6.

| **Ngành** | **Phương thức** |
| --- | --- |
| Sư phạm Toán học | 1, 4, 6 |
| Sư phạm Tin học | 1, 4, 6 |

### Câu 35 Nếu em để Sư phạm ở nguyện vọng 6 thì có được xét không?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Không được xét vào chương trình đào tạo giáo viên nếu nguyện vọng nằm ngoài vị trí 1–5.

DAG — HTTP 200, trạng thái insufficient_context, 2.55 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `83f159c7-a26b-4693-bd28-8b62ee9aeb8d`.

RAG — HTTP 200, trạng thái insufficient_context, 0.95 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 36 Sư phạm có xét học bạ không?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Không. Trường Đại học Quy Nhơn không xét PT2 học bạ đối với các ngành đào tạo giáo viên năm 2026.

DAG — HTTP 200, trạng thái answered, 6.62 giây:

- Sư phạm Toán học xét học bạ không?

Câu trả lời: 
- Sư phạm Toán học không xét học bạ.

- Sư phạm Tin học xét học bạ không?

Câu trả lời: 
- Sư phạm Tin học không xét học bạ.

- Sư phạm Vật lý xét học bạ không?

Câu trả lời: 
- Sư phạm Vật lý không xét học bạ.

- Sư phạm Sinh học xét học bạ không?

Câu trả lời: 
- Sư phạm Sinh học không xét học bạ.

- Sư phạm Ngữ văn xét học bạ không?

Câu trả lời: 
- Sư phạm Ngữ văn không xét học bạ.

- Sư phạm Lịch sử xét học bạ không?

Câu trả lời: 
- Sư phạm Lịch sử không xét học bạ.

- Sư phạm Địa lý xét học bạ không?

Câu trả lời: 
- Sư phạm Địa lý không xét học bạ.

- Sư phạm Tiếng Anh xét học bạ không?

Câu trả lời: 
- Sư phạm Tiếng Anh không xét học bạ.

- Sư phạm Khoa học tự nhiên xét học bạ không?

Câu trả lời: 
- Sư phạm Khoa học tự nhiên không xét học bạ.

- Sư phạm Lịch sử Địa lý xét học bạ không?

Câu trả lời: 
- Sư phạm Lịch sử Địa lý không xét học bạ.

- Sư phạm Toán học có xét học bạ không?

Câu trả lời: 

- Sư phạm Tin học có xét học bạ không?

Câu trả lời: 

- Sư phạm Vật lý có xét học bạ không?

Câu trả lời: 

- Sư phạm Sinh học có xét học bạ không?

Câu trả lời: 

- Sư phạm Ngữ văn có xét học bạ không?

Câu trả lời: 

- Sư phạm Lịch sử có xét học bạ không?

Câu trả lời: 

- Sư phạm Địa lý có xét học bạ không?

Câu trả lời: 

- Sư phạm Tiếng Anh có xét học bạ không?

Câu trả lời: 

- Sư phạm Khoa học tự nhiên có xét học bạ không?

Câu trả lời: 

- Sư phạm Lịch sử Địa lý có xét học bạ không?

Câu trả lời:

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `d3076e80-3893-4534-87f2-fac3cac03e6b`.

RAG — HTTP 200, trạng thái answered, 2.48 giây:

- Xét tuyển theo học bạ (học ba) các ngành ngoài sư phạm.

- Xét tuyển theo kết quả kỳ thi đánh giá năng lực của ĐHQG TP.HCM và của Trường Đại học Sư phạm Hà Nội.

- Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) theo quy định của Bộ Giáo dục và Đào tạo.

- Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026.

- Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

- Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
### Câu 37 Sư phạm có xét ĐGNL ĐHQG TP.HCM không?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Không. Các ngành đào tạo giáo viên không sử dụng PT3.

DAG — HTTP 200, trạng thái answered, 4.62 giây:

Bạn muốn hỏi về phương thức xét tuyển của Trường Đại học Quy Nhơn đối với ngành Sư phạm. Cụ thể, Trường Đại học Quy Nhơn xét tuyển theo phương thức nào cho ngành Sư phạm?

- Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026.
- Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) theo quy định của Bộ Giáo dục và Đào tạo. Các ngành đào tạo giáo viên không xét tuyển phương thức này.
- Xét kết quả kỳ thi đánh giá năng lực (ĐGNL) của ĐHQG TP.HCM. Các ngành đào tạo giáo viên không xét tuyển phương thức này.
- Xét kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội.
- Xét tuyển thẳng theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo.

Tùy thuộc vào điều kiện và nguyện vọng của bạn, bạn có thể lựa chọn phương thức xét tuyển phù hợp.

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB điểm sàn 26 — trang 2; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: TB điểm sàn 26 — trang 3; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `01b4deca-7c53-4f4f-bc1e-875df8704357`.

RAG — HTTP 200, trạng thái answered, 4.61 giây:

Sư phạm có xét ĐGNL ĐHQG TP.HCM không?

Câu trả lời được xác định dựa trên bảng số liệu đã được xác thực và tài liệu trích xuất.

| STT | Mã xét tuyển | Tên ngành/CTĐT xét tuyển | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM |
| :---: | :--- | :--- | :--- |
| 6 | 7140209 | Sư phạm Toán<br>học | – |
| 7 | 7140210 | Sư phạm Tin<br>học | – |
| 8 | 7140211 | Sư phạm Vật<br>lý | – |
| 9 | 7140212 | Sư phạm Hóa<br>học | – |
| 10 | 7140213 | Sư phạm Sinh<br>học | – |
| 11 | 7140217 | Sư phạm Ngữ<br>Văn | – |
| 12 | 7140218 | Sư phạm Lịch<br>sử | – |
| 13 | 7140219 | Sư phạm Địa<br>lý | – |
| 14 | 7140231 | Sư phạm<br>Tiếng Anh | – |
| 15 | 7140247 | Sư phạm Khoa<br>học tự nhiên | – |
| 17 | 7220201 | Ngôn ngữ Anh | 650 |
| 18 | 7220204 | Ngôn ngữ<br>Trung Quốc | 650 |
| 19 | 7229030 | Văn học | 600 |
| 20 | 7310101 | Kinh tế | 600 |
| 21 | 7310109 | Kinh tế số | 600 |
| 22 | 7310205 | Quản lý nhà<br>nước | 600 |
| 23 | 7310403 | Tâm lý học<br>giáo dục | 600 |
| 24 | 7310608 | Đông phương<br>học | 600 |
| 25 | 7140249 | Sư phạm Lịch<br>sử - Địa lý | – |

Từ bảng số liệu trên, có thể thấy rằng các ngành Sư phạm không xét tuyển theo phương thức xét điểm thi ĐGNL ĐHQG TP.HCM, trừ trường hợp Ngôn ngữ Anh và Ngôn ngữ Trung Quốc với điểm thi ĐGNL ĐHQG TP.HCM là 650 và 650 điểm tương ứng.

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: TB điểm sàn 26 — trang 2; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB điểm sàn 26 — trang 3; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 38 Điều kiện đầu vào các ngành sư phạm theo phương thức không sử dụng kết quả thi tốt nghiệp THPT để xét tuyển là gì?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Đối với phương thức xét kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội, thí sinh đăng ký vào các ngành đào tạo giáo viên phải có kết quả học tập lớp 12 xếp loại Tốt (Giỏi) và đồng thời tổng điểm 03 môn thi tốt nghiệp THPT theo tổ hợp xét tuyển đạt từ 18,00 điểm trở lên. Riêng ngành Giáo dục Thể chất, thí sinh phải có kết quả học tập lớp 12 từ Khá trở lên và tổng điểm 03 môn thi tốt nghiệp THPT đạt từ 16,50 điểm trở lên.

DAG — HTTP 200, trạng thái answered, 7.75 giây:

Cảm ơn bạn đã tin tưởng vào sự hỗ trợ của mình. Để trả lời câu hỏi của bạn, mình xin đưa ra thông tin về điều kiện đầu vào cho ngành Sư phạm theo phương thức không sử dụng kết quả thi tốt nghiệp THPT.

| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu | Phương thức | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 2 | 7140201 | Giáo dục Mầm non | 158 | 5,6 | (Toán, Văn, NK GDMN) |
| 3 | 7140202 | Giáo dục Tiểu học | 206 | 1,4,6 | (Toán, Lý, Hóa)<br>(Văn, Sử, Địa)<br>(Toán, Văn, Anh) |
| 5 | 7140206 | Giáo dục Thể chất | 54 | 5,6 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT) |

Để được xét tuyển vào ngành Sư phạm, bạn cần đáp ứng một trong các điều kiện sau:

- Kết quả trung bình chung học tập được đánh giá mức khá (học lực xếp loại từ khá trở lên) cả năm lớp 12 (kết quả học tập 02 học kỳ năm cuối cấp đối với đối tượng trung học nghề và tương đương) và tổng điểm 03 môn thi tốt nghiệp THPT đạt 16,50 điểm trở lên hoặc điểm xét tốt nghiệp THPT (trung học nghề) từ 6,50 trở lên đối với chương trình đào tạo Giáo dục Mầm non trình độ cao đẳng.
- Kết quả trung bình chung học tập được đánh giá mức tốt (học lực xếp loại từ tốt trở lên) cả năm lớp 12 (kết quả học tập 02 học kỳ năm cuối cấp đối với đối tượng trung học nghề và tương đương) và tổng điểm 03 môn thi tốt nghiệp THPT theo tổ hợp xét tuyển (hoặc sử dụng điểm thi môn Toán, Ngữ văn và một môn thi khác) đạt 20,00 điểm trở lên hoặc điểm xét tốt nghiệp THPT (điểm thi tốt nghiệp trung học nghề) từ 8,50 trở lên đối với các chương trình đào tạo Sư phạm.

Mình hy vọng thông tin này sẽ giúp bạn hiểu rõ hơn về điều kiện đầu vào cho ngành Sư phạm theo phương thức không sử dụng kết quả thi tốt nghiệp THPT.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 13; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: TB điểm sàn 26 — trang 8; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: TB điểm sàn 26 — trang 8; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 12; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `315f1aae-2410-4ff0-96f7-41c50a2dac13`.

RAG — HTTP 200, trạng thái answered, 2.0 giây:

**Điều kiện đầu vào các ngành sư phạm theo phương thức không sử dụng kết quả thi tốt nghiệp THPT**

| Điều kiện | Giá trị |
| --- | --- |
| Kết quả trung bình chung học tập cả năm lớp 12 | Mức khá trở lên |
| Tổng điểm 03 môn thi tốt nghiệp THPT | Đạt 16,50 điểm trở lên |
| Hoặc điểm xét tốt nghiệp THPT | Đạt từ 6,50 điểm trở lên đối với chương trình đào tạo Giáo dục thể chất, Sư phạm âm nhạc, Sư phạm mỹ thuật |

Lưu ý: Điều kiện trên chỉ áp dụng đối với các ngành đào tạo giáo viên và chương trình đào tạo thuộc lĩnh vực pháp luật.

- Nguồn: TB điểm sàn 26 — trang 8; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 13; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: TB điểm sàn 26 — trang 8; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 12; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
### Câu 39 Giáo dục Mầm non có thi năng khiếu không?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Có. Năm 2026 Trường tổ chức thi năng khiếu GDMN; thí sinh dùng điểm thi tốt nghiệp THPT kết hợp điểm năng khiếu theo PT5.

DAG — HTTP 200, trạng thái answered, 3.08 giây:

Giáo dục Mầm non không có thi năng khiếu.

- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thông tin TSĐH cập nhật — trang 11; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Cac nganh Tuyen sinh 2025_moi — trang 1; binding `bnd_bdb1f500cdbe`, index `idx_rev_742b1ff6d265`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `927866d0-c511-453d-ad86-1305b6b09eb3`.

RAG — HTTP 200, trạng thái answered, 2.62 giây:

Câu trả lời chính xác là: Có

Giáo dục Mầm non có thi năng khiếu trong quá trình xét tuyển.

Cụ thể, trong phương thức 5 (PT5 - mã 405), Trường Đại học Quy Nhơn xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

Ví dụ, trong bảng thông tin tuyển sinh năm 2026, ngành Giáo dục Mầm non có phương thức xét điểm thi TN. THPT là 20, phương thức xét kết quả học tập THPT là –, phương thức xét điểm thi ĐGNL ĐHQG TPHCM là –, phương thức xét điểm thi ĐGNL ĐHSP HN là 20 và tổ hợp môn xét tuyển là (Văn, Toán, NK GDMN) với tổng điểm 2 môn văn hóa + 2/3 điểm ƯT ≥ 13,34.

Vậy, Giáo dục Mầm non có thi năng khiếu trong quá trình xét tuyển.

- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thông tin TSĐH cập nhật — trang 11; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Cac nganh Tuyen sinh 2025_moi — trang 1; binding `bnd_bdb1f500cdbe`, index `idx_rev_742b1ff6d265`.
### Câu 40 Giáo dục Thể chất có thi năng khiếu không?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Có. Năm 2026 Trường tổ chức thi năng khiếu GDTC; thí sinh dùng điểm thi tốt nghiệp THPT kết hợp điểm năng khiếu theo PT5.

DAG — HTTP 200, trạng thái answered, 8.16 giây:

Câu trả lời của trợ lý ảo:

Giáo dục Thể chất có thi năng khiếu không?

Theo thông tin trên trang web của Trường Đại học Quy Nhơn, Giáo dục Thể chất có thi năng khiếu.

Cụ thể, tại mục "Tổ chức tuyển sinh" của thông tin tuyển sinh đại học năm 2026, có đoạn:

"b) Thi năng khiếu Giáo dục mầm non, Giáo dục thể chất: thi vào các ngày 19, 20, 21/6/2026. Thí sinh đăng ký thi năng khiếu tại https://tsd.qnu.edu.vn từ ngày 20/5/2026 đến 15/6/2026."

Như vậy, Giáo dục Thể chất là một trong những ngành có thi năng khiếu.

[Giáo dục Mầm non]: STT: 2 | Mã xét tuyển: 7140201 | Phương thức xét điểm thi TN. THPT: 20 | Phương thức xét kết quả học tập THPT: – | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM: – | Phương thức xét điểm thi ĐGNL ĐHSP HN: 20 | Tổ hợp môn xét tuyển: (Văn, Toán, NK GDMN)<br>Tổng điểm 2 môn văn hóa + 2/3 điểm ƯT ≥<br>13,34
[Giáo dục Thể chất]: STT: 5 | Mã xét tuyển: 7140206 | Phương thức xét điểm thi TN. THPT: 19 | Phương thức xét kết quả học tập THPT: – | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM: – | Phương thức xét điểm thi ĐGNL ĐHSP HN: 19 | Tổ hợp môn xét tuyển: (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT)<br>Tổng điểm 2 môn văn hóa + 2/3 điểm ƯT ≥<br>12,67

BẢNG MARKDOWN:

| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu | Phương thức | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 2 | 7140201 | Giáo dục Mầm non | 158 | 5,6 | (Toán, Văn, NK GDMN) |
| 4 | 7140206 | Giáo dục Thể chất | 54 | 5,6 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT) |

[Giấy tờ cần thiết]: Để đăng ký thi năng khiếu, thí sinh cần có giấy tờ cần thiết, bao gồm:

* Đăng ký thi năng khiếu tại trang web của Trường Đại học Quy Nhơn
* Chứng minh nhân dân hoặc thẻ căn cước công dân

[Thời gian thi]: Thi năng khiếu sẽ được tổ chức vào các ngày 19, 20, 21/6/2026.

[Địa điểm thi]: Thi năng khiếu sẽ được tổ chức tại Trường Đại học Quy Nhơn.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `4df980f1-0907-42dc-a8a2-6211d31ee3c8`.

RAG — HTTP 200, trạng thái answered, 5.92 giây:

Câu trả lời của người trợ lý: 

Trường Đại học Quy Nhơn thông báo Thông tin tuyển sinh đại học chính quy năm 2025 như sau:

I. THÔNG TIN CHUNG

1. Tên cơ sở đào tạo: Trường Đại học Quy Nhơn

2. Mã cơ sở đào tạo trong tuyển sinh: DQN

3. Địa chỉ: 170 An Dương Vương, TP. Quy Nhơn, tỉnh Bình Định

4. Địa chỉ trang thông tin điện tử: https://qnu.edu.vn

5. Số điện thoại liên hệ tuyển sinh: 1800.55.88.49

6. Địa chỉ công khai quy chế tuyển sinh: https://tuyensinh.qnu.edu.vn

7. Địa chỉ công khai các thông tin về hoạt động của cơ sở đào tạo (chương trình đào tạo; ngành đào tạo; đội ngũ giảng viên, cán bộ quản lý; cơ sở vật chất; quy mô đào tạo; tỷ lệ sinh viên có việc làm; kế hoạch tuyển sinh các ngành, hình thức, trình độ đào tạo ngành...):

https://qnu.edu.vn và https://tuyensinh.qnu.edu.vn

II. TUYỂN SINH ĐÀO TẠO ĐẠI HỌC CHÍNH QUY

1. Đối tượng, điều kiện dự tuyển: Đã tốt nghiệp THPT hoặc tương đương.

2. Phương thức tuyển sinh:

+ Phương thức 1 (PT1 - mã 100): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2025.

+ Phương thức 2 (PT2 - mã 200): Xét tuyển theo kết quả học tập THPT (học bạ), điểm trung bình cả năm lớp 12 các môn thuộc tổ hợp xét tuyển (các ngành đào tạo giáo viên không xét tuyển PT2).

3. Thông tin tuyển sinh năm 2025:

| STT | Mã xét tuyển | Tên ngành xét tuyển | Chỉ tiêu | Phương thức | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 4 | 7140206 | Giáo dục Thể chất | 54 | 5,6 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT)<br>(Văn, Địa, NK TDTT)<br>(Toán, Lý, NK TDTT)<br>(Văn, Giáo dục KT và PL, NK TDTT) |

Giáo dục Thể chất có thi năng khiếu không? 

Theo thông tin tuyển sinh năm 2025 của Trường Đại học Quy Nhơn, Giáo dục Thể chất có phương thức tuyển sinh là 5 và 6, trong đó phương thức 5 là xét tuyển theo kết quả thi tốt nghiệp THPT năm 2025 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.

Vậy, Giáo dục Thể chất có thi năng khiếu không? Câu trả lời là Có.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 2; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
### Câu 41 Giáo dục Thể chất có yêu cầu thể hình không?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Có. Thông tin tuyển sinh 2026 nêu thí sinh không bị dị tật cột sống, tay chân, mắt, phát âm và các dị tật khác; chiều cao tối thiểu nam 1,65 m, nặng 45 kg; nữ 1,55 m, nặng 40 kg.

DAG — HTTP 200, trạng thái answered, 5.08 giây:

Cảm ơn bạn đã đặt câu hỏi!

Giáo dục Thể chất không yêu cầu thể hình.

Dưới đây là thông tin chi tiết về ngành Giáo dục Thể chất:

| STT | Mã xét tuyển | Tên ngành/CTĐT xét tuyển | Phương thức xét điểm thi TN. THPT | Phương thức xét kết quả học tập THPT | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM | Phương thức xét điểm thi ĐGNL ĐHSP HN | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 5 | 7140206 | Giáo dục Thể chất | 19 | – | – | 19 | (Toán, Sinh, NK TDTT)<br>(Toán, Văn, NK TDTT)<br>(Văn, Sinh, NK TDTT), (Văn, Địa, NK TDTT); (Toán, Lý, NK TDTT); (Văn, Giáo dục KT và PL, NK TDTT) |

Giáo dục Thể chất là một ngành học quan trọng, giúp người học hiểu biết về các môn thể thao, cách huấn luyện và quản lý các hoạt động thể thao. Ngành này cũng giúp người học phát triển kỹ năng thể chất và tinh thần.

Nếu bạn có bất kỳ câu hỏi nào khác, vui lòng hỏi tôi!

- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: TB học phí K49 — trang 1; binding `bnd_4bd40bc6a972`, index `idx_rev_57e15196704d`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 11; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `da54307a-4539-4d6b-92e2-8e0cef85b04f`.

RAG — HTTP 200, trạng thái answered, 3.26 giây:

Giáo dục Thể chất có yêu cầu thể hình không?

| STT | Mã xét tuyển | Tên ngành/CTĐT xét tuyển | Phương thức xét điểm thi TN. THPT | Phương thức xét kết quả học tập THPT | Phương thức xét điểm thi ĐGNL ĐHQG TPHCM | Phương thức xét điểm thi ĐGNL ĐHSP HN | Tổ hợp môn xét tuyển |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 4 | 7140206 | Giáo dục thể chất | 19 | – | – | 19 | (Toán, Sinh, NK TDTT); (Toán, Văn, NK TDTT); (Văn, Sinh, NK TDTT); (Văn, Địa, NK TDTT); (Toán, Lý, NK TDTT); (Văn, Giáo dục KT và PL, NK TDTT) |

Giáo dục Thể chất có yêu cầu thể hình, vì trong tổ hợp môn xét tuyển có môn thể dục thể thao (TDTT).

- Nguồn: TB điểm sàn 26 — trang 1; binding `bnd_35c0b812a4fe`, index `idx_rev_ac9ec09ebb97`.
- Nguồn: TB học phí K49 — trang 1; binding `bnd_4bd40bc6a972`, index `idx_rev_57e15196704d`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 11; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
### Câu 42 Điểm sàn Giáo dục Mầm non năm 2026 là bao nhiêu?

Nhóm: VII. CÁC NGÀNH ĐÀO TẠO GIÁO VIÊN

Đáp án tham khảo trong DOCX:

Theo Thông báo 121/TB-HĐTS ngày 09/07/2026, ngưỡng theo phương thức điểm thi THPT của Giáo dục Mầm non là 20 điểm; đồng thời tổng điểm 2 môn văn hóa cộng 2/3 điểm ưu tiên phải đạt ít nhất 13,34.

DAG — HTTP 200, trạng thái answered, 4.95 giây:

Cảm ơn bạn đã tin tưởng và trao đổi với tôi. Tôi sẵn sàng giúp bạn giải đáp mọi câu hỏi liên quan đến thông tin tuyển sinh của Trường Đại học Quy Nhơn.

Về câu hỏi của bạn, điểm sàn Giáo dục Mầm non năm 2026 là 20.25 điểm.

- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 11; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB học phí K49 — trang 1; binding `bnd_4bd40bc6a972`, index `idx_rev_57e15196704d`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `2c92174d-bbd7-43de-8280-e26744648b04`.

RAG — HTTP 200, trạng thái answered, 2.78 giây:

Cảm ơn bạn đã cung cấp thông tin chi tiết về tuyển sinh của Trường Đại học Quy Nhơn năm 2026. Dựa trên thông tin được cung cấp, tôi không tìm thấy thông tin về điểm sàn Giáo dục Mầm non năm 2026. Tuy nhiên, tôi có thể cung cấp thông tin về các ngành đào tạo và phương thức tuyển sinh của Trường Đại học Quy Nhơn năm 2026.

Nếu bạn muốn biết thông tin chi tiết về các ngành đào tạo hoặc phương thức tuyển sinh, vui lòng cho tôi biết thông tin cụ thể bạn đang tìm kiếm.

- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 2; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 11; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB học phí K49 — trang 1; binding `bnd_4bd40bc6a972`, index `idx_rev_57e15196704d`.
### Câu 43 Khu vực 1 được cộng bao nhiêu điểm?

Nhóm: VIII. ĐIỂM ƯU TIÊN, ĐIỂM CỘNG

Đáp án tham khảo trong DOCX:

Mức ưu tiên khu vực theo thang 30: KV1 được 0,75 điểm.

DAG — HTTP 200, trạng thái insufficient_context, 3.81 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `15f43d7b-33a4-406f-83f2-6b41c07fdc88`.

RAG — HTTP 200, trạng thái answered, 1.86 giây:

- **Khu vực 1 được cộng bao nhiêu điểm?**

| Cột 1 | Cột 2 |
| --- | --- |
| **Khu vực 1** | **Điểm** |
| Các xã vùng đồng bào dân tộc thiểu số và miền núi, xã khu vực I, II, III; các xã có thôn vùng đồng bào dân tộc thiểu số và miền núi, thôn đặc biệt khó khăn; các xã/phường hải đảo/đặc khu; các xã/phường biên giới đất liền. | **10 điểm** |

### Câu 44 Khu vực 2 nông thôn được cộng bao nhiêu?

Nhóm: VIII. ĐIỂM ƯU TIÊN, ĐIỂM CỘNG

Đáp án tham khảo trong DOCX:

KV2-NT được 0,50 điểm.

DAG — HTTP 200, trạng thái answered, 3.59 giây:

Bạn hỏi về khu vực 2 nông thôn (KV2-NT) được cộng bao nhiêu điểm ưu tiên.

Theo quy định tại Điều 7 của Quy chế tuyển sinh, mức điểm ưu tiên áp dụng cho khu vực 2 nông thôn (KV2-NT) là 0,50 điểm.

Vậy, khu vực 2 nông thôn (KV2-NT) được cộng 0,50 điểm ưu tiên.

| Cột 1 | Cột 2 |
| --- | --- |
| Khu vực 2 nông thôn (KV2-NT) | 0,50 điểm |

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 9; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `d3ec26a9-2a47-411f-b298-e61743e0ebba`.

RAG — HTTP 200, trạng thái answered, 4.67 giây:

Để trả lời câu hỏi của người dùng, ta cần xem xét thông tin trong Bảng Số Liệu.

| Thực thể / Ngành | Thuộc tính | Giá trị dữ liệu |
| --- | --- | --- |
| Khu vực 1 (KV1) | Mô tả khu vực và điều kiện | **Các xã vùng đồng bào dân tộc thiểu số và miền núi, xã khu vực I, II, III; các xã có thôn vùng đồng bào dân tộc thiểu số và miền núi, thôn đặc biệt khó khăn; các xã/phường hải đảo/đặc khu; các xã/phường biên giới đất liền.** |
| Khu vực 2 nông thôn (KV2-NT) | Mô tả khu vực và điều kiện | **Các địa phương không thuộc KV1, KV2, KV3.** |
| Khu vực 2 (KV2) | Mô tả khu vực và điều kiện | **Các phường thuộc tỉnh; các xã của thành phố trực thuộc Trung ương (trừ các xã thuộc KV1).** |
| Khu vực 3 (KV3) | Mô tả khu vực và điều kiện | **Các phường của thành phố trực thuộc Trung ương.** |

Từ Bảng Số Liệu trên, ta có thể thấy:

- Khu vực 1 (KV1) là các xã vùng đồng bào dân tộc thiểu số và miền núi, xã khu vực I, II, III; các xã có thôn vùng đồng bào dân tộc thiểu số và miền núi, thôn đặc biệt khó khăn; các xã/phường hải đảo/đặc khu; các xã/phường biên giới đất liền.

- Khu vực 2 nông thôn (KV2-NT) là các địa phương không thuộc KV1, KV2, KV3.

Vì vậy, để tính tổng số của khu vực 2 nông thôn (KV2-NT), ta cần cộng số lượng các địa phương không thuộc KV1, KV2, KV3.

Tuy nhiên, thông tin này không được cung cấp trong Bảng Số Liệu.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 9; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 45 Khu vực 2 được cộng bao nhiêu?

Nhóm: VIII. ĐIỂM ƯU TIÊN, ĐIỂM CỘNG

Đáp án tham khảo trong DOCX:

KV2 được 0,25 điểm.

DAG — HTTP 200, trạng thái insufficient_context, 4.36 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `c4d7dcf4-2f7e-4d5c-b3bf-ba7bdcdb8b47`.

RAG — HTTP 200, trạng thái answered, 2.98 giây:

Để trả lời câu hỏi của người dùng, ta cần đối chiếu thông tin trong bảng số liệu.

| Thực thể / Ngành | Thuộc tính | Giá trị dữ liệu |
| --- | --- | --- |
| Khu vực 1 (KV1) | Mô tả khu vực và điều kiện | **Các xã vùng đồng bào dân tộc thiểu số và miền núi, xã khu vực I, II, III; các xã có thôn vùng đồng bào dân tộc thiểu số và miền núi, thôn đặc biệt khó khăn; các xã/phường hải đảo/đặc khu; các xã/phường biên giới đất liền.** |
| Khu vực 2 nông thôn (KV2-NT) | Mô tả khu vực và điều kiện | **Các địa phương không thuộc KV1, KV2, KV3.** |
| Khu vực 2 (KV2) | Mô tả khu vực và điều kiện | **Các phường thuộc tỉnh; các xã của thành phố trực thuộc Trung ương (trừ các xã thuộc KV1).** |
| Khu vực 3 (KV3) | Mô tả khu vực và điều kiện | **Các phường của thành phố trực thuộc Trung ương.** |

Từ thông tin trong bảng số liệu, ta thấy rằng "Khu vực 2 (KV2)" được mô tả là "Các phường thuộc tỉnh; các xã của thành phố trực thuộc Trung ương (trừ các xã thuộc KV1)".

Vậy, Khu vực 2 được cộng bao nhiêu? Câu trả lời chính xác là không có thông tin về số lượng cụ thể trong bảng số liệu này.

### Câu 46 Khu vực 3 có được cộng điểm không?

Nhóm: VIII. ĐIỂM ƯU TIÊN, ĐIỂM CỘNG

Đáp án tham khảo trong DOCX:

KV3 không có điểm ưu tiên khu vực.

DAG — HTTP 200, trạng thái answered, 5.33 giây:

Mình có thể trả lời câu hỏi của bạn như sau:

| Cột 1 | Cột 2 |
| --- | --- |
| Khu vực | Được cộng điểm ưu tiên không |
| Khu vực 3 (KV3) | Không được cộng điểm ưu tiên |

Cụ thể, theo Điều 7 của Quy chế tuyển sinh, khu vực 3 (KV3) không được tính điểm ưu tiên.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 9; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `88a37a27-90a9-45dd-a071-205f0df623a2`.

RAG — HTTP 200, trạng thái answered, 1.3 giây:

Khu vực 3 có được cộng điểm ưu tiên không?

| Khu vực | Điểm ưu tiên |
| --- | --- |
| KV1 | 0,75 điểm |
| KV2-NT | 0,50 điểm |
| KV2 | 0,25 điểm |
| KV3 | **Không được tính điểm ưu tiên** |

Theo quy định tại Điều 7 của Quy chế tuyển sinh, khu vực 3 (KV3) không được tính điểm ưu tiên.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 9; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 47 Ưu tiên đối tượng UT1 và UT2 là bao nhiêu?

Nhóm: VIII. ĐIỂM ƯU TIÊN, ĐIỂM CỘNG

Đáp án tham khảo trong DOCX:

Theo thang 30, nhóm UT1 được 2,0 điểm và nhóm UT2 được 1,0 điểm trước khi áp dụng công thức giảm điểm ưu tiên đối với thí sinh có tổng điểm từ 22,5 trở lên.

DAG — HTTP 200, trạng thái answered, 2.98 giây:

- Đối tượng UT1 được ưu tiên là 2,00 điểm.
- Đối tượng UT2 được ưu tiên là 1,00 điểm.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 9; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `31de9e69-22ac-4fff-aaf1-dc11f9ae58c0`.

RAG — HTTP 200, trạng thái answered, 0.97 giây:

- Đối tượng UT1 được ưu tiên 2,00 điểm.
- Đối tượng UT2 được ưu tiên 1,00 điểm.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 9; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 48 Điểm cao có được cộng đủ điểm ưu tiên không?

Nhóm: VIII. ĐIỂM ƯU TIÊN, ĐIỂM CỘNG

Đáp án tham khảo trong DOCX:

Không phải lúc nào cũng cộng đủ. Nếu tổng điểm đạt từ 22,5/30 trở lên, điểm ưu tiên được xác định theo công thức: [(30 - tổng điểm đạt được) / 7,5] × mức điểm ưu tiên.

DAG — HTTP 200, trạng thái answered, 3.69 giây:

Điểm cao có được cộng đủ điểm ưu tiên không?

Câu trả lời của mình là có, nhưng có một số điều kiện cần lưu ý.

| Điều kiện | Giải thích |
| --- | --- |
| Điểm cao | Điểm cao có thể được cộng đủ điểm ưu tiên, nhưng chỉ nếu thí sinh đáp ứng được các điều kiện cụ thể. |
| Đáp ứng điều kiện | Thí sinh phải đáp ứng được các điều kiện cụ thể để được hưởng điểm ưu tiên, bao gồm: thường trú trên 18 tháng ở khu vực 1 hoặc thường trú trên 18 tháng ở xã đặc biệt khó khăn trong thời gian học THPT hoặc trung cấp. |
| Điểm ưu tiên | Điểm ưu tiên được quy định tại Điều 7 của Quy chế tuyển sinh, bao gồm mức điểm ưu tiên cho các đối tượng chính sách khác được quy định trong các văn bản pháp luật hiện hành. |

Tóm lại, điểm cao có thể được cộng đủ điểm ưu tiên nếu thí sinh đáp ứng được các điều kiện cụ thể.

### Gợi ý câu hỏi tiếp theo:

*

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 19; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 10; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 11; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 5; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: phu-luc-hd-tuyen-sinh-2025.signed — trang 2; binding `bnd_0798d6ebb09d`, index `idx_rev_d64d0baf0c06`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `278ceb23-0e07-4187-a5d6-9c2b688fa099`.

RAG — HTTP 200, trạng thái insufficient_context, 2.34 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 49 Tổng điểm cộng có bị giới hạn không?

Nhóm: VIII. ĐIỂM ƯU TIÊN, ĐIỂM CỘNG

Đáp án tham khảo trong DOCX:

Có. Tổng điểm cộng/điểm thưởng theo quy định không vượt quá 10% mức điểm tối đa của thang điểm xét; tổng điểm xét sau ưu tiên, điểm cộng không vượt quá mức tối đa của thang điểm.

DAG — HTTP 200, trạng thái insufficient_context, 3.36 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["Unsupported numbers detected: 0,1"], "unsupported_numbers": ["0,1"]}

Mã workflow: `d097a603-04cb-4a81-8348-fae8012975c3`.

RAG — HTTP 200, trạng thái answered, 1.73 giây:

Câu trả lời của người trợ lý:

| Tính chất | Giới hạn | Giá trị dữ liệu |
| --- | --- | --- |
| Tổng điểm cộng | Giới hạn | **10% điểm tối đa của thang điểm xét tuyển** |
| Tổng điểm cộng | Giới hạn | **Không vượt quá 10% điểm tối đa của thang điểm xét tuyển** |
| Tổng điểm cộng | Giới hạn | **Bao gồm điểm thương, điểm xét thương, điểm khuyến khích** |
| Điểm xét | Giới hạn | **Không vượt quá mức điểm 30 điểm** |

Lưu ý: Tổng điểm cộng bao gồm điểm thương, điểm xét thương, điểm khuyến khích không vượt quá 10% điểm tối đa của thang điểm xét tuyển.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 7; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 50 Năm 2026 được đăng ký tối đa bao nhiêu nguyện vọng?

Nhóm: IX. ĐĂNG KÝ NGUYỆN VỌNG TRÊN HỆ THỐNG BỘ GD&ĐT

Đáp án tham khảo trong DOCX:

Theo kế hoạch tuyển sinh 2026 đã triển khai, thí sinh đăng ký tối đa 15 nguyện vọng.

DAG — HTTP 200, trạng thái answered, 3.72 giây:

- Thí sinh được đăng ký tối đa 15 nguyện vọng vào các chương trình đào tạo, các cơ sở giáo dục đại học khác nhau.
- Trong trường hợp nhiều nguyện vọng đủ điều kiện trúng tuyển, thí sinh chỉ được công nhận trúng tuyển và gọi nhập học theo nguyện vọng cao nhất.
- Các chương trình đào tạo giáo viên chỉ xét tuyển thí sinh đăng ký ở các nguyên vọng có thứ tự từ 01 đến 05.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `9d37431d-ae3d-40ff-8e86-71bfa97f5e4b`.

RAG — HTTP 200, trạng thái answered, 1.52 giây:

- Thí sinh được đăng ký tối đa 15 nguyện vọng vào các chương trình đào tạo, các cơ sở giáo dục đại học khác nhau.
- Trong trường hợp nhiều nguyện vọng đủ điều kiện trúng tuyển, thí sinh chỉ được công nhận trúng tuyển và gọi nhập học theo nguyện vọng cao nhất.
- Các chương trình đào tạo giáo viên chỉ xét tuyển thí sinh đăng ký ở các nguyện vọng có thứ tự từ 01 đến 05.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 51 Thời gian đăng ký nguyện vọng năm 2026 là khi nào?

Nhóm: IX. ĐĂNG KÝ NGUYỆN VỌNG TRÊN HỆ THỐNG BỘ GD&ĐT

Đáp án tham khảo trong DOCX:

Từ ngày 02/07/2026 đến 17 giờ 00 ngày 14/07/2026 theo kế hoạch triển khai đã sử dụng trong mùa tuyển sinh 2026.

DAG — HTTP 200, trạng thái answered, 4.5 giây:

Theo kế hoạch tuyển sinh của Trường Đại học Quy Nhơn, thời gian đăng ký nguyện vọng năm 2026 như sau:

- **Đợt 1:** Xét tuyển theo kế hoạch của Bộ GDĐT: 04/8/2026 – 10/8/2026.
- **Đợt 2:** Xét tuyển các ngành còn chỉ tiêu sau khi thí sinh đăng ký nhập học đợt 1, thông báo từ ngày 22/8/2026.
- **Đăng ký nguyện vọng và nộp lệ phí xét tuyển trực tuyến trên Hệ thống:**
 + Từ ngày 16/7 đến 17 giờ 00 ngày 28/7/2026, thí sinh đăng ký, điều chỉnh, bổ sung nguyện vọng xét tuyển không giới hạn số lần.
 + Thí sinh sử dụng tài khoản đã được cấp để xử lý thông tin (nhập, sửa, xem) thông tin của thí sinh trên Hệ thống.

Lưu ý: Các mốc thời gian trên được triển khai theo Kế hoạch chung của Bộ GDĐT; trường hợp Bộ GDĐT có điều chỉnh lịch chính thức, các đơn vị cập nhật và thực hiện theo thông báo mới nhất.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: TB lịch xét tuyển ĐH — trang 2; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: TB lịch xét tuyển ĐH — trang 3; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `1400d647-dd0e-40dd-8c12-910f78e51811`.

RAG — HTTP 200, trạng thái answered, 2.78 giây:

Câu trả lời chính xác dựa trên tài liệu được cung cấp:

- **Đợt 1:**

 + Xét tuyển theo kế hoạch của Bộ GDĐT: 04/8/2026 – 10/8/2026.
 + Đợt 2: Xét tuyển các ngành còn chỉ tiêu sau khi thí sinh đăng ký nhập học đợt 1, thông báo từ ngày 22/8/2026.

- **Đăng ký nguyện vọng:**

 + Thí sinh đăng ký, điều chỉnh, bổ sung nguyện vọng không giới hạn số lần từ ngày 29/7 đến 17 giờ 00 ngày 30/7/2026.

- **Thời gian công bố kết quả điểm trúng tuyển và danh sách thí sinh trúng tuyển đợt 1:**

 + Trước 17 giờ 00 ngày 13/8/2026.

- **Thời gian mở cổng xác nhận nhập học trực tuyến:**

 + Mở cổng xác nhận nhập học trực tuyến trên Hệ thống cho thí sinh trúng tuyển đợt 1 (kể cả thí sinh trúng tuyển thẳng có nguyện vọng theo học) sau khi công bố kết quả điểm trúng tuyển và danh sách thí sinh trúng tuyển đợt 1.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: TB lịch xét tuyển ĐH — trang 2; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: TB lịch xét tuyển ĐH — trang 3; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 52 Nếu chỉ đăng ký trên website QNU mà không đăng ký trên Cổng Bộ thì có được xét đợt 1 không?

Nhóm: IX. ĐĂNG KÝ NGUYỆN VỌNG TRÊN HỆ THỐNG BỘ GD&ĐT

Đáp án tham khảo trong DOCX:

Không. Để được xét tuyển đợt 1, thí sinh phải đăng ký nguyện vọng trên Hệ thống hỗ trợ tuyển sinh chung của Bộ GD&ĐT trong thời gian quy định.

DAG — HTTP 200, trạng thái answered, 3.75 giây:

- Đăng ký xét tuyển trên website QNU mà không đăng ký trên Cổng Bộ thì không được xét đợt 1.

- Tất cả thí sinh, tất cả các phương thức phải đăng ký xét tuyển trên hệ thống của Bộ từ ngày 16/7/2025 đến ngày 28/7/2025.

[Giới thiệu]: 
- Gợi ý câu hỏi liên quan:

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `d9e70a5b-7d53-4ba0-9098-fb43c4822366`.

RAG — HTTP 200, trạng thái answered, 2.95 giây:

Đề nghị người dùng xem xét lại câu hỏi của mình. Câu hỏi của người dùng liên quan đến việc đăng ký xét tuyển trên website QNU và đăng ký trên Cổng Bộ, nhưng không rõ ràng về thông tin năm tuyển sinh.

Trong tài liệu trích xuất, có hai đoạn trích liên quan đến đợt 1 và đợt 2 của năm tuyển sinh 2026. 

Đợt 1 của năm tuyển sinh 2026:

- Thí sinh đăng ký thông tin xét tuyển và nộp hồ sơ xét tuyển thẳng, ưu tiên xét tuyển, chứng chỉ IELTS từ ngày 20/5/2026 đến ngày 20/6/2026.
- Thí sinh trúng tuyển thẳng vào Trường phải đăng ký nguyện vọng trên Hệ thống của Bộ GDĐT và xác nhận nhập học theo kế hoạch chung.

Đợt 1 của năm tuyển sinh 2025:

- Thí sinh đăng ký thông tin xét tuyển, nộp hồ sơ xét tuyển thẳng, ưu tiên xét tuyển, chứng chỉ IELTS từ ngày 01/6/2025 đến ngày 30/6/2025.
- Tất cả thí sinh, tất cả các phương thức phải đăng ký xét tuyển trên hệ thống của Bộ từ ngày 16/7/2025 đến ngày 28/7/2025.

Để trả lời câu hỏi của người dùng một cách chính xác, đề nghị người dùng cung cấp thông tin cụ thể về năm tuyển sinh mà họ đang hỏi.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 53 Nếu đỗ nhiều nguyện vọng thì em được công nhận nguyện vọng nào?

Nhóm: IX. ĐĂNG KÝ NGUYỆN VỌNG TRÊN HỆ THỐNG BỘ GD&ĐT

Đáp án tham khảo trong DOCX:

Hệ thống chỉ công nhận thí sinh trúng tuyển ở nguyện vọng có thứ tự ưu tiên cao nhất trong số các nguyện vọng mà thí sinh đủ điều kiện trúng tuyển.

DAG — HTTP 200, trạng thái answered, 2.61 giây:

- Thí sinh chỉ được công nhận trúng tuyển và gọi nhập học theo nguyện vọng cao nhất trong trường hợp nhiều nguyện vọng đủ điều kiện trúng tuyển.
- Nếu thí sinh đăng ký xét tuyển vào các chương trình đào tạo giáo viên, chỉ xét tuyển thí sinh đăng ký ở các nguyện vọng có thứ tự từ 01 đến 05.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `5225074f-46fc-4a04-a9e2-7ef0056a4958`.

RAG — HTTP 200, trạng thái answered, 1.34 giây:

- Nếu đỗ nhiều nguyện vọng, thí sinh chỉ được công nhận trúng tuyển và gọi nhập học theo nguyện vọng cao nhất.
- Trong trường hợp các chương trình đào tạo giáo viên, thí sinh chỉ được xét tuyển ở các nguyện vọng có thứ tự từ 01 đến 05.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 54 Có thể đổi thứ tự nguyện vọng trong thời gian đăng ký không?

Nhóm: IX. ĐĂNG KÝ NGUYỆN VỌNG TRÊN HỆ THỐNG BỘ GD&ĐT

Đáp án tham khảo trong DOCX:

Trong thời gian Hệ thống cho phép điều chỉnh, thí sinh có thể sắp xếp, bổ sung hoặc điều chỉnh nguyện vọng theo hướng dẫn của Bộ; sau thời hạn đóng hệ thống thì không thể tự thay đổi.

DAG — HTTP 200, trạng thái insufficient_context, 4.97 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `198d8d19-b738-475c-b030-2a48792a9f18`.

RAG — HTTP 200, trạng thái answered, 1.58 giây:

Có thể đổi thứ tự nguyện vọng trong thời gian đăng ký không?

**Đáp án:** Có

**Giải thích:** Thông tin được trích xuất từ Bảng Số Liệu trên cho thấy các phương thức đăng ký tuyển sinh của Trường Đại học Quy Nhơn (QNU) bao gồm các số thứ tự từ 1 đến 6. Điều này cho phép thí sinh tự do sắp xếp và đổi thứ tự nguyện vọng của mình trong quá trình đăng ký tuyển sinh.

**Lưu ý:** Trình tự nguyện vọng của thí sinh có thể được thay đổi trong thời gian đăng ký tuyển sinh, nhưng cần đảm bảo rằng các nguyện vọng vẫn nằm trong phạm vi các phương thức được quy định bởi Trường Đại học Quy Nhơn (QNU).

### Câu 55 Lệ phí đăng ký nguyện vọng năm 2026 nộp khi nào?

Nhóm: X. LỆ PHÍ XÉT TUYỂN VÀ THI NĂNG KHIẾU

Đáp án tham khảo trong DOCX:

Theo lịch triển khai 2026 đã sử dụng trong tư vấn, thời gian nộp lệ phí xét tuyển trực tuyến là từ 15/07/2026 đến 17 giờ 00 ngày 21/07/2026.

DAG — HTTP 200, trạng thái answered, 3.72 giây:

Lệ phí đăng ký nguyện vọng năm 2026 sẽ được nộp khi thí sinh đăng ký nguyện vọng trực tuyến trên Hệ thống từ ngày 16/7 đến 17 giờ 00 ngày 28/7/2026.

| TT | Các mốc thời gian | Nội dung | Chủ trì thực hiện | Phối hợp thực hiện |
| :---: | :--- | :--- | :--- | :--- |
| 7. |  | Hỗ trợ thí sinh ĐKXT trực tuyến; cử cán<br>bộ hỗ trợ, tư vấn (không giữ tài khoản,<br>không làm thay thí sinh). Nhắc nhở và hỗ<br>trợ thí sinh nộp lệ phí xét tuyển trực<br>tuyến theo hướng dẫn của Bộ GDĐT |  |  |

Cụ thể, thí sinh sẽ nộp lệ phí xét tuyển trực tuyến trên Hệ thống từ ngày 16/7 đến 17 giờ 00 ngày 28/7/2026.

- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: TB lịch xét tuyển ĐH — trang 2; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `f5b2c3dc-d73e-436b-8945-ad56675da3d3`.

RAG — HTTP 200, trạng thái answered, 1.69 giây:

Căn cứ vào tài liệu và số liệu được cung cấp, bạn có thể trả lời câu hỏi của người dùng như sau:

Lệ phí đăng ký nguyện vọng năm 2026 nộp khi nào?

Theo thông tin được cung cấp trong tài liệu, thí sinh phải nộp lệ phí xét tuyển theo số lượng NVXT bằng hình thức trực tuyến trên Hệ thống. Tuy nhiên, tài liệu không cung cấp thông tin cụ thể về thời gian nộp lệ phí.

Tuy nhiên, căn cứ vào các mốc thời gian được cung cấp trong tài liệu, có thể thấy rằng thí sinh sẽ nộp lệ phí xét tuyển trực tuyến từ ngày 16/7 đến 17 giờ 00 ngày 28/7/2025.

Tuy nhiên, không có thông tin cụ thể về thời gian nộp lệ phí xét tuyển năm 2026.

- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: TB lịch xét tuyển ĐH — trang 2; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
### Câu 56 Lệ phí thi năng khiếu GDMN/GDTC là bao nhiêu?

Nhóm: X. LỆ PHÍ XÉT TUYỂN VÀ THI NĂNG KHIẾU

Đáp án tham khảo trong DOCX:

Thông báo tuyển sinh đầu mùa 2026 của Trường công bố lệ phí thi năng khiếu Giáo dục Mầm non, Giáo dục Thể chất là 300.000 đồng/thí sinh.

DAG — HTTP 200, trạng thái answered, 3.27 giây:

Lệ phí thi năng khiếu Giáo dục Mầm non/Giáo dục Thể chất là 300.000 đồng/thí sinh.

- Nguồn: TB học phí K49 — trang 1; binding `bnd_4bd40bc6a972`, index `idx_rev_57e15196704d`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Muc hoc phi 2024 — trang 1; binding `bnd_18c9c944ee36`, index `idx_rev_2b7b7ec56f95`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 10; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 11; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `0107325e-0649-42b4-a9f1-5fed40f291c9`.

RAG — HTTP 200, trạng thái insufficient_context, 2.3 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 57 Không nộp lệ phí xét tuyển có ảnh hưởng không?

Nhóm: X. LỆ PHÍ XÉT TUYỂN VÀ THI NĂNG KHIẾU

Đáp án tham khảo trong DOCX:

Có. Thí sinh phải hoàn thành nghĩa vụ lệ phí theo hướng dẫn và thời gian quy định để nguyện vọng được xử lý theo kế hoạch tuyển sinh.

DAG — HTTP 200, trạng thái insufficient_context, 3.39 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `50abc9e7-5ec0-48e8-81bd-389155312588`.

RAG — HTTP 200, trạng thái insufficient_context, 2.19 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 58 Năm 2026 thi năng khiếu QNU vào ngày nào?

Nhóm: XI. THI NĂNG KHIẾU

Đáp án tham khảo trong DOCX:

Kế hoạch đầu mùa của Trường tổ chức thi năng khiếu GDMN/GDTC vào các ngày 19, 20 và 21/06/2026.

DAG — HTTP 200, trạng thái answered, 3.58 giây:

Bạn muốn biết năm 2026 thi năng khiếu QNU vào ngày nào?

Theo thông tin được cung cấp, đợt 1:

- Thí sinh nộp hồ sơ xét tuyển thẳng, ưu tiên xét tuyển từ ngày 20/5/2026 đến ngày 20/6/2026.
- Thi năng khiếu Giáo dục mầm non, Giáo dục thể chất: thi vào các ngày 19, 20, 21/6/2026.

[GIỚI Ý]: 
1. Câu hỏi về lịch thi năng khiếu của Trường Đại học Quy Nhơn năm 2026 là gì?
2. Câu hỏi về lịch thi năng khiếu của Trường Đại học Quy Nhơn năm 2027 là gì?

- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Hương dan thi Nang khieu GDTC 2026 — trang 1; binding `bnd_574bfd4e5288`, index `idx_rev_76cae24bd0dd`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB lịch xét tuyển ĐH — trang 1; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `34598ee4-c9c7-449f-bdf5-fff9f754ed36`.

RAG — HTTP 200, trạng thái answered, 2.28 giây:

Câu trả lời của Trợ lý AI chính thức:

Tiêu đề cột và hàng trong bảng sẽ được sắp xếp theo đúng thời gian (năm áp dụng) và đúng bản chất dữ liệu (ví dụ: 'Chỉ tiêu' vs 'Thực hiện'; 'Cơ hữu' vs 'Thỉnh giảng').

Tiêu đề cột và hàng trong bảng sẽ được sắp xếp như sau:

| Cột 1 | Cột 2 |
| --- | --- |
| Năm | Thời gian thi năng khiếu |
| 2026 | 19, 20, 21/6/2026 |

Dựa trên các đoạn trích trong tài liệu, chúng ta có thể xác định được thời gian thi năng khiếu năm 2026 là từ ngày 19 đến 21 tháng 6 năm 2026.

Vậy, câu trả lời của Trợ lý AI chính thức là:

| Năm | Thời gian thi năng khiếu |
| --- | --- |
| 2026 | 19, 20, 21/6/2026 |

- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Hương dan thi Nang khieu GDTC 2026 — trang 1; binding `bnd_574bfd4e5288`, index `idx_rev_76cae24bd0dd`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: TB lịch xét tuyển ĐH — trang 1; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
### Câu 59 Thời gian đăng ký thi năng khiếu năm 2026?

Nhóm: XI. THI NĂNG KHIẾU

Đáp án tham khảo trong DOCX:

Theo thông báo đầu mùa, đăng ký từ 20/05/2026 đến 15/06/2026 trên hệ thống tuyển sinh của Trường.

DAG — HTTP 200, trạng thái answered, 4.72 giây:

| Mốc thời gian | Nội dung | Chủ trì thực hiện | Phối hợp thực hiện |
| --- | --- | --- | --- |
| 14h00 Thứ 6, ngày 19 tháng 6 năm 2026 | Thời gian làm thủ tục dự thi |  |  |
| 7h00 Thứ 7, ngày 20 tháng 6 năm 2026 | Thời gian thi |  |  |
| 20/5/2026 - 20/6/2026 | Thí sinh đăng ký thi năng khiếu |  |  |
| 02/7/2026 - 14/7/2026 | Xét tuyển đợt 1 |  |  |
| 04/8/2026 - 10/8/2026 | Xét tuyển theo kế hoạch của Bộ GDĐT |  |  |
| 22/8/2026 | Xét tuyển các ngành còn chỉ tiêu sau khi thí sinh đăng ký nhập học đợt 1 |  |  |

Thời gian đăng ký thi năng khiếu năm 2026 là từ ngày 20/5/2026 đến ngày 20/6/2026.

- Nguồn: Hương dan thi Nang khieu GDTC 2026 — trang 1; binding `bnd_574bfd4e5288`, index `idx_rev_76cae24bd0dd`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: TB lịch xét tuyển ĐH — trang 1; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `b58bb6c5-aa09-453d-9306-a4e6402f5084`.

RAG — HTTP 200, trạng thái answered, 2.08 giây:

**THỜI GIAN ĐĂNG KÝ THI NĂNG KHIẾU NĂM 2026**

| **Nội dung** | **Thời gian** |
| --- | --- |
| Đăng ký thi năng khiếu | Từ ngày 20/5/2026 đến 15/6/2026 |
| Thi năng khiếu Giáo dục mầm non, Giáo dục thể chất | 19, 20, 21/6/2026 |
| Đăng ký xét tuyển đợt 1 | Từ ngày 02/7/2026 đến ngày 14/7/2026 |
| Xét tuyển theo kế hoạch của Bộ GDĐT | 04/8/2026 – 10/8/2026 |

Lưu ý: Thời gian đăng ký thi năng khiếu và xét tuyển có thể thay đổi theo quy định của Trường Đại học Quy Nhơn.

- Nguồn: Hương dan thi Nang khieu GDTC 2026 — trang 1; binding `bnd_574bfd4e5288`, index `idx_rev_76cae24bd0dd`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: TB lịch xét tuyển ĐH — trang 1; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
### Câu 60 Có thể dùng điểm năng khiếu của trường khác không?

Nhóm: XI. THI NĂNG KHIẾU

Đáp án tham khảo trong DOCX:

Không. Chỉ sử dụng điểm thi năng khiếu do QNU tổ chức.

DAG — HTTP 200, trạng thái answered, 3.72 giây:

Mình có thể trả lời câu hỏi của bạn về việc sử dụng điểm năng khiếu của trường khác hay không.

Theo quy định tại mục I. Đối với thí sinh, tài liệu chính thức trong tài liệu trích xuất, thí sinh xét tuyển có môn năng khiếu, sử dụng điểm năng khiếu của CSĐT khác để xét tuyển, phải liên hệ với CSĐT để đăng ký dự thi, dự thi, hoặc nộp điểm thi năng khiếu.

Vậy, điểm năng khiếu của trường khác có thể được sử dụng để xét tuyển vào trường của mình, nhưng thí sinh phải đăng ký dự thi hoặc nộp điểm thi năng khiếu tại CSĐT khác trước khi nộp hồ sơ xét tuyển.

**Bảng thông tin về quy định sử dụng điểm năng khiếu**

| **Quy định** | **Giá trị** |
| --- | --- |
| Thí sinh xét tuyển có môn năng khiếu, sử dụng điểm năng khiếu của CSĐT khác | Được sử dụng để xét tuyển |
| Thí sinh phải đăng ký dự thi hoặc nộp điểm thi năng khiếu tại CSĐT khác | Phải thực hiện trước khi nộp hồ sơ xét tuyển |

Hy vọng thông tin này hữu ích cho bạn!

- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 3; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `fbc6b0ae-763d-4e5e-96b5-86d44630d802`.

RAG — HTTP 200, trạng thái answered, 1.88 giây:

**Đáp án: Có thể dùng điểm năng khiếu của trường khác không?**

| Câu trả lời | Điểm năng khiếu của trường khác có được sử dụng để xét tuyển |
| --- | --- |
|  | **Có** |

Theo tài liệu trích xuất, thí sinh xét tuyển có môn năng khiếu, sử dụng điểm năng khiếu của CSĐT khác để xét tuyển, phải liên hệ với CSĐT để đăng ký dự thi, dự thi, hoặc nộp điểm thi năng khiếu.

Vậy, điểm năng khiếu của trường khác có thể được sử dụng để xét tuyển.

- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 3; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
### Câu 61 Tại sao điểm học bạ và điểm thi THPT không so trực tiếp với nhau?

Nhóm: XII. QUY ĐỔI ĐIỂM GIỮA CÁC PHƯƠNG THỨC

Đáp án tham khảo trong DOCX:

Vì các phương thức có phân bố điểm khác nhau. Năm 2026, Trường thực hiện quy đổi tương đương giữa các phương thức/tổ hợp theo quy định và bảng công bố chính thức.

DAG — HTTP 200, trạng thái insufficient_context, 4.25 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `14694006-d9ec-4c7b-a84e-53ea6fd53388`.

RAG — HTTP 200, trạng thái answered, 1.66 giây:

Để hiểu tại sao điểm học bạ và điểm thi THPT không so trực tiếp với nhau, chúng ta cần xem xét cách quy đổi điểm giữa hai hệ thống.

| **Điểm quy đổi** | **Điểm học bạ** | **Điểm thi THPT** |
| --- | --- | --- |
| **8.0** | Mức điểm IELTS 5.0 |  |
| **9.0** | Mức điểm IELTS 5.5 |  |
| **10.0** | Mức điểm IELTS 6.0 |  |
|  |  | **15** |

Như vậy, điểm quy đổi giữa học bạ và thi THPT không được cung cấp thông tin. Tuy nhiên, có thể thấy rằng điểm quy đổi giữa IELTS và điểm thi THPT có sự khác biệt.

Vì vậy, điểm học bạ và điểm thi THPT không so trực tiếp với nhau vì chúng được quy đổi theo các mức điểm khác nhau.

### Câu 62 Có công thức quy đổi chung để tự tính không?

Nhóm: XII. QUY ĐỔI ĐIỂM GIỮA CÁC PHƯƠNG THỨC

Đáp án tham khảo trong DOCX:

Không nên tự dùng công thức truyền miệng. Phải sử dụng bảng/quy tắc quy đổi chính thức của Trường cho năm 2026.

DAG — HTTP 200, trạng thái insufficient_context, 4.3 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `713054a6-d2bc-4cb6-a5bf-c5b07fb67957`.

RAG — HTTP 200, trạng thái answered, 1.95 giây:

Câu trả lời của Trợ lý AI chính thức của Trường Đại học Quy Nhơn (QNU):

Câu trả lời của Trợ lý AI chính thức của Trường Đại học Quy Nhơn (QNU) là: Không có công thức quy đổi chung để tự tính các phương thức giáo dục. Bảng số liệu trên chỉ cung cấp các phương thức giáo dục cho các thực thể/ ngành giáo dục khác nhau.

Dưới đây là bảng số liệu được trích xuất từ tài liệu:

| Thực thể / Ngành | Phương thức | Giá trị dữ liệu |
| --- | --- | --- |
| Quản lý giáo dục |  | **1,2,3,4,6** |
| Giáo dục Mầm non |  | **5,6** |
| Giáo dục Tiểu học |  | **1,4,6** |
| Giáo dục Chính trị |  | **1,4,6** |
| Giáo dục Thể chất |  | **5,6** |

Lưu ý: Giá trị dữ liệu trong bảng trên chỉ áp dụng cho các thực thể/ ngành giáo dục tương ứng và không thể tự tính được.

### Câu 63 Điểm chuẩn học bạ cao hơn điểm thi THPT có nghĩa học bạ khó hơn không?

Nhóm: XII. QUY ĐỔI ĐIỂM GIỮA CÁC PHƯƠNG THỨC

Đáp án tham khảo trong DOCX:

Không thể kết luận chỉ từ con số tuyệt đối vì các phương thức dùng thang/phân bố điểm khác nhau và được quy đổi tương đương. Cần xem bảng quy đổi và điểm chuẩn đúng phương thức.

DAG — HTTP 200, trạng thái insufficient_context, 3.78 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `925bbb70-9b67-4389-bd58-809b011c2dd1`.

RAG — HTTP 200, trạng thái answered, 2.8 giây:

Điểm chuẩn học bạ cao hơn điểm thi THPT không nhất thiết phải có nghĩa học bạ khó hơn. Để hiểu rõ hơn, chúng ta cần đối chiếu thông tin về điểm chuẩn học bạ và điểm thi THPT.

| Thực thể / Ngành | Thuộc tính | Giá trị dữ liệu |
| --- | --- | --- |
| 7.0 trở lên | Điểm quy đổi VSTEP | **10** |
| Mức điểm IELTS 5.0 | Điểm quy đổi | **8.0** |
| Mức điểm IELTS 5.5 | Điểm quy đổi | **9.0** |
| Mức điểm IELTS 6.0 | Điểm quy đổi | **10.0** |
| Quản lý Giáo dục | 2023 - Điểm trúng tuyển (TNTHP T) | **15** |

Trong bảng trên, điểm chuẩn học bạ (được quy đổi từ IELTS) cao hơn điểm thi THPT (được quy đổi từ VSTEP). Tuy nhiên, điều này không nhất thiết phải có nghĩa học bạ khó hơn. Có thể điểm thi THPT đã được quy đổi từ thang điểm khác hoặc có cách tính khác biệt so với điểm chuẩn học bạ.

Để có câu trả lời chính xác hơn, cần có thêm thông tin về thang điểm, cách tính điểm và quy đổi giữa các loại điểm thi khác nhau.

### Câu 64 Điểm sàn có phải điểm chuẩn không?

Nhóm: XIII. ĐIỂM SÀN – ĐIỂM CHUẨN – KHẢ NĂNG TRÚNG TUYỂN

Đáp án tham khảo trong DOCX:

Không. Điểm sàn/ngưỡng bảo đảm chất lượng đầu vào là mức tối thiểu để được tham gia xét tuyển; điểm chuẩn là mức điểm trúng tuyển sau quá trình xét tuyển.

DAG — HTTP 200, trạng thái insufficient_context, 3.16 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `fae96515-9b06-4db4-a42d-17cab20fd03d`.

RAG — HTTP 200, trạng thái answered, 1.94 giây:

Điểm sàn và điểm chuẩn là hai khái niệm khác nhau.

Điểm sàn là mức điểm tối thiểu mà thí sinh phải đạt được để được xét tuyển vào một trường đại học hoặc một ngành học cụ thể. Điểm sàn thường được quy định bởi trường đại học hoặc bởi Bộ Giáo dục và Đào tạo.

Điểm chuẩn, còn được gọi là điểm trúng tuyển, là mức điểm tối thiểu mà thí sinh phải đạt được để được trúng tuyển vào một trường đại học hoặc một ngành học cụ thể. Điểm chuẩn thường cao hơn điểm sàn và được xác định dựa trên kết quả tuyển sinh thực tế của trường.

Trong bảng số liệu bạn cung cấp, có một hàng ghi "2023 - Điểm trúng tuyển (TNTHP T) | **15**". Điều này cho thấy rằng điểm **15** là điểm chuẩn (điểm trúng tuyển) của trường Đại học Quy Nhơn (QNU) vào năm 2023, chứ không phải là điểm sàn.

Vậy, để trả lời câu hỏi của bạn: Điểm sàn không phải là điểm chuẩn.

### Câu 65 Đạt điểm sàn có chắc chắn đậu không?

Nhóm: XIII. ĐIỂM SÀN – ĐIỂM CHUẨN – KHẢ NĂNG TRÚNG TUYỂN

Đáp án tham khảo trong DOCX:

Không. Đạt ngưỡng chỉ là điều kiện để được xét. Kết quả còn phụ thuộc chỉ tiêu, số lượng thí sinh, mức điểm, thứ tự nguyện vọng và quy tắc xét tuyển.

DAG — HTTP 200, trạng thái insufficient_context, 3.22 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["citations list is empty"], "unsupported_numbers": []}

Mã workflow: `2dfa0352-6a39-48d0-8f2e-3f2b339ce238`.

RAG — HTTP 200, trạng thái answered, 2.48 giây:

Để xác định chắc chắn có đậu hay không, bạn cần tham khảo điểm sàn của Trường Đại học Quy Nhơn (QNU) trong năm hiện tại. Tuy nhiên, dựa trên thông tin đã được xác thực, bảng dưới đây thể hiện điểm quy đổi và điểm trúng tuyển của một số trường hợp:

| **Ngành/Trường hợp** | **Điểm Quy Đổi** | **Điểm Trúng Tuyển** |
| --- | --- | --- |
| Đạt điểm sàn 7.0 trở lên | **10** | - |
| Đạt điểm IELTS 5.0 | **8.0** | - |
| Đạt điểm IELTS 5.5 | **9.0** | - |
| Đạt điểm IELTS 6.0 | **10.0** | - |
| Quản lý Giáo dục (2023) | - | **15** |

Lưu ý: Điểm trúng tuyển (Điểm sàn) của Trường Đại học Quy Nhơn (QNU) trong năm hiện tại chưa được cung cấp trong tài liệu đã xác thực. Bạn nên tham khảo thông tin chính thức từ Trường Đại học Quy Nhơn (QNU) hoặc Hotline tư vấn tuyển sinh: 0256.3846.156 / Email: tuyensinh@qnu.edu.vn để có thông tin chính xác.

### Câu 66 Có thể lấy điểm chuẩn 2025 để khẳng định đậu 2026 không?

Nhóm: XIII. ĐIỂM SÀN – ĐIỂM CHUẨN – KHẢ NĂNG TRÚNG TUYỂN

Đáp án tham khảo trong DOCX:

Không. Điểm chuẩn năm trước chỉ có giá trị tham khảo. Không được khẳng định chắc chắn kết quả năm sau từ điểm chuẩn cũ.

DAG — HTTP 200, trạng thái insufficient_context, 0.91 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `a041d824-45fa-4177-b40f-5158f014ffbd`.

RAG — HTTP 200, trạng thái insufficient_context, 0.22 giây:

Trong kho tài liệu đã xuất bản, mình chưa tìm thấy căn cứ đủ rõ cho số liệu và ngữ cảnh được hỏi. Không thể dùng số liệu năm hoặc điều kiện khác thay thế.

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 67 Sau khi trúng tuyển QNU phải làm gì?

Nhóm: XIV. KẾT QUẢ XÉT TUYỂN, XÁC NHẬN NHẬP HỌC VÀ NHẬP HỌC

Đáp án tham khảo trong DOCX:

Thí sinh phải xác nhận nhập học trực tuyến trên Hệ thống của Bộ trong thời hạn quy định, sau đó thực hiện các bước nhập học theo hướng dẫn của Trường.

DAG — HTTP 200, trạng thái answered, 6.19 giây:

Sau khi trúng tuyển vào Trường Đại học Quy Nhơn, bạn cần thực hiện các bước sau:

| Bước | Trình tự hành động | Thời gian |
| --- | --- | --- |
| 1 | Đăng ký nhập học trực tuyến qua website: https://nhaphoc.qnu.edu.vn bằng Tài khoản (là Mã sinh viên) và Mật khẩu (là Mã sinh viên) trong Giấy báo nhập học. | Từ ngày 18/8/2026 |
| 2 | Điền đầy đủ thông tin, upload ảnh thẻ và lưu thông tin. |  |
| 3 | Đối với sinh viên ngành sư phạm có nhu cầu thụ hưởng chính sách hỗ trợ tiền đóng học phí, chi phí sinh hoạt theo Nghị định 116/2020/NĐ-CP, tải, in và ký tên vào Đơn đề nghị hưởng và cam kết bồi hoàn học phí, chi phí sinh hoạt (từ trang https://nhaphoc.qnu.edu.vn) và mang theo khi nhập học. |  |
| 4 | Đối với sinh viên thuộc các đối tượng được miễn, giảm học phí theo Nghị định 238/2025/NĐ-CP, tải, in và ký tên vào Đơn miễn, giảm học phí (từ trang https://nhaphoc.qnu.edu.vn) và mang theo khi nhập học. |  |
| 5 | Nộp học phí học kì 1 năm học 2026-2027 và một số khoản thu khác bằng cách chọn ô thanh toán trên trang nhập học hoặc thực hiện theo hướng dẫn chi tiết trong Phụ lục 2 của Hướng dẫn này. |  |
| 6 | Sau khi nhập học, sinh viên đăng nhập vào website https://tinchi.qnu.edu.vn bằng tài khoản và mật khẩu cá nhân (trong Bước 1) để xem chương trình đào tạo, thời khóa biểu. |  |
| 7 | Sinh viên thường xuyên theo dõi thông báo cập nhật trên website của Trường Đại học Quy Nhơn tại địa chỉ https://qnu.edu.vn |  |

Lưu ý: Mọi thắc mắc trong quá trình nhập học, sinh viên liên hệ Bộ phận Tư vấn tuyển sinh, số hotline 1800.55.88.49.

[Giới thiệu]: Bạn có thể hỏi thêm về các bước nhập học chi tiết hay liên hệ với bộ phận tư vấn tuyển sinh để được hỗ trợ.

- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: HD nhập học — trang 3; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `25b55e1e-4876-4d8a-889f-82ae46c0811a`.

RAG — HTTP 200, trạng thái answered, 3.56 giây:

Sau khi trúng tuyển vào Trường Đại học Quy Nhơn, sinh viên cần thực hiện các bước sau:

1. **Đăng ký nhập học trực tuyến**: Từ ngày 18/8/2026, thí sinh trúng tuyển đăng ký nhập học trực tuyến qua website: https://nhaphoc.qnu.edu.vn bằng Tài khoản (là Mã sinh viên) và Mật khẩu (là Mã sinh viên) trong Giấy báo nhập học.
2. **Cung cấp thông tin và upload ảnh thẻ**: Sinh viên điền đầy đủ thông tin, upload ảnh thẻ và lưu thông tin.
3. **Tải, in và ký tên vào Đơn đề nghị hưởng và cam kết bồi hoàn học phí, chi phí sinh hoạt (nếu có)**: Đối với sinh viên ngành sư phạm có nhu cầu thụ hưởng chính sách hỗ trợ tiền đóng học phí, chi phí sinh hoạt theo Nghị định 116/2020/NĐ-CP.
4. **Tải, in và ký tên vào Đơn miễn, giảm học phí (nếu có)**: Đối với sinh viên thuộc các đối tượng được miễn, giảm học phí theo Nghị định 238/2025/NĐ-CP.
5. **Nộp học phí học kì 1 năm học 2026-2027 và các khoản thu khác**: Sinh viên nộp học phí học kì 1 năm học 2026-2027 và các khoản thu khác bằng cách chọn ô thanh toán trên trang nhập học hoặc thực hiện theo hướng dẫn chi tiết trong Phụ lục 2 của Hướng dẫn này.
6. **Đăng nhập vào website tinchi.qnu.edu.vn**: Sinh viên đăng nhập vào website tinchi.qnu.edu.vn bằng tài khoản và mật khẩu cá nhân (trong Bước 1) để xem chương trình đào tạo, thời khóa biểu.
7. **Theo dõi thông báo cập nhật**: Sinh viên thường xuyên theo dõi thông báo cập nhật trên website của Trường Đại học Quy Nhơn tại địa chỉ https://qnu.edu.vn.
8. **Liên hệ Bộ phận Tư vấn tuyển sinh (nếu có thắc mắc)**: Mọi thắc mắc trong quá trình nhập học, sinh viên liên hệ Bộ phận Tư vấn tuyển sinh, số hotline 1800.55.88.49.

- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: HD nhập học — trang 3; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
### Câu 68 Thời gian xác nhận nhập học năm 2026?

Nhóm: XIV. KẾT QUẢ XÉT TUYỂN, XÁC NHẬN NHẬP HỌC VÀ NHẬP HỌC

Đáp án tham khảo trong DOCX:

Theo thông báo kết quả tuyển sinh 2026 của QNU: từ ngày 13/08/2026 đến trước 17 giờ 00 ngày 21/08/2026.

DAG — HTTP 200, trạng thái answered, 3.92 giây:

Bạn đang tìm hiểu về thời gian xác nhận nhập học năm 2026. 

Theo kế hoạch của Trường Đại học Quy Nhơn, thời gian xác nhận nhập học trực tuyến sẽ bắt đầu từ ngày 13/8/2026 và kết thúc vào 17:00 ngày 21/8/2026. 

Trong giai đoạn này, thí sinh sẽ thực hiện các bước sau:

- Đăng ký nhập học trực tuyến trên trang https://nhaphoc.qnu.edu.vn bằng Tài khoản (là Mã sinh viên) và Mật khẩu (là Mã sinh viên) trong Giấy báo nhập học.
- Upload ảnh thẻ và lưu thông tin.
- Tải, in và ký tên vào Đơn đề nghị hưởng và cam kết bồi hoàn học phí, chi phí sinh hoạt (nếu thuộc đối tượng được miễn, giảm học phí theo Nghị định 116/2020/NĐ-CP).
- Tải, in và ký tên vào Đơn miễn, giảm học phí (nếu thuộc đối tượng được miễn, giảm học phí theo Nghị định 238/2025/NĐ-CP).

Sau khi hoàn thành các bước trên, thí sinh sẽ nộp học phí học kì 1 năm học 2026-2027 và một số khoản thu khác bằng cách chọn ô thanh toán trên trang nhập học hoặc thực hiện theo hướng dẫn chi tiết trong Phụ lục 2 của Hướng dẫn này.

[Giới thiệu]: Bạn có thể tham khảo thêm thông tin về quy trình nhập học và các bước cần thực hiện trong kế hoạch này.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: TB lịch xét tuyển ĐH — trang 3; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `4822dc94-633d-4c61-b7e6-25c934071475`.

RAG — HTTP 200, trạng thái answered, 4.26 giây:

- **Thời gian xác nhận nhập học năm 2026:**

| TT | Các mốc thời gian | Nội dung | Chủ trì thực hiện | Phối hợp thực hiện |
| :---: | :--- | :--- | :--- | :--- |
| 28. | Từ 13/8 đến 17:00 ngày 21/8/2026 | Theo dõi, hỗ trợ thí sinh xác nhận nhập học trực tuyến; không yêu cầu thí sinh xác nhận nhập học hoặc nhập học trước ngày 13/8/2026 | Tổ TVTS | Các khoa |

- **Bước 1: Xác nhận nhập học trực tuyến:**
- Thí sinh trúng tuyển đăng ký nhập học trực tuyến qua website: https://nhaphoc.qnu.edu.vn từ ngày 18/8/2026.
- Thí sinh điền đầy đủ thông tin, upload ảnh thẻ và lưu thông tin.
- Đối với sinh viên ngành sư phạm có nhu cầu thụ hưởng chính sách hỗ trợ tiền đóng học phí, chi phí sinh hoạt theo Nghị định 116/2020/NĐ-CP thực hiện tải, in và ký tên vào Đơn đề nghị hưởng và cam kết bồi hoàn học phí, chi phí sinh hoạt (từ trang https://nhaphoc.qnu.edu.vn) và mang theo khi nhập học.
- Đối với sinh viên thuộc các đối tượng được miễn, giảm học phí theo Nghị định 238/2025/NĐ-CP thực hiện tải, in và ký tên vào Đơn miễn, giảm học phí (từ trang https://nhaphoc.qnu.edu.vn) và mang theo khi nhập học.

- **Bước 2: Nhập học trực tiếp:**
- Thời gian nhập học: ngày 24, 25, 26, 27, 28 tháng 8 năm 2026.
- Địa điểm: Hội trường A, Hội trường B, Trường Đại học Quy Nhơn (số 170 An Dương Vương, phường Quy Nhơn Nam, tỉnh Gia Lai) (theo Giấy báo nhập học).

- **Lưu ý:**
- Thí sinh nhập học đúng thời gian, địa điểm trên Giấy báo nhập học và đem theo 01 bộ hồ sơ như yêu cầu trong Giấy báo nhập học.

- **Thời gian nhập học chính thức:**
- Từ ngày 24/8/2026 đến ngày 28/8/2026: Tổ chức nhập học chính thức cho thí sinh trúng tuyển đợt 1 đã xác nhận nhập học và đợt 2 (nếu có); kiểm tra hồ sơ nhập học của thí sinh.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: TB lịch xét tuyển ĐH — trang 3; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 69 Thời gian nhập học trực tiếp K49 năm 2026?

Nhóm: XIV. KẾT QUẢ XÉT TUYỂN, XÁC NHẬN NHẬP HỌC VÀ NHẬP HỌC

Đáp án tham khảo trong DOCX:

Trường tổ chức nhập học trực tiếp từ ngày 24/08/2026 đến 28/08/2026.

DAG — HTTP 200, trạng thái answered, 3.38 giây:

Bạn đang tìm hiểu về thời gian nhập học trực tiếp cho sinh viên khóa 49 năm 2026. Theo kế hoạch của Trường Đại học Quy Nhơn, thời gian nhập học trực tiếp được quy định như sau:

- **Thời gian nhập học:** ngày 24, 25, 26, 27, 28 tháng 8 năm 2026.
- **Địa điểm:** Hội trường A, Hội trường B, Trường Đại học Quy Nhơn (số 170 An Dương Vương, phường Quy Nhơn Nam, tỉnh Gia Lai).

Hãy đảm bảo rằng bạn nhập học đúng thời gian và địa điểm trên Giấy báo nhập học và mang theo 01 bộ hồ sơ như yêu cầu trong Giấy báo nhập học.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `2c7da1f7-dcd2-44f1-a8d4-c338a44205f7`.

RAG — HTTP 200, trạng thái answered, 1.5 giây:

- Thời gian nhập học trực tiếp K49 năm 2026 là ngày 24, 25, 26, 27, 28 tháng 8 năm 2026.

- Địa điểm: Hội trường A, Hội trường B, Trường Đại học Quy Nhơn (số 170 An Dương Vương, phường Quy Nhơn Nam, tỉnh Gia Lai) (theo Giấy báo nhập học).

- Sinh viên nhập học đúng thời gian, địa điểm trên Giấy báo nhập học và đem theo 01 bộ hồ sơ như yêu cầu trong Giấy báo nhập học.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
### Câu 70 Nếu trúng tuyển mà không xác nhận nhập học đúng hạn thì sao?

Nhóm: XIV. KẾT QUẢ XÉT TUYỂN, XÁC NHẬN NHẬP HỌC VÀ NHẬP HỌC

Đáp án tham khảo trong DOCX:

Thí sinh có thể mất quyền nhập học theo kết quả đã công bố, trừ trường hợp được xử lý theo quy định.

DAG — HTTP 200, trạng thái insufficient_context, 3.86 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["Unsupported numbers detected: 27, 15, 50, 22.5"], "unsupported_numbers": ["27", "15", "50", "22.5"]}

Mã workflow: `115cbb62-2151-4dcc-8fec-e148c7c6774a`.

RAG — HTTP 200, trạng thái insufficient_context, 2.74 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 71 Giấy báo trúng tuyển nhận ở đâu?

Nhóm: XIV. KẾT QUẢ XÉT TUYỂN, XÁC NHẬN NHẬP HỌC VÀ NHẬP HỌC

Đáp án tham khảo trong DOCX:

Theo thông báo của Trường, thí sinh trúng tuyển được hướng dẫn nhận thông tin/giấy báo qua kênh do Trường công bố, gồm email và hình thức gửi theo thông báo cụ thể.

DAG — HTTP 200, trạng thái answered, 4.34 giây:

Bạn cần biết giấy báo trúng tuyển được nhận ở đâu. 

Trường Đại học Quy Nhơn sẽ gửi Giấy báo nhập học cho thí sinh trúng tuyển qua email, bưu điện. Thí sinh trúng tuyển cũng có thể tự in Giấy báo nhập học tại link https://tsd.qnu.edu.vn và chọn mục TRA CỨU.

Sau khi xác nhận nhập học trên cổng thông tin tuyển sinh của Bộ Giáo dục và Đào tạo, thí sinh thực hiện các bước sau:

- Đăng ký nhập học trực tuyến qua website: https://nhaphoc.qnu.edu.vn bằng Tài khoản (là Mã sinh viên) và Mật khẩu (là Mã sinh viên) trong Giấy báo nhập học.

- Nhập học trực tiếp tại Hội trường A, Hội trường B, Trường Đại học Quy Nhơn (số 170 An Dương Vương, phường Quy Nhơn Nam, tỉnh Gia Lai) trong thời gian và địa điểm quy định trên Giấy báo nhập học.

Khi nhập học trực tiếp, thí sinh thực hiện theo trình tự sau:

- Nhận bì Hồ sơ sinh viên, ghi đầy đủ thông tin trên bì hồ sơ và trên Giấy biên nhận nhập học.

- Trình giấy tờ liên quan đến phương thức xét tuyển.

- Nộp Hồ sơ nhập học.

- Đăng ký ở Ký túc xá (nếu có).

- Đăng ký Bảo hiểm y tế và Bảo hiểm thân thể.

- Xác nhận thông tin khu vực, đối tượng ưu tiên (nếu có).

[Giải đáp]: Gợi ý câu hỏi tiếp theo về quy trình nhập học, cần lưu ý thông tin chi tiết như: thời gian nhập học, địa điểm nhập học, hồ sơ cần chuẩn bị, và các bước thực hiện.

- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 3; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 20; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: TB lịch xét tuyển ĐH — trang 3; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `ffa762c8-6391-441a-965e-ec5e88a9fc47`.

RAG — HTTP 200, trạng thái answered, 2.02 giây:

Giấy báo trúng tuyển sẽ được gửi cho thí sinh trúng tuyển qua email hoặc bưu điện. Thí sinh cũng có thể tự in Giấy báo nhập học tại địa chỉ https://tsd.qnu.edu.vn và chọn mục TRA CỨU.

Sau khi thí sinh xác nhận nhập học trên cổng thông tin tuyển sinh của Bộ Giáo dục và Đào tạo, đề nghị các thí sinh thực hiện các bước sau:

1. Thí sinh đăng ký nhập học trực tuyến qua website: https://nhaphoc.qnu.edu.vn bằng Tài khoản (là Mã sinh viên) và Mật khẩu (là Mã sinh viên) trong Giấy báo nhập học.
2. Thí sinh nộp học phí học kì 1 năm học 2026-2027 và một số khoản thu khác bằng cách chọn ô thanh toán trên trang nhập học hoặc thực hiện theo hướng dẫn chi tiết trong Phụ lục 2 của Hướng dẫn này.

Thí sinh nhập học đúng thời gian, địa điểm trên Giấy báo nhập học và đem theo 01 bộ hồ sơ như yêu cầu trong Giấy báo nhập học.

- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 3; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 20; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: TB lịch xét tuyển ĐH — trang 3; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: HD nhập học — trang 2; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
### Câu 72 Có phải nhập học trực tuyến ngay khi biết điểm chuẩn không?

Nhóm: XIV. KẾT QUẢ XÉT TUYỂN, XÁC NHẬN NHẬP HỌC VÀ NHẬP HỌC

Đáp án tham khảo trong DOCX:

Cần thực hiện theo đúng mốc Trường công bố. Trong mùa 2026, các thao tác nhập học trực tuyến của QNU được hướng dẫn theo thời gian riêng; không nên thao tác trước khi cổng chức năng mở.

DAG — HTTP 200, trạng thái insufficient_context, 1.98 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `bb7a6514-6913-4ac7-b6a8-0d21204fa6fa`.

RAG — HTTP 200, trạng thái insufficient_context, 0.39 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 73 QNU có xét tuyển bổ sung năm 2026 không?

Nhóm: XV. XÉT TUYỂN BỔ SUNG NĂM 2026

Đáp án tham khảo trong DOCX:

Có. Ngày 22/08/2026, Trường thông báo xét tuyển bổ sung 28 ngành/chương trình đào tạo với tổng 456 chỉ tiêu.

DAG — HTTP 200, trạng thái answered, 3.72 giây:

- Trường Đại học Quy Nhơn có xét tuyển bổ sung năm 2026 không?
- Tùy thuộc vào chỉ tiêu và nhu cầu tuyển sinh, Trường Đại học Quy Nhơn có thể thực hiện xét tuyển bổ sung trong năm 2026. Tuy nhiên, thông tin chính thức về xét tuyển bổ sung sẽ được công bố sau khi có kết quả thi tốt nghiệp THPT năm 2026.

- Nguồn: Thông tin TSĐH cập nhật — trang 1; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `1e6ca3fd-36b3-45d0-a054-60ac1f816f73`.

RAG — HTTP 200, trạng thái answered, 1.31 giây:

- QNU không có thông tin về xét tuyển bổ sung năm 2026.
- Tuy nhiên, thông tin tuyển sinh năm 2026 của QNU có thể được tìm thấy tại trang thông tin điện tử: https://tuyensinh.qnu.edu.vn

- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 1; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
- Nguồn: Thông tin TSĐH cập nhật — trang 9; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 9; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
### Câu 74 Xét tuyển bổ sung dùng những phương thức nào?

Nhóm: XV. XÉT TUYỂN BỔ SUNG NĂM 2026

Đáp án tham khảo trong DOCX:

Gồm: điểm thi tốt nghiệp THPT 2026, kết quả học tập THPT, điểm ĐGNL ĐHQG TP.HCM và điểm ĐGNL Trường ĐHSP Hà Nội, tùy ngành.

DAG — HTTP 200, trạng thái answered, 3.91 giây:

Xét tuyển bổ sung của Trường Đại học Quy Nhơn sử dụng các phương thức sau:

| Phương thức xét tuyển | Mã phương thức xét tuyển |
| --- | --- |
| Xét tuyển theo kết quả thi tốt nghiệp THPT | 1 |
| Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) | 2 |
| Xét kết quả kỳ thi đánh giá năng lực của Đại học Quốc gia Thành phố Hồ Chí Minh | 3 |
| Xét kết quả kỳ thi đánh giá năng lực của Trường Đại học Sư phạm Hà Nội | 4 |
| Xét tuyển theo kết quả thi tốt nghiệp THPT với điểm thi năng khiếu | 5 |

Lưu ý: Các phương thức xét tuyển trên chỉ áp dụng cho xét tuyển bổ sung và không nhất thiết phải áp dụng cho xét tuyển chính quy.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 20; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 21; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 3; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `ccb1c098-777a-410a-a776-6f7be3a09c8a`.

RAG — HTTP 200, trạng thái answered, 2.77 giây:

Câu trả lời chính xác dựa trên tài liệu và số liệu cung cấp:

Xét tuyển bổ sung sử dụng các phương thức sau:

- Phương thức 1 (PT1 - mã 100): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026.
- Phương thức 2 (PT2 - mã 200): Xét tuyển theo kết quả học tập 3 năm THPT (học bạ) theo quy định của Bộ Giáo dục và Đào tạo.
- Phương thức 3 (PT3 - mã 402A): Xét kết quả kỳ thi đánh giá năng lực (ĐGNL) của Đại học Quốc gia Thành phố Hồ Chí Minh.
- Phương thức 4 (PT4 - mã 402B): Xét kết quả kỳ thi ĐGNL của Trường Đại học Sư phạm Hà Nội.
- Phương thức 5 (PT5 - mã 405): Xét tuyển theo kết quả thi tốt nghiệp THPT năm 2026 với điểm thi năng khiếu GDMN/GDTC của Trường Đại học Quy Nhơn.
- Xét tuyển thẳng (mã 301) theo Quy chế tuyển sinh của Bộ Giáo dục và Đào tạo.

Lưu ý: Các phương thức trên chỉ được áp dụng cho các ngành và chương trình đào tạo cụ thể, và có thể có thêm các phương thức khác tùy thuộc vào từng trường hợp.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 20; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 21; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Thông tin TSĐH cập nhật — trang 2; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: NQ57.2024_ Phương hướng tuyển sinh 2025 — trang 3; binding `bnd_0a0fefc849ab`, index `idx_rev_a90d85902c4f`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 3; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 75 Đăng ký xét bổ sung ở đâu?

Nhóm: XV. XÉT TUYỂN BỔ SUNG NĂM 2026

Đáp án tham khảo trong DOCX:

Theo Thông báo 151/TB-HĐTS, thí sinh đăng ký trực tuyến trên hệ thống tuyển sinh của Trường theo đường dẫn được công bố trong thông báo.

DAG — HTTP 200, trạng thái answered, 3.55 giây:

- Thí sinh chưa trúng tuyển hoặc đã trúng tuyển nhưng chưa xác nhận nhập học vào một cơ sở đào tạo bất kỳ có thể đăng ký xét tuyển các đợt bổ sung theo kế hoạch và hướng dẫn của cơ sở đào tạo.
- Cơ sở đào tạo thông báo kế hoạch xét tuyển, phương thức xét tuyển, hình thức đăng ký xét tuyển các đợt bổ sung và điều kiện xét tuyển bổ sung.
- Thí sinh cần đăng ký xét tuyển bổ sung trên trang thông tin điện tử của cơ sở đào tạo hoặc trên Cổng dịch vụ công Quốc gia.
- Thí sinh cần hoàn thành thanh toán mức thu dịch vụ tuyển sinh trước khi kết thúc thủ tục đăng ký dự tuyển theo quy định của cơ sở đào tạo.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 21; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 20; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 17; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `0545c63b-e5cd-4192-852a-015b3ff10106`.

RAG — HTTP 200, trạng thái answered, 1.94 giây:

- Đăng ký xét tuyển bổ sung tại cơ sở đào tạo đã công bố kế hoạch xét tuyển bổ sung.
- Thí sinh chưa trúng tuyển hoặc đã trúng tuyển nhưng chưa xác nhận nhập học vào một cơ sở đào tạo bất kỳ có thể đăng ký xét tuyển các đợt bổ sung theo kế hoạch và hướng dẫn của cơ sở đào tạo.
- Cơ sở đào tạo có thể công bố xét tuyển đợt bổ sung ngay sau khi có kết quả thí sinh xác nhận nhập học các đợt nếu số thí sinh xác nhận nhập học các đợt thấp hơn số lượng tuyển sinh của cơ sở đào tạo công bố trong tuyển sinh đợt 1.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 21; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 20; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 17; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
### Câu 76 Hạn đăng ký bổ sung đợt năm 2026?

Nhóm: XV. XÉT TUYỂN BỔ SUNG NĂM 2026

Đáp án tham khảo trong DOCX:

Theo Thông báo 151/TB-HĐTS, thời hạn đăng ký đến trước 17 giờ 00 ngày 24/08/2026.

DAG — HTTP 200, trạng thái answered, 2.84 giây:

- Hạn đăng ký bổ sung đợt 1: Từ ngày 24/8/2026 đến ngày 28/8/2026.
- Hạn đăng ký bổ sung đợt 2: Xét tuyển các ngành còn chỉ tiêu sau khi thí sinh đăng ký nhập học đợt 1, thông báo từ ngày 22/8/2026.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `7d9dd2ad-8a1b-40b7-8fc0-48760fb64425`.

RAG — HTTP 200, trạng thái answered, 1.59 giây:

- Hạn đăng ký bổ sung đợt năm 2026 chưa được quy định cụ thể trong tài liệu và số liệu cung cấp.

- Tuy nhiên, dựa trên các mốc thời gian trong kế hoạch tuyển sinh, có thể thấy rằng đợt 1 xét tuyển đã được công bố kết quả điểm trúng tuyển và danh sách thí sinh trúng tuyển vào ngày 13/8/2026.

- Không có thông tin nào về hạn đăng ký bổ sung đợt năm 2026 trong tài liệu và số liệu cung cấp.

- Nguồn: TB lịch xét tuyển ĐH — trang 4; binding `bnd_db935aea6524`, index `idx_rev_44d332b2f2e8`.
- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 2; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 77 Xét bổ sung được đăng ký bao nhiêu nguyện vọng?

Nhóm: XV. XÉT TUYỂN BỔ SUNG NĂM 2026

Đáp án tham khảo trong DOCX:

Đợt bổ sung 2026 của QNU cho phép tối đa 3 nguyện vọng theo thông báo của Trường.

DAG — HTTP 200, trạng thái answered, 3.2 giây:

- Thí sinh đăng ký tối đa 15 nguyện vọng vào các chương trình đào tạo, các cơ sở giáo dục đại học khác nhau.
- Trong trường hợp nhiều nguyện vọng đủ điều kiện trúng tuyển, thí sinh chỉ được công nhận trúng tuyển và gọi nhập học theo nguyện vọng cao nhất.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `c83e1207-a0b1-4251-aeda-fb37a9f118f5`.

RAG — HTTP 200, trạng thái answered, 1.56 giây:

Dưới đây là danh sách các thông tin liên quan đến số lượng nguyện vọng mà thí sinh có thể đăng ký:

- Thí sinh được đăng ký tối đa 15 nguyện vọng vào các chương trình đào tạo, các cơ sở giáo dục đại học khác nhau.

- Các thí sinh thuộc diện xét tuyển thẳng chỉ được đăng ký 5 nguyện vọng.

- Trong trường hợp nhiều nguyện vọng đủ điều kiện trúng tuyển, thí sinh chỉ được công nhận trúng tuyển và gọi nhập học theo nguyện vọng cao nhất.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 18; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.
- Nguồn: 2025_huong-dan-tuyen-sinh-dh-cd — trang 2; binding `bnd_8dc32a78128f`, index `idx_rev_97f860b2edbf`.
### Câu 78 Lệ phí xét tuyển bổ sung 2026 là bao nhiêu?

Nhóm: XV. XÉT TUYỂN BỔ SUNG NĂM 2026

Đáp án tham khảo trong DOCX:

Thông báo đợt bổ sung 2026 quy định 15.000 đồng/nguyện vọng.

DAG — HTTP 200, trạng thái answered, 2.81 giây:

Lệ phí xét tuyển bổ sung 2026 là 300.000 đ/thí sinh.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 10; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `9121b6d2-a5f0-481f-af61-75aad3ab2dad`.

RAG — HTTP 200, trạng thái answered, 1.59 giây:

Câu trả lời chính thức như sau:

| **Thực thể / Ngành** | **Thuộc tính** | **Giá trị dữ liệu** |
| --- | --- | --- |
| **Tuyển sinh** | **Lệ phí xét tuyển** | **Theo quy định của Bộ Giáo dục Đào tạo** |

Lưu ý: Theo tài liệu trích xuất, lệ phí xét tuyển sẽ được quy định bởi Bộ Giáo dục Đào tạo.

- Nguồn: Thong tin Tuyen_sinh_2025_QNU_V6_signed_signed_signed — trang 10; binding `bnd_5fe00fd59740`, index `idx_rev_c0a54bf73b18`.
- Nguồn: Thông tin TSĐH cập nhật — trang 10; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
### Câu 79 Điểm chuẩn bổ sung được công bố khi nào?

Nhóm: XV. XÉT TUYỂN BỔ SUNG NĂM 2026

Đáp án tham khảo trong DOCX:

Trường ban hành Thông báo 158/TB-HĐTS ngày 25/08/2026 về điểm chuẩn trúng tuyển đợt bổ sung.

DAG — HTTP 200, trạng thái answered, 3.75 giây:

Điểm chuẩn bổ sung thường được công bố sau khi kết thúc đợt xét tuyển chính thức và sau khi thí sinh xác nhận nhập học vào các đợt trước đó. Theo quy định, cơ sở đào tạo có thể công bố xét tuyển đợt bổ sung ngay sau khi có kết quả thí sinh xác nhận nhập học các đợt thấp hơn số lượng tuyển sinh đã công bố trong đợt 1.

Dưới đây là bảng thông tin về thời gian công bố điểm chuẩn bổ sung:

| Năm áp dụng | Thời gian công bố điểm chuẩn bổ sung |
| --- | --- |
| 2023 | 10 ngày sau khi công bố phương án xét tuyển |

Lưu ý rằng thời gian công bố điểm chuẩn bổ sung có thể thay đổi tùy thuộc vào quy định của từng cơ sở đào tạo.

- Nguồn: Quy chế tuyển sinh đại học 2026 - 363 — trang 21; binding `bnd_62ff83603eec`, index `idx_rev_e0dc72a9102b`.

Kiểm tra DAG: {"is_grounded": true, "failure_reasons": [], "unsupported_numbers": []}

Mã workflow: `fab657c4-c11c-4c8b-ac3b-d1137650ba73`.

RAG — HTTP 200, trạng thái answered, 0.95 giây:

| Thời gian | Điểm chuẩn bổ sung | 
| --- | --- |
| 2023 | **Chưa có thông tin** |

### Câu 80 Học phí QNU năm 2026 khoảng bao nhiêu?

Nhóm: XVI. HỌC PHÍ, HỌC BỔNG VÀ CHÍNH SÁCH HỖ TRỢ

Đáp án tham khảo trong DOCX:

Thông báo đầu mùa 2026 dự kiến học phí toàn khóa các ngành cử nhân đại trà khoảng 83–97 triệu đồng/khóa 4 năm; chương trình kỹ sư đại trà khoảng 112,3 triệu đồng/khóa 4,5 năm. Mức thực tế thực hiện theo quy định và thông báo tài chính của Trường.

DAG — HTTP 200, trạng thái insufficient_context, 5.06 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["Unsupported numbers detected: 63,9, 2149, 67.590.000, 460.000, 9.200.000, 88.643.000, 603.000, 12.663.000"], "unsupported_numbers": ["63,9", "2149", "67.590.000", "460.000", "9.200.000", "88.643.000", "603.000", "12.663.000"]}

Mã workflow: `db092667-0cb8-43ba-9222-c249f65062a9`.

RAG — HTTP 200, trạng thái answered, 2.31 giây:

Câu trả lời của Trợ lý AI chính thức của Trường Đại học Quy Nhơn (QNU) là:

| **Học phí** | **Giá trị** |
| --- | --- |
| Mức học phí phù hợp với hoàn cảnh gia đình | **2149** (Đồng) |
| Mức học phí học kỳ I (tạm thu) | **9.200.000** (Đồng) |
| Học phí toàn khóa học (tạm tính) | **67.590.000** (Đồng) |
| Mức học phí /tín chỉ (tạm tính) | **460.000** (Đồng) |

Lưu ý: Thông tin trên được trích dẫn từ tài liệu chính thức của Trường Đại học Quy Nhơn (QNU) và áp dụng cho năm học 2026-2027.

- Nguồn: TB học phí K49 — trang 1; binding `bnd_4bd40bc6a972`, index `idx_rev_57e15196704d`.
- Nguồn: HD nhập học — trang 1; binding `bnd_e4492e8d7016`, index `idx_rev_42074c9dee55`.
- Nguồn: Thông tin TSĐH cập nhật — trang 1; binding `bnd_b7be60e6ada9`, index `idx_rev_33446987e9fc`.
- Nguồn: FLYER TUYENSINH 2026-final2-16032026 (1) — trang 1; binding `bnd_ed14ffc71bc0`, index `idx_rev_46812c2c2247`.
### Câu 81 Sinh viên QNU có học bổng không?

Nhóm: XVI. HỌC PHÍ, HỌC BỔNG VÀ CHÍNH SÁCH HỖ TRỢ

Đáp án tham khảo trong DOCX:

Có nhiều nguồn học bổng khuyến khích học tập và học bổng tài trợ. Dữ liệu năm 2025 từng tổng hợp 19 đơn vị tài trợ, 226 suất với tổng giá trị khoảng 1,57 tỷ đồng; đây là số liệu tham khảo, không phải cam kết số lượng cho năm 2026/2027.

DAG — HTTP 200, trạng thái insufficient_context, 2.23 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `e7c5a225-1332-4b8b-945d-83f1a302dc48`.

RAG — HTTP 200, trạng thái insufficient_context, 0.36 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

### Câu 82 Sinh viên sư phạm có chính sách hỗ trợ học phí/sinh hoạt phí không?

Nhóm: XVI. HỌC PHÍ, HỌC BỔNG VÀ CHÍNH SÁCH HỖ TRỢ

Đáp án tham khảo trong DOCX:

Có. Sinh viên sư phạm thuộc đối tượng hưởng chính sách theo Nghị định 116/2020/NĐ-CP được Nhà nước hỗ trợ tiền đóng học phí bằng mức thu học phí của cơ sở đào tạo và hỗ trợ chi phí sinh hoạt 3.630.000 đồng/tháng, thời gian hỗ trợ theo số tháng học thực tế nhưng không quá 10 tháng/năm học. Sinh viên đăng ký hưởng chính sách phải thực hiện các nội dung cam kết theo quy định; sau khi tốt nghiệp, nếu thuộc trường hợp phải bồi hoàn kinh phí hỗ trợ do không công tác trong ngành giáo dục sau 02 năm kể từ ngày có quyết định công nhận tốt nghiệp hoặc có công tác trong ngành giáo dục nhưng không đủ thời gian theo quy định, sinh viên phải thực hiện bồi hoàn kinh phí đã được Nhà nước hỗ trợ. Chính sách hiện thực hiện theo Nghị định 116/2020/NĐ-CP và các quy định sửa đổi, bổ sung hiện hành.

DAG — HTTP 200, trạng thái insufficient_context, 8.01 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: 0256.3846.156 hoặc Email: tuyensinh@qnu.edu.vn nhé!


Kiểm tra DAG: {"is_grounded": false, "failure_reasons": ["rag_status 'insufficient_context' not in accepted", "require_grounded_answer set and status != answered", "citations list is empty", "answer self-declares lack of context"], "unsupported_numbers": []}

Mã workflow: `ed2a41a0-101c-4dbf-8fd5-c9d3aa4413bb`.

RAG — HTTP 200, trạng thái insufficient_context, 2.78 giây:

Chào bạn! Thông tin này hiện chưa có trong Đề án tuyển sinh chính thức của Trường Đại học Quy Nhơn mà mình được cung cấp.

Bạn có thể thử hỏi mình các chủ đề phổ biến như:
- **Phương thức xét tuyển**: Phương thức xét tuyển và điều kiện nộp hồ sơ
- **Điểm chuẩn**: Điểm chuẩn trúng tuyển các ngành đào tạo
- **Học phí & Học bổng**: Mức học phí và chính sách học bổng của trường

Nếu cần hỗ trợ trực tiếp, bạn vui lòng liên hệ Ban Tư vấn Tuyển sinh QNU qua Hotline: **0256.3846.156** hoặc Email: **tuyensinh@qnu.edu.vn** nhé!

