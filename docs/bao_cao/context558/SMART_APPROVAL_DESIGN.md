# Context558 — Thiết kế theo Automatic Ingestion

## Luồng mặc định

Pipeline nạp/reparse mới gọi chuẩn hóa với `automatic=True`. Không gọi semantic enrichment tự động cho bản chuẩn trong nhánh này. Sau khi kiểm tra source bytes, MD/JSON pair và dẫn xuất, policy `automatic-content-v1` lưu kết quả máy:

- AUTO_READY: cấu trúc/nội dung đủ điều kiện nạp vector.
- READY_WITH_LIMITATIONS: giữ các ô blank/not_stated hoặc literal chưa diễn giải; không dùng chúng làm fact số.
- NEEDS_ATTENTION: dữ liệu không đọc được, lỗi hash, mất bảng, lỗi toàn vẹn hoặc cảnh báo chưa có căn cứ cho phép bỏ chặn.

Kết quả được ghim source/revision/hash, bảng, manifest, graph, facts, chất lượng và version. Proposal ngữ nghĩa không nằm trong các dữ liệu có hiệu lực nếu chưa được duyệt. Thay nội dung hoặc chất lượng làm certificate hết hiệu lực. Việc sinh và lưu proposal riêng, không đổi dữ liệu nguồn, không làm certificate nội dung hết hiệu lực.

**Không retroactive:** bản cũ không có certificate vẫn giữ workflow cũ. Không batch cập nhật dữ liệu Context552–557 hoặc tự chạy lại tài liệu thật.

## Index và publication

Giữ API/worker hiện có. Bản nội dung ready được chia đoạn và nạp staging theo revision được chọn. Trước queue/chunk/publication, kiểm tra lại tệp gốc, canonical pair và effective snapshot. Nạp embeddings không đổi active_index, epoch hay publication. Publication vẫn là hành động riêng, có quyền, collection, revision, parity và CAS.

Đây là chính sách phục vụ **nội dung nguồn đã kiểm chứng**, không phải bật cờ chấp nhận mọi semantic limitation cho dữ liệu cũ. Unknown tiếp tục hiện diện như raw/ambiguous trong evidence; không phát sinh fact số cho ô này.

## Advanced Review

Smart Approval `qnu-smart-approval-v1` giữ lại cho revision cần đối chiếu nâng cao. Policy/version, fixture allowlist theo provenance và standard conservative policy vẫn riêng. Source binding đúng không tự chứng minh semantic scope. Snapshot v3 giữ machine certificate và bulk user action; v1/v2 giữ cách tính hash cũ. Không giả 18 context_decisions của người dùng.

Các thao tác áp dụng ngữ nghĩa vẫn tuân thủ lifecycle revision nháp. Tài liệu đang phục vụ cần revision nháp phù hợp trước khi thay diễn giải; không sửa ngầm dữ liệu của bản đã xuất bản.

## Audit và transaction

Automatic certificate ghi machine_content_validation, thời điểm, policy và proof; không ghi actor giả đã đọc từng issue. Smart Approval dùng actor xác thực, source lock, idempotency, sidecar bất biến/readback và transaction DB; lỗi hoặc cancellation rollback. Sidecar đã ghi trước commit lỗi có thể còn unreferenced, không được phục vụ.
