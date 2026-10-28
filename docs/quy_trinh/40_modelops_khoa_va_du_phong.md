# 40 — ModelOps: nhóm khóa và model dự phòng

Vào **ModelOps → Providers → chọn provider → Khóa và dự phòng**.
Tính năng áp dụng cho V1. Mặc định nhóm khóa tắt và chưa có model dự phòng;
cấu hình mới không tự thay model/default/quyền/hạn mức đang dùng.

Nếu phiên chạy cũ chưa nạp mã mới, dừng đúng phiên đó bằng Ctrl+C rồi chạy lại
`.\make.ps1 v1-dev`. Không cần migration mới cho các chức năng này.

## Nhóm khóa

1. Thêm các khóa hợp lệ ở **API keys**. Chúng phải thuộc cùng endpoint/model.
2. Bật **Dùng nhóm khóa**. Mỗi khóa được giữ riêng cho một lượt gọi đang chạy.
   Khóa có số ưu tiên nhỏ hơn được chọn trước; các khóa cùng ưu tiên luân phiên
   theo lần cập nhật gần nhất.
3. Chọn **Bên quản lý thử lại**:
   - **QNU**: tối đa 1–3 lượt gọi, tính cả lượt đầu, trong cùng thời gian cho phép.
   - **Gateway / 9router**: QNU chỉ gửi một lần, để gateway quản lý việc thử lại.
4. Đặt thời gian nghỉ khi sai khóa hoặc giới hạn tần suất, rồi **Lưu chính sách**.

Chỉ HTTP401/429 mới cho phép tạm nghỉ và thử khóa khác. Lỗi nội dung, quyền,
phản hồi sai hoặc không xác định model đã xử lý hay chưa sẽ báo lỗi. Nếu server
báo đã sử dụng token, QNU không tự thử lại. Hủy yêu cầu sẽ dừng việc thử khóa.

Bảng khóa hiển thị **Sẵn sàng**, **Đang gọi**, **Tạm nghỉ** hoặc **Đã thu hồi**.
Sẵn sàng nghĩa là có thể được chọn, không phải chứng nhận khóa đã chạy thử thành công. Bấm **Làm mới** để xem trạng thái gần nhất. Khóa tạm nghỉ vẫn tồn tại; không cần
xóa và thêm lại chỉ vì bị giới hạn tần suất.

## Model dự phòng

1. Tạo và chạy thử model dự phòng ở provider riêng; khai báo capacity đúng model.
2. Cấp cả model gốc và model dự phòng cho workspace cần dùng.
3. Tại provider mặc định, chọn thứ tự dự phòng cho từng tác vụ rồi lưu.

QNU chỉ chọn dự phòng **trước khi bắt đầu tác vụ và đặt ngân sách**, khi model
mặc định bị tắt hoặc không có khóa sẵn sàng. Model dự phòng vẫn phải đủ quyền,
đúng chức năng và đủ capacity; hết hạn mức không được lách bằng model khác.
Model đã được người dùng chọn cụ thể sẽ giữ nguyên.

OCR/Compiler giữ model đã ghi nhận khi chạy. Embedding giữ đúng model của chỉ
mục, kể cả khi một model khác có cùng số chiều vector. QNU không chuyển model
sau một request timeout hoặc sau khi model đã trả lời lỗi.

Các provider QNU được tạo ở phiên694 mới có một model cho mỗi chức năng. Vì vậy cần bổ sung model/khóa
dự phòng hợp lệ trước khi cấu hình một chuỗi có ý nghĩa; hệ thống không tự tạo
model dự phòng hay cấp quyền thay bạn.

## Nhật ký và giao thức

**Lượt gọi gần đây** cho biết model, lần thử, thời gian, HTTP/lỗi và token nếu
server có trả. **Mã truy vết** liên kết lượt gọi, khóa và sổ sử dụng của workspace.
Không có prompt, ảnh OCR hoặc secret trong lịch sử này. Token chưa đo vẫn hiện
là chưa biết. Các lượt **Chạy thử** chẩn đoán có lịch sử riêng ở phía trên.

Thông tin giao thức lấy từ BE, phân biệt adapter QNU đã hỗ trợ với chức năng
model đã được chạy thử. Responses API, streaming và tools chưa được hỗ trợ.
Không suy chất lượng hay giới hạn context từ nhãn loại provider.

Đổi endpoint/model khiến chính sách cũ cần xem và lưu lại. Sau nâng cấp này,
một số kết quả chạy thử cũ có thể yêu cầu thử lại do thay cách nhận diện khóa;
hoạt động giữ/tạm nghỉ khóa không làm cũ kết quả kiểm tra mới.

[Hợp đồng BE](../../backendV1/docs/modelops-resilience.md) ·
[Lấy danh sách và chạy thử](39_modelops_lay_danh_sach_va_chay_thu.md)
