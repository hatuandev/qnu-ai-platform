# Phiên641 — Capacity ModelOps backendV1

Người dùng giao xử lý capacity trong khi prompt OCR chạy ở tác vụ khác. Dùng skill
backend/clean-code/ModelOps; đọc context/Git/source và giữ thay đổi đồng thời.

Thêm token_limits trên API provider, profile JSONB ghim endpoint/model, trạng thái
unknown/configured/stale và public API resolve/plan budget có kiểm quyền. Không
trần context/output chung8K/32K. Gỡ le32768 của OCR_MAX_OUTPUT_TOKENS; mặc định8192
vẫn là ngân sách workflow. Có hợp đồng handoff và ADR010, không thêm migration.

Baseline API3FAIL và setting1FAIL đúng lỗi. Focused cuối44PASS/15,33s/exit0,
33ca mới. Full snapshot152PASS/2FAIL/0SKIP/51,70s/exit1: regression downgrade639
không khớp migration0006 OCR mới, và lỗi Windows replace/read khi ghi đồng thời.
Full vẫn FAIL, không tự sửa/nới hai ca ngoài phạm vi. Ruff/format10file/OpenAPI PASS.

4DBtest dọn/sentinel giữ;475legacy app giữ hash; DB chính chưa migrate. Không
restart/deploy/default/key/Git. Chưa discovery hoặc live OCR; helper capacity chưa
được execution OCR của tác vụ khác gọi, cần nối trước HTTP và ghim config hash.

[Báo cáo/lệnh/giới hạn](../bao_cao/context641/REVIEW.md).
[Hợp đồng cho tác vụ OCR](../../backendV1/docs/model-capacity.md).
