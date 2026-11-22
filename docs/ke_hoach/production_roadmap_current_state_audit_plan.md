# Kế hoạch mở rộng Production & Rà soát hiện trạng hệ thống

Tài liệu này định hướng các hạng mục mở rộng để đưa hệ thống từ bản chạy ổn định trên môi trường phát triển/thử nghiệm lên vận hành **Production** thực tế, giữ nguyên các luồng đang hoạt động tốt (5 tầng xử lý tài liệu, `hybrid_rerank`, `Row Cards` kèm tên `Sheet`, ràng buộc chống suy diễn từ viết tắt trong `SYSTEM_PROMPT`, và `Benchmark Suite`), đồng thời **không** thêm giới hạn thời hạn/hiệu lực văn bản.

---

## 1. Các mảnh ghép mở rộng trọng tâm

### Mảnh ghép 1: Quản lý Người dùng & Phân quyền theo Đơn vị / Vai trò (Ưu tiên hàng đầu)
- **Phạm vi đơn vị (Unit / Workspace):** Tách phạm vi dữ liệu kho tri thức, trợ lý AI và lịch sử hội thoại theo từng đơn vị, đảm bảo người dùng/đơn vị này không can thiệp trái phép vào dữ liệu của đơn vị khác (trừ phần chia sẻ được phép rõ ràng).
- **Phân vai trò (RBAC):** Phân định rõ quyền hạn giữa:
  - Quản trị hệ thống (`super_admin`)
  - Quản trị đơn vị (`unit_admin`)
  - Biên tập viên tri thức (`knowledge_editor`)
  - Người dùng nội bộ (`viewer` / `member`)
- **Quản trị tài khoản & kiểm soát quyền API/UI:** Tạo/khóa tài khoản, gán đơn vị và vai trò, đặt lại mật khẩu, và kiểm tra quyền chặt chẽ ở cả API backend lẫn giao diện quản trị (không chỉ ẩn nút ở frontend).

### Mảnh ghép 2: Gia cố Kênh Công khai & Tích hợp Ngoài
- **Chống quá tải / lạm dụng kênh công khai:** Rate limit theo IP/phiên, giới hạn độ dài câu hỏi và xử lý an toàn khi model/vector store tạm thời quá tải hoặc mất chỉ mục.
- **Trải nghiệm chia sẻ & nhúng:** Hỗ trợ sao chép liên kết nhanh, mã nhúng (`iframe` / widget) cho cổng thông tin/website đơn vị và thông báo phạm vi/miễn trừ trách nhiệm rõ ràng cho người dùng khách.
- **Tích hợp hệ thống ngoài:** Quản lý API key theo trợ lý (tạo/thu hồi) để phần mềm nội bộ khác gọi vào khi cần.

### Mảnh ghép 3: Log Hội thoại Bắt lỗi & Vòng lặp Kiểm thử
- **Ghi nhận tín hiệu chẩn đoán từng lượt hỏi – đáp:** Lưu trạng thái truy xuất (`retrieved_count`, điểm khớp cao nhất, nguồn trích dẫn), độ trễ (`latency_ms`), kênh (`public` / nội bộ / hỏi thử), trạng thái (`ok` / `empty_evidence` / `error`) và phản hồi/gắn cờ lỗi — ghi log theo hướng không làm chậm hay làm hỏng luồng trả lời chính.
- **Lọc & đưa ca lỗi vào kiểm thử:** Hỗ trợ lọc nhanh các lượt `empty_evidence`, lỗi, phản hồi chưa tốt hoặc độ trễ cao trên giao diện hội thoại/nhật ký để tái hiện và đối chiếu qua `Benchmark Suite`.

### Mảnh ghép 4: Sao lưu Tự động, Nhật ký Kiểm toán & Dọn dẹp Dữ liệu
- **Sao lưu định kỳ:** Lịch sao lưu và quy trình khôi phục cho cơ sở dữ liệu quan hệ, vector store và thư mục lưu trữ file gốc.
- **Nhật ký kiểm toán (Audit Log):** Ghi lại các thao tác nhạy cảm (quản lý user/vai trò, duyệt/xóa tài liệu, bật/tắt kênh công khai, đổi cấu hình nhà cung cấp).
- **Chính sách lưu trữ (Retention):** Dọn dẹp an toàn dữ liệu tạm/phiên khách/log cũ quá hạn để tránh đầy đĩa trên máy chủ.

---

## 2. Yêu cầu đối với Agent ở bước rà soát hiện trạng (Chưa sửa code vội)

Trước khi bắt tay vào viết code mới, Agent cần **chỉ đọc code và cấu hình hiện có** (tuân thủ nghiêm ngặt `AGENTS.md`, không sửa file) để lập **Báo cáo hiện trạng ("Đã có gì — Đang thiếu gì")** cho cả 4 mảnh ghép trên, tập trung vào:

1. **Người dùng, Đơn vị & Phân quyền:** Hiện đã có bảng/model/API/UI nào cho `User`, `Unit` (đơn vị), `Role`/quyền hạn và kiểm tra quyền ở endpoint chưa? Đang còn thiếu điểm nào?
2. **Kênh Công khai & Tích hợp:** Tab/luồng `Công khai` và API chat hiện đã có rate limit, giới hạn độ dài, mã nhúng/widget hoặc API key theo trợ lý chưa?
3. **Hội thoại, Nhật ký & Log bắt lỗi:** Các bảng lưu hội thoại/tin nhắn, nhật ký hệ thống và giao diện `Hội thoại` / `Nhật ký` hiện ghi nhận những trường nào (có `empty_evidence`, `latency`, `citations`, `feedback`/gắn cờ chưa)?
4. **Sao lưu, Audit Log & Dọn dẹp:** Hiện có script/cấu hình backup định kỳ cho DB/Vector store/File gốc, bảng audit log thao tác quản trị và chính sách dọn dẹp dữ liệu cũ chưa?
5. **Đề xuất thứ tự triển khai tối thiểu & an toàn:** Dựa trên cấu trúc thực tế của repo, Agent gợi ý thứ tự làm từng bước nhỏ nhất để không làm gãy luồng hiện tại.