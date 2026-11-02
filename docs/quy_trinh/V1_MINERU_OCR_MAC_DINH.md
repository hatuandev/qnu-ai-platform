# V1 — MinerU làm OCR mặc định

MinerU được đăng ký trong ModelOps bằng giao thức **MinerU PDF OCR**, URL dịch vụ
kết thúc `/mineru` hoặc `/mineru/v1`, API key nhập tại ModelOps và model có chức năng
**OCR** (tên nhãn có thể là `mineru`). Không cần nhập context/input/output token LLM.
Chọn model đó làm mặc định hệ thống và trong danh sách model được cấp cho đơn vị.

## Luồng sử dụng

1. Khởi động API/worker bằng bộ lệnh V1 hiện có; schema cần0011_mineru_ocr.
2. Tải PDF hoặc DOCX. Tự động ưu tiên phần chữ có sẵn; phần cần OCR đi qua MinerU.
   Chọn OCR bắt buộc nếu muốn nhận dạng toàn bộ bằng OCR. Lựa chọn provider tường
   minh luôn được giữ, kể cả Nemotron.
3. MinerU nhận cả PDF một lượt. App giữ task ID và chờ hoàn tất, không cố định300s
   cho toàn tài liệu. Giới hạn worker vận hành vẫn cấu hình được.
4. Kết quả được lưu thành ZIP raw, JSON canonical và Markdown có nguồn/bbox/bảng.
   Mở màn rà soát, yêu cầu AI đề xuất sửa chính tả nếu cần; đối chiếu ảnh, sửa và lưu
   phiên bản được xác nhận rồi tiếp tục Compiler → duyệt → xuất bản → lập chỉ mục.

## Khi bị ngắt hoặc gặp lỗi

- Có task ID: xử lý phục hồi nội bộ chỉ kiểm tra tác vụ đã có; không gửi PDF lại.
- POST mơ hồ chưa có task ID: trạng thái uncertain; kiểm tra ở server trước khi tạo
  lượt mới. Không tự retry để làm kết quả xanh.
- Thiếu/trùng trang hoặc kết quả sai cấu trúc: báo lỗi; raw đã lưu giữ nguyên.
- Chỉ có tín hiệu kỹ thuật hoàn tất không chứng minh OCR đúng chính tả. Người dùng
  vẫn phải xem và xác nhận nội dung quan trọng.
- MinerU không công bố token: tổng token/chi phí là chưa biết; không tính0 như usage
  đo được. Workspace bị khóa vẫn không chạy. Quota tháng vẫn cần cấu hình.

## Phạm vi cấu hình phiên823

Đã cấu hình DB app root và E2E93faa11f0caf. Chưa restart app đang mở, chưa deploy.
Tài liệu cũ không tự OCR lại. Workspace mới hoặc DB cài mới cần cấp model/mặc định
qua ModelOps; không có provider/key hardcode. Runner provider-setup riêng có thể áp
lại profile test Nemotron khi chạy lại; kiểm ModelOps mặc định trước khi test tiếp.

Live363:32trang,36,89s trong lượt quan sát,600mục rà soát,8bảng. Cache/warm chưa được
kiểm soát; thời gian này không phải cam kết cho mọi tài liệu. [Chi tiết phiên823](../nhat_ky/2026-11-02_phien_823_mineru_ocr_mac_dinh.md).
