# Context604 — Kết quả kiểm chứng

Ngày 23/10/2026. **Chưa APPROVED chất lượng nội dung compiler thật.** Bảo vệ nguồn/năm và chiều quan hệ đã bổ sung; artifact thật cuối vẫn `needs_attention`. Chưa triển khai đợt5/UI/serving. P10 và benchmark64 để sau theo yêu cầu.

## Môi trường

Kiểm DB, MinIO và Qdrant phát triển ở loopback trước chạy. DB thử riêng `qnu_test_context604_0a3b12ea0d87`, ownership comment kèm nonce; Storage riêng `backend/storage/context604-runtime-0a3b12ea0d87/objects`. Schema chỉ tạo trong DB thử, không migration DB ứng dụng. Pytest ENV test, dịch vụ ngoài trỏ `127.0.0.1:1`, có network guard. Sao một defaults row inactive vào DB thử,0 credential/provider row. ModelOps thật đọc cấu hình động hiện có qua session riêng.

Baseline là snapshot app đầu604, gồm các thay đổi600–603 chưa commit; không dùng HEAD ghi đè working tree. Tám file app604 khác snapshot, không xóa file app. Không parser/RAG/P10/FE/model/defaults thay đổi; không subagent, cài dependency, commit/stage/push/reset/reindex/restart/deploy/publication.

## Regression

| Kiểm tra | Kết quả | Exit |
|---|---|---:|
| Full baseline đầu604 | 3468 PASS /18 FAIL /17 SKIP, +23 subtest PASS | 1 |
| Probe tái hiện trước sửa | 4 FAIL đúng lỗi scope/source/year/heading | 1 |
| Focused cuối `focused-final` | 138 PASS,1 warning Qdrant offline;102,50s | 0 |
| Ruff phạm vi12 file | PASS | 0 |
| Full cuối | 3520 PASS /18 FAIL /17 SKIP, +23 subtest PASS;13 warnings;564,20s | 1 |
| FE/build/browser/chatbot64 | NOT RUN, ngoài batch này | — |

Không cộng các lượt focused thành full PASS. Bốn probe mới604 được chạy riêng trên app snapshot cũ; baseline full không gồm module604. Fixture603 thích ứng số nhóm synthesis theo budget, vẫn kiểm phase/source, một inference owner và không resend khi replay. Không bỏ assertion/guard để làm suite xanh.

[Đối chiếu exact test IDs](./TEST_ID_COMPARISON.md):52 ID mới đều PASS;0 failure ID mới,0 đổi failure message/cause,0 mất ID cũ,0 lỗi nền được sửa. Full suite vẫn **FAIL** với18 lỗi nền. Các nhóm lỗi giữ nguyên gồm schema/seed legacy, auth contract cũ, assertion legacy và dịch vụ ngoài bị chặn trong môi trường test; không gọi những lỗi đó là PASS hoặc bỏ qua.

Lệnh từ root; helper đặt cwd pytest là `backend`, lưu argv/exit/DB/Storage:

```powershell
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context604_checks.py run --baseline --label baseline-full -- --ignore=tests/test_compilation_semantics_604.py
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context604_checks.py run --label focused-final -- <9 modules trong focused-final-run.json>
backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context604_checks.py run --label full-final
```

Ruff dùng `.venv/Scripts/python.exe -m ruff check` đúng12 file trong `checks/ruff-final-run.json`. Receipts/JUnit/log local tại `backend/storage/context604/checks/`.

## ModelOps thật — các lượt giữ riêng

Cùng ba DOCX2024/2025/2026, canonical parser602; primary `cx/gpt-6-luna`, observed `gpt-6-luna`. Không đổi model/defaults; fallback config giữ nguyên, thí nghiệm chỉ cho primary đã chọn,0 fallback thực tế. ASGI handler/DB/LocalStorage và inference là thật; không phải browser/published chatbot E2E. Source fixtures ready chỉ format-only, chưa full Quality Gate.

| Folder artifact | HTTP/trạng thái | Luna usage success | Nhận định |
|---|---|---:|---|
| `live` | 422 coverage_unknown_assertion | 20 | Object ID chưa cấp bị chặn |
| `live-handles` | 200 needs_attention | 30 | Scope/hướng gốc sửa; còn role/navigation và coverage |
| `live-policy3` | 422 deferred_reference_outside_primary | 19 | Tách offered context khỏi primary |
| `live-inventory` | 422 unknown_section_assertion | 32 | Bổ sung enum reference mọi bước |
| `live-reference-contract` | 200 needs_attention | 39 | 0 missed proof, còn condition/exception |
| `live-qualifiers` | 200 needs_attention | 43 | 0 missed proof; điều kiện đạt, còn role phiên bản/citation năm |
| `live-temporal` | 200 needs_attention | 41 | Thời gian/sections đạt;3 bất đồng relevance, direction unresolved |
| `direction-probe` trên code cuối | FAIL ALL_PROVIDERS_UNAVAILABLE | 0 success row;1 request timeout | Provider ReadTimeout, chưa có nội dung để đánh giá ngữ nghĩa |

Tổng224 usage success Luna qua7 build. Probe timeout không có success row; không tính0 row thành0 request. Giữ intent/error receipts, không tự resend timeout. Build mới có key/tag riêng sau sửa hợp đồng và có receipt kết thúc; không gửi lại intent chưa rõ. Lỗi Python runner chọn/đọc artifact được xử lý bằng đọc lại read-only, không resend model.

## Artifact thật cuối và audit độc lập

Job `kc_777596862bcf4bd8be4dac337131b75d`: create200/exact GET200;10 assertions/3 sections/1 relation;212.206,33ms.41 Luna success,137.079 input/17.469 output tokens, input lớn nhất5.067;0 fallback. Không suy chi phí hoặc khả năng Qwen32K từ số này.

Audit read-only `source-audit.json` đạt:

- 381/381 proof khớp exact source/revision/canonical text/offset/hash/locator; bytes ba DOCX không đổi. Binding/render/hash và machine_complete=false được tính lại.
- Tổng2024 là5948, nhóm giáo viên1613 kèm điều kiện phân bổ; không mượn nhãn Dự thảo2025. Ngày22/12/2023 giữ publication, không thành năm dữ liệu2023.
- Nguồn2025 giữ nhãn Dự thảo; không tự gọi mẫu số nhập học5308 là quota.
- Proposal supersedes đúng mới5.173 → cũ4.500, có nguồn cập nhật; không cộng quota bổ sung456 vào tổng. Ngày18/09/2026 giữ event phiên bản.
- Item và synthesis checks lượt7 đều đạt, nhưng coverage còn3 proof và direction review chưa đạt. Không dùng audit thủ công thay verdict hoặc human approval.

### Những gì còn chặn

| Proof | Bất đồng | Bảo vệ |
|---|---|---|
| `proof_3ce10d6e16bc2e5264872633` | Chú giải X của cột đăng ký: unrelated so với required qualifier | Giữ raw/ledger, không suy X thành quota hoặc0 |
| `proof_79fd39c9639cb779bd2dc897` | Tiêu đề2025 có ngày/tháng trống: supporting context so với unrelated | Không bịa ngày công bố hoặc đổi authored status |
| `proof_d550f8afe81037fe688a61c6` | Quota bổ sung456: ngoài topic tổng năm so với required metric riêng | Giữ metric/đợt riêng, không cộng hoặc loại lặng |

Đây là bất đồng phân loại chủ đề ở compiler, chưa chứng minh parser mất nội dung. Các đoạn vẫn còn trong canonical/proof catalog. Association cần dựa cột/metric/quan hệ cụ thể, không từ điển câu test.

Direction review lượt7 nhận ra nguồn5.173 thay4.500, nhưng hiểu thứ tự mảng endpoint là chiều đề xuất nên trả unresolved. Code cuối đổi thành membership map; regression xác minh payload giống nhau khi đảo chiều đề xuất, witness phải dựng chiều từ nguồn. Probe thật code cuối bị provider timeout: **chưa có full compiler thật thành công trên code cuối**. Không đổi artifact7 thành ready hoặc ghép probe thành whole workflow PASS.

[Đối soát24 proof cũ](./RECONCILIATION_24.md):24/24 exact span;20 dòng danh mục không có quota ngành, một ngày ban hành, một tỷ lệ nhập học chưa chứng minh quota, một căn cứ văn bản, một metric bổ sung. Đây là source audit, không human approval.

## Bảo toàn và bàn giao

Postcheck cuối (`postcheck-final.json`) đạt: bytes ba nguồn và full vector payload2943 giữ so trước/sau602,0 retrievable. Shared read-only seals khớp trước604 cho5 collections/24 bindings/12 source revisions/37 index revisions/5 assistants/13 model configs. Inference có usage/audit/lease theo ModelOps hiện có, không sửa cấu hình model. Code seal cuối khớp revision đã chạy full tests và attempted direction probe; không diễn giải code equality thành model PASS.

DB thử đã dọn thành công sau kiểm exact name + ownership nonce, không đụng DB ứng dụng. Storage local còn giữ: trạng thái `database_removed_storage_pending`, do recursive deletion đã bị policy chặn ở phiên trước. Không thử lách hoặc tắt guard; bằng chứng ngoài Git vẫn có thể đọc. Các raw/proposal receipts không được ghi vào docs hoặc commit.

Chưa APPROVED toàn nội dung. Bước sau là làm rõ relevance/association ba proof theo topic và kiểm direction khi provider đáp ứng; chưa mở rộng UI/serving bằng artifact còn blocker. Không cần reparse hoặc đổi nguồn/model chỉ để bỏ cảnh báo. Không chuyển điểm59/60 lịch sử602 thành kết quả604.
