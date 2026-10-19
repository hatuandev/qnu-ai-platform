# Phiên550 — Qwen primary và cập nhật credential

Ngày 2026-10-19. Phạm vi được người dùng cho phép: đổi primary chat sang `qwen3.5-9b`, dùng endpoint/credential được cung cấp và gọi thử lại. Cấu hình được cập nhật ở database phát triển local, không phải production.

## Cấu hình đã xác minh

- Primary `qwen3.5-9b`, provider `prov_rtx5090_vllm`; fallback `cx/gpt-6-luna`. Giữ chế độ combo và các default embedding/reranker/OCR khác; so sánh hash và đọc lại bằng session DB mới đạt.
- Base URL `http://100.105.13.53:8000/v1` đã đúng từ trước; Chat Completions dùng đường dẫn `/chat/completions`.
- Credential mới được truyền qua stdin, cập nhật bằng service ModelOps hiện có. Provider column, relational key và pool tương thích đều đã mã hóa, đọc lại đối chiếu trong bộ nhớ đạt. Không lưu plaintext vào source, tham số tiến trình, `.env` hoặc báo cáo. Không xóa key/provider.
- Provider dùng key chung cho các model cùng connection; chỉ thay credential theo yêu cầu, không đổi danh mục/capability/model embedding. Không thực hiện embedding inference hoặc chuyển index.

## Kết quả thực chạy

| Test ID | Thời điểm | Kết quả | Exit | Nguyên nhân / bằng chứng |
|---|---|---|---|---|
| `live-table` | Sau đổi primary, trước khóa mới | FAIL / BLOCKED | 1 | Qwen HTTP400; GPT dự phòng trả JSON/schema hợp lệ nhưng evidence binding từ chối `EVIDENCE_SCOPE_ROW_AMBIGUOUS_SELECT_NARROWER_SPAN` |
| `live-api` | Sau đổi primary, trước khóa mới | FAIL / BLOCKED | 1 | Qwen HTTP400 context; GPT dự phòng HTTP200 nhưng cùng lỗi evidence scope |
| `minimal-chat` | Trước khóa mới | PASS | 0 | Qwen thật, không fallback, stop; 22 input / 2 output tokens, 242,6 ms. Vì vậy không có bằng chứng lỗi trước do thiếu key |
| `new-key-chat` | Sau khóa mới | PASS | 0 | Prompt tiếng Việt theo yêu cầu, max output150; Qwen thật, không fallback, stop; 23 input / 29 output tokens, 643,1 ms |
| `new-key-api` | Sau khóa mới | FAIL / BLOCKED | 1 | Qwen HTTP400 với cùng hash body lỗi context; fallback GPT `ReadTimeout`, kết quả `ALL_PROVIDERS_UNAVAILABLE`. JSON/schema/binding/human review/apply NOT RUN ở lượt này |
| Ruff hai helper | Sau batch | PASS | 0 | `switch_chat_primary.py`, `verify_json_output_contract.py` |
| Full Pytest phiên550 | Không chạy | NOT RUN | — | Chỉ đổi cấu hình/operational helper, không sửa app code trong phiên550. Full phiên549 là lịch sử: **18 FAIL / 2336 PASS / 17 SKIP**, không coi là current PASS |

Đối chiếu đúng lỗi: Qwen trước/sau credential đều có HTTP400, body SHA256 `f17f1e4499445ee17b46b215c99ff244234457e0732288d5e59fd249afe1a53d`. Sau cập nhật, phản hồi số xác nhận context tối đa8192, request dành6000 token output, nên còn2192 cho input; server báo input **ít nhất2193**, không phải tổng input chính xác đã đo. Credential mới không giải quyết giới hạn này. Lỗi fallback ở `new-key-api` khác lỗi binder của `live-api`; không báo binder đã sửa hoặc đạt khi nó chưa chạy.

Không cắt context hoặc tự đổi output/server context để vượt lỗi trong tác vụ cập nhật khóa. Bước xử lý tiếp cần điều chỉnh tương thích budget/context ở tầng phù hợp rồi kiểm lại evidence; chưa có proposal hợp lệ hoặc phê duyệt người dùng.

## Môi trường và dọn dẹp

DB/MinIO/Qdrant được đối chiếu qua `backend/storage/context550-safety.json` trước chạy. Shared DB local chỉ ghi các cấu hình ModelOps đã được cho phép. Fixture/API writes chạy trong DB riêng `qnu_test_context548_cb82a5c633d0`, có nonce ownership; Storage local tạm. MinIO/Qdrant/Redis của test trỏ dead port `127.0.0.1:1`, không ghi vào dịch vụ thật. Tên548 là prefix harness tái sử dụng, không phải DB lịch sử.

Metadata được xuất trước cleanup; DB riêng đã xóa sau xác minh ownership, runtime tạm đã xóa và xác nhận không còn. Không migration production, không approve/apply nguồn, không index/publish/restart/deploy/commit/push.

## Lệnh và chứng cứ

Cwd tất cả lệnh: root repo. Các lệnh dùng `backend/.venv/Scripts/python.exe`:

- `backend/scripts/switch_chat_primary.py --model qwen3.5-9b --audit backend/storage/context550-safety.json --output backend/storage/context550-evidence/default-change.json` — exit0.
- `backend/scripts/context_patch_validation.py script --label <TEST_ID> --args-json backend/storage/context550-evidence/<TEST_ID>-args.json --state-file backend/storage/context550-isolation.json --evidence-dir backend/storage/context550-evidence --audit-file backend/storage/context550-safety.json` — exit theo bảng. Ngoại lệ ID `minimal-chat` dùng cùng tên args; toàn bộ args không chứa credential.
- One-time rotation helper đọc secret qua stdin bằng pipe, gọi `modelops_service.update_provider`, xác minh session mới và refresh bản sao mã hóa trong DB test có ownership — exit0. Không lưu input bí mật.
- `-m ruff check backend/scripts/switch_chat_primary.py backend/scripts/verify_json_output_contract.py` — exit0.
- `backend/scripts/context_patch_validation.py cleanup --state-file backend/storage/context550-isolation.json --evidence-dir backend/storage/context550-evidence --audit-file backend/storage/context550-safety.json` — exit0; tiếp theo `backend/scripts/cleanup_context_patch.ps1` với cùng StateFile/EvidenceDirectory — exit0.

[Checks theo ID](checks.json), [default trước/sau](default-change.json), [credential receipt không chứa key](credential-change.json), [cleanup](cleanup.json), [hash metadata](manifest.json). Không xuất raw model response, DB dump hoặc tài liệu nguồn.
