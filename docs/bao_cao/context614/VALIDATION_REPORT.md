# Context614 — Kiểm chứng cuối

## Kết luận

Thay đổi liên kết cấu trúc đạt regression trọng tâm và không thêm failure vào full baseline. Full suite vẫn **FAIL** vì 18 lỗi nền. Compiler chạy thật đã hoàn tất nhưng nội dung **chưa APPROVED**, có finding metric 5.081 gán nhầm quota; xem [báo cáo nội dung](LIVE_COMPILER_REPORT.md).

| Check | Kết quả | Exit |
|---|---|---:|
| Regression tái hiện trước sửa | Section/header thiếu: 2 FAIL/1 PASS; cap packet, repair budget và explanation: FAIL đúng nguyên nhân | 1 |
| Focused cuối | 88 PASS, 36,88s | 0 |
| Test mới trong full | 21/21 PASS | 0 đối với các case mới |
| Ruff cuối | 13 file có phạm vi | 0 |
| Full cuối | 3.622 PASS/18 FAIL nền/17 SKIP, thêm 23 subtests PASS; 741,75s | 1 |
| Exact ID/cause so Context613 | 0 failure mới, 0 cause đổi, 0 ID thiếu, 0 lỗi nền bị che/sửa ngoài phạm vi | 0 |
| Compiler thật ba nguồn | Bundle lưu/đọc lại khớp; needs_attention, unpublished | 0 tiến trình, không phải semantic APPROVED |
| Source/config/vector seals | Hash nguồn/shared rows/default model/2.943 vector payload giữ | 0 |

[Bảng exact test IDs](TEST_ID_COMPARISON.md) chứa 21 case mới và 18 lỗi nền. Không suy từ tổng PASS. Các warning compatibility Qdrant khi endpoint thử là loopback:1 không phải chứng nhận Qdrant live; vector seal được kiểm riêng, chỉ đọc.

## Môi trường an toàn

Trước tạo fixture đã xác minh environment local/dev, DB/MinIO/Qdrant là loopback. Shared DB chỉ đọc để lấy seals/cấu hình và để ModelOps thực hiện inference/usage được phép; không migration/DDL nguồn. Test có DB riêng prefix Context614 và comment nonce; `create_all` chỉ trên DB sở hữu. LocalStorage riêng; endpoint test không dùng network thật ngoài loopback, có guard egress. Typed default metadata inactive được sao sang DB thử, không sao credential/provider rows.

Năm DB đã dọn sau khi job kết thúc, kiểm nonce và xác nhận không còn tên trong pg_database. Không xóa Storage bảo vệ để che dấu vết. Những run giữa chừng bị dừng/gián đoạn giữ INCOMPLETE; run sai đường dẫn test exit 4 là NOT RUN, không tính PASS. Full trước repair/diagnostic change là 3.618/18/17, được giữ lịch sử, không dùng thay full cuối 3.622/18/17.

## Phạm vi regression

- Mục lặp tên/nhánh khác, outline chỉ là candidate; không lan scope sang nhánh sau.
- Header rỗng, missing/duplicate locator, header metadata bất đồng với literal; không nuốt hàng Alpha hoặc gán body thành header đã xác nhận.
- Vị trí cột, header nhiều tầng/override, pipe escape, năm 2027, unknown khác 0; metadata sai không ghi đè raw cell.
- Note gắn đúng field/revision; foreign/missing ref bị chặn; raw context lớn không bị cắt.
- Wire handles của structural refs, temporal authority chia sẻ, persisted structure/context drift, invalidation khi field link đổi.
- Ngân sách đầy đủ có source hashes/navigation/prior selection; actual budget khớp đúng request, planning giữ một phong bì correction tối thiểu, không dự phòng correction thứ ba.
- Cap vận hành có thể cấu hình lớn hơn mà mặc định không đổi; audit/repair quá budget giữ NOT_RUN và coverage debt; lý do review dài không làm scope=false thành complete.

## Lệnh và bằng chứng

Từ root: `backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context614_final_validation.py run --label envelope-compat-final tests/test_compilation_structure_614.py tests/test_compilation_semantics_604.py tests/test_compilation_context_608.py tests/test_compilation_checkpoint_611.py::test_separate_request_budgets_do_not_double_charge_quotes_to_extraction`.

Full qua cùng runner `run --label full-final`; subprocess thật là Python 3.12 `-m pytest -v`, cwd `backend`, env test/LocalStorage/owned DB. XML/log/command/exit code lưu tại `backend/storage/context614/final-validation/`. Ruff chạy bằng Python venv `-m ruff check` trên 11 file app và 2 test, receipt ở `backend/storage/context614/ruff-final-run.json`.

Offline structural audit chặn network, giữ 381 proof/snapshot, không mất primary. Final inference qua ModelOps có wire/metrics và immutable receipts; không CLI/model API bypass. Seals/postcheck so raw hash/shared rows và count/full payload hash Qdrant; không đọc embedding floats nên không tuyên bố hash float vectors.

NOT RUN: frontend/build/browser E2E, fresh parser/ingestion Quality Gate toàn tài liệu, benchmark RAG 64 câu, indexing/reindex/publication/serving E2E. Những việc đó không thuộc quyền thực thi lần này. Không có stage/commit/push/restart/deploy.
