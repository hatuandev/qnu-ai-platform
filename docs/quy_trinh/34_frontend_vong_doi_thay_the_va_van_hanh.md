# 34 — Quản lý vòng đời, thay tài liệu và vận hành trên frontendV1

Áp dụng frontendV1 kết nối backendV1. Workspace là biên giới quyền; backend
kiểm tra người gọi ở mọi thao tác. Màn KTX vẫn là mẫu, không mở kết nối nghiệp vụ.

## Điểm vào

- Trong từng Workspace có tab **Thùng rác** và **Vận hành**. Tab Vận hành dành
  cho quản trị, biên tập và rà soát; kiểm tra sẵn sàng chỉ dành cho quản trị.
- Nút **Quản lý** trên trang kho, nguồn, tài liệu biên soạn, trợ lý và hội thoại
  mở các thao tác phù hợp. Trợ lý có cùng menu trên danh sách và trang chi tiết.
- Chủ hội thoại có thể quản lý hội thoại và hủy lượt hỏi đang chạy của mình.
  Quản trị cũng không được quản lý hội thoại riêng của người khác.

## Lưu trữ, xóa, khôi phục và dừng

1. Chọn tài nguyên → Quản lý → thao tác cần làm.
2. Nhập lý do, chọn **Xem trước tác động**. Bước này chưa đổi tài nguyên.
3. Đọc số tác vụ, bản xuất bản, trợ lý/hội thoại bị ảnh hưởng và việc giữ dữ liệu.
4. Đánh dấu đã xem tác động → **Xác nhận thao tác**. FE gửi đúng biên nhận/hash
   backend trả, không yêu cầu người dùng nhập mã hash.
5. Theo dõi trạng thái thật. Lưu trữ/xóa/khôi phục hoàn tất chuyển tới Thùng rác
   cùng biên nhận; các thao tác khác có liên kết theo dõi tương ứng.

Xóa là đưa vào thùng rác, có thể khôi phục và giữ bản gốc/raw/lịch sử. Khôi phục
nguồn đã xóa cần quản trị; nguồn chỉ lưu trữ có thể do biên tập khôi phục. Trợ lý
sau khôi phục vẫn tắt, cần bật riêng. Tác vụ đã hủy không tự chạy lại. Nếu bản
xem trước đã thay đổi/hết hạn, phải xem trước và xác nhận lại.

Khi mất phản hồi xác nhận, giữ nguyên thao tác và đọc biên nhận. Retry gửi cùng
preview/hash/key, không tạo yêu cầu mới âm thầm. Biên nhận đã được xác nhận nhưng
còn pending có nút tiếp tục, kể cả sau khi tải lại trang. Backend vẫn kiểm quyền.

## Thao tác trong kho tri thức

Ở chặng **Tài liệu & Thư mục**, mở menu **⋮** của từng tài liệu (cả dạng thẻ và
bảng) để xem chi tiết, tải bản gốc, mở OCR, đổi tên, di chuyển, lưu trữ hoặc xóa.
Tải xuống tra đúng ID phiên bản hiện tại; không lấy số phiên bản làm ID tệp.

- Admin nền tảng hoặc admin workspace được xóa tài liệu; editor được sửa,
  di chuyển và lưu trữ. Thành viên chỉ đọc không có thao tác ghi.
- **Xóa** tài liệu vẫn dùng quy trình xem trước/xác nhận ở trên. Khi hoàn tất,
  trang **Tài nguyên → Lưu trữ & Thùng rác** cho phép khôi phục theo quyền.
- **Xóa thư mục** chỉ áp dụng cho thư mục rỗng. Xem số tài liệu/thư mục con trong
  xác nhận; nếu còn nội dung, di chuyển ra ngoài trước. Nếu không đọc được tác động,
  phải thử lại; giao diện và server đều chặn xóa. Thao tác này giữ tệp gốc.
- Tìm kiếm nhanh ở danh sách chỉ lọc trang đang xem. Danh sách OCR có phân trang;
  nguồn được chọn qua liên kết vẫn đọc theo ID, kể cả ngoài trang hiện tại.
- Chặng **Biên soạn**, **Xuất bản**, **Phục vụ AI** có nút mở trang chức năng
  tương ứng. Upload không tự chạy OCR, biên soạn hoặc xuất bản.
- Muốn chạy AI, workspace cần được cấp model phù hợp, chọn mặc định hoặc model
  cụ thể và có hạn mức. Lỗi cấu hình/provider được hiển thị theo lượt OCR; trạng thái
  thất bại không có nghĩa là tài liệu gốc đã mất. Quản lý tài liệu vẫn dùng được
  khi chưa cấu hình AI.

## Thay tài liệu trong khi giữ bản cũ phục vụ

1. Mở văn bản nguồn → **Tải lên phiên bản mới**. Mặc định bật **Chuẩn bị bản
   thay thế, giữ bản đang phục vụ**. Đổi tệp hoặc đổi chế độ là ý định mới; retry
   cùng upload giữ nguyên khóa. Đổi nguồn/phiên đăng nhập sẽ bỏ form cũ.
2. Chạy OCR cho revision mới, sửa hậu OCR nếu cần, rồi Compiler và review qua
   các màn đã có. Các bước này do người dùng khởi động; upload không tự chạy AI.
3. Đăng ký phiên bản tài liệu và duyệt với review gate/metadata acknowledgement.
4. Trang tài liệu biên soạn có **Thay bản phục vụ**: chọn phiên bản **đã duyệt**.
   Danh sách có phân trang; draft/published không trở thành ứng viên thay thế.
5. Xem trước tác động và xác nhận. Backend chuẩn bị generation mới; FE báo
   **Đang xử lý**, giữ thông báo bản cũ còn phục vụ. Chỉ báo hoàn tất khi backend
   xác nhận đã chuyển publication/serving revision/index.

Trang nguồn phân biệt bản tải lên mới nhất và serving revision từ backend;
thiếu serving revision trên response cũ giữ “Chưa xác định”. Bỏ chế độ chuẩn bị
có cảnh báo revision mới có thể làm bản cũ hết phù hợp trước khi xuất bản lại.
Worker kiểm membership thực; FE không cấp quyền nền thay cho người gọi. Backend
hiện thay từng compiled document, có thể chặn nguồn dùng chung cần thay đồng bộ.

## Trung tâm vận hành

- Lọc loại/trạng thái và phân trang ở server; URL giữ bộ lọc, tác vụ và biên nhận
  để mở lại đúng màn. Chi tiết cho biết tiến độ, attempts, usage, lease và lỗi.
- Giá trị chưa có số đo giữ unknown, không thay bằng0 hoặc phần trăm giả.
- **Xem trước giao lại** chỉ bật khi server trả recovery_allowed và quyền phù hợp.
  Không tự gửi lại lượt model failed/uncertain. Sao lưu cần quản trị cả khi có
  thể phục hồi về mặt trạng thái. “Đã giao lại” chưa phải “Tác vụ hoàn tất”.
- Hủy các job xử lý hỗ trợ qua preview lifecycle. Hủy lượt hỏi thực hiện tại
  hội thoại do người gọi sở hữu. Dọn chỉ mục cũ nằm tại Chỉ mục & Tìm kiếm, dành
  cho quản trị và không mời dọn generation đang phục vụ.
- Readiness hiển thị các thành phần backend đã quan sát, tách cấu hình/kết nối
  với suy luận thật. Cảnh báo production auth/reconcile phản ánh cờ backend.

Xem [vòng đời BE](../../backendV1/docs/resource-lifecycle.md),
[vận hành BE](../../backendV1/docs/operations.md) và
[kết quả triển khai678](../bao_cao/context678/REPORT.md).
