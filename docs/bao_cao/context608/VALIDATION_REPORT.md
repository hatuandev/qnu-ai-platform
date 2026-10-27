# Context608 — Kiểm chứng hai blocker và chạy compiler ba DOCX

## Môi trường

Đã kiểm ENV development, DB loopback, MinIO/Qdrant loopback bằng read-only query trước regression. Test dùng DB qnu_test_context608_* có nonce ownership comment, LocalStorage riêng, endpoints ngoài test thay bằng127.0.0.1:1 và network guard. Không schema migration hoặc reset DB ứng dụng.

Ba database riêng: checks cho baseline/first full, live-checks cho real compiler fixtures và focused, release-checks cho full chốt sau lượt bị gián đoạn. Defaults metadata inactive/no credential ở release DB lấy từ DB test baseline đã xác minh, giữ cùng dữ liệu typed với baseline; không lấy routing đang đổi gh làm thay đổi giả lập regression. Không sao chép provider/key vào test DB.

Source fixtures dùng cùng ba file DOCX2024–2026 và canonical602 đã ghim hash,381noncontainerproofs. Filebytes được kiểm trước sao chép vào LocalStorage test. Đây là compiler API/ASGI với nguồn thật và ModelOps thật; không browser E2E, không fresh parse hoặc chứng nhận lại toàn Source Quality Gate. Fixture quality report chỉ format_only; không đổi gate của nguồn thật.

## Kiểm thử nội bộ

| Kiểm tra | Kết quả | Exit |
|---|---|---:|
| Baseline full app snapshot đầu608 |3551PASS/18FAIL/17SKIP,+23subtestPASS,600,67s |1|
|9regression tái hiện trước sửa |9FAIL |1|
| Focused đầu sau sửa |178PASS,66,90s |0|
| Focused13test mới sau mở rộng |182PASS,68,48s |0|
| Release-focused lần1 | Không có output/JUnit; process trả1 |1|
| Release-focused lần2 trên code cuối |182PASS,69,97s |0|
| Scoped Ruff |5files PASS |0|
| Final full lần1 |INCOMPLETE, log dừng46%, không JUnit/exit receipt, process không còn |Không xác định|

Final full lần1 xảy ra qua các lượt bị ngắt/steering; chưa xác định chắc nguyên nhân dừng, không báo PASS hoặc tự quy cho mã/model. Một helper chẩn đoán khác gặp OpenBLAS memory allocation; lúc đó host còn dưới0,5GB RAM. Release full dùng DB mới và OPENBLAS_NUM_THREADS=1 cho tiến trình test, không sửa app config hoặc model. Không gộp focused hoặc các phần log thành full PASS.

Final full chốt: **3564PASS/18FAIL/17SKIP,+23subtestPASS**,13warnings,551,27s,exit1. Baseline3551/18/17:13test mới PASS; exact failure IDs và cause giống baseline,0lỗi mới/0cause đổi/0ID mất. Full suite vẫn FAIL; không ghép các lượt chưa hoàn thành thành PASS. [Bảng exact IDs](TEST_ID_COMPARISON.md).

## Qwen thật trước khi đổi model

- Partial-date probe:2calls PASS. Full date unknown/null, raw year2025 giữ; temporal_roles=true, không đoán ngày/tháng. Scope literal giữ dấu vết nguồn.
- Frozen-empty control:4calls PASS theo thứ tự CoverageAudit,CoverageAudit,PacketDraft,PacketCheck. Trạng thái empty đầu là control lấy lại tình huống rỗng đã từng quan sát, không phải tuyên bố Qwen tự tạo empty lần mới. Hai audit yêu cầu bổ sung, targeted repair giữ null và năm2025, review complete. Không item review cho empty, không proof bị tự cho unrelated.
- Full ba DOCX:HTTP502, job kc_110450f04c8948d9b41acbed66a61508/uncertain,78436,19ms. PacketDraft initial bị schema reject rồi correction có5assertions; PacketCheck initial+correction đều không đạt, reason vượt400ký tự. Chưa có bundle hoàn thành. Không tăng reason limit, không truncate text để làm PASS.
- Đọc độc lập candidate Qwen: có unknown tổng chỉ tiêu gắn vào bảng bìa trống; bìa không chứng minh tổng chỉ tiêu chưa được nguồn xác định. Canonical source1 có tổng5948/teacher1613 phía sau. Chưa cấp semantic PASS cho candidate; không quy toàn bộ lỗi là trình bày.

## Chuyển sang gh/gpt-6-luna theo chỉ đạo bổ sung

- Exact alias probe chat HTTP200/available. Thêm alias vào9router qua API, giữ cx cũ; primary defaults/admissions ghi/read-back200, single/no fallback.
- Generic probe HTTP200/stop/no fallback; requested alias gh/gpt-6-luna, provider trả served model gpt-6-luna. Helper exact-string check FAIL được giữ, follow-up xác nhận routing gh và không resend mutation. Phần seal helper cũng FAIL do row metadata runtime provider đổi, không phải source thay đổi; đối chiếu cuối phải giới hạn đúng provider/defaults/admissions được phép.
- Token Saver đã tắt theo người dùng; chưa chứng nhận config nội bộ9router bằng độc lập.

### Kết quả compiler gh/gpt-6-luna

HTTP502 KNOWLEDGE_WIKI_INVALID/json_syntax/JSONDecodeError, job kc_b037db50513b4ed984f46a580e4ffb68/uncertain,307088,32ms.20model calls,18TopicSelection qua ba nguồn rồi2PacketDraft(initial+1format correction) đều JSON syntax failure. Hai request draft có input upper bound11431/11541, tổng reserve13931/14041 dưới workflow24000, finish_reason=stop và provider usage báo0input/0output. Không có dấu hiệu length exhaustion trong các metadata quan sát, không chứng minh context32K thiếu. Raw response body chưa được lưu nên chưa chốt output rỗng, prose, refusal hoặc lỗi router nào.

Request dùng exact alias gh/gpt-6-luna; metrics/usage upstream trả gpt-6-luna, provider9router/custom,0fallback. Không có Qwen trong lượt Luna. GET jobHTTP200 chỉ đọc job thất bại, bundle=null/proposal_hash=null; chưa có Markdown/bundle606/608 mới để nghiệm thu. Không resend uncertain intent hoặc chạy vòng whole-build mới để tìm một lượt may mắn.

Qwen và Luna đều chưa đạt whole compiler trong lượt608; khác lỗi và khác tuyến thực thi nên chưa báo model nào cải thiện bao nhiêu. Cần xử lý hợp đồng/quan sát JSON tại ranh giới ModelOps trước khi quy toàn bộ cho năng lực model. Hai ca blocker ban đầu có Qwen focused probe PASS, không dùng chúng thay whole pipeline PASS.

Ledger gắn tag608:49records =28Qwen (22whole+2partial-date+4frozen-empty) và21served gpt-6-luna (20whole+1generic probe),0fallback,186848input/22582output tokens theo provider. Một catalog chat probe gh riêng không nằm trong ledger49records. Status success trong ledger chỉ là inference/transport, không semantic/compiler PASS.

## Bảo toàn, giới hạn và dọn dẹp

Read-only postcheck giữ hash ba rawDOCX, các row knowledge collection/binding/source/index và toàn payload2943Qdrantpoints khớp baseline602,0retrievable. Hai app file cũ đổi và một app module mới;457Python app files được ghi final hash. Chỉ provider9router (catalog/capability/runtime metadata), system defaults và admissions được phép đổi; tất cả row khác khớp đầu608. Không gửi API key update hoặc ghi key vào env. ModelOps audit/key usage có thể cập nhật metadata trong quá trình inference.

Cả ba database test608 đã drop sau khi kiểm exact tên/nonce ownership comment và khác DB ứng dụng; xác nhận không còn DB. LocalStorage/bằng chứng vẫn giữ theo policy bảo vệ đã được ghi nhận từ các lượt trước; không thử bypass để xóa, không tuyên bố Storage đã dọn sạch.

Không reindex/source publication/approval, không gọi lại benchmark64, không FE/build vì không sửa FE, không restart/deploy/commit/push. GitHub blocker PDF162,41MB trong lịch sử từ607 giữ nguyên; không rewrite hoặc force-push.

ModelOps status success phản ánh tầng inference; phải đọc JSON/entailment/scope/coverage và policy trước nghiệm thu. Nếu còn vấn đề, compiler phải needs_attention hoặc lỗi thật, không đổi thành nguồn trống hay dữ liệu đã được duyệt.

## Lệnh và receipts

Từ root D:\DuAnPhanMem\qnu-ai-platform, dùng backend/.venv/Scripts/python.exe với các helper .antigravity-bridge/validation/context608_*.py. Regression child cwd backend.

- checks.py setup/seed-defaults/seals, run --baseline --label baseline-full tests: exit1, lưu snapshot app đầu608 và ignore test608 mới.
- live_checks.py run --label baseline-two-blockers tests/test_compilation_context_608.py: exit1/9FAIL; các focused trước/sau được giữ riêng trong run receipts.
- release_checks.py setup/seed-defaults/run --label final-full tests: child exit1 với3564/18/17; OPENBLAS_NUM_THREADS=1 chỉ trong tiến trình.
- compare_tests.py: exit0, exact ID/cause; ruff scoped command5files exit0 lưu checks/ruff-final-run.json.
- partial_date_probe.py và empty_coverage_probe.py: exit0, Qwen focused2/4calls.
- live_qwen.py --execute và live_luna.py --execute: helper kết thúc, nhưng API compiler đều502, không ghi compiler PASS từ exit của helper.
- switch_luna.py: helper exit1 do exact alias response string và seal assumption, giữ receipt; verification-followup xác nhận writes/readback routing đúng, không resend. ModelOps catalog probe và provider/catalog update chạy qua HTTP API đang chạy.
- postcheck.py: exit0, nguồn/vector/app scope giữ đúng; shared-row-verification kiểm model switch được phép.
- cleanup của checks.py/live_checks.py/release_checks.py: exit0, chỉ DB sở hữu608.

Command/args/cwd/exit Pytest đầy đủ ở checks/*-run.json, live-checks/*-run.json và release-checks/final-full-run.json. Baseline full có code snapshot trước thay đổi. Những helper chẩn đoán sai tên candidate hoặc lỗi startup/argparse đã sửa trước bước tương ứng; không tính chúng thành PASS ứng dụng hoặc model.
