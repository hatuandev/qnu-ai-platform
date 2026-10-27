# Phiên617 — Capacity endpoint và ngân sách compiler động

Ngày 24/10/2026, theo yêu cầu tận dụng context thực của model cloud mà không phụ thuộc form ModelOps còn thiếu.

## Phạm vi

Tái sử dụng protected ModelOps, adapter, quota và usage. Không thay default `gh/gpt-6-luna`. Thử GPT-OSS120B medium trên ba DOCX fixture giữ nguyên source/Quality Gate; không reindex, publish, restart, commit hoặc push. Giữ mọi thay đổi chưa commit của các Context trước.

## Triển khai và bằng chứng

- Metadata endpoint/model thay hardcoded context. OpenAI-compatible/OpenRouter và native Gemini/Claude có đường đọc đúng auth; thiếu metadata thì báo chưa xác định, không suy capacity từ tên model.
- Tokenizer registry + calibration framing; output được tính theo phần còn lại từng request và output capacity provider. Fallback tự tính ở lúc dispatch, không ép primary theo model nhỏ hoặc probe fallback trước khi cần.
- Cache process10phút gắn endpoint/model/config fingerprint. Explicit context rejection có thể giảm giới hạn; auth/quota/413/output errors không được biến thành context.
- Calibration/decoder/unknown-role guards giữ nguồn, schema và quyền. Streaming chưa opt-in automatic budget. Thêm tiktoken và lockfile.
- Live synthetic: metadata128000/context,64000/output; framing2075. Request **120002input/219output/stop**, cả3marker đúng,0fallback,0token-count delta; dynamic output7998. Chưa chứng minh exact maximum128000.
- Lượt lớn đầu chưa inference vì harness giữ transaction metadata read-only và lease không UPDATE được; ghi FAIL trước khi sửa giao dịch. Không tự retry một request inference uncertain.
- Compiler thật:29calls, maxinput32535/maxoutput2898, toànstop/0fallback; FAIL span enum ở PacketDraft, không overflow. Không sửa semantic hoặc nới QG trong task capacity để tạo PASS giả.

## Kiểm thử

Baseline discovery14PASS/5FAIL và baseline dynamic2PASS/5FAIL, exit1; giữ nguyên XML/test IDs. Các case ấy đã PASS sau sửa. Focused rộng338PASS/1FAIL vì fixture mock603 chưa có contract discovery mới; fixture được cập nhật và kiểm tra seal/rotation vẫn giữ. Focused chốt54PASS/exit0, Ruff16filePASS. Full đầu bị dừng khi phát hiện cần lazy fallback discovery, INCOMPLETE; không ghép partial. Full cuối **3744PASS/18FAIL nền/17SKIP**, exit1; exact18 ID/cause khớp baseline614 cuối. 123ID thêm đềuPASS, một ID đổi tham số có mapping, không regression/test mất không giải thích được.

Lệnh thực dùng Python3.12 trong `backend/.venv`, runner `.antigravity-bridge/validation/context617_checks.py` và `context617_acceptance_checks.py`; cwd root cho runner/cwd backend cho pytest. Artifact XML, exit receipt, profile, probe, compiler failure/metrics/seals nằm trong `backend/storage/context617`, không stage.

DB/MinIO/Qdrant đều kiểm loopback; regression dùng DB nonce riêng, LocalStorage riêng và egress guard tới endpoint127.0.0.1:1. Không migration/DDL shared DB. ModelOps live được phép ghi lease/usage bình thường; sáu nhóm source/default/provider/domain seals và ba raw-source hashes giữ. Bốn DB617 focus/acceptance/partial-full/final đã dọn theo nonce; Storage bằng chứng giữ theo policy bảo vệ, không bypass lệnh xóa bị chặn trước đây. Hai DB616 cũ giữ theo bàn giao trước.

Kết quả đối chiếu full cuối, cleanup và giới hạn xem [báo cáo617](../bao_cao/context617/REVIEW.md). **Chưa APPROVED compiler; không có kết quả benchmark64 mới.**
