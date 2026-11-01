# Phiên778 — Chạy riêng compiler sau khi tắt máy

Ngày: 2026-11-01 (Asia/Bangkok).

Người dùng yêu cầu khởi động lại test và tạm thời chỉ compiler, chưa review. Thêm chặng tùy chọn `admissions-draft`; không đổi backend, prompt hoặc cấu hình model. Chặng này dùng request `auto_review=false`, kiểm tra draft/citation/hash/version giống luồng đầy đủ, giữ checkpoint để `admissions-compilation` review lại các draft đã xong. PASS draft không thay thế compilation có review và không mở khóa publication/chat. Prerequisites của luồng cũ không bắt buộc draft.

Compiler preflight đọc quota tháng hiện tại trước khi tạo lượt. Phục hồi quota chỉ cho failed `quota_not_configured`, đúng provider, chưa review/version, tất cả part pending và attempt_count=0; cần `--recover`, giữ lịch sử, không gửi lại part uncertain.

## Vận hành thật

- Phiên giữ nguyên `93faa11f0caf`; upload/extraction/model stages vẫn PASS lịch sử.
- Docker engine sẵn sàng nhưng 5 container của phiên stopped sau tắt máy. Đã `compose up -d` đúng project, giữ volumes; khởi động serve ẩn, PID8524, frontend64625/API64624. Không cleanup/init, không upload/OCR lại, không đổi provider/key.
- Lượt `cmp_275350db4f66` cũ chạy từ tối trước; ARQ job hết lượt. Kích hoạt hàm đối soát sẵn có qua queue E2E; lượt thành uncertain/`compilation_request_interrupted`, không replay request dở. Test draft lần đầu FAIL do lỗi này.
- Phục hồi chủ đích tạo `cmp_1186d695f02e`; failed `quota_not_configured` trước mọi model part. Ngày mới đã sang tháng11 trong khi quota tháng10 không áp dụng. Đã dùng API được xác thực, kiểm tra workspace code thuộc phiên, cấu hình quota tháng2026-11-01 đúng20.000.000 user đã duyệt; counters used/reserved giữ nguyên. Không đọc/in key upstream.
- Lượt tiếp `cmp_f891264dee77` đang chạy thật, concurrency2, 4root parts cho floor2026; chưa review/publish/index/chat. Kết quả live đang chờ, chưa nghiệm thu.

## Kiểm chứng

- `npx vitest run tests/admissions-recovery.test.ts tests/admissions-pipeline-777.test.ts`:33PASS (17recovery +12pipeline +4transport).
- Python unittest scripts/test_v1_e2e_draft_778.py:3PASS; runtime741:2PASS; cleanup:10PASS, dùng fake không dọn phiên thật.
- TypeScript E2E, build, Biome7file, Ruff2file, diff whitespace:PASS. Build có cảnh báo chunk lớn.
- Full frontend cuối cùng:565PASS/33FAIL/598total, exit1. Cùng9file UI/fixture nền như777:final-functions-ui682,knowledge-actions708,lifecycle678,maintenance679,navigation692,rag674,sidebar691,connection705,workspace689. Không sửa fixture ngoài phạm vi.
- Biome gọi nhầm từ repo root một lần báo nested config; chạy lại đúng cwd frontendV1 đạt, không đổi config.

## File logic

`frontendV1/e2e/stages/admissions-publication.ts`, `admissions-recovery.ts`, `admissions.spec.ts`; testpipeline777/recovery; `scripts/v1_e2e_session.py`, test_v1_e2e_draft_778.py; hướng dẫn test tuyển sinh và memory.

## Quan sát output model thật

Hai raw response root1/root2 của cmp_f891264dee77: finish_reason=length, completion_tokens8192, content_chars0; reasoning_chars24437/26508. Prompt tokens32009/38903, total40201/47095. Refiner đã mở child5/6 và7/8. Không lưu nội dung raw/prompt trong docs, chỉ chỉ số an toàn. Chưa đổi reasoning policy hoặc giới hạn model. Đây là nguyên nhân compiler chậm độc lập với review.

## Đổi reasoning theo xác nhận trực tiếp của user

User chọn tắt suy luận cho compiler qua câu hỏi tùy chọn trong phiên. Đã xác minh đúng worker PID26352 thuộc cây serve E2E778, dừng worker; serve cha tự dọn API/worker/FE, không dừng Docker. Test đang đợi bị ngắt, giữ FAIL 7.4phút. Khởi động lại serve PID33356, kiểm tra API/FE ready.

Vì worker đã chết được kiểm chứng, tác vụ quản trị được xác thực qua bearer/resolve_actor và require_model_admin, authorize_collection(write=True) trước khi dùng cơ chế domain `_mark_uncertain_segments` + `finish` cho đúng runcmp_f891264dee77: trạng thái uncertain/compilation_request_interrupted; audit workspace `compilation.operator_interrupted`; raw/completed/unknownusage được giữ. Không SQL cập nhật hàng loạt hay giả PASS, không resend call dở.

Probe tổng hợp qua prepare_chat_request, quota reserve/settle và ManagedChatModel/key pool: chat_template_kwargs.enable_thinking=false,512output. JSON {ok:true} đúng, finishstop, reasoning0, completion6,total33,0.64s. Sau probe mới lưu ModelOps reasoning policy verified cho đúng providerQwen của phiên, tasks.off=[compiler]. Không đổi compiler_review/answer, endpoint/key/capacity/output/timeout. Đây là probe nhỏ, không chứng minh chất lượng PDF. Metadata an toàn lưu reasoning-probe-778.json trong phiên.

Lượt compiler mới sau đổi cấu hình đang chạy từ OCR cũ, giữ lịch sử. Floor2026 hoàn tất4/4 trong80.5s; info2025 đang xử lý8parts. Review vẫn không gọi.

Bổ sung chặn lỗi transport Playwright mang Authorization/full calllog ra báo cáo: Api.raw trả thông báo an toàn, không cause/rawerror và không tự retry. Regression dùng token giả xác nhận không leak; các textartifact và embeddedHTML của lượt chủ đích dừng đã redacted Authorization, giữ lỗi/trạng thái. Không công bố token hoặc corpus.

## Kết quả cuối cùng

Chạy `test-v1-e2e.ps1 run admissions-draft --headed --recover` sau khi đổi reasoning được user xác nhận: **PASS**,1test,5.1phút,retries=0. Report: tmp/v1-e2e/93faa11f0caf/runs/admissions-draft-1793506464739306600. Không tạo lại lượt để chọn đáp án tốt; các lượt bị gián đoạn/quota và lượt trước đổi config vẫn được giữ.

| Tài liệu | Phần hoàn tất | Thời gian server | Run |
|---|---|---|---|
| floor2026 |4/4|80.5s|cmp_17416ea9e495|
| info2025 |8/8|129.2s|cmp_86929befc053|
| report2024 |5/5|85.4s|cmp_12a8793e3b0a|

API xác nhận cả3 completed,17rawcalls đều finish_reason=stop và reasoning0,0review mỗi run,không publicationversion. Tổng usage400409 gồm input+output,không phải riêng output. Không refinement thêm sau tắtthinking. Metadata compiler-only-778.json chỉ chứa số đo an toàn.

Kiểm chứng cuối:33focusedVitestPASS,15scriptunittestPASS,TypeScript/build/Biome7file/Ruff/diffPASS. Fullfrontend565PASS/33FAIL/598total; đối chiếu exact33failureIDs bằng JSON với777 giống nhau, không có failuremới. Các report trước/sau config khác nhau được giữ riêng.

Để tiếp tục: giữ phiên93faa11f0caf và các nguồn/OCR; chặng admissions-draftPASS độc lập, admissions-compilation/publication/chat chưa PASS trong lượt này. Chạy admissions-compilation để dùng lại3draft và review khi cần; không cleanup/init hoặc dùngrecover cho các runcompleted. API/worker/frontend do agent bật vẫn chạyẩn dưới servePID33356; Docker project giữ nguyên. Chưa chạy53câu, chưa chứng minh chất lượng nội dung bằng review; không nghiệmthu cảquytrình.
