# Phiên #351 — Nút Xóa nguồn thực sự xóa gì?

## Phạm vi

Chẩn đoán read-only theo yêu cầu: người dùng đã xóa nguồn rồi nạp lại nhưng OCR rất nhanh. Theo clean-code skill, lần theo FE/API/service và đối chiếu DB/storage; không DELETE thêm, không restart, không sửa runtime hay chạy lại OCR.

## Luồng hiện tại

`DeleteSourceButton` -> `knowledgeApi.detachBinding` -> DELETE `/knowledge/bindings/{id}` -> `binding_service.detach_binding`. Đây là soft delete (gỡ nguồn), không purge.

Service khóa collection/binding, chặn nguồn đang xử lý/lập chỉ mục, gọi deactivate từng index revision, chuyển revisions archived, binding detached, xóa active_index_revision_id, tăng binding.active_epoch/collection.index_epoch rồi commit. List nguồn lọc detached. Không xóa active_source_revision_id, source revision, markdown, manifest/layout, snapshot, chunk set, chunks/facts, jobs/import history hay Repository file.

Qdrant: chỉ set payload is_retrievable=False/document_status=archived, không xóa point. RAG snapshot và truy vấn facts/lexical hiện có điều kiện binding active. Tuy nhiên deactivate_index_revision bắt Exception và chỉ warning; lỗi Qdrant có thể bị che khiến DELETE vẫn thành công. Chưa fault-injection E2E, không cam kết mọi đường retrieval an toàn tuyệt đối từ việc đọc code này.

## Vì sao nạp lại dùng dữ liệu cũ

Ingestion tìm binding theo collection + repository_document_id, không loại detached; tìm source artifact ready cùng file hash/parser profile trong tenant/workspace, không loại binding detached. Sau đó dùng lại markdown/page manifest/quality report; ready chuyển binding active. Chunk set cũng reuse nội dung/config tương ứng. Vì vậy đây là gỡ rồi kích hoạt lại, không phải cold OCR test.

## Đối chiếu thực tế

Hai binding `bnd_57cea287b8a9`, `bnd_f6ffca83f861` hiện active/epoch2 sau các lần nạp lại. Mỗi binding còn 3 source revisions ready (1 ban đầu, 2 reused), snapshot tồn tại. Tổng 6 chunk sets còn trong DB. Hai nguồn hiện không có KnowledgeChunk/KnowledgeFact/index revision tương ứng và active_index=None (đợt chưa chọn vector generation); không coi đó là bằng chứng DELETE đã xóa vector/facts.

GC hiện tại `gc_service.collect_garbage` lọc KnowledgeBinding.status != detached và chỉ xử lý index revisions cũ, không purge source revisions/chunk sets/snapshots. Do đó không có cơ sở nói dữ liệu OCR của nguồn đã gỡ sẽ tự được dọn bằng GC này.

## Đề xuất trước khi sửa

- Nếu giữ soft-delete: đổi nhãn thành Gỡ nguồn và thông báo rõ giữ OCR/snapshot/lịch sử. Bóc tách lại phải bỏ qua cache theo thao tác chủ động.
- Nếu người dùng muốn Xóa vĩnh viễn: luồng riêng có xác nhận, worker purge có trạng thái/retry, ngừng truy xuất trước rồi xóa artifacts/vector thuộc nguồn. Kiểm tra reference để không xóa chunk/cache/snapshot còn được nguồn/mô hình khác dùng; giữ tệp Repository. Không chỉ sửa tên nút hoặc cascade bừa vì dữ liệu đa embedding có thể chia sẻ.
- Sửa observability về engine/thời gian/reuse và cách báo lỗi Qdrant. Chưa triển khai, chờ lựa chọn semantics.

## Verification

Đối chiếu code + DB counts + storage.exists read-only. Không pytest/build vì không đổi mã. Chưa tái hiện DELETE mới hay lỗi Qdrant thực tế. Đồng bộ journal/memory/worklog.
