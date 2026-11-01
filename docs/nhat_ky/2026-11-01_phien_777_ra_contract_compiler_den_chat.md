# Phiên 777 — Rà hợp đồng từ compiler đến hỏi đáp

## Yêu cầu và phạm vi

Người dùng yêu cầu rà và sửa luồng từ compiler đến hết quy trình sau lỗi422validation_error. Áp dụng clean-code, ingestion, rag-evaluation và kiểm chứng frontend có phạm vi. Chỉ sửa runner/schema-check test, không sửa backend nghiệp vụ hay OCR gốc; giữ thay đổi chưa commit của các lượt trước. Không tự gọi compiler/model, restart, cleanup/init, publish/reindex dữ liệu live.

## Nguyên nhân đã tái hiện

POSTcompiler ở bộ đa tài liệu dùng source_id/revision_id, nhưng CompilationRequest yêu cầu topic/ocr_run_ids và extra=forbid. Dùng chính body_field của APIRoute backend xác nhận4lỗi: thiếu topic, thiếu ocr_run_ids, thừa source_id, thừa revision_id. Red kiểm tra offline exit1 trước sửa body. Lỗi xảy ra trước inference, không liên quan giới hạn token.

## Sửa và rà cả chuỗi

- admissions-publication: đổi payload sang topic theo tiêu đề nguồn, ocr_run_ids, text_versions, provider_id; structured_output=true. auto_review=false vì runner gọi review tường minh, tránh hai review.
- Trước compiler đầu tiên: kiểm đủ cả3source/hash và trạng thái/pagecount OCR; đọc text-review để ghim version/hash canonical (Source.textSha256 mới). Các lần sau đọc đúng version đã ghim và chặn hash khác. Không sửa bản OCR.
- Recovery chỉ cập nhật compilationHistory sau khi POST thành công. Nếu POST lỗi thì lần thực hiện sau vẫn dùng cùng khóa phục hồi, không tăng lịch sử/khóa vô tình.
- Draft phải có sections/citations không rỗng, citation trỏ đúng OCR run. Review xong phải đọc report đúng review ID và không có finding.
- Trước tạo tài liệu/xuất bản: rà cả3review completed/compilation ID/report ID/findings, không publish tài liệu1 khi đã biết tài liệu2 còn issue. Gateapprove phải là review đã kiểm tra; preview/hash/idempotent commit giữ nguyên.
- Trước chat: index phải completed/active, đúng embedding provider và đúng tập document duy nhất; tiếp tục kiểm version/publication receipt/bundle/state như775.
- Đọc schema các request còn lại: ReviewRequest, CreateDocumentRequest, PreviewRequest/review_ack, CommitRequest, IndexRequest, AssistantConfig/AssistantUpdate, ConversationCreate/TurnRequest. Luồng hỏi đáp giữ single/all scope, version/proof, cohort, no-retry từ775.

## Kiểm thử mới và giới hạn

scripts/check_v1_e2e_contracts.py nhận request thu từ runner và dùng APIRoute thật để kiểm method/path/Pydanticbody/header/query. Không chạy handler/dependency, DB, secret hay LLM. Fixture tạo3doc qua compile/review/preview/approve/publish/index/assistant create+update/conversation single+all; không dùng bản schema tự chép để tuyên bố tương thích.

admissions-pipeline-777.test.ts có9cases: cảchuỗi/requestvalidation; oldpayloadreject; findingschặnxuấtbản; reviewgatekháccheckpoint; OCRhashđổi; reruncompletedkhôngPOSTmới; recoveryPOSTfailgiữkey/history; inactiveindex; saihashnguồnthứ2chặnmodelđầu. Test requestlegacy khi chạy full gặp trần mặc định5s do startup Python; đặt giới hạn30s giống helper (không thay kết quả/mở guard, không retry model), chạy lại full để kiểm chứng.

## Kết quả thực chạy

| Kiểm tra | Kết quả |
|---|---|
| Vitest trọng tâm lúc đầu4file |52PASS trước bổ sung nhánh assistant update |
| FullVitest cuối: npm test -- --reporter=json --outputFile=../tmp/verification777-vitest-final.json |560PASS/33FAIL/593; exit1. Trong đó8file tuyển sinh/provider/quota gồm88cases đềuPASS |
| npm run test:e2e:typecheck |PASS exit0 |
| npm run build |PASS exit0; warning Viteconfig và chunks>500kB như trước |
| Biome check các5TS sửa |PASS exit0 sau formatter |
| ruff check scripts/check_v1_e2e_contracts.py |PASS exit0 sau sắp import |
| git diff --check |PASS exit0 |
| test-v1-e2e.ps1 status |Session93faa11f0caf: provider/discovery/4model/navigation/admissions-upload/admissions-extractionPASS; compilationFAIL422cũ, publication/chatNOT_RUN |

9file vẫnFAIL: final-functions-ui-682, knowledge-actions-708, lifecycle-operations-ui-678, maintenance-evaluation-ui-679, navigation-scope-692, rag-ui-674, sidebar-navigation-691, test_connection_review_705, workspace-sidebar-689. Không sửa các fixture/UI ngoài phạm vi và không báo fullsuitePASS. 33lỗi này có ở lần full đầu của lượt777 và giữ nguyên ở lần cuối; lỗi mớitimeout của test777 đã hết.

## Bàn giao

Chưa chạy E2E compiler/review/model thật trong lượt này: hợp đồng/schema và fake adapter không chứng minh chất lượng nội dung hay đủ53câu. Không tự đổi nguồn/nhãn/index/quota, không retry inference để làm xanh. Không đổi PROMPT_VERSION vì không sửa prompt backend.

Giữ phiên/sourceOCR hiện tại, khôngcleanup/init/restart. Chạy lại admissions-compilation --headed; nếuPASS mới admissions-publication --headed, rồi admissions-chat --headed. Không cần --recover cho lỗi422body vì chưa tạo run. Nếu review có finding/model trả lỗi, giữ đúng lỗi và lịch sử, dừng để rà; không autoack/bỏfindings.
