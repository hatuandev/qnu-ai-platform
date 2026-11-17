# Phiên 981 — Ổn định rà soát bản biên soạn có bảng lớn

## Phạm vi

Thực hiện bước 1 của kế hoạch. Giữ hợp đồng trích dẫn đã sửa, kiểm tính toàn vẹn của phần cần đối chiếu, đưa vị trí nguồn vào cổng duyệt và chạy riêng worker trên bản đã biên dịch. [Báo cáo ban đầu](../compilation-review-run-defects.md).

## Thay đổi

- Dùng lại phản hồi Qwen đã lưu và danh sách nguồn của đúng phần biên dịch. Bộ phân tích nhận đủ 129 trích dẫn hợp lệ và từ chối khi thay bằng ID ngoài nguồn.
- Worker đối chiếu danh sách đánh giá do bộ lập kế hoạch tạo với manifest. Nhánh vượt ngân sách phân biệt ngữ cảnh bắt buộc và đầu ra dự kiến. Phần báo cáo lưu vị trí bảng trên bản nguồn đã ghim, cùng đoạn biên soạn cần kiểm tra. Các vị trí này dùng để mở nguồn.
- Hộp duyệt FE V2 hiện vị trí bảng và đoạn cần đối chiếu. Khi người dùng mở, UI tải đúng revision. PDF mở ở đúng trang, các định dạng khác có thể tải tệp gốc.

## Kiểm chứng

- Backend V1: Ruff đạt, 26 unit test liên quan đạt. 13 integration test về rà soát phân đoạn, đối chiếu trực tiếp và cổng duyệt đạt. Ca chạy riêng bổ sung đạt 1/1, dùng provider giả lập để xác nhận worker hoàn tất báo cáo khi bảng vượt ngân sách, giữ đoạn cần đối chiếu ở phía server và trả đúng revision và trang.
- Frontend V2: Biome và `npm run build` đạt. Chrome headless với phản hồi API thử nghiệm và PDF thật xác nhận chỉ tải tệp khi mở, URL xem trước trỏ trang 11, xem được đoạn và đóng lại được.
- Cổng full V1 chạy fail-fast, 556 đạt và dừng ở hai lỗi nền đã ghi từ phiên 978: `test_legacy_source_deletion_718.py::test_deleted_source_can_request_new_permanent_preview_but_other_deletes_stay_blocked` và `test_migration_baseline_661.py::test_initial_schema_offline_sql_creates_v1_without_touching_legacy`.

## Môi trường

Kiểm thử thật dùng PostgreSQL sao chép cục bộ, Redis riêng và chỉ đọc tệp gốc từ MinIO. Artifact rà soát ghi vào thư mục kiểm thử cục bộ. Không đổi bản phát hành, không chạy lại OCR hoặc biên dịch, không chạy bộ 100 câu G3.

## Kết quả với Qwen thật

- Bản đã biên dịch `cmp_2b61941ad6e0` tạo được lượt `rvw_4a0a269cda53` với 43 phần. Worker đi qua bước lập kế hoạch và nhận phản hồi model.
- Sau 462 giây, worker dừng với `compilation_review_refinement_atomic_limit`. Có 8 nút hoàn tất, 4 nút lỗi và 37 nút đang chờ trong cây đã chia. Tổng usage thực ở 12 nút có số đo là 218.203 token. Chưa có báo cáo tổng hợp.
- Đọc lại raw tại các nút lỗi. ID đơn vị đánh giá có đủ, nhưng tham chiếu bên trong bị trùng, vượt phạm vi hoặc thiếu cho kết luận cần dẫn chứng. Nút nhỏ nhất 49 có 12 tham chiếu nguồn ngoài danh sách được cấp. Chốt kiểm chứng từ chối đúng các kết luận đó.
- Thử một lần trên chính nút 49 với đầu ra có schema, dùng ModelOps và bộ kiểm tra tham chiếu hiện có. Qwen trả hoàn tất, vượt qua kiểm tra hợp đồng và dẫn chứng, dùng 6.139 token. Kết quả này chỉ áp dụng cho nút 49. Chưa chạy lại toàn lượt với chế độ đầu ra có schema.
- Đã đối chiếu DB ứng dụng. Bản phát hành vẫn ở trạng thái `published` và lượt kiểm thử chỉ tồn tại trong DB cô lập.
