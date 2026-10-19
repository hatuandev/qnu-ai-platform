# Phiên549 — JSON output contract ModelOps

User giao triển khai prompt JSON contract; giữ Context547/548, không đổi model/
config/Markdown/parser/resolver/RAG/persistence, không tự duyệt/commit/push/deploy.
Đầu phiên HEAD ebd68292, tree sạch. Áp dụng clean-code/backend/ModelOps skills,
không subagent. OpenAI docs đối chiếu API payload; không suy capability proxy.

G0: raw548 NOT_AVAILABLE sau cleanup548; không dựng lại nguyên nhân Extra data.
Code cũ thiếu response_format, bỏ metadata finish/refusal và dùng defaults khi
parse selector. Red qua generation2FAIL/1PASS, missing/duplicate được chấp nhận.

Thêm backend preset/wire compiler từ business Pydantic, optional OutputContract,
per-route endpoint/model capability, actual response_format trên Chat Completions.
Không drop contract ở thinking signature/param negotiation; không crop context.
Strict parser whole object/no duplicate/nonfinite/coerce/fill/repair; fence chỉ
whole-envelope prompt-only; refusal/length/empty không stage.1syntax format retry
per original packet, shared deadline/calls/HTTP input/transient budget và atomic
stage. HTTP hashes/attempt trace, schema/business hashes, unknown finish trung thực.

Safe read-only audit DB/MinIO/Qdrant local; reusable548 harness tạo nonce mới
6d949a792a14, state/evidence549 riêng, localStorage tạm/dead-port endpoints.
Baseline app code copy/hashes. Lượt thiếu config19FAIL/2288PASS/17skip; copy
defaults/3provider/2encrypted credential READ ONLY vào testDB, đo lại frozen app
**18FAIL/2289PASS/17skip**,exit1,379,82s. Không lấy18lịch sử548 thay phép đo mới.

Focused238PASS gồm47new,108,55s; Ruff22filesPASS. Gate trước236PASS/2FAIL vì
TEST fallback response thiếu required lists; chỉ sửa fixture, assertion routing
giữ nguyên. Các snapshot/review/unit/scope/deadline regressions548 vẫn chạy.
Boundary63PASS/42,32s; full18FAIL/2336PASS/17skip/0ERROR/23subtests,exit1,407,20s.
Exact18ID/cause giữ nguyên,0ID mất/0status đổi/0lỗi mới,47thêmPASS. Red riêng
missing/duplicateFAIL→PASS; không gán2ca đó vào fullbaseline vốn chưa có testfile.

G3 live Bảng1: providerPASS/stop, JSON/schemaPASS, binderFAIL scope row ambiguous;
1call/0formatretry, khôngstage/apply. G4 HTTP API whole document:22packet build,
1gửi, JSON/schemaPASS rồi expansionbudgetFAIL; binderNOT_RUN, exit1. TEST actor
chỉgeneration ở isolated ASGI, không phải humanreview. Setup G4 đầu thiếu
origin_document_id nên chưaprovider; sửa fixture và chạy API đúng. Hai lượt thật
không fallback, default cx/gpt-6-luna/qwen3.5-9b giữ nguyên. Effective prompt_only
do chưa declared JSON capability; không gọi native strictverified. LiveE2EBLOCKED,
không validproposal/humanreview/apply/rebuild thật. Không retry semantic để tìmPASS.

Hồ sơ [context549](../bao_cao/context549/VALIDATION_REPORT.md) có chẩn đoán,
implementation/plan, schemas/payload minh họa từbuilder, JUnit/commands/hashes/
exactcompare/trace đãlọc. Đã export trước cleanup; ownership-verified DROP testDB
và SELECT không còn, xóa đúng runtime tạm/no-reparse-point và xác nhận không còn.
ZIP cuối có cleanup.json=cleaned và manifest/checksum. Giữ báo cáo548 nguyên lịch sử.
