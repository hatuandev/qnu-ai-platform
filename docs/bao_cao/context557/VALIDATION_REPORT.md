# Context557 — Kiểm chứng

Trước test đã xác minh DB local, MinIO và Qdrant. Regression dùng DB mới có nonce/comment ownership và LocalStorage riêng, MinIO/Qdrant/Redis127.0.0.1:1, auto-migrate/seed=false. Tạo49bảng chỉ trong DB test; không migration/schema writes ứng dụng thật. Cấu hình ModelOps đã mã hóa copy READ ONLY một chiều vào DB test để cùng điều kiện; không log secret hoặc sinh proposal LLM.

Riêng ứng dụng thật local: người dùng đã cho phép **một revision nháp và một pending proposal trên DOCX kiểm thử đã xác minh**. Mọi thao tác ghi chỉ qua service/API chính thức trong phạm vi đó; không nhận regression TEST là thao tác thật.

| Kiểm tra thực chạy | Kết quả | Exit |
|---|---|---|
| Focused7file backend | 158 PASS +23 subtestsPASS | 0 |
| Probe XML/artifact/bindings đầu | 5 PASS/1 FAIL do kiểu input helper | 1 |
| Probe XML/artifact/bindings cuối | 6 PASS; 83 bindings | 0 |
| Full backend mới, một lần | 2.429 PASS/18FAIL/17 SKIP/23 subtestsPASS,447,46 s | 1 |
| Frontend preview | 21 PASS | 0 |
| Frontend Vite +tsc --noEmit | PASS | 0 |
| Scoped Ruff4file | PASS | 0 |
| Scoped Biome6file/LF | PASS | 0 |
| Canonical actual/service readback | 233core/10table/3 footnote, exact source/hash | 0 |
| Reconcile actual | 12mapped/0blocked,6 reference mapped | 0 |
| Import API actual | POST200 duy nhất1lần; pending persist/rebuild PASS | HTTP200 |
| Studio +download MD/JSON | 200/200/200, exact hashes; enforced auth no session401 | 0 |

Baseline full là **kết quả lịch sử Context556**, không gọi đó là baseline mới chạy. Mọi test ID/status/first failure cause giữ nguyên:0added,0removed,0status change,0cause change. Full vẫn **FAIL18**, không nâng thành PASS. [18ID lỗi nền](REGRESSION_IDS.md), [toàn bộ so sánh](regression-comparison.json), [lệnh/cwd/exit code và các lỗi helper](commands.json).

## T01–T15

| ID | Bằng chứng | Kết quả |
|---|---|---|
| T01 | Receipt một draft/service; old row checksum/active pointers giữ nguyên | PASS thật |
| T02 | Official job/service v18, standard profile, S3 read-back | PASS thật |
| T03 | 3 native XML notes + bidirectional anchors/context_refs | PASS, page footnote 3 unknown |
| T04 | Core body/type/parent/section/order khớp tất cả233record | PASS, không chỉ đếm |
| T05 | Toàn10table header/row/raw/state + Bảng1/codes | PASS |
| T06 | 12 assertions exact evidence/target/roles | PASS |
| T07 | Footnote2 + c02/r001–3,0012/00027/AM-0007 | PASS |
| T08 | A03 workflow/nhóm A, columns rỗng, no effective | PASS |
| T09 | MD/JSON exact hashes, full pending payload seal | PASS |
| T10 | 18 issue labels/ID maps/6 references, no decisions | PASS |
| T11 | Dry-run rebind/validation, negative import tests | PASS |
| T12 | Real configured dev actor/quyền; no-session enforced401; TEST unauthorized/forged cases | PASS API/TEST; human SSO NOT RUN |
| T13 | Publication rows/counts/active pointer unchanged; no semantic_effective | PASS thật |
| T14 | API200→new DB session→rebuild +Studio GET/exact downloads | PASS thật |
| T15 | 158 focused/6artifact probes/21FE và full ID/cause comparison | Focused PASS, full FAIL18 nền |

Không thay đổi test repo hoặc expected product để che lỗi. Sáu probe riêng ở private Storage, ngoài full testpaths; không cộng chúng vào số2429 của full. Không chạy full thêm lần thứ hai.

## Integrity và phạm vi chưa thực hiện

Đã xác minh pair loader +evidence offsets/source identity, actual pending full digest, six typed references,18 issues, old checkpoints14+5+5 file và manifest Context556 không đổi. Header c02 mới khớp vai trò offline; A12 không còn bị chặn. `at` được sinh khi stage là audit metadata tham gia hash, nên không nhận hypothetical dry-run hash thành actual pending hash.

UI browser đã mở đúng deep link nhưng chuyển tớiSSO. **UI_LIVE_NOT_RUN** cho màn hình review sau đăng nhập, chọn18 quyết định hoặc yêu cầu sửa bằng tài khoản thật. Không dùng Dev Access Gate/cookie/token giả để vượt qua. API thật với development actor đang cấu hình đã nhập/readback; không tuyên bố human SSO/E2E.

Không approve/apply/publish/index/retrieval benchmark, không E2E RAG PASS. Page mapping partial; footnote 3 chưa chứng minh page, locator XML/anchor hợp lệ. Quality warnings preview/legacy giữ nguyên để người dùng xem, không tự đóng cùng18 issue ngữ nghĩa.

## Dọn dẹp

DB test đã DROP với nonce/comment guard, xác nhận vắng. Runtime riêng mới có491file/7892907byte,0links/0tracked/0process phù hợp. Guarded Remove-Item bị kiểm duyệt tự động chặn `blocked by policy`, không thực thi. Storage còn; không chuyển shell/công cụ để vượt, không retry thư mục cũ bị chặn. Canonical/source/checkpoint/evidence giữ có chủ đích. Cleanup filesystem chưa hoàn tất; [receipt](cleanup.json).
