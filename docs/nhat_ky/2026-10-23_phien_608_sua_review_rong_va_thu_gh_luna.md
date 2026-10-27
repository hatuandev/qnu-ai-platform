# Phiên608 — Sửa review rỗng và kiểm chứng gh/gpt-6-luna

Ngày23/10/2026. Ban đầu người dùng yêu cầu sửa hai blocker, thêm regression và chạy compiler trên3DOCX2024–2026 bằng Qwen, giữ nguồn/QualityGate và không reindex/publish/commit/push. Sau khi hỏi đánh giá Qwen, người dùng chỉ đạo chuyển primary sang đúng gh/gpt-6-luna và chạy lại, xác nhận đã tắt Token Saver. Ngoại lệ chỉ cho phép thay model/cấu hình chat liên quan, không triển khai hoặc sửa dữ liệu nguồn.

sửa empty draft→coverage và tách temporal review;13test mới, focused182/Ruff5 PASS. Full3564PASS/18FAIL baseline/17SKIP,+23subtestPASS, exact IDs/cause giữ. Qwen hai probe hẹp PASS nhưng whole3DOCX FAIL reason>400. Theo chỉ đạo tiếp, thêm đúng alias gh/gpt-6-luna/9router sau probe thật, đổi primary defaults+admissions single/no fallback, giữ role khác; provider trả model gpt-6-luna. Luna chọn bằng chứng18lượt qua3nguồn rồi2draft JSON syntax FAIL, HTTP502/bundle null; chưa APPROVED. Nguồn/model ngoài phạm vi/vector2943/0retrievable giữ,3DBtestdọn/Storagegiữpolicy. Không reindex/publish/restart/commit/push. Gitea607commit09d254da đã đồng bộ; GitHub còn GH001 PDF lịch sử, không rewrite.

## Thay đổi và phương pháp

Đọc AGENTS/memory/diff/verification, dùng skill Clean Code, Backend và ModelOps đã nêu. Không subagent. Hai file app sửa services/compilation_engine.py, compilation_modelops.py; mới compilation_review.py. Empty không còn gửi item verifier; giữ mọi primary proof chờ hai coverage audit và một repair tối đa. Không đồng thuận hoặc repair vẫn rỗng thì incomplete. Time review tách claimed scopes với raw year literals đúng proof, bỏ navigation classifier khỏi reviewer, không tự gán year role hay false→true. Unknown/null và source_unspecified wire alias giữ tương thích. Cache hash đổi theo protocol/guidance.

13test mới kiểm success/failure/ambiguity/repeated empty/coverage unanimity/partial time/no cross-proof inference/negative temporal verdict/cache, với9ca tái hiện FAIL trước sửa. Snapshot integration test chỉ thêm DB608prefix, vẫn ownership/environment/host. ModelOps dynamic, không hardcode tên model trong app. Không frontend/parser/schema migration mới.

## Kết quả thực chạy

- [Triển khai](../bao_cao/context608/IMPLEMENTATION_REPORT.md).
- [Kiểm chứng và lệnh](../bao_cao/context608/VALIDATION_REPORT.md).
- [Exact test IDs/cause](../bao_cao/context608/TEST_ID_COMPARISON.md).
- [Đánh giá model và giới hạn so sánh](../bao_cao/context608/MODEL_ASSESSMENT.md).

Baseline full3551/18/17, final3564/18/17;13mới PASS,0failure/cause/ID regression. Một full không có JUnit/exit receipt giữ INCOMPLETE, không tự quy nguyên nhân; final chạy DB mới. Một focused trả1/output rỗng, rerun đầy đủ182PASS. Helper phân tích khác từng báo thiếu RAM OpenBLAS; giới hạn1thread cho final process, không đổi app/runtime config. Full vẫn FAIL18baseline.

Qwen partial-date2calls và frozen-empty4calls PASS. Frozen-empty là control từ lỗi đã quan sát, không giả whole live E2E. WholeQwen HTTP502 reason>400,22calls; không nới/cắt reason. Đọc candidate còn thấy unknown tổng chỉ tiêu gắn bảng bìa trống, chưa đủ bằng chứng giới hạn nguồn. Không nghiệm thu proposal này.

ModelOps catalog cũ chỉ có cx/gpt-6-luna; probe exact gh chat HTTP200/available rồi thêm alias qua API, giữ model cũ/provider default/endpoint/key/timeout. Defaults và admissions PUT/PATCH/GET200 primarygh single/no fallback; genericprobeHTTP200/stop trả served model gpt-6-luna nên check so chuỗi alias tuyệt đối của helper FAIL, follow-up read-only xác nhận requested route đúng. Một seal assumption không cho provider runtime metadata đổi cũng FAIL; giữ các receipts và đối chiếu lại đúng row cho phép. Không resend writes/intent. Token Saver tắt theo người dùng, chưa kiểm độc lập config9router.

WholeLuna307,09s,20calls,18TopicSelection rồi2PacketDraft invalidJSON,HTTP502/uncertain/bundle null. Hai phản hồi draft provider báo0tokens/stop, reserved request dưới24K; không kết luận thiếu context, hết quota hoặc mất kết nối. Chưa có raw response body để phân loại prose/refusal/router error. Câu hỏi “gh không gọi được sao” được làm rõ: gọi được và18selection validJSON; thất bại ở bước output draft. Giữ primarygh, không tự fallback hoặc đổi lạiQwen.

Ledger49taggedrecords:28Qwen/21servedgpt-6-luna,0fallback,186848input/22582outputtokens; catalogprobe riêng ngoài ledger. Success usage không phải semanticPASS. Nguồn/rawhash/knowledge rows/vector payload2943/0retrievable giữ. Chỉ9router catalog/capability/runtime metadata, system defaults và admissions đổi trong phạm vi được phép; các row khác khớp.

## Dọn và tiếp tục

Ba DBtest608 đã dọn theo exactname+nonce ownership, Storage giữ theo policy. Không live source/index/publication writes, không benchmark64, không FE/build vì không sửa FE, không restart/deploy/Git writes.

Compiler chưa APPROVED. Tiếp theo nên quan sát phản hồi JSON ở ranh giới ModelOps với dữ liệu/prompt bảo vệ, rồi xác định lỗi model/router/adapter và cân nhắc native output contract. Không tiếp tục whole-build may rủi hoặc hạ validation. Chưa triển khai việc đó trong608. Gitea607đã có09d254da; GitHub GH001 PDF162,41MB lịch sử chưa được cho phép rewrite, giữ nguyên.
