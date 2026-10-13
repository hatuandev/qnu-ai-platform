# Phiên #406 — Fix hộp thoại duyệt nhiều nguồn

## Mục tiêu

Chẩn đoán trường hợp danh sách đã nhận đúng 8 nguồn cần xác nhận nhưng nút `Duyệt đã chọn` không tạo thay đổi, khiến thao tác xuất bản tiếp tục bị khóa; xác định có cần reset cơ sở dữ liệu hay không.

## Chẩn đoán

- PostgreSQL vẫn giữ nguyên 8 structured artifact ở trạng thái `review.required`; thời điểm cập nhật không đổi sau thao tác trên giao diện. Vì vậy request duyệt chưa commit, không phải dữ liệu đã duyệt nhưng bị Redis trả lại lỗi cũ.
- OpenAPI runtime có endpoint bulk review và probe an toàn với source không tồn tại trả đúng RFC 7807 `SOURCE_NOT_FOUND`; backend mới đã được nạp.
- Hộp xác nhận bulk review được render bên trong Dialog nạp vector. Hai modal Radix lồng nhau tạo xung đột focus/portal, nên thao tác mở hộp xác nhận có thể im lặng ngay tại giao diện trước khi gọi API.
- Không có căn cứ reset DB. Reset sẽ xóa dữ liệu hợp lệ nhưng không sửa được lỗi tương tác modal.

## Thay đổi

- Tách `BulkSourceReview` thành khối chọn nguồn thuần, chỉ phát selection lên component cha.
- Chuyển `ConfirmDialog` duyệt hàng loạt thành sibling của Dialog nạp vector, cùng mẫu kiến trúc đã dùng cho xác nhận xuất bản.
- Mutation bulk review được quản lý ở `VectorLoadControls`; sau thành công xóa selection và làm mới toàn bộ trạng thái knowledge/vector.
- Khóa đóng Dialog, nạp vector và xuất bản trong lúc request duyệt đang chạy để tránh thao tác đua.
- Tiếp tục dùng các primitive có sẵn `Button`, `Checkbox`, `ConfirmDialog`; không tự duyệt, không publish và không thay đổi dữ liệu runtime.

## Tệp thay đổi

- `frontend/src/features/knowledge/components/bulk-source-review.tsx`
- `frontend/src/features/knowledge/components/vector-load-controls.tsx`

## Kiểm thử

- Biome check hai component: đạt.
- `npm run build` (Vite + TypeScript): đạt, 5092 module được biên dịch.
- Không chạy backend suite vì bản sửa cuối chỉ thay đổi frontend và endpoint backend đã được probe trên runtime.

## Bài học

Các modal xác nhận dùng portal/focus trap không nên được sở hữu bởi một component nằm bên trong modal khác. Danh sách con chỉ nên phát intent; modal xác nhận và mutation phải được nâng lên cùng tầng với modal chính để bảo đảm focus, overlay và vòng đời request ổn định.
