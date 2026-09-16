# NHẬT KÝ LÀM VIỆC — Khắc Phục Vấn Đề Chọn Tệp & Kích Hoạt FileUpload Trong Modal Nạp Tri Thức

- **Thời gian**: 2026-09-16 16:35 (UTC+7)
- **Mục tiêu**: Khắc phục lỗi người dùng bấm chọn tệp không hoạt động trong Modal Nạp Văn Bản của Kho Tri Thức. Tích hợp component `FileUpload` chuẩn, kích hoạt File Picker của hệ điều hành, kéo thả tệp, tự động điền tiêu đề từ tên file và kết nối hàm `uploadDocument` trong `apiClient`.

---

## 1. Nguyên Nhân Sự Cố

- Trong phiên làm việc trước, vùng tải lên trong Modal Nạp Văn Bản mới chỉ là một thẻ `<div>` giao diện mô phỏng tĩnh, chưa có thẻ `<input type="file" />` ẩn, chưa có trình lắng nghe sự kiện `onClick` mở hộp thoại chọn tệp của Windows/OS và chưa có state lưu đối tượng `File`. Do đó, khi người dùng nhấp chuột vào khung này thì không có bất kỳ hành động nào diễn ra.

---

## 2. Các Thay Đổi Kỹ Thuật

1. **Bổ sung phương thức `uploadDocument` trong [`frontend/src/services/api-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/api-client.ts)**:
   - Gửi `FormData` chứa tệp nguồn và tiêu đề văn bản đến endpoint `POST /knowledge/collections/{collection_id}/upload`.
   - Chuẩn bị dữ liệu tài liệu mới và cập nhật danh sách hiển thị.
2. **Tích hợp Component `FileUpload` vào [`frontend/src/pages/collection-detail-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/collection-detail-page.tsx)**:
   - Thay thế toàn bộ khối dropzone tĩnh bằng `<FileUpload />`.
   - Khi người dùng bấm vào vùng tải lên hoặc bấm vào chữ *"chọn từ máy tính"*, hộp thoại chọn tệp của hệ điều hành sẽ lập tức bật lên.
   - Hỗ trợ kéo và thả tệp trực tiếp (`drag and drop`).
   - Tự động lấy tên tệp (bỏ đuôi `.pdf`, `.docx`, thay `_` bằng khoảng trắng) để điền vào ô "Tiêu đề văn bản chính thức" nếu ô này đang trống.
   - Nút submit nạp văn bản kiểm tra `disabled={isUploading || uploadSuccess || (!selectedFile && !uploadTitle.trim())}`.
   - Tự động gọi `queryClient.invalidateQueries` để cập nhật bảng tài liệu con ngay sau khi nạp hoàn tất.
3. **Đồng bộ hóa trong Tab Wizard của [`frontend/src/pages/knowledge-page.tsx`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/pages/knowledge-page.tsx)**:
   - Cập nhật tương tự để đảm bảo tính nhất quán trên toàn bộ hệ thống.

---

## 3. Kết Quả Kiểm Thử (Verification)

- **`npm run lint`**: 0 errors (Biome check 60 files pass).
- **`npm run typecheck`**: 0 errors (TypeScript compile pass).
- **`npm run build`**: Đóng gói thành công bundle 1,083 kB trong 8.46s.
- **Playwright Browser Subagent**:
  - Đã nạp thành công tệp tài liệu mẫu.
  - Danh mục tài liệu con của bộ sưu tập ngay lập tức hiển thị văn bản mới nạp ở trạng thái "Sẵn sàng" kèm 4 Chunks đã bóc tách.
  - Video ghi hình phiên test: `verify_file_upload_1789551038455.webp`.
