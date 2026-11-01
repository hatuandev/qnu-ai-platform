# Phiên 788 — Sửa RAG và chạy lại chín câu, một lượt mỗi câu

Ngày: 2026-11-01. Yêu cầu: sửa các vấn đề đã review ở phiên787, chạy chín câu bằng model thật, không retry để làm xanh.

## Thay đổi

1. Runner được đưa vào source: `scripts/run_admissions_retest.py`, Playwright config/spec riêng và `retest9-runner.ts`. Ghi ý định dispatch trước POST; chỉ GET đối soát khi không rõ kết quả, không gửi lại. Scope single thiếu binding bị chặn. Đọc fingerprint runtime trước/sau từng câu; drift hoặc uncertain dừng cohort. Kiểm tra cuối buộc đủ danh tính và kết quả thật, có FAIL thì exit1.
2. Evaluator chỉ ghép các statement văn bản cùng tập citation chính xác; vẫn kiểm nguồn, năm, hash, trang và fact. Không sửa gold. Các dữ kiện bảng vẫn cần chứng cứ ô riêng. Không dùng một năm đúng để bỏ qua năm mâu thuẫn khác.
3. Answer dùng JSON Schema của DTO với khóa bắt buộc và object đóng; `PROMPT_VERSION=qnu.rag.answer/v10`. Khi sai cấu trúc, audit chỉ ghi đường dẫn/loại lỗi, hash và usage; không lưu raw câu trả lời hay suy luận. Trace quan sát finish reason và bộ đếm reasoning nếu provider thực sự công bố; không đổi unknown thành0.
4. Header dẫn xuất cho bảng native hình chữ nhật có cột định lượng, không merged cell và không cờ cần review. Cho phép chủ thể số có header xác định; giữ đủ bằng chứng ô khóa/giá trị/header. `qnu.answer-cells/v3`. Giữ nguyên canonical, dấu header gốc, index và hash nguồn; không tự nối trang từ quy tắc header mới.
5. Câu nhiều ý có những mệnh đề hỏi độc lập được truy vấn riêng rồi xen kẽ kết quả trong cùng top-k. Cùng scope/filter/index/generation/provider; không sinh câu hỏi bằng model hoặc dùng từ khóa benchmark. Những lời gọi embedding/rerank này là các nhánh kế hoạch có trước, không phải retry.
6. Context văn bản lấy thêm đúng các block nguồn đã được citation của chunk ghim tới, thay cho chỉ dựa vào bản compiler tóm tắt. Không lấy trang lân cận tùy ý. Generation, budget và verification cùng một projection nguồn.

Các file chính thuộc `backendV1/qnu/domains/rag/answer/`, `knowledge/index/table_dependencies.py`, E2E retest/evaluator và regression tương ứng. Giữ các thay đổi có trước của người dùng. Không cleanup/init/upload/OCR/compile/review/publish/reindex hoặc đổi ModelOps trong task này.

## Kiểm chứng mã

- RED tái hiện header/chủ thể số:3 FAIL/4 PASS trước sửa; sau sửa nhóm cuối43 PASS. Nhóm backend trọng tâm trước đó68 PASS.
- Full backend unit: **611 PASS/1 FAIL**, không phải toàn bộ PASS. Lỗi nền `test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` (`invalid_identity`). Log `tmp/788-backend-unit-verified.log`. Lần đầu còn lỗi quyền thư mục temp Windows; đã chạy lại với basetemp trong workspace.
- API/PostgreSQL/Qdrant cô lập: **63 PASS/2 FAIL** ở hai nhánh fixture judge672. Baseline một nhánh cũng FAIL với production code cũ trong shadow checkout. Fixture cũ chỉ quote một số nhưng statement còn năm; guard từ chối đúng. Sửa fixture để quote các ô nguồn thực dùng, không nới guard, chạy cả11 nhánh judge: **11 PASS**. Chưa chạy lại toàn bộ batch65 sau thay đổi fixture. Log `tmp/verification788-integration.log`, `tmp/verification788-baseline.log`, `tmp/verification788-judge-final.log`. Các DB test được tạo riêng rồi drop; không reset DB live.
- Frontend trọng tâm76 PASS; TypeScript E2E, build, Biome scoped, Ruff scoped và whitespace PASS. Full Vitest **589 PASS/33 FAIL** ở9 file; đối chiếu đúng33 ID lỗi với baseline779, không thêm/bớt ID. Log `tmp/788-frontend-full.log`, `tmp/788-build-final.log`.
- Regression bao gồm malformed/extra schema keys, audit không chứa nội dung riêng, reasoning unknown, native/OCR/review/header ambiguity, provenance ô số, câu nhiều ý, scope giữ nguyên, generation đổi, no-resend và incomplete runner.

## Lượt model thật

Lệnh tại root:

```powershell
.\backendV1\.venv\Scripts\python.exe -X utf8 scripts/run_admissions_retest.py --headed
```

Phiên E2E giữ nguyên `93faa11f0caf`; bật serve cùng phiên bằng UTF-8 sau khi kiểm tra server cũ không còn hoạt động. Qwen `qwen3.8-27b-q4`, answer off, output16384, evidence98304byte, context131072, assistantrev2. Promptv10. Giữ index ba tài liệu/179 chunk và lịch sử trước.

Cohort: `retest9-1793518415739`. Thư mục:

`tmp/v1-e2e/93faa11f0caf/runs/admissions-retest9-1793518412735523800/`

Report: `retest9-answers.json`; Playwright `results.json`; log `tmp/788-live-retest9.log`. Cohort chạy khoảng177.7 giây, **7 PASS/2 FAIL/0 NOT_RUN/0 UNCERTAIN**, exit1. Không ghép PASS với các cohort trước.

| Câu | Kết quả | Thời gian client |
|---|---|---:|
| F13 | PASS | 21.4s |
| F14 | FAIL — model_abstained | 15.5s |
| I25-04 | PASS | 17.5s |
| I25-05 | PASS | 17.5s |
| BC24-05 | PASS | 12.5s |
| BC24-08 | PASS | 13.1s |
| MX-02 | PASS | 24.7s |
| MX-05 | FAIL — model_abstained | 21.1s |
| MX-10 | PASS | 21.6s |

Audit DB chỉ đọc:9 conversation/9 turn/9 key riêng, mỗi conversation đúng1 turn, response DB khớp report; **9 chat**,14 embedding và14 rerank, mọi execution `attempt=1/code=ok`, không fallback. Tổng usage quan sát366452 token,0 usage unknown. Cả9 response finish_reason=stop, không lỗi schema hoặc output truncation trong cohort này. Trace xác nhận enable_thinking=false được áp dụng; reasoning_chars/tokens=null vì provider không công bố, không khẳng định thực đo bằng0. Audit `tmp/audit788.json`.

Hash checkpoint và hai report retest9-786/retest16-783 không đổi so với `tmp/788-before-history.json`. Không nâng trạng thái full53 dựa trên nhóm9.

## Hai câu chưa giải quyết

- **F14:** retrieval chọn đúng hai paragraph đứng đầu; các block nguồn chứa phần điều kiện nhưng bị cắt ngang câu giữa hai evidence. Context67287/98304byte, model hoàn tất JSON hợp lệ rồi abstain. Bằng chứng có trong context ghép lại; chưa chứng minh tác nhân duy nhất là fragmentation hay chỉ dẫn quá bảo thủ. Cần cải thiện cách trình bày quan hệ đoạn liền mạch có căn cứ, không đổi thành ngưỡng đoán hoặc sửa câu hỏi/gold.
- **MX-05:** truy vấn hai nhánh đã mang vào cả bảng quy đổi và phần khảo sát, catalog có ô cần chọn và đoạn nguồn giải thích kênh nổi trội. Context57558/98304byte, model vẫn abstain với17 completion token. Không còn căn cứ nói mất hẳn một tài liệu hoặc hết output. Điểm còn vướng nằm ở khâu tổng hợp/tuân thủ hợp đồng trả lời nhiều loại bằng chứng; cần đo riêng việc phối hợp lookup và văn bản/so sánh, giữ guard nguồn và scope.

Đã đọc thủ công bảy câu PASS, kể cả điều kiện năm tốt nghiệp của F13. Đây chưa phải đánh giá semantic độc lập toàn53 câu hay holdout. Không retry hai câu còn lỗi và không tuyên bố hoàn thành chất lượng9/9. Bước sau phải là thay đổi tổng quát có regression rồi một cohort mới tách biệt nếu được yêu cầu; giữ nguyên cohort FAIL này.
