# Context557 — Revision nháp canonical

**CANONICAL_REVISION_VALID.** Tạo đúng một revision mới bằng service/tác vụ chính thức; không dùng standalone parser rồi chèn artifact vào DB.

| Thành phần | Kết quả đã đọc lại |
|---|---|
| Collection / Source | `col_admissions / bnd_21c09bbc6ca0` |
| Revision cũ | `ks_rev_84c4950c9ce2`; toàn row/hash/status giữ nguyên |
| Revision mới | `ks_rev_2b5e0352565f` |
| Job chính thức | `job_ab29c145476d`, completed |
| DOCX | SHA256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`, 102,423 byte |
| Pipeline | `layout-v18-semantic-evidence`, profile `standard`, engine `docling+native+paddleocr_vl` |
| Parser profile hash | `fe6d3468cf5c74d8ec2a95b40f2e05338c37a4202f8fad692d2b64a9cf9b468a` |
| Storage | MinIO/S3 đang cấu hình; snapshot gốc giữ nguyên, artifact content-addressed mới |
| Markdown | `cb11dfbef6640362c462610154380fa1c1407f75b530356baf1011b2d4368f97` |
| Structured JSON | `f2e6df262e33af8e9e61c5e23633a34ac43f5d9b6b6f84d13607afd1657ed83b` |
| Khối / bảng / footnote | 233 /10 /3 |
| Trạng thái | `review_required`; không chuyển active/ready/published |

Preflight tìm duy nhất source bằng DOCX SHA256 rồi kiểm byte equality với file kiểm thử local; không chọn bằng tên. DB ứng dụng local được kiểm READ ONLY trước ghi. Quyền `ai.knowledge.update` giải bằng dependency có sẵn; API đọc đúng source trả200. Actor là development mặc định đang cấu hình, không giả token/actor và không phải đăng nhập SSO người dùng. Quyền tạo nháp/stage đã được người dùng cấp trong prompt557.

Tạo bằng `queue_reparse(dispatch=False)` rồi `task_knowledge_source_reparse` chính thức trong tiến trình mã hiện tại. Reservation inline ngăn broker/worker cũ nhận trùng; không restart hoặc chỉnh cấu hình. Receipt ghi ID ngay sau queue và chặn tạo lặp. Policy `unit_temporal_annotation=null`; không chạy pipeline đề xuất LLM. LLM usage ledger trước/sau giữ 1774; xử lý preview có OCR PaddleOCR-VL theo pipeline hiện có, không gọi22packet annotation.

## Chứng minh nội dung và footnote

Toàn bộ core records theo thứ tự (ID/type/body/parent/section) **khớp từng phần tử** với source offline đầy đủ; không chỉ so233. Toàn bộ10 bảng: header metadata, row IDs, raw values và states khớp. Rich-cell paragraph lặp của bản299 khối không tái xuất hiện. Bảng1 giữ header nhiều tầng, các năm2025/2026/2027, dòng tổng, mã chuỗi0012/00027/AM-0007/AM-0070 và các chú thích theo phạm vi.

Cả ba footnote có `type=note`, `role=footnote`, locator `word/footnotes.xml#id=1/2/3`, source anchors và context_refs ngược. Kiểm độc lập với XML DOCX thật, không tìm chữ gần giống trong Markdown. A12 dùng footnote 2 nguyên văn, anchors tới `p052`; c02/r001–r003 giữ chuỗi và số 0 đầu. Resource ZIP được GET, kiểm checksum và CRC, giữ ảnh gốc có truy vết.

## Giới hạn cần người dùng đối soát

Page mapping là partial theo bản PDF xem trước18 trang. Footnote1 ở trang 3, footnote 2 trang 6; footnote 3 chưa chứng minh được trang nên giữ unknown, locator XML vẫn đầy đủ. PDF Inspector báo không thành công và giữ native evidence; không tự xóa cảnh báo. Canonical raw source/đối chiếu XML và toàn bảng vẫn đạt.

Quality report còn 16 cảnh báo ở lớp preview/legacy, gồm TABLE_WIDTH_MISMATCH (1), REPEATED_MARGIN_REVIEW (9), TABLES_NOT_MATERIALIZED (2), VISUAL_CONTENT_REVIEW (1), CONTENT_TABLE_WIDTH (2), CONTENT_HEADER_REVIEW (1). Hai nhãn TABLES_NOT_MATERIALIZED thuộc preview không đồng nghĩa mất bảng trong canonical: cả10 bảng canonical đã đối chiếu raw/header/row. Đây là bản nháp cần review, không chứng nhận toàn tài liệu sẵn sàng xuất bản.

## Bảo toàn và rollback

Hash toàn row revision cũ, mọi binding/collection row và các active pointers/epoch giữ nguyên. Index revisions26, chunks56, facts0 trong DB không đổi. Nếu muốn sửa hoặc loại proposal, dùng luồng Yêu cầu sửa/Từ chối có quyền trên **bản nháp mới**; không khôi phục bằng xóa/sửa DB hoặc ghi đè revision cũ. Không cần rollback publication vì chưa có thay đổi publication.

[Checksum](source-checksums.json), [kiểm cấu trúc](canonical-validation-summary.json), [receipt](staging-receipt.json).

Artifact nháp chứa 392 facts dẫn xuất từ nguồn, đã có trước staging và giữ nguyên checksum sau staging. Chúng chưa được đưa vào facts DB hoặc index đang phục vụ; không phải 392 facts đã được proposal duyệt. [Kiểm tra toàn vẹn cuối](final-integrity.json).
