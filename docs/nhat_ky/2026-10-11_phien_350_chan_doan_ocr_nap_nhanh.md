# Phiên #350 — Chẩn đoán hai file nạp nhanh

## Phạm vi

Người dùng nghi nạp hai file quá nhanh và nhớ PDF quyết định có 28 trang. Kiểm tra read-only DB, worker logs, snapshot MinIO, mã reuse/parsing bằng skills ingestion/clean-code. Không chạy OCR lại, không sửa runtime, không restart/reset/xóa.

## Kết quả

- Hai batch mới `imp_batch_12c6b6b886a5` (17:44:38) và `imp_batch_e62740a065ab` (17:46:14) completed. Cả hai không có vector generation đích.
- Logs xác nhận `Reusing existing parsed source artifact` và `Reusing identical chunk set`. Các revisions mới có `reused_artifact=True`. Hai task gần nhất mất 0.34s và 0.57s, không gọi Paddle mới. Đây là tái sử dụng dữ liệu bóc tách cùng file hash/profile trong tenant/workspace, phù hợp parse-once/embed-many; không phải bằng chứng tốc độ OCR mới.
- Lần scan mới trước đó: worker gọi `/layout-parsing` lúc 17:36:39.204, task hoàn tất 17:36:55.251 (16.86s toàn task). Không lấy started_at/finished_at revision làm thời gian OCR: code hiện gán cả hai khi tạo record sau parsing.
- Đọc bytes snapshot từ MinIO bằng storage driver, xác minh SHA-256 khớp origin hash, mở PyMuPDF: PDF tuyển sinh 353,576 bytes / 14 trang; quyết định QĐ2705 18,507,242 bytes / **48 trang**, không phải 28 trong tệp đang nạp. Manifest 48 trang, 47 trang chars>0, 680 blocks, canonical markdown 70,973 ký tự. Chưa soát nội dung từng trang hoặc xác định trang chars=0 có thực sự trắng, nên không khẳng định chất lượng OCR tuyệt đối.
- Có điểm observability chưa đúng: scan đã gọi Paddle nhưng parse_provenance ghi ocr_engine=native do lấy `ocr_engine or 'native'` từ tham số thay vì engine thực tế. Bản reuse cũng giữ nhãn này. Chưa sửa theo yêu cầu chẩn đoán.
- UI chưa phân biệt bóc tách mới và dùng lại kết quả; đề xuất nhãn tái sử dụng + engine/thời gian/số trang thực và thao tác bóc tách lại có chủ đích, không tắt cache mặc định.

## Verification / giới hạn

DB + logs + bytes PDF/hash read-only đối chiếu đạt. Không pytest/build vì không đổi code. Chưa browser E2E, chưa OCR cold run mới, chưa embedding/publish. Đồng bộ nhật ký, memory và work log.
