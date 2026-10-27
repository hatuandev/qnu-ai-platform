# Context613 — Kiểm chứng triển khai compiler theo nhóm

## Kết luận theo phạm vi

Đã tạo được Markdown và manifest lớn qua nhiều nhóm, không mất145assertion đầu vào, giữ92thực thể và nguồn/bằng chứng. ModelOps hỗ trợ profile dung lượng theo alias/endpoint; không còn trần chung8.192/32K cho mọi model trong các schema compiler. Nội dung bản thử vẫn `needs_attention`, không được xem là APPROVED.

Full regression cuối trong `backend/storage/context613/acceptance-checks`: **3.601PASS /18FAIL nền /17SKIP, +23subtestPASS**, 708,05s, **exit1**. So với baseline611:15test mới đềuPASS,0failure mới,0cause đổi,0ID mất. Full vẫn **FAIL** vì còn18lỗi nền. Chỉ XML/receipt của lượt hoàn tất này được dùng nghiệm thu; các lượt dừng sớm giữ INCOMPLETE, không ghép số PASS.

## Regression trước và sau sửa

Ba ca đầu mới chạy trên bản sao mã trước613, exit1, đều FAIL đúng các vấn đề: model profile không được dùng; synthesis reserve5.000 chặn request vừa ngân sách; tổng70thực thể bị Draft64 chặn. Không dùng lần chạy mã sau sửa làm baseline.

Trong quá trình self-review bổ sung hai negative cases tái hiện việc review/direction của quan hệ chưa vừa budget; cả hai FAIL trước fix tương ứng. Sau sửa, đề xuất không đủ điều kiện giữ riêng candidate_only/effective=false/NOT_RUN, không trở thành relation đã kiểm chứng.

Lượt focused chốt `final-release-focus`: **70PASS**, exit0,84,61s. Bao gồm **15ca regression mới** và các ca checkpoint/ModelOps hiện có. Các focused trước đó:134PASS,119PASS,93PASS theo phạm vi ghi trong receipt; không cộng chúng thành tổng test duy nhất.

| Test ID trong `tests.test_compilation_groups_613` | Hành vi đã kiểm | Kết quả focused cuối |
|---|---|---|
| `test_model_budget_uses_resolved_limits_instead_of_global_24k_8192_caps` | Model128K/output16K qua policy | PASS |
| `test_large_output_request_and_capacity_profile_roundtrip_are_endpoint_bound` | Profile/alias/endpoint, giới hạn đầu ra và URL không credential | PASS |
| `test_fallback_is_sized_for_its_own_profile_and_unknown_capacity_is_explicit` | Fallback nhỏ, provenance unknown và operator cap | PASS |
| `test_thinking_separate_from_output_requires_a_confirmed_budget_not_a_numeric_guess` | Thinking riêng chưa xác minh bị chặn | PASS |
| `test_label_overlap_is_only_a_candidate_and_search_exhaustion_remains_unknown` | Candidate không là fact, hết search giữ tổng unknown | PASS |
| `test_synthesis_can_pack_a_single_complete_request_without_fixed_5000_reserve` | Request đơn hợp lệ không bị reserve chung chặn | PASS |
| `test_large_compilation_keeps_all_objects_sections_checks_and_resume_checkpoints[1]` | 70entities/70assertions/70sections, resume và readback | PASS |
| `test_large_compilation_keeps_all_objects_sections_checks_and_resume_checkpoints[2]` | 70entities/140assertions/140sections và coverage toàn cục | PASS |
| `test_capacity_failure_through_handler_has_explicit_stage_and_no_retry_or_publication` | API422/capacity_blocked/idempotency | PASS |
| `test_partitioned_synthesis_review_keeps_raw_context_and_exact_global_coverage[supported]` | Chia review giữ raw context và global index | PASS |
| `test_partitioned_synthesis_review_keeps_raw_context_and_exact_global_coverage[unresolved]` | Review chưa đủ căn cứ không được nâng thành PASS | PASS |
| `test_provider_update_persists_capacity_and_old_forms_cannot_silently_clear_it` | PostgreSQL thật, merge form cũ và explicit clear | PASS |
| `test_cross_group_shared_names_require_raw_evidence_and_independent_verdict` | Hai nguồn/80assertions, trùng tên không tự xác nhận identity | PASS |
| `test_cross_relation_budget_deferral_keeps_candidate_without_effective_relation[review]` | Review không vừa không gọi inference, giữ proposal riêng | PASS |
| `test_cross_relation_budget_deferral_keeps_candidate_without_effective_relation[direction]` | Direction không vừa không kích hoạt relation | PASS |

Ruff19file thuộc phạm vi: **PASS**, exit0, theo `ruff-final-run.json`. Các file nguồn/docs mới UTF-8 khôngBOM, LF; kiểm link và diff ở bước bàn giao.

## Compiler thật

Ba DOCX dùng rawhash đúng và canonical381proof đã lưu. Có model thật qua ModelOps, StageCheckpoints, StorageDriver local, registry, service finish/read và kiểm source/hash/quyền. Đọc lại bundle khớp chính xác. Không được gọi là E2E upload/parser mới hoặc published serving.

Kết quả cuối:92entities/145assertions/25sections/16groups/9relations ứng viên;32unknown giữ nguyên. Tổng54model calls mới gồm36source synthesis,1probe cũ,17cross validation;96lượt trước không gửi lại. Toàn54response stop,0fallback, medium/output8.192 đã gửi đúng wire. Chi tiết và giới hạn effort/context nằm trong [báo cáo chạy thật](LIVE_COMPILER_REPORT.md).

Đối soát độc lập xác nhận mọi assertion giữ nguyên value/state/source/scope/condition/exception cùng entity có bằng chứng; không bỏ hoặc sửa dữ kiện để vừa cap. Mười packet cũ chưa complete và các vấn đề ngữ nghĩa tiếp tục làm machine_complete=false. Hai mươi lăm section đã sinh không chứng minh25section đều đúng; hai section còn verdict chưa supported.

## Môi trường và tác động dữ liệu

Trước test xác minh ENV dev/test, DB/MinIO/Qdrant loopback. Mỗi DB mới có prefix613 và nonce comment sở hữu, `create_all` chỉ trong DB đó; không migration hoặc ghi schema sharedDB. Test dùng LocalStorage riêng, endpoint mạng ngoài phạm vi test được trỏ loopback:1. Model thật chỉ dùng provider được phép qua ModelOps, secret không sao chép vào DB thử.

Sau chạy, shared seal khớp trên collection/binding/source/index/assistant/provider configuration rows. Rawhash baDOCX giữ nguyên;2.943Qdrantpoints/fullpayload khớp snapshot602,0retrievable. Không publish hoặc reindex. Đổi usage/lease do inference thật được quản lý bởi ModelOps, không giả dùng0token.

Không chạy frontend/build/browser, benchmark64, parser mới, vector generation hoặc publication E2E: **NOT RUN**, ngoài phạm vi mã thay đổi. Không tự restart hoặc deploy dịch vụ.

Sau khi các lượt chạy hoàn tất, cả năm DB thử613 đã được dọn theo đúng tên và nonce sở hữu, xác nhận không còn trong pg_database. Storage bằng chứng được giữ theo chính sách bảo vệ, không retry/bypass thao tác xóa đệ quy đã từng bị chặn. Nguồn và các hàng shared đã được đối soát sau cùng, giữ nguyên.

## Lượt chưa hoàn tất và lỗi trong quá trình kiểm

- `final-checks/full-final`, `release-checks/full-final`: dừng có chủ đích để hoàn thiện persistence/budget cross-source; INCOMPLETE.
- `handoff-checks/full-final`: phiên bị gián đoạn tại log86%, không XML/receipt hoàn tất, không còn process; INCOMPLETE.
- `acceptance-checks/full-final`: DB mới riêng cho nghiệm thu cuối, không trộn kết quả các lượt trên.
- Một lệnh dùng nhầm tên file test cho exit4/no tests ran; giữ receipt, không tính PASS.
- Một fixture ID dài quá VARCHAR36; sửa ID fixture, không sửa schemaDB hay nới assertion sản phẩm.
- Một preflight Storage được chặn trước inference do package eager export; harness sau đó bind rõ LocalStorageDriver ở các ranh giới I/O thực. Không có ghi S3 nguồn thật.
- Một khóa idempotency trùng bị409 trước inference; receipt giữ nguyên, dùng mã thử riêng sau đối soát.

JUnit/log/receipt từng lượt nằm trong thư mục thử; corpus và checkpoint không đưa vào Git. [Đối chiếu test ID](TEST_ID_COMPARISON.md) là nguồn cho exact failure/cause, không chỉ tổng số lỗi.
