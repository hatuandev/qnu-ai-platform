# Context603 — Kiểm chứng đợt3–4

Ngày 22/10/2026. **Đã triển khai backend compiler và vòng đời dẫn xuất; chưa
nghiệm thu chất lượng nội dung compiler với nguồn thật.** P10 được để sau theo
yêu cầu. Không chạy lại64 câu, không đổi điểm59/60 lịch sử602.

## Phạm vi và an toàn

Đọc AGENTS/rules/memory, diff và thiết kế602 trước sửa. Giữ thay đổi600–602 đang
có; snapshot app đầu603 dùng làm baseline, không lấy HEAD để ghi đè working tree.
Áp dụng clean-code/backend/ingestion/ModelOps/evaluation. Không tạo subagent.

DB/MinIO/Qdrant phát triển ở loopback được kiểm trước chạy. DB riêng
`qnu_test_context603_328b50b64817`, ownership comment có nonce; Storage riêng
`backend/storage/context603-runtime-328b50b64817/objects`. Pytest có network guard,
endpoint test dịch vụ ngoài là `127.0.0.1:1`. Tạo schema chỉ trong DB test, không
migration DB ứng dụng. Một defaults row inactive được sao vào testDB,0 credential/
provider row; inference thật đọc cấu hình ModelOps hiện có qua session riêng.

Chức năng mới không hook vào RAG, không nạp vector hoặc xuất bản.13 file app sửa/
mới,4 file test mới và fixture integration600 nhận thêm DB603 có ownership guard.
Không sửa frontend, parser hoặc logic trả lời P10.

## Regression

| Kiểm tra | Kết quả | Exit |
|---|---|---:|
| Full baseline snapshot trước603 | 3413 PASS /18 FAIL /17 SKIP, +23 subtest PASS | 1 |
| Baseline metadata/API trước guard mới | 4 FAIL đúng nguyên nhân, gồm PUT handler thật ghi được registry | 1 |
| Focused cuối `release-final-focused` | 139 PASS,1 warning Qdrant offline | 0 |
| Test mới trong focused | 55 PASS | 0 theo focused |
| Full cuối | 3468 PASS /18 FAIL /17 SKIP, +23 subtest PASS | 1 |
| Ruff phạm vi18 file | PASS | 0 |
| FE/build/browser | NOT RUN, không thay FE | — |

Full suite vẫn FAIL nếu giữ lỗi nền. Không coi139 focused PASS là full PASS.
Đối chiếu đầy đủ: [TEST_ID_COMPARISON.md](./TEST_ID_COMPARISON.md).

Exact comparison:0 failure ID mới,0 đổi failure message/cause,0 mất ID cũ,0 lỗi
nền được sửa;55 ID mới đều PASS.18 lỗi nền vẫn thuộc schema/seed test cũ, dịch
vụ bị guard chặn, auth contract cũ và assertion legacy. Không hạ assertion hoặc
bỏ guard để làm suite xanh. Full cuối588,42s, chỉ chạy một lần sau batch ổn định.

Các ca mới kiểm compiler/topic selection, proof handles, scope evidence closure,
unassigned inventory không thành fact, schema repair tối đa một lần/call budget,
unknown, năm bịa, metadata injection, provider/Storage/cancellation, quyền, sai
hash/revision, stale/source đổi khi build, GET/read-back sau đóng session,
idempotency hai key cùng build, review concurrency/OCC, audit, incremental reuse
cả topic/extraction, revocation lan qua lineage và no fact/index/publication write.

ASGI handler + PostgreSQL + LocalStorage là thật, model trong pytest là giả có
chủ đích. Đây không phải bằng chứng model/provider thật đã hoạt động. Baseline
chỉ4 test metadata có trước/sau đúng nghĩa; các API/compiler mới chưa tồn tại
trước603, không gọi thiếu module là lỗi nghiệp vụ đã tái hiện.

Lệnh từ root:

```powershell
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context603_checks.py setup
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context603_checks.py run --baseline --label baseline-full
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context603_checks.py run --baseline --label baseline-metadata-api tests/test_compilation_metadata_603.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context603_checks.py run --label release-final-focused <10 modules ghi trong receipt>
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context603_checks.py run --label full-final
```

Helper đặt cwd pytest là `backend`, ghi argv, DB/Storage và exit trong `*-run.json`.
Ruff dùng `.venv/Scripts/python.exe -m ruff check` đúng18 file ghi trong
`checks/ruff-final-run.json`. Không cài dependency, auto-fix toàn repo hoặc lặp
full suite để tìm lượt xanh. Các test trọng tâm chạy lại khi có thay đổi mới
hoặc failure cụ thể; các lượt cũ được giữ riêng.

## Workflow ModelOps thật trên ba DOCX

Dùng lại canonical/structured artifact do parser602 tạo từ ba file thật2024,
2025(dự thảo),2026(thuyết minh).381 noncontainer proofs; tổng số unit cấu trúc
cũ có container nên không cộng lẫn hai mẫu số. Raw files được đọc/hash và sao
vào Storage thử; không parse lại hoặc tạo source revision trong kho ứng dụng.
Các source records ready trong DB test là fixture **format-only**, không phải
chứng nhận full Quality Gate hay official status cho nguồn.

Primary vẫn `cx/gpt-6-luna`, observed `gpt-6-luna`, fallback Qwen cấu hình giữ
nguyên. Thí nghiệm chỉ cho primary đã chọn;0 fallback thực tế. API qua ASGI thật
với testDB/localStorage, route resolver đến ModelOps DB hiện có, không sao chép
credential. Mỗi lần gọi thật gắn conversation tag riêng để đối soát usage chính
xác, không lấy toàn bộ log cùng thời gian của người dùng khác.

### Các lượt phát triển không được che hoặc trộn

| Artifact folder | Kết quả | LLM calls | Nhận định |
|---|---|---:|---|
| `live` | HTTP502 JSON syntax | 3 | Không có artifact có hiệu lực; không kết luận nguyên nhân chắc chắn do ID dài |
| `live-handles` | HTTP422 scope proof ngoài main evidence | 15 | Cần closure proof mà model đã khai báo, không suy role mới |
| `live-closure` | HTTP422 topic coverage ledger | 5 | Phân loại thiếu được đổi sang giữ unit, không loại lặng |
| `live-final` | HTTP502 temporal schema | 15 | Contract thời gian giữ chặt; thêm feedback/error code an toàn và correction có giới hạn |
| `live-release` | HTTP422 packet coverage | 18 | Đối soát inventory explicit unassigned; reviewer vẫn phải kiểm nội dung thiếu |
| `live-inventory` | HTTP200, needs_attention | **33** | Có bundle bền vững, chưa được duyệt/chấp nhận nội dung |

Đây là các build mới sau sửa code/policy và sau khi có receipt kết thúc lỗi,
không resend một network intent chưa rõ trạng thái. Mỗi intent/usage/audit giữ
riêng; không dùng lượt thành công API để xóa failure lịch sử. Trong một build
cuối, chỉ một correction cho output JSON/schema đã bị từ chối rõ ràng; error
mạng/quyền/quota/cancel không được gửi lại ở compiler.

### Lượt cuối có gì

- Job `kc_4a731f3f6ba54fc2955bb0cad696dba5`: create200, exact job GET200 qua session
  mới,5 assertions/3 sections/1 relation. Đọc lại đúng job ID từ create receipt;
  thứ tự key trong JSONB registry không phải thứ tự tạo. Lỗi chọn job trong runner
  trước đó được sửa bằng GET read-only, không gọi lại LLM.
- 381/381 proof khớp exact canonical text/hash/source/revision/offset; raw bytes
  không đổi. Nguồn/locator/bbox được giữ trong catalog, không viết lại nguồn.
- 33 observed Luna calls, tất cả finish_reason=stop,0 fallback;110.809 input/
  12.244 output tokens, prompt lớn nhất5056tokens. Toàn request166.970,74ms.
  Đơn giá/chi phí chưa tổng hợp, không đoán giá. Con số này không chứng minh mọi
  trường hợp hay Qwen32K đều đủ context.
- Status **needs_attention**, machine_complete=false;24 proof còn trong missed
  evidence ledger và một section unresolved. Không nhấn approval, không ghi fact
  có hiệu lực, không vector/index/publication. Read-back/ledger là integration
  workflow hoàn thành, **chất lượng nội dung vẫn FAIL**.

### Review độc lập phát hiện gì

1. Tổng2024 và năng lực nhóm giáo viên được trích đúng số và điều kiện phân bổ
   giữ trong diễn giải. Nhưng proposal gán scope “dự thảo” cho2024 bằng proof chỉ
   chứa tiêu đề/năm. Literal “Dự thảo” thực tế thuộc source2025. Section0 còn gộp
   assertion trạng thái2025 dưới heading2024: đây là lỗi gán scope xuyên nguồn.
2. Hai giá trị cập nhật2026 và thông báo/ngày có nguồn. Relation `supersedes`
   lại trỏ mức cũ→mức mới; với nghĩa subject thay thế object, chiều này bị đảo.
   Reviewer model chỉ kiểm mô tả thay thế chung và bỏ sót hướng quan hệ.
3. Ngày ban hành2023 của nguồn2024 còn trong missed evidence; chưa biểu diễn đủ
   publication role. Coverage chưa khép. Không được xóa missed ledger để duyệt.
4. Synthesis reviewer đã chặn một câu diễn giải chưa có căn cứ, nhưng **không bắt
   hết** lỗi1–2. Machine verification cùng model không phải chứng nhận ngữ nghĩa
   hoặc thay quyết định người dùng. Tọa độ đúng không chứng minh diễn giải đúng.

Vì vậy chưa được dùng bundle này làm nội dung có hiệu lực. Rubric do Codex đối
chiếu nguồn, không phải human holdout; không gọi judgeLLM. Chi tiết private ghim
response hash tại `live-inventory/offline-audit.json`. Không lưu corpus/raw output
LLM sai hoặc prompt riêng vào Git/docs.

Phần cần tiếp tục trước rollout nội dung: kiểm từng scope claim với đúng source,
ngăn trạng thái nguồn này chi phối section của nguồn khác, định nghĩa/kiểm hướng
relation và hoàn tất missed coverage/time roles. Đây là giới hạn của compiler
ngữ nghĩa mới, **không phải P10** và không được lấy lý do này để sửa RAG ngoài
phạm vi hoặc publish thử.

## Kiểm tra dữ liệu vận hành và dọn thử nghiệm

Seals sau live khớp trước603 cho5 collections/24bindings/12source revisions/
37index revisions/5assistants/13model configs. Full vector namespace2943point giữ
hash payload giống trước/sau602,0retrievable; raw ba file không đổi. Không đổi
model/config/nguồn/index/publication thật; chỉ ModelOps usage/audit hợp lệ tăng.

DB603 đã drop sau full gate và xác minh exact name/ownership nonce,
đọc lại xác nhận không còn; cleanup helper exit0. Storage runtime/evidence giữ theo chính sách bảo vệ;
không recursive delete hoặc tắt policy. Trạng thái cleanup cuối nằm trong
`checks/isolation.json`, được chốt khi bàn giao.

Không commit/stage/push/reset/reindex/restart/deploy. UI và serving integration
là đợt sau theo602, chưa làm trong603. Các phần lifecycle/API đã có mã và test;
không tuyên bố APPROVED toàn compiler, RAG, hoặc production E2E.

Kiểm bàn giao offline cuối exit0:454app code seals khớp, schema602 giữ nguyên
shape,18source/test files và8 tài liệu UTF-8 không BOM/LF,37liên kết local đúng,
0secret pattern flag, `git diff --check` exit0,0file staged. Receipt
`backend/storage/context603/closing-checks.json`; PASS toàn vẹn bàn giao không
đổi FAIL18 nền hoặc FAIL nội dung compiler thành PASS.
