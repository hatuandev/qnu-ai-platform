# Context628 — Thử một PDF thực tế trước Compiler

Ngày 2026-10-25, người dùng yêu cầu chọn một PDF và xác nhận phạm vi: **bóc tách Markdown/JSON rồi chạy Compiler trên PDF mới**. Đây là lượt thử mới; không chạy lại bộ Compiler ba DOCX đã được nghiệm thu ở Context627.

**Kết quả: NEEDS_ATTENTION.** Đã tạo cặp Markdown/JSON và thử cửa vào Compiler. Compiler từ chối nguồn `review_required` bằng `KNOWLEDGE_COMPILATION_INVALID / source_not_current_ready`, **0 lượt gọi LLM Compiler**. Chưa hoàn thành biên soạn nội dung PDF; không coi kiểm tra chặn đúng là Compiler PASS.

**Xác minh tiếp ở [Context629](../context629/REVIEW.md):** người dùng chỉ định endpoint Paddle nội bộ, đã thử đúng một crop qua Redis capacity thật và nhận HTTP200/errorCode0 trong1,578s. Phép thử mới không thay lịch sử628 hoặc chứng nhận toàn PDF. Phát hiện số văn bản có trong raw header nhưng không có Markdown mà header rescue đang đọc; chưa sửa app.

## Tài liệu và đầu ra

- Nguồn: [Thông báo quy đổi tương đương QNU 2026](../../tai_lieu/tuyen_sinh/Thong_bao_quy_doi_tuong_duong_QNU_2026_Chinh%20thuc-signed.pdf), 5 trang. Đây là PDF thực tế khác PDF mô phỏng 18 trang đã thử trước.
- SHA-256 nguồn: `96207cca90ecd30df23d9ffcf74fb982a6277e4d89b08270e3465a4a2bd5dc8e`.
- [Bản Markdown dễ đọc](../../../backend/storage/context628/automatic/reader.md), [Markdown QNU v1.0](../../../backend/storage/context628/automatic/standard.md), [JSON companion đã kiểm hash](../../../backend/storage/context628/automatic/structured.json).
- [Đối soát độc lập](../../../backend/storage/context628/audit.json), [kết quả luồng tự động](../../../backend/storage/context628/automatic/result.json), [biên nhận Compiler](../../../backend/storage/context628/automatic/compiler-receipt.json), [biên nhận tổng hợp](../../../backend/storage/context628/closeout.json).

Nguồn được lưu qua LocalStorageDriver trước xử lý. Bản gốc, trang PNG, native glyph/layout, bbox, bảng, raw evidence, MD/JSON và projection đều được giữ trong Storage riêng. Đã xem trực quan đủ 5 trang. Không ghi corpus vào Git.

## Những gì đạt và chưa đạt

| Kiểm tra | Kết quả | Bằng chứng/giới hạn |
|---|---|---|
| Cú pháp QNU RAG Markdown v1.0 | PASS | Validation 117 blocks, 0 lỗi/0 cảnh báo cú pháp |
| MD/JSON lưu bền vững và khớp nguồn/hash | PASS | `load_document` đọc lại cặp thật, kiểm checksum/identity/parity; source replay native đạt |
| Giữ ô từ lưới đã bóc tách sang JSON fields | PASS | 760/760 vị trí raw khớp lưới dẫn xuất, gồm cả header chưa được phân vai; không phải chứng nhận mọi ngữ nghĩa ô đúng |
| Nhận diện header | FAIL | Cả 3 phần bảng có `header_depth=0`, toàn bộ `header_path=[]` |
| Bảng nối trang | Chưa đạt | Phụ lục 2 ở trang 4–5 còn `table_continuation_needs_review` |
| Readiness nội dung | NEEDS_ATTENTION | 7 blockers: 6 vùng hình chưa xác nhận + 1 bảng nối trang; 760 limitations do ô chưa có vai trò header xác định |
| Compiler từ chối nguồn chưa sẵn sàng | PASS cho guard | Preview/create thực tế đều chặn; không hạ trạng thái kiểm duyệt hoặc giả nguồn `ready` |
| Compiler phân tích/tổng hợp PDF | NOT RUN | Nguồn chưa đạt, 0 model dispatches; chưa có bundle biên soạn |
| OCR thật | NOT RUN | Lượt đầu bị môi trường thử chặn ở Redis trước inference; lượt xác minh sau bị kiểm duyệt tự động từ chối trước thực thi |
| Kiểm tra ứng dụng/full regression | NOT RUN | Không sửa mã ứng dụng; kết quả full Context627 là lịch sử, không phải PASS hiện tại |

**760 limitations không có nghĩa mất 760 ô.** Header đang được giữ như dòng raw thay vì bị xóa; mọi ô chưa có tên cột đã được chứng minh nên bị giữ dưới dạng literal/ambiguous. Đây là hạn chế về vai trò cấu trúc và diễn giải, không phải bằng chứng rằng tất cả giá trị đã bị mất.

## Đối chiếu các phần bảng

| Phần nguồn | Cấu trúc nhìn thấy trên PDF | Kết quả hiện tại |
|---|---|---|
| Phụ lục 1, trang 3 | 23 cột; header 2 tầng; 22 dòng dữ liệu | Lưới 24×23, đủ 23 cột nhưng 2 dòng header vẫn nằm trong 24 dòng raw; mất đường dẫn như tổ hợp → SPT/HB/THPT |
| Phụ lục 2, trang 4 | 4 cột; 1 header; 45 dòng dữ liệu | Lưới 46×4; header chưa phân vai |
| Phụ lục 2, trang 5 | Tiếp bảng trang 4; lặp header; 5 dòng dữ liệu còn lại | Lưới 6×4; header chưa phân vai, liên kết nối bảng chưa xác nhận |

Như vậy nguồn có **2 bảng logic, 3 phần bảng vật lý**, không phải ba bảng nghiệp vụ độc lập. Đã xác nhận bảng rộng không bị nở số cột như lỗi PDF mô phỏng cũ. Chưa chứng nhận khả năng dùng từng giá trị để quy đổi điểm.

## Nguyên nhân đã có bằng chứng

1. **Header nền trắng bị bỏ qua.** `header_role_evidence` trong `backend/app/modules/knowledge/parsers/pdf_header_roles.py` yêu cầu đồng thời chữ đậm và dải nền màu chung. Header của tài liệu này in đậm nhưng nền trắng. Probe với raw glyph/drawings cho thấy trang 3 hai dòng đầu bold, dòng dưới thường; trang 4–5 dòng đầu bold, các dòng dưới thường; mọi dải màu đều rỗng. Hàm trả `{}`, nên `native_table` giữ `header_depth=0`. Không phải thiếu context LLM: giai đoạn này không gọi LLM.
2. **Nối bảng chưa chắc chắn.** Bảng trang 5 chưa có header được xác minh để liên kết an toàn với phần trang 4. Cần kiểm cấu trúc, căn cột, nội dung header và phạm vi; không tự nối mọi bảng 4 cột.
3. **Phân loại vùng ký/dấu còn thận trọng quá rộng.** Sáu vùng hình trên trang 2, 3, 5 vẫn chặn vì `visual_content_untranscribed`; xem trang gốc cho thấy liên quan vùng chữ ký/dấu. Cần giữ nguyên hình và chứng cứ, phân biệt hình mang dữ liệu với dấu/ký; chưa tự bỏ cờ hoặc tạo bản chép được duyệt.
4. **Công thức cần được kiểm riêng.** Công thức nội suy ở trang 1 được giữ glyph nhưng phân số bị tách qua các dòng/block trong Markdown dễ đọc. Chưa chứng minh biểu diễn này đủ cho thực thi phép tính hoặc Compiler hiểu đúng; không tự đoán hay sửa công thức nguồn.

## Phần OCR bị chặn và giới hạn kết luận

Luồng `extract_pdf(auto, auto)` chọn native cho cả 5 trang. Chỉ vùng đầu trang 1 cần header rescue vì số/ngày được chèn ở vị trí rời khỏi dòng nhãn trong native text.

Lượt thử đầu dùng Redis cô lập tại cổng không phục vụ; Paddle bị `PROVIDER_CAPACITY_UNAVAILABLE` trước khi gửi OCR. Các provider dự phòng cấu hình sẵn không hoạt động trong bản cấu hình đọc được; header rescue cuối trả `OCR_CONTENT_EMPTY`. **Không được quy lỗi tiền kiểm này cho OCR server hoặc tài liệu thật.** Nó không phải kết quả OCR upstream.

Đã chuẩn bị lượt kiểm tra mới giữ nguyên cơ chế Redis capacity. Kiểm duyệt tự động từ chối `context628_pipeline.py --live-ocr` vì chưa có xác nhận rõ nội dung và đích OCR có thể nhận PDF, bao gồm fallback cloud. Không thực thi lại bằng đường vòng, không đổi chính sách bảo vệ và chưa gửi request OCR upstream từ lượt bị chặn.

Preview chỉ đọc xác định PaddleOCR nội bộ đang hoạt động theo cấu hình tại `http://100.105.13.53:8080`. Phạm vi có thể xin phép tiếp theo là **chỉ ảnh vùng đầu trang 1**, bbox `[0,0,595.32,336.77]` PDF points, chứa tên trường/tiêu đề/số/ngày và phần căn cứ; chỉ Paddle nội bộ, không fallback cloud. Điều này chưa phải phê duyệt hoặc áp dụng nội dung OCR. OCR đầu trang cũng không tự giải quyết lỗi header bảng nền trắng.

## Hướng xử lý đề xuất

Ưu tiên sửa nhận diện header nền trắng bằng tổ hợp bằng chứng độc lập từ typography, ô gộp, ranh giới hình học và khác biệt với dòng dữ liệu. Không chỉ nới thành “hễ chữ đậm là header”; cần regression giữ dòng dữ liệu đầu, bảng không header và ô gộp thân bảng. Sau đó xử lý nối bảng có bằng chứng, phân loại dấu/ký và biểu diễn công thức. Chỉ thử lại Compiler khi nguồn thực sự đủ điều kiện; không sửa code trong lượt thử này.

## An toàn và dọn dẹp

Đã xác minh DB, MinIO, Qdrant cấu hình là loopback; DB dùng thử là hai database mới có nonce/comment sở hữu. Không migration DB đang dùng. Cấu hình provider có bảo vệ được sao chép trực tiếp trong bộ nhớ giữa hai phiên DB local để phục vụ môi trường thử, không xuất credential ra file/log. Bản sao credential nằm trong database thử đã được xóa cùng database.

Hai database thử đã dọn và xác minh không còn: `qnu_test_context616_6cf816359f0c`, `qnu_test_context616_adf215b3232d`. Storage bằng chứng và runtime còn được giữ theo chính sách; không báo đã xóa Storage. Không tắt chính sách để dọn tệp.

Hash trước/sau xác nhận mã ứng dụng, nguồn PDF, collection/binding/source/index/assistant/provider/key rows đang dùng giữ nguyên. Không nạp vector, xuất bản, đổi model mặc định, sửa mã ứng dụng, restart, commit hoặc push.

Các lệnh thực chạy, cwd và exit code nằm trong `closeout.json`. Lượt native đầu có lỗi guard Windows asyncio trong script thử, các tiền kiểm import/DB/Storage dừng trước run intent đã được sửa; không coi chúng là lỗi parser. Đối soát ban đầu khác metadata do writer thêm tham chiếu raw evidence vào bản sao lưu; lượt cuối kiểm chính xác phần khác biệt hợp lệ này và mọi block/nguồn.
