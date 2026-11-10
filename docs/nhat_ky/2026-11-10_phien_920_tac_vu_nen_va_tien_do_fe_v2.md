# Phiên 920 — Tác vụ nền và tiến độ FE V2

## Yêu cầu và phạm vi

Người dùng báo thông báo chồng lên bảng tác vụ sau upload và yêu cầu tiến độ %. Chỉ sửa FE V2; giữ BE, dữ liệu, nguồn, ModelOps và các thay đổi chưa commit khác.

## Thay đổi

- `providers.tsx` dùng AppNotifications chung: toast góc trên phải, chừa 72px; bảng tác vụ giữ góc dưới phải. Theme theo ứng dụng.
- Bảng tác vụ hiển thị tên một lần, hàng phẳng, tên dài có tooltip; nút thu gọn/ẩn/dừng phân biệt. Theo dõi vẫn mount khi thu gọn hoặc ẩn, chỉ hiển thị tác vụ thuộc workspace đang chọn. Gộp các bước xử lý thành 1 line tiến độ % duy nhất (`unifiedPercent` 0-100%), chuyển bước OCR sang Compilation nối tiếp từ 50% không thụt lùi về 0%, nhãn bước hiển thị chi tiết (ví dụ: "Đã đọc 8/14 trang", "Đã chuẩn bị 2/4 phần", "Đã chuẩn bị xong"). Tối ưu bố cục hàng sang cấu trúc **Compact 2-Line** tinh gọn: Dòng 1 gồm icon + tên tệp + %/CTA 'Mở bản nháp' + nút đóng; Dòng 2 gồm thanh progress mỏng 4px và nhãn trạng thái ngắn gọn, giảm 60% chiều cao, loại bỏ hoàn toàn các cụm từ lặp lại.
- Đọc endpoint processing-run đúng source/revision/run đã ghim và compiler progress đúng run của intent. % theo số đơn vị hoàn tất / tổng trong bước hiện tại, không ước lượng thời gian hay gán trọng số toàn quy trình. DOCX pagination=document gọi đơn vị, không giả trang vật lý. Tổng chưa biết/không hợp lệ thì không hiện %; ready mới báo hoàn tất chuẩn bị. 100% một bước vẫn chờ intent kết thúc.
- Lỗi truy vấn theo dõi không đổi job thành uncertain; giữ trạng thái backend, báo mất kết nối và tiếp tục đọc. Chỉ thao tác dừng tường minh gửi POST cancel. Hoàn tất làm mới danh sách và summary, toast có khóa ổn định.
- Thêm DTO/request/hook đọc tiến độ, helper kiểm số liệu và regression trình duyệt cô lập.

## Kiểm chứng thực chạy

CWD frontendV2:

- `node --test --experimental-strip-types src/lib/document-task-progress.test.ts src/lib/knowledge-studio-helpers.test.ts`: **11 passed, 0 failed**, exit 0. Kiểm chứng đầy đủ tính đơn điệu của 1-line progress %, chuyển bước giữ 50% không reset 0%, hoàn thành 100% khi ready, terminal states không giả 100%.
- Lượt đầu 17/18: fixture remount cùng ID tác vụ đã terminal giữ observer cache cũ; tách kiểm dừng sang context mới đúng lifecycle. Không bỏ assertion; lượt cuối thêm kiểm dừng độc lập.
- `npm run build`: Vite + TypeScript exit0.
- `npm run lint`: Biome toàn FE V2 **165 files**, exit0, không sửa tự động.
- Scoped Biome12tệp exit0; root `git diff --check` exit0.
- Ảnh desktop1440x900/mobile390x844 light/dark tại `tmp/background-920/`, đã mở xem.

Mock chứng minh UI/API contract, không chứng minh OCR/model thật. **NOT RUN**: upload/OCR/model live, full BE. Không restart, migrate, reindex, publish, commit/push. Giữ lỗi nền BE/F13 lịch sử. Không thêm trường BE hay thay đổi quy trình nghiệp vụ.
