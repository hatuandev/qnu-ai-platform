# Phiên775 — Sửa benchmark tuyển sinh đa tài liệu

## Phạm vi

Người dùng yêu cầu sửa các lỗi review774 và test lại. Chỉ sửa runner/nhãn/evaluator E2E và kiểm nguồn offline; giữ các thay đổi ứng dụng/Backend có sẵn. Không restart, cleanup/init, reindex, publish hay gọi model để làm xanh. Skill áp dụng: clean-code, rag-evaluation; tham chiếu frontend/verification khi sửa TypeScript.

## Thay đổi và nguyên nhân

- Khôi phục nguyên trường của F01–F19 từ bộ 2026 ban đầu. Nâng bộ đa tài liệu thành v2-775 để tách nhãn cũ.
- Đọc PDF gốc, sửa nhãn mới: Tin học/Tiếng Anh THPT2026 đều20; CNTT An toàn, an ninh mạng15/trang5; học phí kỹ sư info2025/trang10; nữ nhập học report2024/trang2. Bỏ câu suy mẫu số4.826 thành tổng trúng tuyển; thay câu mã402 không có căn cứ bằng đối chiếu IELTS/khảo sát. Bỏ gợi đáp án trong câu mới. Giữ hash/nguồn gốc.
- Mỗi fact có document/year/physical-page/subject/metric/typed-number và locator; bảng cần source cell proof. Chỉ đúng con số nhưng sai nguồn/revision/version/publication/page/header/subject/năm đều FAIL. Giá trị bảng phải nằm ở ô được chọn đầu proof và đúng trang, không lấy số ở header. Refusal vẫn kiểm nguồn để phát hiện leak ngoài scope.
- Typed parser giữ1.65/62.7 và đọc đúng300.000/4.681/2 974. Hỗ trợ đơn vị m liền số.
- Single scope thiếu publication hoặc conversation cũ sai assistant/document_ids đều BLOCKED trước dispatch. Lưu request fingerprint và dispatch trước POST; HTTP lỗi/timeout không làm mất vết và không tự gửi lần hai. Giữ idempotency, replay/resume không tính first-attempt.
- Chấm tiếp lỗi nội dung độc lập, tổng hợp FAIL cuối lượt; quota/provider/capacity/transport dừng với phần còn lại NOT_RUN. Có regression chạy chính vòng runner để xác nhận hành vi.
- Bỏ autoquota20M ở admissions-upload/chat; chỉ đọc hạn mức/used/reserved và báo thiếu, không PUT/reset reservation.
- Assistant mới ghi rõ top20/candidate50/history0/output4096/context theo capacity; không còn rơi về16000byte mặc định hoặc nuốt lỗi GET/PUT. Cấu hình cũ chỉ được chỉnh khi chưa có query/cohort.
- Verify manifest đủ3 publication/version/decision/bundle/state với API published; freeze benchmark/index/assistant/provider trước chấm, khóa prompt/config trace từ response đầu.
- Budget là dự toán UTF8-byte theo capacity và dự phòng overhead16384, evidence cap128000. Kiểm cặp query/chunk rerank và quota trước chat, ghi bundle bytes/plan vào report. Chưa phải phép đo toàn bộ prompt/schema/catalog thật; ModelOps vẫn chặn payload cuối. Không khẳng định mọi tài liệu/model sẽ hết lỗi token.

## Kiểm chứng đã thực chạy

Cwd root hoặc frontendV1 đúng phạm vi:

| Lệnh | Kết quả |
|---|---|
| `backendV1/.venv/Scripts/python.exe -X utf8 scripts/verify_admissions_benchmark.py` | PASS exit0:3PDF/28trang/53case/55factchecks; kiểm hash/pagecount và số ở nguồn; critical floor row-code/cột cũng được đối chiếu |
| `npx vitest run tests/admissions-integrity-775.test.ts tests/admissions-cohort-775.test.ts tests/admissions-replay-764.test.ts tests/admissions-multi-docs-773.test.ts` | PASS exit0:49/49 cuối batch |
| `npm run test:e2e:typecheck` | PASS exit0 cuối batch |
| `npx biome check <11 TS/JSON files sửa>` | PASS exit0, không warning cuối batch |
| `backendV1/.venv/Scripts/ruff.exe check scripts/verify_admissions_benchmark.py` | PASS exit0 |
| `npm run build` | PASS exit0; có warning Vite config native tương lai và chunk>500kB |
| `npm test -- --reporter=dot` | FAIL exit1:539PASS/33FAIL,9file fail/58file pass. Full run ở thời điểm46 scoped tests;3negative cuối được chạy lại trong49scopedPASS, không suy tổng full mới |
| `git diff --check` | PASS exit0 |
| `.\test-v1-e2e.ps1 status` | Phiên93faa11f0caf provider-setupBLOCKED, các chặng model/navigation/admissionsNOT_RUN |

Full frontend fail ở: rag-ui-674, lifecycle-operations-ui-678, maintenance-evaluation-ui-679, final-functions-ui-682, workspace-sidebar-689, sidebar-navigation-691, navigation-scope-692, test_connection_review_705, knowledge-actions-708. Ví dụ lỗi: thiếu QueryClientProvider, auth provider, mock hasV1Permission. Không sửa các fixture/UI này vì ngoài phạm vi. Chưa đối chiếu baseline riêng nên không khẳng định cả33 là lỗi nền đã xác nhận. Tổng full suite vẫn FAIL.

## Giới hạn và bàn giao

- **Live53câu NOT_RUN:** DB phiên mới chưa có upstream key; provider-setup yêu cầu terminal tương tác. Không đọc/ghi key vào file hoặc log.
- Người dùng chạy `.\test-v1-e2e.ps1 run provider-setup --headed` tại root, nhập key ẩn, rồi các chặng theo tài liệu test đã cập nhật. Giữ phiên hiện tại, không cleanup/init thêm.
- Nhãn draft chưa có human approval; semantic_reviewNOT_RUN. Offline source audit và mock tests không chứng minh recall/chất lượng model thật hoặc PDF/OCR chính xác hoàn toàn.
- Không sửa production prompt nên không đổi PROMPT_VERSION trong lượt này.
