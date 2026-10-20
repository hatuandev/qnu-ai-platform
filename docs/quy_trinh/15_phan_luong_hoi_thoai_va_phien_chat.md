# 15 — Phân luồng hội thoại và phiên chat

Chat dùng chung backend cho Sandbox, cổng chat và widget nhúng. Sau kiểm quyền/phiên và input guard, hệ thống phân loại toàn thông điệp trước khi truy xuất nguồn.

- Lời chào/cảm ơn/tạm biệt thuần túy trả lời giao tiếp từ cấu hình, không gọi model/retrieval.
- Câu hỏi danh tính/phạm vi trả lời từ cấu hình trợ lý server.
- Câu hỏi kiến thức, kể cả có lời chào, vẫn phải qua nguồn đã xuất bản và kiểm chứng bằng chứng.
- Câu tiếp nối dùng các câu người dùng hữu ích trong phiên, không lấy khẳng định assistant làm dữ kiện. Một structured call gộp phân loại và rewrite khi cần; ràng buộc trong câu hiện tại được ưu tiên hơn thông tin cũ trong lịch sử, thiếu/mâu thuẫn căn cứ thì hỏi lại.
- Lỗi model/hạ tầng hoặc bằng chứng không biến thành câu trả lời giả hay xã giao.

Phiên mới public không cần đăng nhập. Để tiếp tục, client giữ `X-Conversation-Token` do server trả về và gửi cùng conversation ID. Không xem ID đơn lẻ là quyền sở hữu. Capability hết hạn sau một ngày, gắn đúng trợ lý/phiên, không phải access token. Không đưa vào log, URL, Markdown export hoặc báo cáo.

UI chat giữ session trong metadata của đúng đoạn chat. Chọn A/B hoặc tải lại phải khôi phục session tương ứng; đoạn chat cũ chưa có capability bắt đầu server context mới. Widget độc lập giữ session trong bộ nhớ tới khi trang bị tải lại. Stream thiếu sự kiện hoàn tất hoặc có lỗi phải hiển thị lỗi, không đánh dấu thành công.

Debug phân luồng trong Sandbox yêu cầu `ai.access.admin`; đọc lịch sử quản trị yêu cầu `ai.audit.view`. Không cấp quyền từ client hoặc model. Theo dõi reason, intent, rewrite, RAG invocation và model thực gọi, không công khai trace nội bộ.

Kiểm thử và các giới hạn live hiện tại: [Context562](../bao_cao/context562/REVIEW_READY.md). Đây không phải quy trình nạp hoặc xuất bản tài liệu.
