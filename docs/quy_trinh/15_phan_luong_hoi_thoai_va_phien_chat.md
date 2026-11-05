# 15 — Phân luồng hội thoại và phiên chat

> **TÀI LIỆU LỊCH SỬ — không phải hiện trạng V1.** Nội dung dưới đây mô tả hệ thống `backend/` + `frontend/` trước V1 (hai thư mục đã gỡ khỏi checkout) và chỉ dùng để truy vết. Bản đang chạy là [`backendV1/`](../../backendV1) + [`frontendV1/`](../../frontendV1); xem [bản đồ tài liệu](../README.md).

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

## Số liệu bảng có mã thực thể (Context565)

Mã trong câu hỏi là ứng viên. Server đối chiếu đúng cột mã trong snapshot đã xuất bản, giữ số0đầu và dấu phân cách; không lấy mã từ ô giá trị hoặc đoán theo tên gần giống. Metadata cũ thiếu entity_code có thể được đọc qua tọa độ canonical row/column đã kiểm hash, không ghi lại artifact hoặc yêu cầu nạp vector lại.

Chọn fact theo mã, đại lượng, năm dữ liệu, đơn vị, điều kiện và revision. Chỉ tiêu khác số ghi nhận; bare “Số lượng” chưa đủ căn cứ thì giữ unknown. Câu hiện tại đổi đại lượng/đơn vị phải thắng phần rewrite được kế thừa. Câu hỏi nhiều mã thiếu một phần không được đánh dấu đủ dữ liệu.

Fact được chọn vẫn phải giữ đủ canonical row/header/chú thích, đóng gói toàn nhóm trong ngân sách và qua claim projection. Citation giữ exact raw span; approved semantic overrides giữ nguyên. Fact answer trực tiếp không cần LLM/dense/reranker; câu tiếp nối có thể cần model để xác định ý định, lịch sử không trở thành bằng chứng dữ kiện. Trace chọn fact chỉ hiển thị trong debug có quyền quản trị.

Kiểm chứng và giới hạn: [Context565](../bao_cao/context565/REVIEW_READY.md). E2E đạt không thay cho full regression, benchmark chất lượng hoặc quyền xuất bản.
