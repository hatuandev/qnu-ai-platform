# Phiên #398 — Chẩn đoán hai job nạp vector treo

## Mục tiêu và phạm vi

Điều tra vì sao `phu-luc-hd-tuyen-sinh-2025.signed.pdf` và `HD nhập học.pdf` vẫn hiện **Đang nạp** trong khi 17 nguồn còn lại của cùng đợt đã hoàn tất. Chỉ đọc mã nguồn, log worker và PostgreSQL trong transaction `READ ONLY`; không sửa runtime, không đổi trạng thái job, không retry, không xuất bản và không thay đổi dữ liệu người dùng.

## Bằng chứng runtime

- Đợt nguồn `imp_batch_dbb64be0fa04` có 19 mục: 11 `succeeded`, 8 `review_required`, 0 queued/processing/failed. Bóc tách nguồn của cả hai tệp đã kết thúc; source revisions `ks_rev_0c8c458af2ba` và `ks_rev_af49aa4b6e1b` đều đang `ready`.
- Hai job dựng chỉ mục chính xác là:
  - `job_3f4bbde98ff8` cho binding `bnd_8357006bcb8e`, source `ks_rev_0c8c458af2ba`.
  - `job_12a2dfdd2e8c` cho binding `bnd_414020985fd0`, source `ks_rev_af49aa4b6e1b`.
- Cả hai job vẫn nằm ở `status=running`, `phase=running`, `progress=10`, không có error và không cập nhật từ khoảng 23:11 giờ địa phương; 17 job cùng batch đã `completed`.
- Log worker ghi cả hai lệnh `INSERT knowledge_facts` lỗi PostgreSQL `StringDataRightTruncationError: value too long for type character varying(512)`. Dữ liệu lỗi là các hàng bảng dài được đưa nguyên văn vào `KnowledgeFact.entity_name`, trong khi schema giới hạn `VARCHAR(512)`.
- Sau lỗi flush, `task_knowledge_index_build` gọi `_is_cancelled` và `_set_job` trên chính `AsyncSession` đang ở trạng thái rollback-only. Việc thiếu `await db.rollback()` làm phát sinh `PendingRollbackError`, nên worker không ghi được trạng thái `failed` và error vào `job_records`.
- Hàng đợi sau đó không còn hai tác vụ này; giao diện đọc đúng hai bản ghi `running` bị bỏ lại nên tiếp tục hiển thị **Đang nạp** vô thời hạn. Đây không phải lỗi OCR, embedding, khóa provider hay trình duyệt không polling.

## Nguyên nhân gốc

Lỗi gồm hai tầng nối tiếp:

1. **Vi phạm contract dữ liệu Fact**: nội dung mô tả dài của ô bảng bị dùng làm định danh `entity_name`, vượt giới hạn lưu trữ 512 ký tự.
2. **Exception path không an toàn giao dịch**: sau lỗi database, worker không rollback trước khi kiểm tra hủy/cập nhật job, làm mất trạng thái thất bại quan sát được và để job treo giả ở `running`.

## Đề xuất thuật toán trước khi triển khai

1. Chuẩn hóa fact theo bất biến cấu trúc, không hardcode từ điển:
   - NFC và gộp whitespace cho mọi trường.
   - `entity_name` chỉ là định danh ngắn của hàng/thực thể. Nếu ô khóa là đoạn mô tả dài, sinh định danh cấu trúc ổn định từ `table_id + row_index + source_revision_id`; giữ nguyên toàn bộ văn bản gốc trong `raw_data`/`attribute_value` để không mất dữ liệu và vẫn truy vết được.
   - Validate độ dài tất cả trường có giới hạn trước khi tạo ORM record; lỗi contract phải có mã rõ ràng, không để PostgreSQL là lớp phát hiện đầu tiên. Không cắt chuỗi mù vì có thể gây trùng định danh và mất nghĩa.
2. Làm exception path an toàn:
   - `await db.rollback()` ngay khi flush/commit lỗi, rồi dùng transaction/session sạch để đánh dấu index revision và job `failed`.
   - Bảo đảm wrapper worker có đường cập nhật fail-safe độc lập khi task con để session ở trạng thái hỏng.
   - Reconciliation phải nhận diện job `running` hết heartbeat và kết thúc/requeue có giới hạn, không để treo vô hạn.
3. Regression cần có:
   - Hai bảng với ô khóa dài hơn 512 ký tự, Unicode tiếng Việt và xuống dòng.
   - Kiểm chứng toàn văn vẫn nằm trong provenance, định danh ổn định và không collision trong cùng bảng.
   - Ép flush DB lỗi và xác nhận job/index revision chuyển `failed`, error được lưu, session sạch.
   - Sau khi sửa, chỉ retry hai nguồn lỗi; không OCR/nạp lại 17 nguồn đã đạt và không tự xuất bản.

## Kiểm chứng và bàn giao

- Đối chiếu PostgreSQL, worker log và code exception path; không gọi inference, không phát sinh chi phí AI.
- Sau khi chẩn đoán xong, một tác vụ bên ngoài phiên này đã làm sạch/reset dữ liệu runtime: lần đọc cuối cho thấy `job_records`, batch và hai bindings nêu trên đều không còn trong PostgreSQL. Worker vẫn nhận các mã ARQ cũ nhưng trả `missing`. Vì vậy các ID/trạng thái ở trên là snapshot bằng chứng trước lần reset, còn nguyên nhân gốc vẫn được xác nhận độc lập trong log worker. Phiên này không thực hiện reset hoặc xóa dữ liệu.
- Không chạy Ruff/Pytest/Vite vì không thay đổi mã nguồn ứng dụng.
- Chưa sửa code, chưa đổi trạng thái hai job, chưa retry, chưa publish, chưa restart và chưa thay provider/key.
- Cập nhật nhật ký, `PROJECT_CONTEXT.md` và `WORK_LOG.md` theo quy định dự án.
