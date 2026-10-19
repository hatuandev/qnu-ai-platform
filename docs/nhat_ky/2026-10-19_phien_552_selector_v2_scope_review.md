# Phiên552 — Selector v2 và scope review

Triển khai prompt evidence binding final integration trong phạm vi hẹp. Áp dụng clean-code/backend/ingestion/ModelOps và frontend cho preview. Giữ diff chưa commit549–551, không đổi parser/RAG/model/provider/context/output/deadline hoặc annotation snapshot schema.

Wire v2 bỏ owner trùng lặp, backend xác minh evidence registry/packet/canonical source rồi giải owner. V1 giữ schema/hash và tiếp tục từ chối owner thiếu/sai. Prompt/provider/parser/binder/trace ghim cùng contract; retry/fallback không đổi selector version. Row/group scope luôn cần issue riêng từ toàn canonical unit; không suy nghĩa phủ định/khoảng mã bằng từ điển. Preview hiển thị exact dòng/cột. Sửa false rejection khi mixed cell/limitation kiểm hash sau mutation dẫn xuất; guard nguồn, unknown và review giữ nguyên.

Python3.12.13, safe local audit mới; baseline frozenapp18FAIL/2336PASS/17SKIP/23subtests. Red29FAIL/2PASS và registry1FAIL. Focused cuối217PASS; new39PASS; Ruff14PASS; frontend15PASS/Biome2PASS/buildPASS. Full sau18FAIL/2375PASS/17SKIP/23subtests, exact18ID/cause giữ nguyên,0ID mất/status đổi/lỗi mới. JUnit/commands/comparison tại [báo cáo552](../bao_cao/context552/VALIDATION_REPORT.md).

Live Bảng1: một request Qwen3.5-9B, no fallback/retry,16469input/519output,5542,88ms; selector v2/effectiveprompt_only, JSON/schema/bindingPASS. Stage4note proposals,8issue (2scope/6deferred), scope selected_tables; runnerexit2WAITING_FOR_REVIEW. Chưa human approval/apply/persist-rebuild thật hoặc full-documentAPI. TEST lifecycle/session/Storage/rebuild3lầnPASS không thay E02. Raw551NOT_AVAILABLE, không bịa response gốc.

Hai DB test/LocalStorage runtime đã dọn, source appDB chỉREADONLY; config/defaults/provider settings fresh-read giữ nguyên. Giữ checkpoint private gồm pending proposal/sealed source/REVIEW.md/hashes để chờ từng issue, đã read-back không LLM/không apply. Đây là checkpoint offline, không phải UI pending revision/job hoặc authority duyệt. Sau người dùng duyệt phải kiểm actor/nguồn/revision/hash và thực hiện checkpoint C/D thật. Không commit/push/stage/reset/index/publish/restart/deploy/approve nguồn thật.
