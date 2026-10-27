# Context623 — Nghiệm thu compiler trên ba DOCX 2024–2026

Ngày 24/10/2026. **Chưa đạt nghiệm thu toàn compiler. Đã dừng gọi model theo yêu cầu người dùng để kiểm tra 9router.**

## Kết quả chính

Luồng service thật đã tạo, tiếp tục từ checkpoint, lưu và đọc lại được bản biên soạn của cả ba nguồn. Hai lỗi kỹ thuật từng chặn lưu đã được sửa. Các mốc 5.948 năm 2024, 5.081 thực nhập học năm 2025 và 5.173 chỉ tiêu năm 2026 đều truy vết đúng nguồn/năm trong lượt đầu. Tuy nhiên, bản ấy vẫn có coverage hoặc nhận định chưa được chứng minh và một mục tổng hợp gán năm chưa đủ căn cứ. Hệ thống giữ `needs_attention`, không tự chấp thuận.

Đã bổ sung hướng dẫn phân loại phạm vi để không ép danh mục định danh thành fact số lượng. Lượt chạy lại cùng câu hỏi và nguồn mới nhận 7 phản hồi; request thứ 8 bị ReadTimeout sau 30 giây tại 9router. Không có đủ bằng chứng để kết luận sửa phạm vi đã vượt qua toàn bộ nghiệm thu. Người dùng chọn giữ nguyên để tự kiểm tra 9router; không gọi lại bước bất định.

## Phạm vi thay đổi

| File | Nội dung |
|---|---|
| `compilation_review.py` | Bản nháp rỗng ghi ledger xác định toàn bộ primary proof là coverage debt. Đây là kiểm kê của server, không giả mạo một đánh giá LLM đã PASS. |
| `compilation_validation.py` | Kiểm ledger rỗng, hash và nghĩa vụ coverage; tách giai đoạn semantic repair khỏi phần dữ liệu bổ sung sau đó. Kiểm nguyên trạng fact cũ và fact được thêm; không nhầm việc bổ sung coverage với kích hoạt candidate bị từ chối. |
| `compilation_coverage.py` | Phân biệt ô dữ liệu được nguồn để trống với header/layout trống hoặc danh mục chỉ có tên/mã. Chỉ liên hệ nội dung đúng thuộc tính và mức tổng hợp được hỏi; không tạo một assertion chỉ để có ID gắn vào heading/danh mục. |
| `test_compilation_stage_ledgers_623.py` | 7 regression cho empty→grounded repair, repair bị từ chối rồi bổ sung coverage, sửa debt/hash/review và sửa fact cũ/mới sau khi lưu JSON. |

Review protocol v2 và instruction tham gia configuration hash. Không sửa hoặc giả trạng thái checkpoint cũ. Không vá bằng số 5.173/5.081, từ điển header hay từ khóa của riêng câu test.

## Kiểm chứng mã

| Kiểm tra | Kết quả |
|---|---|
| Baseline trước sửa, cùng 7 test cuối | 3 FAIL / 4 PASS, exit 1; hai lỗi lưu/đối soát tái hiện, thêm ca kiểm tra fact bổ sung bị thay đổi |
| Regression trọng tâm | 154 PASS, exit 0; 7 test mới PASS trong full cuối |
| Ruff | 4 file PASS, exit 0 |
| Full cuối sau chỉnh instruction | 3.785 PASS / 18 FAIL nền / 17 SKIP, exit 1, 807,90 giây |
| Đối chiếu Context622 | Exact 18 test IDs và nguyên nhân khớp; không mất ID cũ hoặc phát sinh regression; 7 ID mới PASS |

Full suite vẫn **FAIL**. Lượt full trước bổ sung instruction cũng có 3.785/18/17; giữ riêng, không cộng số PASS hai lượt. Các lượt focused trung gian còn lỗi về kỳ vọng kiểm tra alias trong fixture được giữ log; bản cuối kiểm JSON đọc lại thực chất và đã đạt.

Lệnh thật chạy bằng `backend/.venv/Scripts/python.exe`, từ root dùng helper `context623_checks.py`; pytest có cwd `backend`, `--basetemp` và JUnit XML trong thư mục task. Ruff có phạm vi ba file app và test mới. Receipt từng lệnh/cwd/exit code và exact test IDs ở `backend/storage/context623/test-id-comparison.json`, `checks/*-run.json`, `final/*-run.json` và `ruff.json`.

## Thử service thật và các kết quả độc lập

Giữ nguyên ba raw DOCX và snapshot 381 proof từ Context602, hash catalog `59eb474ad57dc88b943504a46bc9cce8c718a302072b309c5c87022bd7f6ef66`. Câu hỏi cả hai lượt giống nhau: đối chiếu số nhập học và chỉ tiêu đại học chính quy theo từng năm 2024–2026, phân biệt thực tế với kế hoạch và giữ phạm vi từng nguồn. Không thay câu hỏi hoặc nhãn để làm kết quả xanh.

Model thử riêng: `gh/gpt-5.6-luna`, thinking medium, ngân sách context/output động; timeout provider giữ 30 giây. Không đổi model mặc định của ứng dụng. Không reparse, reindex hoặc xuất bản.

### Lượt đầu — trước chỉnh hướng dẫn phạm vi

- 120 stage compiler có phản hồi, 0 fallback; có một lỗi định dạng đã biết được bounded correction xử lý và lưu riêng, không phải inference bất định.
- 2 lần pause/resume qua service; bản cuối gồm 71 assertion, 12 section, 1 relation.
- Lưu rồi đọc bằng session DB mới khớp; gửi lại cùng idempotency key không tạo job hay gọi model thêm.
- Đối chiếu độc lập với raw hash/canonical: 5.948/data2024 đúng; 5.081/data2025 có đúng locator dòng tổng của bảng Giới tính và preamble mô tả đã nhập học; 5.173/data2026 đúng. Giá trị 4.500 và các thông báo cập nhật vẫn truy vết trong nguồn 2026.
- Snapshot, source binding, hash, một nguồn cho mỗi assertion và trạng thái unpublished đều đạt.
- **Không đạt:** còn primary evidence chưa được đối soát, một số danh mục không cung cấp chỉ tiêu bị yêu cầu tạo assertion, scope/metric của một số dòng chưa rõ và tổng hợp có `heading_year_outside_assertion_scope`. Các nhận định không đạt vẫn chặn `machine_complete`.
- Source unknown không được chuyển thành 0. Lượt này không sinh assertion unknown; policy unknown được kiểm qua regression, không gọi đó là unknown E2E PASS.

Artifact: `compiler-live-final/result.json`, `acceptance-review.json`, `acceptance-targets-private.json`, `bundle-private.json`, requests/outputs trong Storage riêng. Private artifact giữ nội dung nguồn; không sao chép corpus vào Git.

### Hai lần khởi chạy với instruction mới

1. Lần đầu bị từ chối lease do provider chỉ cấp một lượt đồng thời: 0 phản hồi model, không có output được áp dụng; giữ receipt lỗi, không đổi checkpoint thành PASS.
2. Sau khi lượt đầu kết thúc, một lượt riêng chạy nối tiếp nhận 7 phản hồi; stage8 bị **ReadTimeout**, sau đó service báo `ALL_PROVIDERS_UNAVAILABLE`. Đây là lỗi provider chưa trả xong, không phải HTTP400 tràn context hay mất dữ liệu nguồn. Kết quả request8 chưa xác định; metadata không có upstream request ID để xác minh một phản hồi hoàn tất.

Trạng thái `uncertain` được giữ nguyên. Không tự resume, xóa stage, sửa ledger hay gửi lại request8. Không thể suy từ 7 phản hồi hoặc unit test PASS rằng cả luồng mới đã đạt. `compiler-scope-final` và `compiler-scope-serial` giữ riêng toàn bộ receipt, metrics, phase và lỗi.

## An toàn và bàn giao

Preflight xác minh DB, MinIO, Qdrant là local. Regression dùng hai DB nonce riêng, Storage local tạm và egress guard; chỉ tạo schema trong DB test, không migration DB ứng dụng. Hai DB regression đã xóa sau kiểm nonce. **DB acceptance và toàn bộ checkpoint/Storage được giữ theo lựa chọn mới của người dùng**, chờ kiểm tra 9router; không dọn phiên đang giữ.

Seals trước/sau từng lượt service xác nhận collections, bindings, revisions, indexes, assistants, provider/default rows của ứng dụng giữ nguyên. ModelOps dùng credential được bảo vệ; không ghi secret ra docs/env. Chỉ ba file app trong phạm vi đổi, các thay đổi chưa commit của người dùng được giữ.

Không commit, stage, push, restart, deploy, đổi model/config, reindex, approve nguồn hoặc publish. Đây là kiểm thử service thật với actor test trong DB riêng, không phải HTTP/UI E2E hay nghiệm thu toàn backend.

## Điều kiện tiếp tục

Người dùng kiểm tra 9router trước. Khi có chỉ dẫn tiếp theo, giữ nguyên phiên uncertain hiện tại; chỉ chạy một lượt nghiệm thu mới khi đã được cho phép, cùng model/nguồn/câu hỏi và Quality Gate. Lượt mới phải thực sự đạt `machine_complete=true`, toàn bộ packet/review hợp lệ, lưu/đọc lại và các mốc số/năm đều đúng trước khi kết luận nghiệm thu compiler. Không cần chạy lại full Pytest nếu không sửa thêm mã; kết quả full hiện tại đã đối chiếu bằng ID và nguyên nhân.
