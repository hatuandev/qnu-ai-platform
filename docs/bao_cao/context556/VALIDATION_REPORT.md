# Context556 — Kiểm chứng

## Môi trường trước khi chạy

Đã audit DB/MinIO/Qdrant trước test. DB app chung localhost/qnu_ai_platform chỉ được đọc trong transaction READ ONLY; Storage snapshot chỉ GET. Test dùng DB riêng có nonce/comment sở hữu, LocalStorage riêng. Child test đặt ENVIRONMENT=test, MinIO/Qdrant/Redis vào127.0.0.1:1, auto-migrate/seed=false; không khởi động app hoặc migration production. Metadata tạo chỉ trong49bảng DB test. Cấu hình ModelOps mã hóa được sao chép đọc một chiều vào DB test để regression so cùng điều kiện, **0 LLM call trong nhiệm vụ**.

## Kết quả thực chạy

| Run | Kết quả | Exit code |
|---|---|---|
| Safety baseline mới trước sửa | 80PASS | 0 |
| Red trước có module | 11FAIL ModuleNotFoundError | 1 |
| Focused cuối6file | 146PASS +23subtestsPASS | 0 |
| Historical builder cùng DOCX | 1PASS, đúng299/233core records | 0 |
| Hai tiến trình native/Storage riêng | 1PASS MD/JSON/manifest/IDs/spans/resources | 0 |
| Full-inventory in-memory probe | 1PASS:12assertion/18issue/6reference, giữ roles/labels | 0 |
| Backend full mới, một lần | 18FAIL /2.429PASS /17SKIP /23subtestsPASS | 1 |
| Frontend preview tests | 21PASS | 0 |
| Scoped Ruff | 2file PASS | 0 |
| Scoped Biome | 6file PASS, override LF theo source | 0 |
| Frontend Vite build + tsc --noEmit | PASS | 0 |
| CLI chặn output trong input checkpoint | Child exit1 đúng guard,0file sinh | Probe0 |
| Checkpoint checksum trước/sau | 14+5+5file và3manifest không đổi | 0 |
| Reconcile actual old/live | 11mapped /A12blocked; no package/stage | CLI0, business BLOCKED |

Lệnh đầy đủ/cwd/exit/isolated endpoints ở [commands.json](commands.json). Các lệnh kiểm tra bổ sung và trạng thái browser ở [supplemental-checks.json](supplemental-checks.json). Không xem CLI exit0 là reconciliation thành công. Full suite vẫn **FAIL**, không đổi lỗi nền thành PASS.

Probe full-inventory đầu FAIL vì assertion của probe đòi input_hash đổi chỉ do revision identity; điều này sai với contract semantic_input_hash(content_hash, unit_manifest_hash, tables). Sửa đúng giả định của probe, không sửa runtime/expected product để che lỗi. Lượt cuối PASS, proposal hash và evidence source identity mới, đủ12/18 và roles giữ nguyên. Bằng chứng hai lượt ở full-inventory-first.xml/full-inventory.xml. Probe nằm ngoài full suite, không cộng vào13test mới của full.

Baseline full Context555 là **lịch sử** 2.416PASS/18FAIL/17SKIP. Đối chiếu từng test ID và nguyên nhân đầu tiên: 0ID bỏ, 0trạng thái đổi, 0failure cause đổi, 0FAIL mới; 13ID thêm đều PASS. Chi tiết18lỗi nền tại [REGRESSION_IDS.md](REGRESSION_IDS.md), toàn bộ status/cause trước/sau tại [regression-comparison.json](regression-comparison.json). Không chỉ so tổng số.

## T01–T16 theo yêu cầu556

| ID | Bằng chứng đã chạy | Kết quả/giới hạn |
|---|---|---|
| T01 | SHA256/bytes DOCX thực + wrong_lineage test | PASS; cùng tên không đủ |
| T02 | Exact MD byte/encoding/metadata và diff content | PASS diagnosis; artifact không bằng nhau |
| T03 | Field diff/ID mapping/targeted header test | PASS; không reuse ID/role mù |
| T04 | Native determinism, hai child process/Storage | PASS bounded; preview PDF NOT RUN |
| T05 | Checkpoint import wrong revision/hash negative cases | PASS TEST |
| T06 | ExactSourceMap full body/locator/ancestry/target + negative variants | PASS |
| T07 | Missing source blocked, actual A12 | PASS guard; actual reconciliation BLOCKED |
| T08 | Tampered proposal/hash/manifest tests | PASS |
| T09 | Changed ID/source builds NEW proposal hash | PASS TEST; no valid live proposal generated |
| T10 | Workflow cannot claim numeric columns /A03 audit | PASS TEST +11mapped audit |
| T11 | Typed reference roles advisory /conditions target-set tests | PASS TEST; no effective edges |
| T12 | Authenticated TEST checkpoint import | PASS TEST |
| T13 | Actor/revision/hash/forged approval rejection | PASS TEST |
| T14 | Pending only; no semantic_effective or active snapshot | PASS TEST |
| T15 | Close DB session →new session→rebuild pending exactly | PASS TEST |
| T16 | Selector v1/v2/import/scope focused+full | Focused PASS; full18FAIL nền |

## Những bước chưa chạy

- `UI_LIVE_NOT_RUN`: mở app localhost3000, đi vào quản trị thì tới SSO sign-in. Không có session người dùng được cấp; không dùng Dev Access Gate hay tạo token.
- Chưa nhập proposal thật, chưa human approval, apply, index, publish hoặc E2E; không có staging receipt thật.
- Chưa reparse/new revision ứng dụng thật; không chạy lại toàn tài liệu qua LLM.
- Không kiểm toàn LibreOffice/PDF preview determinism hoặc tái dựng toàn dependency deployment cũ.

## Dọn dẹp

DB test đã DROP sau khi xác minh nonce/comment và xác nhận vắng. Storage runtime được kiểm tra đúng đường dẫn thuộc repo:550file/9.962.350byte,0reparse link,0tracked,0process phù hợp. Thao tác Remove-Item có guard bị kiểm duyệt tự động từ chối `blocked by policy`; Storage còn nguyên, cleanup **chưa hoàn thành**, không thử phương thức xóa khác. Các checkpoint/audit/evidence được giữ có chủ đích. Không retry các Storage cũ đã từng bị policy chặn.
