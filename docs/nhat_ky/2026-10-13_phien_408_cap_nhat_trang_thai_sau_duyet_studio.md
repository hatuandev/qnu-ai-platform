# Phiên #408 — Cập nhật trạng thái sau duyệt Studio

## Mục tiêu và nguyên nhân

Sau khi duyệt trong Studio OCR, quay lại danh sách nguồn vẫn thấy trạng thái cũ cho đến khi F5. Studio chỉ tải lại bản hiển thị và trang chi tiết; cache `knowledge-bindings` và `collection-summary-metrics` không được invalidated. Cấu hình QueryClient có staleTime 30 giây nên dữ liệu cache còn được coi là mới khi quay lại.

## Thay đổi

- Thêm helper `refreshSourceQueries` dùng TanStack Query để invalidate và refetch cả query inactive của nguồn, binding list, collection, summary và vector state, giới hạn đúng collection/source.
- Studio gọi và chờ helper ngay sau khi API lưu/duyệt thành công, trước khi tải lại bản hiển thị. Nếu bước tải Studio sau đó lỗi, cache danh sách vẫn đã được làm mới.
- Thao tác duyệt/từ chối ở trang chi tiết dùng cùng helper; bỏ refetch trùng trong callback Studio.
- Giữ nguyên giao diện và primitives có sẵn, chỉ sửa quản lý server state theo quy chuẩn frontend/clean code. Không thay backend, dữ liệu, Redis hay cơ sở dữ liệu.

## Tệp chính

- `frontend/src/features/knowledge/utils/source-query-cache.ts`
- `frontend/src/features/knowledge/utils/source-query-cache.test.ts`
- `frontend/src/components/knowledge/ocr/document-studio-workspace.tsx`
- `frontend/src/features/knowledge/source-detail-page.tsx`

## Kiểm tra

- Regression với QueryClient thật và query inactive: đạt; các cache nguồn/danh sách/summary/vector cập nhật trước khi helper hoàn tất, kho khác giữ nguyên.
- Biome bốn tệp thay đổi: đạt.
- Frontend Vite + TypeScript build: đạt.
- Chưa thao tác duyệt trên tài liệu thật bằng trình duyệt; không tự duyệt thay người dùng.

## Bài học

Mutation làm thay đổi một nguồn phải invalidation cả các read model phụ thuộc vào nguồn đó, đặc biệt query của trang danh sách đang inactive. Refetch riêng trang đang mở không đồng bộ trạng thái khi điều hướng trở lại.
