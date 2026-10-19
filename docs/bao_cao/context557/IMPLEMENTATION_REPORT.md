# Context557 — Tái sử dụng pipeline hiện có

**Không sửa mã nguồn ứng dụng.** Chỉ tạo các helper vận hành/kiểm chứng private trong Storage và báo cáo theo workflow repo. Working tree đầu lượt sạch; không refactor hoặc thay đổi standard v1.0.

Luồng thực hiện:

1. Preflight đọc DB với READ ONLY, xác minh duy nhất nguồn theo DOCX bytes/SHA256, old row/manifest, quyền và Storage. Kiểm tra API thật trả đúng source.
2. `source_reparse.queue_reparse(dispatch=False)` tạo ID/revision/job qua model/service chính thức, receipt chống tạo trùng; `workers.tasks.task_knowledge_source_reparse` chạy `source_ingestion_service.execute_reparse` bằng mã current. Không standalone parser chèn DB, không broker/worker cũ, không restart.
3. `verify_revision_pair`, `validate_projection_binding`, `proposal_base`, `verify_effective_projection` và đọc lại MinIO kiểm cặp source thực. Native XML/footnote và raw/header/row mọi bảng được đối chiếu độc lập.
4. Công cụ `backend/scripts/reconcile_semantic_checkpoint.py` của556 tạo gói mới không LLM; input/checkpoints cũ không đổi.
5. `rebind_checkpoint` và staging trên bản copy làm dry-run không ghi. Sau đó POST endpoint `/semantic-checkpoint` thật bằng cơ chế development actor/quyền có sẵn. Không giả JWT/SSO hoặc override dependency, không gọi endpoint review/apply.
6. Đóng session, đọc lại pending, kiểm toàn proposal hash, source binding và rebuild. Bảng/manifest/graph/facts persist trước-sau không đổi; mọi active pointer/index/epoch và revision cũ giữ nguyên.

## Chẩn đoán helper, không phải sửa runtime để che lỗi

Helper đầu import schemas trước services gặp vòng import đã có, dừng trước ghi; đổi thứ tự bootstrap helper. Sau POST200, helper so cả envelope dry-run với envelope staging mới nên vướng `at`/hash; không gửi lại POST. Kiểm đọc riêng xác minh đầy đủ hash thực, nội dung phải khớp ngoài thời điểm/audit hash sinh mới theo contract. Một phép so facts trong helper lấy Python projection mới thay vì JSON đã persist; đã chuyển sang so **stored artifact trước với stored artifact sau** và kiểm hash đầy đủ, không nới app guard. Probe A03 đầu truyền SimpleNamespace vào hàm nhận NoteScope nên5 PASS/1 FAIL; sửa kiểu input probe, cuối6 PASS. Các kết quả đầu/cuối đều được ghi rõ ở commands/XML.

Không sửa payload hoặc app để làm test xanh; không bỏ checksum, source/revision, permission, pending/conflict, approval hoặc effective graph guard. DB test riêng chỉ phục vụ regression; source test thật chỉ có đúng một nháp và một pending import theo quyền557. Không migration, ModelOps config, LLM annotation, index, publish, deploy, Git commit/push.

Rollback an toàn là giữ bản nháp chưa duyệt và dùng thao tác yêu cầu sửa/từ chối của người dùng; không xóa checkpoint hoặc sửa DB để quay lại.
