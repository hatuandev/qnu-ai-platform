# Phiên 434 Gom thao tác nguồn vào menu ba chấm

Ngày: 2026-10-14. Phạm vi: giao diện nguồn tài liệu tại `/knowledge/:collectionId`.

## Mục tiêu và kết quả

Thay năm nút trên mỗi dòng bằng một nút ba chấm. Menu gồm Nạp vector, Studio OCR, Chi tiết, Ngừng dùng và Xóa; có phân cách trước nhóm quản lý nguồn, màu destructive cho Xóa và nhãn truy cập kèm tên tài liệu. Nạp vector hàng loạt vẫn nằm trên thanh công cụ.

## Tệp thay đổi

- `frontend/src/features/knowledge/components/source-actions-menu.tsx`: composition nghiệp vụ dùng Button và DropdownMenu Radix có sẵn, điều hướng giữ nguyên URL chi tiết/Studio.
- `frontend/src/components/knowledge/tabs/collection-bindings-tab.tsx`: dùng SourceActionsMenu thay cụm nút từng dòng.
- `frontend/src/features/knowledge/components/{vector-load-controls,pause-source-button,delete-source-button}.tsx`: thêm renderTrigger tùy chọn cho menu; giữ nút cũ làm mặc định ở các màn hình khác.
- Nhật ký, mục lục, WORK_LOG và memory cập nhật theo phiên.

## Quyết định kiến trúc

Giữ component sở hữu dialog, mutation và polling tác vụ bên ngoài DropdownMenuContent. Render-prop chỉ đưa phần kích hoạt vào menu; menu đóng không tháo dialog hoặc ngắt theo dõi xóa. Không thay endpoint, điều kiện duyệt, xác nhận, invalidation hay cách nạp/xuất bản. Dropdown không modal, dialog vẫn quản lý focus bằng Radix. Tái sử dụng primitives theo qnu-frontend-architect/admin-frontend-design; không tạo primitive mới.

## Kiểm chứng

- Biome scoped 5 tệp: đạt, không lỗi.
- `npm run build`: đạt, Vite 5115 modules trong 3,82 giây, TypeScript exit 0.
- Browser đăng nhập thật: menu đủ năm mục; Xóa bị khóa khi nguồn còn active; hộp thoại nạp một nguồn và xác nhận ngừng dùng vẫn mở sau khi menu đóng, focus nằm trong dialog; đã hủy, không thực hiện mutation.
- Chi tiết mở đúng `/knowledge/col_admissions/sources/bnd_4bd40bc6a972`; Studio mở cùng nguồn với `?view=studio`.
- Ảnh đối chiếu desktop 1280×900 lưu ngoài repository: `ui434-source-actions.png` trong thư mục visualizations của phiên chat.
- Mobile 390×844: năm mục nằm trong viewport, document scrollWidth 375 ≤ viewport 390; bảng cuộn nội bộ. Escape đóng menu và trả focus về đúng nút ba chấm. Đã hoàn trả viewport mặc định.
- Không chạy test/backend lint theo fast-path frontend. Không kiểm thử xóa thật hoặc nạp lại/publish; dữ liệu 19 nguồn đang phục vụ được giữ nguyên.

## Bài học và tiếp quản

Không đặt dialog owner trong menu content được tháo khi đóng. RenderTrigger mới là tùy chọn, tránh thay đổi màn hình chi tiết và toolbar đang dùng nút độc lập. Không cần reset DB/reindex để áp dụng thay đổi này. Backup vẫn tạm dừng; các hạng mục còn lại của phiên 433 giữ nguyên.
