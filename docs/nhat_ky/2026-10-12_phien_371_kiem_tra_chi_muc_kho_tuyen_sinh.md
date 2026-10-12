# Phiên #371 — Kiểm tra chỉ mục kho tuyển sinh

- Ngày: 2026-10-12.
- Mục tiêu: Xác nhận trạng thái sau khi người dùng thêm 4 văn bản vào `col_admissions`.
- Phạm vi: Chỉ đọc PostgreSQL/Qdrant và mã điều khiển nạp vector; không sửa runtime hoặc dữ liệu nghiệp vụ.

## Bằng chứng thực tế

- PostgreSQL chạy transaction read-only: 4 binding active, mỗi nguồn có source revision `ready` và Markdown không rỗng (74.712, 50.114, 23.436, 101.505 ký tự).
- Cả 4 `active_index_revision_id` đều null; `active_vector_generation_id` của kho null, `index_epoch = 1`.
- Không có vector generation và index revision thuộc kho tuyển sinh.
- Qdrant phản hồi thành công: không có namespace `col_admissions` hoặc namespace generation có tiền tố `col_admissions_`.
- Nguồn: QĐ 2705 (PDF), Quy chế đào tạo K48 (PDF), Thông tin tuyển sinh 2026 (DOCX), 30.signed (PDF).

## Kết luận và hướng dẫn

Đã bóc tách/chuẩn hóa không đồng nghĩa đã embedding hoặc xuất bản. Trạng thái giao diện phù hợp dữ liệu thực: chưa có chỉ mục vector.

Chọn cả 4 nguồn → Nạp vector → chọn embedding từ ModelOps → đợi worker nạp thành công → Xuất bản. `VectorLoadControls` tự tạo generation khi chọn model mới; không cần tạo riêng trong Nâng cao. Xuất bản áp dụng toàn kho và yêu cầu mọi nguồn active có chỉ mục cho Markdown hiện hành. Nạp vector tái sử dụng Markdown đã lưu, không OCR lại.

## Kiểm chứng và thay đổi

- PostgreSQL/Qdrant live read-only: đạt; kiểm tra contract UI qua mã nguồn, chưa thao tác browser.
- Ruff/Pytest/Vite: không chạy, không thay đổi mã ứng dụng.
- Không embedding, publish, OCR lại, reset, migration, restart, sửa provider/key hoặc qnu-sso.
- Chỉ thêm nhật ký/snapshot, cập nhật mục lục, PROJECT_CONTEXT và WORK_LOG; không thay đổi quy trình hiện hữu.
- Bài học: Phân biệt source revision ready, index revision ready và chỉ mục published; không dùng trạng thái binding active để kết luận chatbot đã có vector.
