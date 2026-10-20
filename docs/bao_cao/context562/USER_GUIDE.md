# Context562 — Hướng dẫn kiểm tra hội thoại

1. Mở trợ lý tuyển sinh, vào Sandbox hoặc trang chat công khai. Bắt đầu đoạn chat mới.
2. Gửi “Xin chào” hoặc “Cảm ơn”. Trợ lý trả lời giao tiếp, không cần trích dẫn tài liệu.
3. Gửi câu hỏi kiến thức có ngành/mã và năm rõ ràng. Dù bắt đầu bằng “Xin chào”, câu hỏi vẫn qua kho tri thức và kiểm chứng nguồn đã xuất bản.
4. Sau câu hỏi về một ngành, gửi “Cảm ơn”, rồi “Còn môn tự chọn?”. Hệ thống dùng chủ đề trước nếu xác định chắc. Khi đổi ngành/năm, thông tin mới được ưu tiên.
5. Nếu trước đó so sánh hai ngành rồi hỏi “ngành đó”, trợ lý có thể hỏi lại để xác định ngành. Nó không được tự chọn một ngành làm dữ kiện chắc chắn.

Chọn đoạn chat ở thanh bên sẽ khôi phục đúng phiên của đoạn đó. Tạo đoạn mới bắt đầu ngữ cảnh mới. Lịch sử được tạo trước thay đổi này chưa có thông tin tiếp tục phiên an toàn; có thể xem lại nhưng cần nêu đủ chủ đề ở lượt đầu để bắt đầu context server mới. Capability tiếp tục phiên có hạn một ngày; khi hết hạn, hãy tạo đoạn chat mới.

Chỉ quản trị viên thấy phần **Phân luồng và truy xuất** trong Sandbox. Kiểm các mục `intent`, `classification_method`, `rag_invoked`, `router_model_calls`, `rewritten_query` và `context_referents`. Với lời chào thuần: SOCIAL, RAG false, model calls 0. Không chia sẻ token tiếp tục phiên hoặc header xác thực.

Không hiểu “có trích dẫn” là điểm chất lượng đã được đo. Giao diện giữ trạng thái chưa đo khi không có phép đo thật.

## Giới hạn hiện tại cần biết

Lời chào, cảm ơn và hỏi danh tính đã chạy trên trình duyệt thật. Provider thật đã kiểm ba ca giải ngữ cảnh. Tuy nhiên, hỏi số liệu AM-0007/2026 từ DOCX hiện xuất bản còn gặp lỗi `EVIDENCE_CONTEXT_MISSING` ở bước đóng gói bằng chứng có sẵn. Nguồn đầy đủ, nhưng tập context gửi tiếp thiếu dòng nguồn của fact. Hệ thống chặn thay vì trả số thiếu căn cứ. Chưa nghiệm thu toàn luồng Knowledge E2E cho tài liệu này.

Không cần tải lại tài liệu, nạp lại vector, duyệt proposal hoặc xuất bản lại chỉ để kiểm lời chào. Những dữ liệu đó được giữ nguyên trong phiên triển khai này.
