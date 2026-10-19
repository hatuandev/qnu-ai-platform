# Báo cáo triển khai Context555

## Phạm vi thay đổi

| File/hàm | Thay đổi phục vụ nhiệm vụ |
|---|---|
| `semantic_annotations.py`: NoteScope, _note_targets, _apply_notes, stage_semantic_annotations | Workflow scope không có column/field dependency; metadata mặc định không đổi seal cũ; labels ánh xạ đúng thứ tự assertions. |
| `semantic_assertions.py`: attach_assertion | Giữ loại/nhãn workflow trong metadata đơn vị nguồn dẫn xuất. |
| `semantic_context_review.py`: ReferenceLink, ReferenceAssessment, validate_reference_assessments | Vai trò tham chiếu, điều kiện và evidence nguồn; không tạo effective edges hay quyết định duyệt. |
| `semantic_checkpoint.py`: rebind_checkpoint, import_semantic_checkpoint | Adapter kiểm chứng nguồn chính xác, quyền, draft/lease, hash/binding, remap ID, pending mới, idempotency và rollback. |
| `schemas.py`, `router.py` | Request nghiêm extra-forbid và endpoint có `ai.knowledge.update` theo cơ chế xác thực hiện có. |
| `prepare_semantic_review_checkpoint.py` | Bổ sung labels dữ liệu review vào gói offline mới; checkpoint cũ không đổi. |
| `semantic-review-preview.tsx` | Hiển thị A/O/S, nhóm 8 issue gốc và 10 scope, vai trò/điều kiện/evidence, loại workflow, hash và trạng thái chưa gửi quyết định. |
| `semantic-checkpoint-import.tsx` | Chọn gói JSON, lý do và hành động tạo pending rõ ràng; không có auto approve. |
| `source-detail-page.tsx`, `knowledge-api.ts`, `knowledge.ts` | Nối import vào hộp kiểm duyệt nguồn hiện có; quyền backend thực, hash/revision, reset lựa chọn khi đổi proposal, query invalidation và lỗi thật. |
| `test_semantic_checkpoint_import.py`, `semantic-review-preview.test.mjs` | Test dữ liệu/quyền/API và UI. Chi tiết kết quả ở VALIDATION_REPORT. |

Các thay đổi đang có từ Context553/554 được giữ lại. Không coi toàn bộ Git diff là thay đổi riêng của phiên này; audit lưu hash source trước khi sửa.

## API và lifecycle

`POST /knowledge/collections/{collection_id}/sources/{source_id}/revisions/{revision_id}/semantic-checkpoint` (dưới prefix API hiện hành).

Body gồm `checkpoint` (contract/source_artifact/proposal), `comment`, và `expected_semantic_proposal_hash` nếu thay gói đã bị yêu cầu sửa hoặc từ chối. Không nhận actor/approval từ checkpoint. Cần token/session thật và quyền `ai.knowledge.update`.

Luồng: chọn đúng revision nháp → kiểm hash MD/JSON và cấu trúc → tạo proposal mới chưa áp dụng → mở Preview → chọn từng issue với evidence/lý do → action review hiện có → snapshot Storage đã đọc lại/DB pointer → rebuild. Nút nhập không thay bước duyệt; các decision cũ không đi sang hash mới. API review vẫn chặn nếu thiếu một issue hoặc dùng hash offline/stale.

Gói private tại `backend/storage/context555-review-ready/import-package.json`, khoảng 2,31 MiB. Không đưa corpus/gói nguồn vào thư mục báo cáo public hoặc ZIP bằng chứng. Giao diện có giới hạn 8 MiB để đọc file; backend là nơi xác minh toàn bộ nội dung và quyền.

## Tương thích

Không migration, không đổi Markdown Standard v1.0 hoặc selector v1/v2. `context_kind=data`, context_label rỗng và links rỗng được bỏ khỏi serialization; snapshot/assertion cũ giữ seal và ID. Snapshot schema vẫn qnu-semantic-v1, cơ chế context-decision/hash v2 hiện có giữ nguyên. Import từ bên ngoài yêu cầu annotation có binding; điều này không làm annotation legacy đã lưu mất khả năng đọc/rebuild.

## Đã chủ động dừng ở đâu

Không sửa Semantic Store/Source Ingestion/RAG để vượt lỗi hash. Revision thật cùng DOCX có cặp MD/JSON khác checkpoint nên **không stage thật**. Chưa có quyết định người dùng thật, chưa apply/publish/index/reparse/khởi động lại/triển khai. Không gọi lại LLM để tạo/sửa 12 quan hệ. Không đổi ModelOps, policy, config hoặc dữ liệu production. Không commit/push.

Không thêm resolver ngữ nghĩa, bộ tính Q, object hồ sơ giả, từ điển header hoặc ánh xạ domain trong runtime. Mapping A/O/S cụ thể nằm trong dữ liệu checkpoint được chuẩn bị để người dùng đối chiếu.
