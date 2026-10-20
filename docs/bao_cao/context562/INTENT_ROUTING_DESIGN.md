# Context562 — Thiết kế phân luồng hội thoại

## Vị trí tích hợp

Chat API → xác thực quyền/phiên → assistant runtime và input guard → `RAGService.ask` trong ModelOps policy scope → router → trả lời xã giao / làm rõ / resolver hiện có → RAG bằng chứng hiện có.

Không tạo workflow, conversation database hoặc model deployment mới. Không đổi ModelOps defaults, publication, Qdrant schema hay pipeline tài liệu.

| Intent | Hành vi |
|---|---|
| SOCIAL | Chỉ khi toàn thông điệp là giao tiếp thuần túy; template không có dữ kiện tài liệu |
| ASSISTANT_META | Danh tính/phạm vi lấy từ assistant server, không từ client/model |
| KNOWLEDGE | Đi vào RAG hiện có, giữ publication/revision/source scope |
| KNOWLEDGE_FOLLOWUP | Giải ngữ cảnh từ các câu người dùng, kiểm chứng rewrite rồi vào RAG |
| MIXED | Lời chào/cảm ơn kèm câu hỏi vẫn là yêu cầu kiến thức |
| CLARIFICATION | Hỏi ngắn khi ngữ cảnh thiếu/mơ hồ hoặc router không hoạt động |

## Quy tắc và model

Fast path khớp toàn thông điệp, có Unicode/case/punctuation normalization dành riêng cho ý định giao tiếp. Không áp normalization này lên dữ liệu nguồn. Không dùng từ điển ngành, bảng hay đáp án của tài liệu để phân loại.

Câu độc lập rõ ràng dùng nhánh hiện có, không thêm lần gọi classifier. Câu phụ thuộc lịch sử dùng một structured call gộp phân loại và rewrite qua ModelOps, timeout 20 giây và tối đa một attempt ở tầng router. ModelOps vẫn áp chính sách provider/fallback đã cấu hình. Không tạo chuỗi classifier → resolver → rewriter ba lần gọi.

`FollowupResolution` mở rộng contract cũ với intent, confidence và referents có trích đoạn người dùng. Giữ các mode explain/reformat/recheck/filter. Filter năm của một dữ kiện đơn lẻ được chuyển thành followup; không dùng nhầm thao tác lọc danh sách tổ hợp.

## Bảo toàn ngữ cảnh

- Tối đa 8 câu người dùng hữu ích cho hybrid resolver; không lấy lời assistant làm bằng chứng thật.
- Lịch sử DB thuộc đúng assistant, sau thời điểm cấu hình hiện hành; đọc phân trang tối đa 256 tin nhắn, giữ 6 cặp hữu ích. Đây là giới hạn có chủ ý, không bảo đảm nhớ chủ đề vô hạn.
- Referent phải xuất hiện nguyên văn trong câu nguồn và rewrite; nguồn chỉ là user turn. Giá trị hiện tại ưu tiên giá trị cũ. Kiểm số, mã có số 0 đầu, tập năm, năm học và phủ định; thiếu căn cứ thì hỏi lại.
- Với “Có/Không”, chỉ thêm câu hỏi làm rõ cuối của assistant làm ngữ cảnh giao tiếp; nó vẫn không cấp dữ kiện nguồn.
- Query gửi downstream gồm rewrite và câu hiện tại nguyên văn, không gửi cả lịch sử vào truy vấn vector.

Trích đoạn chính xác là điều kiện cần, không phải chứng minh mọi suy luận ngữ nghĩa của model đều đúng. Ba ca provider thật và các ca adversarial giúp kiểm contract; chưa phải benchmark độ chính xác tổng quát của model.

## Quyền và riêng tư

`?debug=true` chỉ cho quyền canonical `ai.access.admin`; client JSON không bật được private trace. ContextVar được reset đúng phạm vi request/generator. Trace dùng conversation hash, model/provider thực gọi; không ghi capability, API key hay toàn bộ lịch sử.

Chat public khởi tạo phiên mới không cần đăng nhập. Tiếp tục phiên phải gửi `X-Conversation-Token`, có audience, expiry 1 ngày, assistant và conversation ID. Khóa ký dẫn xuất HMAC tách miền khỏi token SSO/platform; không thêm secret/config mới. Không tin ID client tự chọn. Phiên bị xóa không được hồi sinh bằng capability cũ. Admin có thể mở phiên cũ trong phạm vi quyền sẵn có.

Danh sách/chi tiết lịch sử quản trị cần quyền canonical `ai.audit.view`. Không tạo permission mới ngoài manifest. CORS chỉ expose thêm header cho các origin đã được phép, không mở origin mới.

UI lưu continuation capability cùng metadata của đúng đoạn chat trong kho lịch sử trình duyệt đang có. Capability là dữ liệu nhạy cảm: không đưa vào URL, Markdown export, diagnostics, log hoặc báo cáo; xóa đoạn chat/xóa lịch sử loại bỏ metadata cùng nó. Client tích hợp tùy chỉnh phải giữ và gửi lại header để tiếp tục phiên. Lịch sử cũ không có capability chỉ cung cấp nội dung hiển thị, không chứng minh quyền nối lại server context.

## Hạ tầng lỗi

Timeout/429/502/503/504 của router dẫn tới hỏi làm rõ với mã lỗi trong debug; không bịa câu trả lời. Lỗi đọc lịch sử trả 503 riêng. Lỗi provider hoặc evidence của nhánh Knowledge vẫn là lỗi thật, không đổi thành “không có dữ liệu” hay SOCIAL.
