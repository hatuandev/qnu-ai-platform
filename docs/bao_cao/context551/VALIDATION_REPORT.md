# Phiên551 — Live retest sau khi người vận hành tăng Qwen lên32K

Ngày 2026-10-19. Người dùng báo đã tăng context Qwen lên32K và cung cấp ảnh Qwen/Luna HTTP200 với câu hỏi ngắn; yêu cầu chạy lại. Ảnh là ngữ cảnh, các kết quả dưới đây đến từ phép thử mới qua ModelOps.

## Kết quả thực tế

| Test ID | Model thực | Kết quả | Exit | Bằng chứng |
|---|---|---|---|---|
| `chat-qwen` | `qwen3.5-9b` | PASS | 0 | Primary chỉ định, không fallback, stop;23 input/29 output tokens;509,98ms |
| `chat-luna` | `gpt-6-luna`, requested `cx/gpt-6-luna` | PASS | 0 | Provider Luna chỉ định, không fallback, stop;798 input/19 output tokens;4935,17ms |
| `live-table` | `qwen3.5-9b` | FAIL / BLOCKED | 1 | HTTP200, stop, JSON/schemaPASS;16338 input/1191 output tokens. Evidence bindingFAIL: `EVIDENCE_SCOPE_ROW_AMBIGUOUS_SELECT_NARROWER_SPAN` |
| `live-api` | `qwen3.5-9b` | FAIL / BLOCKED | 1 | HTTP200, stop, JSON/schemaPASS;16312 input/1587 output tokens. Evidence bindingFAIL: `EVIDENCE_UNIT_MISMATCH` |
| Scoped Ruff | Operational helper | PASS | 0 | `backend/scripts/verify_json_output_contract.py` |
| Full Pytest | — | NOT RUN | — | Chỉ live retest và helper vận hành; không sửa application code trong551. Historical549 vẫn18FAIL/2336PASS/17SKIP, không phải kết quả current |

Cả hai phép thử tài liệu đều chỉ có1logical call/1provider attempt/1HTTP attempt, không fallback, không format retry. Policy cho output6000; gói lớn nhất16338 input +6000 output reserve =22338, nằm trong32768. Context tăng đã đủ cho **hai gói thực sự được gửi**, không có lỗi8192 cũ ở các lượt này. Chưa gọi endpoint quản trị để xác minh chính xác trần server, và không suy rằng tất cả gói tương lai đều vừa32K.

API tạo kế hoạch22packet nhưng dừng sau packet đầu do evidence binding, nên21packet còn lại chưa kiểm chứng. Human review/apply/persist-reload/projection downstream NOT RUN. Luna chỉ được kiểm tra short chat riêng trong551; không tuyên bố Luna đã qua semantic document test. JSON/schemaPASS do parser/backend kiểm chứng; effective output contract `prompt_only`, không chứng minh upstream native JSON Schema enforcement.

## Đối chiếu đúng lỗi với550

- Cùng fixture DOCX SHA256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`, cùng Bảng1 `qnu:t001`, projection hiện tại và settings mặc định. Bản selected-table dùng pair offline có kiểm hash/raw archive; bản API parse DOCX hiện tại và gọi đúng handler semantic-proposals trong ASGI test.
- `live-table`550: Qwen400context rồi GPTfallback JSON/schemaPASS nhưng scope ambiguousFAIL. `live-table`551: Qwen200, không fallback, cùng mã scope ambiguousFAIL. **Chỉ lỗi dung lượng đã được vượt qua; scope chưa đạt.**
- `new-key-api`550: Qwen400context và GPTfallbackReadTimeout, `ALL_PROVIDERS_UNAVAILABLE`, downstreamNOT_RUN. `live-api`551: Qwen200, JSON/schemaPASS, không fallback, lỗi mới được quan sát ở binding `EVIDENCE_UNIT_MISMATCH`. Không coi đổi mã lỗi là đạt.
- Short Qwen550 đãPASS; Qwen551 vẫnPASS. Luna551 short chatPASS không chứng minh timeout của yêu cầu dài đã được giải quyết.

## Giải nghĩa finding

`EVIDENCE_SCOPE_ROW_AMBIGUOUS_SELECT_NARROWER_SPAN`: guard hiện tại từ chối scope `row` nếu đoạn evidence nhắc nhiều mã dòng. Model cần chọn span hẹp hơn hoặc phạm vi có căn cứ phù hợp. Không tự nới guard.

`EVIDENCE_UNIT_MISMATCH`: guard kiểm `binding.source_unit_id` phải khớp unit mà selection khai báo. Lượt API bị từ chối ở quan hệ này; JSON hợp lệ không đồng nghĩa liên kết nguồn chính xác. Chưa triển khai sửa hoặc ép proposal qua validator trong tác vụ chạy lại.

## An toàn và phạm vi

Áp dụng skill ModelOps; helper giữ thay đổi nhỏ theo clean-code. Audit mới kiểm cấu hình DB/MinIO/Qdrant: source DB phát triển `127.0.0.1:5432/qnu_ai_platform`, transaction READ ONLY; MinIO127.0.0.1:9000, Qdrant127.0.0.1:6333. Source chỉ đọc để sao chép cấu hình/credential **mã hóa**. Không sử dụng key từ ảnh hoặc thêm `.env`.

Test DB riêng `qnu_test_context548_352314b47a8f`, nonce ownership; runtime LocalStorage riêng. Prefix548 do harness tái sử dụng, không phải DB lịch sử. Child config chặn MinIO/Qdrant/Redis bằng127.0.0.1:1, tắt auto migration/seed của ứng dụng. DDL setup chỉ tạo49 bảng trong DB test trống; không migration hay schema change production. API dùng TEST generation actor trong app cô lập, không actor phê duyệt.

Sau export metadata, đã xác minh ownership/xóa DB test, xóa runtime/Storage và xác nhận không còn. Read-only session mới so sánh hash defaults/provider public settings trước/sau đạt: primaryQwen/fallbackLuna, URL/timeout/activity giữ nguyên. Qwen timeout60s; Luna15s theo cấu hình hiện có, không tự tăng.

Không sửa app code, không approve/apply nguồn, không index/publish/reparse dữ liệu thật/restart/deploy/commit/push. Raw corpus/model response nằm trong runtime đã dọn; báo cáo chỉ giữ metadata/hash/traces không chứa khóa hoặc trích nội dung nguồn.

## Thay đổi và lệnh

`backend/scripts/verify_json_output_contract.py`: thêm `--chat-model`, chỉ chọn một model active trong chain được cấu hình; no-fallback probe xác minh provider và requested model, chấp nhận tên model trả về do router chuẩn hóa nhưng ghi rõ cả hai. Không đổi model defaults hoặc inference service.

Cwd: root repo. Python: `backend/.venv/Scripts/python.exe`.

1. `backend/scripts/audit_context_patch.py --output backend/storage/context551-safety.json` — exit0.
2. `backend/scripts/context_patch_validation.py setup` rồi `seed-modelops`, cùng `--state-file backend/storage/context551-isolation.json --evidence-dir backend/storage/context551-evidence --audit-file backend/storage/context551-safety.json` — exit0 mỗi bước.
3. `backend/scripts/context_patch_validation.py script --label <TEST_ID> --args-json backend/storage/context551-evidence/<TEST_ID>-args.json` với cùng state/evidence/audit — exit theo bảng. Exact argument arrays và cwd ở [checks](checks.json), không chứa secret.
4. `-m ruff check backend/scripts/verify_json_output_contract.py` — exit0.
5. Harness `cleanup` với cùng state/evidence/audit — exit0; tiếp theo `backend/scripts/cleanup_context_patch.ps1` với cùng StateFile/EvidenceDirectory — exit0. Fresh read-only config comparison — exit0.

[Checks và exact-ID comparison](checks.json), [cleanup](cleanup.json), [config verification](config-after.json), [hash manifest](manifest.json).
