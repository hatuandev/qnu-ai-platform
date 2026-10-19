# Phiên552 — Evidence binding & selector final integration

## Kết luận theo checkpoint

- **A — Implemented / focused PASS**: selector v2 được ghim nhất quán; v1 giữ nguyên schema hash và guard owner. Scope row/group chuyển thành issue cụ thể có toàn nguồn; không tự suy nghĩa từ mã hoặc khoảng mã. Focused217PASS, thêm39case so baseline; Ruff14filePASS, frontend15PASS/Biome2file/buildPASS.
- **Full backend vẫn FAIL**: baseline mới18FAIL/2336PASS/17SKIP; sau sửa18FAIL/2375PASS/17SKIP, cùng23subtests. Cả18ID/cause giống nhau, không ID mất/status đổi/lỗi mới;39ID mới đềuPASS. Không lấy lịch sử549/551 làm baseline.
- **B — Live provider/JSON/schema/binding PASS, proposal pending**: một request Qwen thật với selector v2, không fallback/retry. Có4note proposals,8issue mở, scope selected_tables. Python runner exit2 là checkpoint chờ review, không phải E2EPASS.
- **C — Human review WAITING_FOR_REVIEW**: chưa có actor người dùng thật duyệt, chưa apply/persist/rebuild annotation thật. Các test TEST actor/Storage/session/rebuild ba lần PASS riêng, không thay E02.
- **D — Toàn tài liệu NOT RUN**: chưa qua checkpoint người dùng B/C. Không lấy22packet của551 làm số hiện tại và không tuyên bố helper selected-table là API toàn tài liệu. Khi tiếp tục phải tính lại packet/policy và budget qua API thật; không tái gọi model để chỉ đọc proposal đã có.

## Bằng chứng deterministic

Python3.12.13 trong `backend/.venv`, phù hợp `backend/pyproject.toml` yêu cầu>=3.12,<3.13. Baseline dùng bản app đóng băng trước sửa và cùng cấu hình test có ModelOps copy mã hóa. Red đầu29FAIL/2PASS; registry-only red thêm1FAIL. Sau sửa,39test mới và các tests lifecycle/contract/context/known-unknown liên quan đều đạt.

| Matrix ID | Expected | Actual / test ứng dụng |
|---|---|---|
| B01/B04 | V1 owner đúng chạy; v2 suy owner qua registry | PASS, `test_B01_B04_expected_contract_derives_same_verified_annotation` cả2version |
| B02/B03 | V1 sai/thiếu owner không được cứu | PASS, `test_B02_B03_v1_never_recovers_wrong_or_missing_owner` |
| B05 | V2 thêm owner/quote/approval bị từ chối | PASS,3param extra-field |
| B06/C01 | Expected contract/hash/version được ghim; cache/fallback không trộn | PASS, schema cache xen kẽ, mismatched metadata và actual ModelOps HTTP fallback cảv1/v2 |
| B07/B08 | Unknown/private-only/foreign/tampered evidence, target sai bị từ chối | PASS,9mutation trong `test_B07_B08_v2_keeps_packet_and_canonical_source_guards`; guard cột/ô và sibling tiếp tục được kiểm ở bộ binding/known-unknown |
| B09 | Notes/cells/limitations v2 giữ raw, owner và validator | PASS, mixed meanings/limitation; slash còn ambiguous, chưa áp dụng |
| S01/S02 | Nhiều mã/negative subspan không tự chứng nhận scope | PASS, full source issue; generic approval bị chặn |
| S03/S04 | Range có ngoại lệ, mã0 đầu giữ chuỗi và exact set | PASS, `test_S03_range_exception_never_enters_confirmed_target_set` và group/string-code params |
| S05 | Specific decision chỉ áp đúng target | PASS, graph relation không lan dòng bị loại |
| S06 | Sai target/issue/hash, actor giả, evidence bị cắt bị từ chối | PASS,5param decisions |
| S07/L03/L04 | Reject/changes_requested giữ active; fresh Storage/rebuild idempotent; stale bị chặn | PASS, new row scope test và lifecycle/context548 tests |
| S08 | Hai note cùng chữ giữ owner/target riêng | PASS, v2 duplicate text/tables và actual-DOCX v1 compatibility test |
| S09 | Multi-year, unresolved, slash không regression | PASS, focused context548/binding/source_limitations |
| L01 | Packet1 bind thật, packet2 JSON/ID/timeout lỗi, zero stage | PASS, actual binder wrapped; two-packet contract/context548 tests |
| L02 | Deadline/cancel không ghi muộn lên caller | PASS, thread stage/deadline/cancel tests |
| C02 | V2 format retry giữ packet/hash/contract và stage1lần | PASS, new pipeline test + real HTTP→ModelOps→parser→binder test |
| C03/E01 | Bảng1 scope chọn, pending, không publication toàn nguồn | PASS cho kỹ thuật; pending8issue, chưa semantic complete |
| E02 | Người thật duyệt và persistent reload/rebuild thật | WAITING_FOR_REVIEW / NOT RUN |
| E03 | Toàn tài liệu qua API thật | NOT RUN sau checkpoint C, không thay bằng mock/helper |

JUnit và exact statuses ở [focused](focused-final.xml), [full](full.xml), [baseline](baseline.xml), [comparison](regression-comparison.json), [18failure IDs/cause](REGRESSION_IDS.md). Đã bỏ captured bodies/source dump khỏi XML xuất, giữ exact IDs/status/first-line causes; original raw XML còn trong dossier vận hành private. Invalid token literal trong test ID `test_configuration_seed` là dữ liệu synthetic cố ý sai, không phải credential.

## Live Bảng1

Fixture DOCX SHA256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`, không sửa. Pair/raw resource archive được xác minh checksum, load bằng StorageDriver rồi rebuild projection CURRENT trước gọi. Đúng `qnu:t001`,1packet bắt buộc trong selected scope.

- Model/provider thực: `qwen3.5-9b`/`prov_rtx5090_vllm`, HTTP200, finishstop, is_fallbackfalse.
- Contract `qnu_semantic_selector_v2`, version2; requestedjson_schema/effectiveprompt_only theo policy đã cho phép. **Native JSON SchemaNOT_VERIFIED**.
- Input16469tokens, output519tokens, output reserve6000 giữ nguyên. Model latency5542,88ms; aggregate model_ms5665,78. Một call/provider/transport attempt; format_retries0, context expansionNOT_RUN.
- Build192,19ms; binding218,48ms;4accepted/0rejected. Đây là4candidate notes, không phải4annotation đã duyệt.
- Pending proposal hash `80308912eba6ceecfcec7283e7ebedef225fe756000eb57c14602b0b58bbcfc3`.
- 8 issue: 2 scope confirmation (row/column), 6 deferred reference. Packets complete trong scope chọn; semantic_completefalse/application_blockedtrue/publication_blockedtrue.
- Policy trong trace: max_calls4, max_packets24, run120s/call90s, max_packet48000bytes/max_total1000000bytes, output6000. Actual packet/accounting47651bytes; HTTP payload48938bytes, được tính riêng vào transport budget. Không tăng các giới hạn để né lỗi.

[Live summary](live-summary.json), [trace/schema/policy/source hashes và redacted selectors](live-trace.json), [v1/v2 schema hashes](schema-hashes.json). Raw selector bytes và nguồn cần review được giữ riêng trong checkpoint private; không đưa prompt/corpus vào báo cáo chung. Raw551 **NOT_AVAILABLE**, không dùng synthetic payload như response gốc.

## Checkpoint cần người dùng

[Bản đối soát private:4chú thích/8issue](../../../backend/storage/context552-checkpoint-06689f8f17dc/REVIEW.md).

Đây là checkpoint **offline**, chưa phải pending revision trong UI hoặc ứng dụng job đã resume. File đề xuất, projection, sealed source pair/raw resources và hashes đã được giữ; read-back bằng context/StorageDriver mới xác minh source/bindings đạt, không gọi LLM hoặc áp dụng. [Receipt](checkpoint-receipt.json), [readback](checkpoint-readback.json).

Người dùng cần kiểm4note, nhất là full-unit table note có các điều kiện riêng và c11 (2027/Dự kiến/Ước tính) so với các cột2027 khác; không tự mở rộng hay thu hẹp scope từ tên cột. Mỗi issue cần quyết định riêng với full source và exact target. Nếu đích sai hoặc deferred reference còn chi phối, dùng luồng yêu cầu sửa/từ chối; không xác nhận để vượt guard. Tiếp tục qua ứng dụng thật cần actor/quyền và source/revision/hash còn khớp; file checkpoint không tự cấp quyền hoặc phê duyệt.

## Cấu hình, môi trường và cleanup

Audit mới xác nhận source DB local development127.0.0.1:5432/qnu_ai_platform, transactionREADONLY; kiểm cấu hình MinIO127.0.0.1:9000/Qdrant127.0.0.1:6333. Source chỉ đọc cấu hình ModelOps và copy credential mã hóa; live copy được đối chiếu identity trước inference. Không thay primary/fallback/provider/endpoint/key hoặc giới hạn server.

Hai DB test riêng có nonce ownership: `qnu_test_context548_d85a1e66bd1d` cho baseline/regression, `qnu_test_context548_06689f8f17dc` cho live. Prefix548 do harness tái sử dụng. Mỗi DB tạo49bảng riêng, LocalStorage tạm riêng; child config MinIO/Qdrant/Redis trỏ127.0.0.1:1, tắt dev auto migration/seed. Không DDL hoặc fixture writes lên DB ứng dụng/production. Không mock binder/review/store trong các test lifecycle cần kiểm; chỉ mock provider/HTTP/TEST auth tại ranh giới đã nêu.

Hai DB/runtime đã dọn sau export và ownership checks; checkpoint private được giữ có chủ đích để chờ review, không chứa DB dump hoặc credential. [Cleanup](cleanup.json). Không commit/push/stage/reset/restart/deploy/index/publish/approve nguồn thật.

## Lệnh và giới hạn

Cwd root repo; Python `backend/.venv/Scripts/python.exe`. Exact commands/cwd/environment/exit ở [commands](commands.json).

1. Audit → harness setup/seed-modelops với state/evidence/audit552: exit0. Baseline frozen app: exit1 (18FAIL).
2. Harness run red/registry-red: exit1. Focused-final217PASS: exit0. Full-after: exit1 (18FAIL/0new).
3. Scoped Ruff14files: exit0. Frontend15tests: exit0; Biome2files: exit0; `npm run build` (Vite + tsc): exit0.
4. Harness script selected-table: Python runner/harness exit2, WAITING_FOR_REVIEW; PowerShell outer command báo nonzero. Không đổi mã chờ thành PASS/E2E.
5. Pending checkpoint readback: exit0, no LLM/no apply. Cleanup2DB/2runtime: exit0. Source config read-back và evidence hashes ở receipt bổ sung.

Không chạy lại full suite hoặc live model cho cùng proposal khi không có thay đổi/failure mới. Checkpoint C/D còn việc thật cần hoàn thành; tên “Final Integration” không phải kết luận E2E đã đạt.

Gói bàn giao: [evidence.zip](evidence.zip), [manifest](manifest.sha256). JSON/XML/MD cũng được xuất riêng trong thư mục báo cáo để kiểm tra khi slim archive bỏ fileZIP. Checkpoint private không được đưa vào gói báo cáo chung.
