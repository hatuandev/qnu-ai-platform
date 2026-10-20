# Context564 — Kết quả kiểm thử

Ngày 2026-10-20. Kết luận tổng thể **PARTIAL**: sửa packing được kiểm chứng; Reviewed Fact chat E2E chưa đạt vì blocker chọn thực thể/dữ kiện độc lập.

## Môi trường và cách chạy

Đã xác minh development, PostgreSQL/MinIO/Qdrant trên loopback trước chạy. Pytest dùng database riêng có nonce/ownership comment, Storage riêng; MinIO/Qdrant/Redis của test trỏ port 1, không truy cập dịch vụ đang chứa dữ liệu thật. Không migration/auto-seed database dùng chung. ModelOps phục vụ tests được sao chép có bảo vệ vào DB test, không xuất credentials.

Từ root repo, runner hiện có được gọi với state/evidence riêng:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/context_patch_validation.py run --state-file backend/storage/context564/isolation.json --audit-file backend/storage/context564/safety.json --evidence-dir backend/storage/context564/tests --label verification-final tests/test_evidence_closure_564.py tests/test_review536_findings.py tests/test_qnu_serving.py tests/test_evidence_quality_444.py tests/test_evidence_claims.py tests/test_evidence_contracts_500.py tests/test_evidence_scope_452.py tests/test_evidence_retrieval_regressions.py tests/test_hybrid_conversation.py tests/test_hybrid_intent_routing.py tests/test_hybrid_chat_integration.py
backend/.venv/Scripts/python.exe backend/scripts/context_patch_validation.py run --state-file backend/storage/context564/isolation.json --audit-file backend/storage/context564/safety.json --evidence-dir backend/storage/context564/tests --label full-final
backend/.venv/Scripts/ruff.exe check backend/app/modules/rag/evidence_blocks.py backend/app/modules/rag/evidence_dependencies.py backend/tests/test_evidence_closure_564.py
git diff --check
```

Runner thực thi Python venv / `pytest -q`, cwd `backend`, ghi exact command, exit code, DB/Storage riêng và JUnit. Bằng chứng private: `backend/storage/context564/tests/*-run.json`, `*.xml`, `*.log`. Không coi exit code của runner/HTTP 200 thay cho trạng thái assertions.

| Lượt | Kết quả | Exit | Ý nghĩa |
|---|---|---:|---|
| `red` | 5 FAIL / 14 PASS | 1 | Tái hiện mất source row trước sửa |
| `focused` | NOT RUN | 4 | Gõ nhầm tên file test; không gọi PASS |
| `focused-corrected` | 317 PASS | 0 | Batch sửa source row |
| `integration` | 1 FAIL / 49 PASS | 1 | Test so snapshot mới có timestamp khác; đã sửa test để so deepcopy trước/sau |
| `integration-final` | 50 PASS | 0 | Fixture published → chọn fact → pack → projection |
| `canonical-red` | 1 FAIL | 1 | Thiếu directed canonical closure bắc cầu |
| `group-red` | 1 FAIL / 1 PASS | 1 | Một fixture chưa tách footnote đủ rõ; tăng độ thực chất rồi chạy lại |
| `group-red-separated` | 2 FAIL | 1 | List member/ancestor được thêm nhưng mất footnote |
| `directed-note-red` | 1 FAIL | 1 | Closure mở nhầm enumeration siblings của shared note |
| `verification-final` | **343 PASS** | **0** | Regression trọng tâm trên mã cuối |
| `full-after` | 2686 PASS / 18 FAIL / 17 SKIP + 23 subtests PASS | 1 | Lịch sử giữa batch, trước hoàn tất canonical/member closure |
| `full-final` | **2693 PASS / 18 FAIL / 17 SKIP + 23 subtests PASS** | **1** | Full gate cuối, 464,34 giây; **FAIL** |
| Ruff 3 files | PASS | 0 | Chạy lại trên mã cuối |
| Git diff whitespace | PASS | 0 | Cảnh báo autocrlf không phải bytes CRLF hiện tại |

## Đối chiếu regression chính xác

Baseline gần nhất có JUnit đáng tin cậy là Context562 `tests/full-verified.xml`: 2666 PASS / 18 FAIL / 17 SKIP. Context563 chỉ chẩn đoán, không có baseline suite mới.

So với `full-final.xml`: **27 test ID mới đều PASS, 0 test đổi trạng thái, 0 test bị bỏ, 18 failure IDs và nguyên nhân đầu tiên giống hệt**. Phụ lục [REGRESSION_IDS](REGRESSION_IDS.md) liệt kê từng ID và nguyên nhân; comparison đầy đủ giữ private. Không gọi toàn suite PASS và không sửa expectation của tests cũ.

27 test mới bao gồm missing/duplicate/cross identity, malformed refs, cycles, shared notes, budget, canonical text và published artifact fixture. Đây là LOCAL_INTEGRATION_PASS; không thay thế chat Reviewed Fact E2E.

## An toàn và giới hạn

Post-run seal khớp toàn bộ trước/sau: 5 collections, 23 bindings, 2 source revisions, 27 index revisions, 5 assistants và 13 ModelProviderConfigs. Không viết lại source/hash/publication/model settings. Không frontend change nên frontend build NOT RUN trong phiên này.

DB test đã được xóa qua runner có xác minh ownership. Tổng 11 hội thoại và 8 KnowledgeGap records mới thuộc các batch live/TCP đã dọn; usage audit giữ nguyên. Evidence private trong `backend/storage/context564` được giữ phục vụ đối soát.

Xóa runtime Storage riêng bị kiểm duyệt tự động từ chối: **blocked by policy**. Không đổi chính sách, không dùng cách xóa thay thế; runtime được giữ và ghi inventory trong evidence. Không xóa dữ liệu nguồn thật.

