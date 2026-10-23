# Phiên603 — Compiler chủ đề và vòng đời dẫn xuất

Ngày 22/10/2026. Người dùng cho triển khai đợt3–4 theo thiết kế602, để P10 sau.
Không mở scope sửa RAG/P10 hoặc tự làm UI/serving integration thuộc đợt sau.

## Đã triển khai

Đọc repo instructions/memory/diff và thiết kế602; giữ nguyên thay đổi600–602 chưa
commit. Dùng skill clean-code/backend/ingestion/ModelOps/evaluation. Không agent
phụ. Snapshot app trước603 và baseline cô lập thay cho suy hiện trạng từ memory.

Compiler theo topic có hai lượt chọn bằng chứng, conservative retention khi
phân loại thiếu/bất đồng, namespace ID và request-local proof handles. Bóc
assertion theo nguồn, closure các proof scope/time được chọn, inventory primary/
deferred/unassigned và independent checks. Synthesis chia nhóm vừa budget,
coverage/dependency/review ledgers giữ nguyên. Unknown không thành0, cùng tên
không tự chứng minh identity, metadata không thành condition nghiệp vụ.

Dynamic ModelOps giữ preferred route/defaults/fallback trong phạm vi policy.
Toàn request đo trước gọi;64calls/600s, sửa JSON/schema hoàn tất lỗi rõ ràng tối
đa một lần, không compiler retry mạng/quota/quyền/cancel. Mọi lượt sửa vẫn tính
budget. Source/raw/artifact/context/config/credential rotation opaque hash gắn
cache; topic và assertion packets của nguồn không đổi có thể reuse. Synthesis
kiểm lại theo source set mới; không reuse dẫn xuất bị thu hồi.

Collection-locked JSONB registry trong model hiện có, StorageDriver immutable
artifacts/read-back, durable intent trước inference, OCC/idempotency ở decisions,
audit riêng automated/user, source/pointer/epoch/lineage stale và revocation.
GET không gọi model; API metadata thông thường không được import/sửa registry.
Không bảng/migration/worker mới, không mutation semantic annotations nguồn.

13 file app sửa/mới;4 file test mới và mở allowlist DB fixture600 sang603 có
ownership guard. Schema602 giữ shape, tách helper integrity khỏi authorization
cho GET và dùng mã lỗi temporal rõ hơn. Chi tiết file/phương pháp:
[IMPLEMENTATION_REPORT](../bao_cao/context603/IMPLEMENTATION_REPORT.md).

## Kiểm chứng

DB/MinIO/Qdrant phát triển loopback đã xác minh. DB riêng
`qnu_test_context603_328b50b64817` có ownership nonce, Storage runtime riêng.
Pytest network guard không cho inference/service thật. Không migration DB ứng
dụng, không sao credential/provider sang testDB; chỉ defaults metadata inactive.

Baseline full trước603:3413 PASS/18 FAIL/17 SKIP,+23subtestPASS,exit1.
Baseline metadata4 FAIL đúng chỗ, gồm PUT handler thật trước guard. Focused cuối
139 PASS/1warning,55test mới PASS; Ruff18file PASS. Full final/exactIDs và cleanup
cuối được ghi trong [báo cáo kiểm chứng](../bao_cao/context603/VALIDATION_REPORT.md)
và [đối chiếu test ID](../bao_cao/context603/TEST_ID_COMPARISON.md).
Không ghi focused như full PASS hoặc mock như ModelOps E2E.

Full cuối3468 PASS/18 FAIL/17 SKIP,+23subtestPASS,exit1; exact failureIDs/message
khớp baseline,0 lỗi mới/đổi cause/mất ID cũ. Tổng suite vẫn FAIL. Chỉ chạy một full
cuối batch sau khi model thật hoàn tất, không song song cùng DB test.

## ModelOps thật: workflow hoàn thành, nội dung chưa nghiệm thu

Dùng lại parser602 artifacts/raw3DOCX2024/2025/2026,381noncontainer proofs; tạo
source fixtures chỉ trong DB test/localStorage, format-only, không chứng nhận
fullQualityGate nguồn. Không reparse tài liệu/kho thật hoặc nạp vector mới.

Giữ primary Luna và cấu hình Qwen fallback,0fallback thực tế. Sáu build phát
triển có receipt riêng, các lỗi trước không bị che: JSON syntax, scope proof
ngoài main evidence, thiếu classification ledger, temporal schema, packet
inventory và lượt cuối needs_attention. Không resend network intent chưa rõ.

Lượt cuối create200/GET đúng job200,33Luna calls/0fallback,110.809input/12.244output,
maxprompt5056tokens,166.970,74ms.5assertions/3sections/1relation và381/381exact
proofs được lưu/đọc lại. Bản cuối machine_complete=false,24missedproofs và1section
unresolved; không nhấn approval hoặc ghi fact/vector/publication.

Manual source review bổ sung hai blocker mà model chưa bắt đủ: gán trạng thái
dự thảo2025 sang2024 và đảo hướng relation thay thế mức cũ/mới. Một số số liệu,
thông báo/điều kiện đúng không bù được lỗi scope/direction hoặc coverage thiếu.
Đây là kết quả FAIL về nội dung, không phải P10 và không phải mất source/context.
API/storage/lifecycle hoàn tất không được gọi là compiler content APPROVED.

Runner ban đầu lấy job cuối theo thứ tự JSONB nên chọn nhầm receipt cũ; đã đọc
lại đúng ID từ create response bằng GET read-only, không inference lại. Bằng
chứng và manual rubric ghim response hash trong
`backend/storage/context603/live-inventory/offline-audit.json`. Không judgeLLM,
rubric draft Codex, không human holdout hay published chatbot E2E.

## Bàn giao và giới hạn

Seals nguồn/model/config/shared rows và toàn namespace2943point khớp,0retrievable;
ba rawfile hashes giữ. Các phép đo/model audit được giữ, không xóa trace lỗi.
Dọn đúng DB test sau full gate, Storage tạm giữ theo policy; xem receipt cleanup
cuối trong báo cáo. Không commit/stage/push/reset/reindex/publish/restart/deploy.

Đã drop riêng DB603 sau xác minh tên/comment nonce và kiểm lại DB không còn;
helper exit0, status database_removed_storage_pending. Không xóa Storage bằng
đường thay thế hoặc tắt policy. Code/nguồn/model/vector seals và diff được chốt
trong closing-checks.json sau khi cập nhật báo cáo/memory.

Có API/Storage/lifecycle cho advanced review; chưa frontend hoặc RAG hook mới.
Việc cần tiếp tục trước rollout: kiểm mọi scope claim đúng source, cấu trúc
section không mượn trạng thái nguồn khác, chiều relation và missed temporal/
coverage. Không tự áp dụng proposal trong lúc còn blocker; ingestion phổ thông
vẫn độc lập như trước. P10 và benchmark64 không thay đổi trong603.

[Hướng dẫn API](../bao_cao/context603/USER_GUIDE.md) ·
[Quy trình18](../quy_trinh/18_bien_soan_chu_de_nhieu_nguon.md) ·
[Snapshot603](../memory/snapshots/2026-10-22_session_603.md).
