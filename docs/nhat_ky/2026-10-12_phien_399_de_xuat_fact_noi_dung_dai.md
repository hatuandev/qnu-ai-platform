# Phiên #399 — Đề xuất kiến trúc Fact cho nội dung dài

## Mục tiêu

Đề xuất cách xử lý dữ liệu bảng có nội dung dài hơn giới hạn 512 ký tự mà không mất dữ liệu, không tăng giới hạn tùy tiện và không hardcode từ vựng. Phiên này chỉ thống nhất thiết kế, chưa sửa schema/runtime hoặc dữ liệu.

## Nguyên tắc cốt lõi

`entity_name` hiện đang gánh đồng thời ba vai trò: định danh, nhãn hiển thị và toàn văn nội dung. Đây là nguyên nhân gốc. Cần tách thành các trường có trách nhiệm riêng:

- `entity_key`: khóa kỹ thuật ngắn, ổn định và duy nhất; ưu tiên mã định danh chuyên biệt nếu có, nếu không dùng hash xác định từ source revision, table, row và identity span.
- `entity_label`: nhãn ngắn phục vụ UI; có thể lấy cụm định danh hình thái học hoặc preview cắt ở ranh giới từ kèm suffix hash. Không dùng làm nguồn sự thật.
- `entity_text`: toàn văn định danh/ngữ cảnh hàng, kiểu PostgreSQL `TEXT`, không cắt.
- `attribute_value`: toàn văn giá trị, tiếp tục dùng `TEXT`.
- `raw_data`: JSONB giữ toàn bộ hàng, header path, vị trí trang/bảng/hàng/cột, content hash và provenance.

Chỉ các mã nội bộ/enums/hashes mới dùng `VARCHAR` giới hạn. Mọi nội dung do tài liệu cung cấp dùng `TEXT`. Không tạo B-tree index trên toàn văn dài; exact/dedup dùng `entity_key`/hash, tìm kiếm dùng PostgreSQL FTS GIN hoặc trigram phù hợp.

## Xử lý nội dung rất dài

- PostgreSQL `TEXT`/TOAST phù hợp cho đoạn văn hàng nghìn đến hàng trăm nghìn ký tự; không cần nới `VARCHAR` theo từng lỗi.
- Nội dung toàn văn được lưu một lần và có checksum. Lớp embedding không nhúng cả khối: chia parent-child theo token/đoạn/cấu trúc, mỗi child giữ `parent_fact_id` và evidence span.
- Số liệu nguyên tử vẫn là fact riêng; đoạn mô tả dài là evidence/context, không biến thành khóa.
- Với ô cực lớn cỡ tài liệu/megabyte, canonical artifact là nguồn toàn văn; DB giữ metadata, hash, locator và các đoạn con cần truy hồi. Không làm mất nguồn gốc.

## Validation và an toàn giao dịch

- Chuẩn hóa Unicode NFC và whitespace trước fingerprint.
- Validate contract trước ORM: field kỹ thuật có giới hạn; field nội dung phải là `TEXT`; không silent truncation.
- Nếu persistence lỗi, rollback session trước mọi truy vấn/cập nhật trạng thái; dùng transaction sạch để ghi job/index failed.
- Recovery phát hiện job `running` hết heartbeat và kết thúc/requeue có giới hạn.

## Lộ trình migration an toàn

1. Thêm `entity_key`, `entity_label`, `entity_text` và index mới; giữ cột cũ.
2. Dual-write và backfill deterministic từ artifact hiện có.
3. Chuyển lookup/dedup/UI/RAG sang trường mới; kiểm chứng fact-set parity và collision.
4. Retry corpus dài, lỗi DB, Unicode, bảng nối trang và nội dung rất lớn.
5. Chỉ bỏ contract `entity_name` cũ sau khi rollout và rollback gate đạt.

## Kiểm chứng và bàn giao

- Đối chiếu code artifact → KnowledgeFact → vector generation hiện tại.
- Không sửa code/schema/data, không migration, không retry, không publish và không chạy test ứng dụng.
- Cập nhật nhật ký, `PROJECT_CONTEXT.md` và `WORK_LOG.md`.
