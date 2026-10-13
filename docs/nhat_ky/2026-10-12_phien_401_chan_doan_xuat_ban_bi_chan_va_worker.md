# Phiên #401 — Chẩn đoán xuất bản bị chặn và log worker

## Phạm vi

Đối chiếu ảnh lỗi `Cần duyệt dữ liệu có cấu trúc`, log worker do người dùng cung cấp, trạng thái PostgreSQL của kho `col_admissions` và logic review/publish. Chỉ đọc và chẩn đoán; không duyệt, publish, retry, reset, restart hoặc sửa code.

## Kết luận

- Worker hoạt động ổn định: PostgreSQL có 19 job ingestion và 19 job index build đều `completed`; thế hệ `vg_2fd42633fb29` có 19/19 index revision `ready`, 19/19 parity đạt, không có failure code.
- Ba kết quả `status=missing` lúc worker vừa khởi động là job Redis cũ không còn `JobRecord` sau lần reset trước; chúng được kết thúc nhanh và không ảnh hưởng batch hiện tại.
- Các cảnh báo PDF Inspector timeout/exit dùng đường fallback giữ native evidence; cảnh báo DrawingML thiếu converter có thể làm giảm bằng chứng hình ảnh nhưng không làm job thất bại. Cuối log: `j_failed=0`, `j_ongoing=0`, `queued=0`.
- Xuất bản bị chặn đúng tại `FACT_SET_REVIEW_REQUIRED`: 8 nguồn có structured artifact `review.status=required`.
- Có lệch trạng thái: cả 8 source revision lại đang `ready`. Nhánh tái sử dụng artifact lấy `quality_report` cũ nhưng không nâng `overall_status` thành warning theo `structured_artifact.issues`; UI chỉ hiện nút duyệt khi revision là `review_required`, còn publication kiểm trực tiếp artifact nên vẫn chặn.

## Tám nguồn cần duyệt

1. Báo cáo tư vấn tuyển sinh 2024 — visual trang 4.
2. Báo cáo tư vấn tuyển sinh 2025 — visual trang 4, 7.
3. Khảo sát tư vấn tuyển sinh 2022 — visual trang 3, 4.
4. Các ngành tuyển sinh 2025 — visual trang 1.
5. Flyer tuyển sinh 2026 — 3 vùng visual trang 1.
6. Hướng dẫn nhập học — visual trang 6 và 6 vùng trang 7.
7. NQ57 Phương hướng tuyển sinh 2025 — header bảng chưa giải quyết trang 8–9 và visual trang 2.
8. Phương hướng tuyển sinh 2024 — header bảng chưa giải quyết trang 5–6.

## Đề xuất xử lý

Sửa đồng bộ trạng thái review khi reuse artifact, cho UI hiển thị danh sách issue/page và cho phép cán bộ duyệt structured artifact một cách có audit. Sau đó duyệt đúng 8 nguồn, dựng lại candidate nếu fact-set thay đổi và xuất bản. Không được ép publish hoặc tự chuyển `approved` trong DB.
