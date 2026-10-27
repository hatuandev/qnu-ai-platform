# Phiên652 — Review ngữ nghĩa sau Compiler backendV1

Người dùng cho triển khai review để tìm ý bị bỏ sót/sai diễn giải sau Compiler.
Giữ phạm vi chỉ backendV1 đã chốt, giao diện làm sau. Không thêm framework hoặc
tự triển khai/cấu hình dữ liệu đang phục vụ.

Module `knowledge/compilation/review/` ghim input/draft/bundle, kiểm nguồn→draft
và draft→nguồn, đòi đủ mỗi ID đúng1lần, server đính nguyên văn và trang/ô. Báo cáo
JSON/Markdown có findings/gợi ý và limits. Verdict chỉ needs_attention hoặc
no_issues_detected; không tự sửa/approve. POST khởi tạo riêng sau Compiler
completed, không auto-call trong worker hiện tại. Cho chọn reviewer qua ModelOps.

Durable request trước quota commit, raw/snapshot/report artifacts, key replay,
usage/reservation, expiry/fence, quyền/provider/revision/hash trước/sau HTTP.
Migration0012/2bảng, routes/ownership/fixture/ORM; Compiler cũ không đổi.

Baseline1FAIL404→smoke2PASS. Focused22PASS/1FAIL do test hiểu truncated là502,
adapter đúng422; sửa expectation theo từng mode, focused24PASS. Extra2PASS/1FAIL
do test thiếuimportAPI; sửaimport, selected1PASS. Không sửa adapter hoặc hạ guard.
Full cuối qua4nhóm **460PASS/0FAIL/0ERROR/0SKIP**,25mới/0mất, tất cảexit0,
383,56s wall, tổng case1019,24s.47testfile đủ, unionXML giữ435nodeID651.

Ruff/format16PASS, UTF8/LF/link kiểm cuối; OpenAPI75path/101op/70path cũ giữ.
475legacy khớp baseline;10DBtest kiểm lại0còn/0v1vector quan sát, sentinel giữ.
Model/OCR loopback là fixture; chưa đo chất lượng LLM thật hoặc so ảnh nguồn.

Chưa auto repair, UI, binding text hậu OCR vào Compiler, ARQ/reconcile review,
multi-pass/chunk hoặc GC blob dở. Không migrate DB phục vụ, đổi provider/secret/
default, publish/index, restart, commit/push. Rủi ro shutdown Windows từ phiên
trước giữ nguyên,4nhóm cuối không gặp hang.

[API](../../backendV1/docs/compiler-review.md) ·
[Báo cáo652](../bao_cao/context652/REVIEW.md) ·
[Quy trình28](../quy_trinh/28_review_ngu_nghia_compiler_backendv1.md).
