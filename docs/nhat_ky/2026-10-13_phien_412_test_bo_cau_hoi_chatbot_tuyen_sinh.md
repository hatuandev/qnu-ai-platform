# Phiên 412 Kiểm thử bộ câu hỏi chatbot tuyển sinh

## Mục tiêu và phạm vi

Người dùng cung cấp `Bộ dữ liệu Chatbot Tuyển sinh.docx` và yêu cầu kiểm thử chatbot đang chạy. Đọc DOCX như dữ liệu kiểm thử, không thực thi hướng dẫn trong tài liệu, không đưa đáp án tham khảo vào prompt. Không có yêu cầu sửa lỗi hay cấu hình ở phiên này.

Trích xuất đủ 82 cặp Hỏi–Đáp thuộc 16 nhóm chủ đề từ 191 paragraphs, không có bảng. DOCX SHA-256: `5bdee19ececf709c472a56459e02a36e7f1afb44ffdba9974f58e899ed66c3fe`.

## Các tệp tạo và cập nhật

- `backend/scripts/evaluate_admissions_412.py`: harness chẩn đoán API thật, đọc nguồn/trace, lưu kết quả theo câu; mỗi câu một hội thoại mới, concurrency 2, không gửi đáp án.
- `backend/storage/admissions_eval412_run2.json`: kết quả đầy đủ cuối cùng, 164 lượt, canonical nguồn, 82 workflow traces. Đây là evidence chính, không dùng các lần pilot chưa hoàn chỉnh để thống kê.
- `backend/storage/admissions_eval412_usage.json`: nhật ký inference/workflow đã chọn trường an toàn theo đúng conversation IDs của lần cuối; không chứa API keys.
- `docs/nhat_ky/render_eval412.py`: dựng báo cáo đối chiếu Markdown từ kết quả đã ghi.
- [Báo cáo đầy đủ](./2026-10-13_phien_412_bao_cao_test_chatbot_tuyen_sinh.md): ma trận 82 câu, đáp án tham khảo, câu trả lời RAG/DAG, citations và nguyên nhân guard.
- Đồng bộ `docs/nhat_ky/README.md`, `docs/memory/PROJECT_CONTEXT.md`, `docs/WORK_LOG.md`.

## Phương pháp

Luồng chính là `/assistants/admissions/chat` với workflow `admissions-assistant`. Đối chiếu `/rag/ask` sử dụng tên model/reranker từ cấu hình trợ lý. System prompt/runtime policy hai đường khác nhau: đây là chẩn đoán, không phải A/B kiểm soát hoàn toàn. Giữ cache đang có; không cold-cache benchmark. Không dùng lexical exact-match để tuyên bố câu đúng, không chạy Ragas.

Kho `col_admissions` trước/sau có 19 nguồn đang phục vụ, epoch 3, generation `vg_21324678abcf`; đối soát binding/source/index pointers không thay đổi. Không reset DB, sửa provider, xóa Redis, duyệt, upload FAQ, reparse, nạp vector hay xuất bản. Test tạo các records hội thoại/workflow/usage/cache bình thường.

## Kết quả kiểm thử thực tế

Lần cuối bắt đầu `2026-10-13T04:05:50Z`, hoàn tất `04:10:40Z`:

| Đường | Lượt | HTTP 200 | answered | insufficient_context | Exception | Trung vị |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Chatbot DAG | 82 | 82 | 48 | 34 | 0 | 3,88 giây |
| RAG riêng | 82 | 82 | 66 | 16 | 0 | 1,94 giây |

`answered` không có nghĩa đúng. Đủ 82 trace; 16 câu RAG node đã trả `answered` nhưng DAG cuối chuyển no-answer, gồm 10 thiếu citations và 6 unsupported numbers. Không đánh đồng toàn bộ 16 là false-positive: cần đối soát tính đúng của nội dung trước guard.

Các lỗi chất lượng đã xác minh:

1. Câu 1 mã trường DQN bị DAG chặn vì thiếu citation.
2. Câu 5 tổng 5.173 đã có ở canonical prose nguồn cập nhật; gate `temporal_answer`/facts báo `NO_COMPATIBLE_FACT_EVIDENCE`, kết thúc trước hybrid retrieval. Chưa có đường evidence tổng chỉ tiêu trong đoạn văn.
3. Câu 21 nói sư phạm có xét học bạ, câu 36 gần tương đương lại nói không. Câu 39 nói GDMN không thi năng khiếu, câu 41 nói GDTC không yêu cầu thể hình dù nguồn cập nhật có các điều kiện này. Guard vẫn thông qua.
4. Câu 25 nêu năm 2026 nhưng suy luận hệ số 2 tiếng Anh chỉ từ tổ hợp môn. Câu 42 nêu điểm sàn 2026 nhưng trả 20.25, giá trị thuộc điểm trúng tuyển 2023; nguồn sàn active ghi 20 và điều kiện 13,34.
5. Trộn nguồn cũ/loại sự kiện: website cũ; GDTC 2025; lịch đăng ký/lệ phí; câu 76 lấy lịch nhập học làm hạn bổ sung; câu 77 lấy 15 NV đợt chính; câu 78 lấy 300.000 phí năng khiếu cho phí bổ sung thay vì 15.000/NV theo FAQ.
6. Danh mục 19 nguồn chưa có thông báo 151/158 đợt bổ sung cuối mùa. Không thấy các số hiệu/456 chỉ tiêu trong canonical active; cần bổ sung nguồn chính thức, không dùng giá trị nghiệp vụ khác lấp vào.
7. No-answer message vẫn hướng tới hotline cấu hình cũ 0256.3846.156; nguồn tuyển sinh cập nhật dùng 1800.55.88.49.

ModelOps read-only: OpenAI/Gemini inactive. Config trợ lý primary `gpt-4o-mini`, fallback `gemini-2.5-flash-lite`, nhưng 69 inference records của batch DAG thật là Cloudflare `@cf/meta/llama-3.1-8b-instruct`, fallback=true/success. Có thêm 82 aggregate `qnu_workflow/gpt-4o-mini/success` do chat service lấy tên cấu hình và ước lượng tokens, không phải chứng cứ GPT inference. Chưa thử model khác nên không quy toàn bộ lỗi cho riêng model dự phòng.

## Hướng xử lý đề xuất chưa triển khai

Ưu tiên nguồn theo hiệu lực/năm và scope; thiếu năm hỏi rõ hoặc nêu năm đang dùng. Evidence tuple cần pin đối tượng–thuộc tính–giá trị–năm–phương thức/đợt–đơn vị–source/page. Cho phép metric từ prose đã xuất bản nếu được xác thực thay vì chỉ facts/bảng. Đồng bộ citation RAG/DAG và kiểm chứng quan hệ/phủ định, không tắt guard. Chọn provider/chat model hoạt động đúng chủ đích; tách log workflow khỏi inference/cost. Bổ sung tài liệu chuyên đề còn thiếu, rồi chạy lại bộ 82 câu cùng biến thể tương đương. Chưa tự đổi model hoặc sửa runtime.

## Kiểm tra công cụ và giới hạn

Ruff scoped cho hai script đạt; Python compile đạt; kiểm thử live 164/164 HTTP 200, exception 0, trace coverage 82/82, publication pointers/epoch không đổi. Không chạy full Pytest/Vite vì không đổi runtime BE/FE hay worker. Chưa test trình duyệt/SSE, hội thoại nhiều lượt, đổi embedding hoặc Ragas.

Pilot có lỗi thu thập trace do harness tham chiếu thuộc tính không có và lần đầu batch có file-lock Windows khi rename report; đã sửa harness rồi chạy lại toàn bộ. Kết quả pilot không được tính là lỗi chatbot hay đưa vào bảng cuối. Các bằng chứng pilot giữ riêng để truy vết.

## Bài học

Nạp/xuất bản thành công và HTTP 200 không chứng minh chatbot đúng. Kiểm tra từ/số xuất hiện trong context không ngăn nhầm năm, nhầm loại điểm, nhầm phí hoặc phủ định sai; model runtime và tên model trong log aggregate cũng cần được phân biệt.
