# Phiên559 — Kiểm thử thật Automatic Ingestion bằng DOCX phức tạp

Ngày 2026-10-19. Người dùng cho phép dùng đúng DOCX trước đó, tạo revision mới, kiểm tra Markdown/JSON và nạp vector staging; chưa xuất bản. Không sửa source ứng dụng, commit/push/deploy hoặc thay policy để nạp bằng mọi giá.

## Môi trường và phạm vi

Đọc Git/diff, PROJECT_CONTEXT, skill ingestion/clean-code và quy tắc verification/memory. Xác minh file local102.423byte khớp snapshot S3/hash58b3f780...99274; đúng binding bnd_21c09bbc6ca0/col_admissions. DB/MinIO/Qdrant local, API/Qdrant200; quyền view/update/upload qua configured development actor hiện có, không token/override. Không coi là humanSSO.

Đây là live operation được người dùng cho phép trên một nguồn mô phỏng, không chạy regression ghi vào DB dùng chung. Tạo đúng một reservation bằng queue_reparse(dispatch=False), chạy leased worker thật inline từ code hiện tại; không broker/worker cũ hoặc restart. Dùng DB/Storage thật, không mock. New revision3 **ks_rev_9c93b4b4e2be**, job **job_db44750a8c07**, worker completed.

## Kết quả

- Markdown Standard validator: PASS233block/0error/0warning; MD/JSON/source/projection/resources hash hợp lệ và API download200 khớp Storage.
- Native oracle và revision557 trước: khớp từng core block/body/type/parent/order; mọi bảng/header/row/raw/state khớp,10bảng/3footnote có locator;0012/00027/AM-0007/AM-0070 giữ chuỗi.
- **NEEDS_ATTENTION**,8blocker: list l002 chưa định vị chắc;5hàng gộp r014/r030/r046/r047(t002),r072(t004) chưa rõ vai trò; header t004 chưa xác minh; hình fg001 chưa phiên âm/kiểm chứng. Không đồng nghĩa8chỗ mất raw data. Đính chính lời cập nhật ban đầu: spanning row ở đây là hàng gộp chưa rõ vai trò, không phải dòng qua trang.
-4limitations:1blank và3literal chưa diễn giải, giữ nguyên/khôngfact; footnote3pageunknown có Word anchor nên warning riêng. Pending/effective semantic mới không có; proposal cũ nguyên.
- POST vector-load thật đúng1lần, generation BGE-M3 hiện có: **HTTP404 SOURCE_NOT_FOUND** do binding vẫn pending/khôngactive sau QC, dù nguồn tồn tại đúng kho. Thông báo API chưa nêu đúng QC, ghi nhận chưa sửa code trong nhiệm vụ test.
- **VECTOR_BLOCKED**, khôngjob/index/embedding mới; Qdrant exactcount newrevision0point. Không báo E2E vectorPASS. Không activate/publish.
- Final READ ONLY: mọicột2revision cũ/pairs, toànbinding/collection và generation nguyên; active_source/index null. Source revisions13→14; index26/chunk56/fact0/LLMusage1774 giữ. KhôngsemanticLLMproposal; pipeline engine docling+native+paddleocr_vl, PDFInspector nonzero warning giữnative, không tuyên bố offline hoàn toàn hoặc hình đã kiểm chứng.

## Lệnh và evidence

Từ root, Python venv chạy backend/storage/context559/{preflight,create_revision,validate_revision,final_integrity}.py. Preflight/create/finalvalidation/finalintegrity exit0. Helper validation đầu exit1 do async generator/all trong script riêng; sửa helper và đọc lại cùng revision, không tạo lại. Log đầu/final giữ. Không chạy build/fullsuite vì không sửa source ứng dụng; không nhận baseline558 là test mới.

Evidence riêng backend/storage/context559: before/safety/created-receipt/validation/api-validation/final-integrity; MD/JSON ở canonical/. Không đưa corpus hoặc credential vào nhật ký. Giữ revision/artifacts ứng dụng người dùng vừa yêu cầu để xem, không tự dọn nguồn thật như testDB. Không tạo DBtest/runtime mới, không retry xóa runtime cũ bị policy chặn.

[Báo cáo live](../bao_cao/context559/LIVE_INGESTION_REPORT.md), [kết quả JSON](../bao_cao/context559/RESULT.json). Cần xử lý8vị trí structural/page/visual theo bằng chứng trước khi nạp vector, không hạ gate hoặc coi nguyênraw là semanticapproved. Chưa có dữ liệu mới được chatbot phục vụ.
