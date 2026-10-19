# Phiên 557 — Canonical draft và pending semantic review

Ngày 2026-10-19. Người dùng giao triển khai Context557 và cho phép tạo đúng một revision nháp của DOCX kiểm thử, đối soát và stage pending qua service/API có quyền; không approve/apply/publish hoặc gọi lại pipeline LLM annotation.

## Kết quả thực tế

**STAGED — WAITING_FOR_REVIEW.** Source `bnd_21c09bbc6ca0`/`col_admissions`; revision mới `ks_rev_2b5e0352565f`, job `job_ab29c145476d` completed, status review_required. Preflight chứng minh DOCX cùng SHA256/102.423 byte, duy nhất source kiểm thử, Storage MinIO và DB local. Revision cũ `ks_rev_84c4950c9ce2` giữ nguyên toàn row/checksum/status; chỉ có hai revision của binding sau xử lý.

Tái dùng queue_reparse(dispatch=False) và task_knowledge_source_reparse chính thức, chạy pipeline v18 current/standard profile; không standalone parser chèn DB, không broker/worker cũ/restart. Source policy annotation null, LLM usage ledger1774 trước/sau; không22packet. Pipeline preview vẫn dùng PaddleOCR-VL theo cấu hình OCR sẵn có.

Native canonical có233block/10table/3footnote; tất cả core records theo thứ tự và mọi header/row/raw/state khớp offline đầy đủ. Kiểm native XML và bidirectional anchors/context_refs; A12 footnote2 đúng0012/00027/AM-0007/c02/r001–3, A03 workflow groupA/2027/no c10–12. Footnote3 page unknown được giữ, XML locator có thật; page mapping partial/18trang. PDF Inspector diagnostic thất bại giữ native; cảnh báo preview/legacy nguồn giữ để người dùng đối soát, không tự duyệt.

Reconcile12/12 và6references PASS, giữ18issue O01–O08/S01–S10/roles/conditions/exclusions và mapping lịch sử. Source MD hash cb11dfbe...8f97, JSON f2e6df26...ed83b. Proposal chuẩn bị e98ea06f...4d2c; actual pending hash **543ddd61aa0b1527babe8c6adcb122c5cb2157f30d542c91d1de6fa5407207df**, input343aad54...e1cad. Hash staging khác vì metadata/audit at được sinh mới; full actual payload/hash và83binding đã kiểm, không nới guard.

Dry-run trên copy không ghi; POST semantic-checkpoint thật200 duy nhất1lần. Actor giải từ get_current_actor/require_permission mặc định development đang cấu hình, không synthetic actor/token/dependency override, không phải human SSO. New DB session/rebuild/Studio GET và tải MD/JSON200 exact hashes; enforced auth không session401. Browser mở deep link chuyển SSO: UI_LIVE_NOT_RUN cho tài khoản người dùng. Không tự gửi review decision.

Actual persisted tables/facts/context_graph/retrieval_units trước-sau stage giữ hash; chỉ semantic_annotations và source_policy pending thay đổi. Draft artifact392facts chưa hiệu lực, DB facts0/index revisions26/chunks56 và mọi binding/collection/active pointers/epoch không đổi. Không semantic_effective hoặc snapshot active, không publication/RAG benchmark/E2E RAG PASS.

## Mã nguồn và kiểm chứng

Không sửa mã nguồn runtime/tests repo/standard. Chỉ helper private trong backend/storage/context557 và báo cáo/memory theo workflow. Original552/553/555 và báo cáo556 giữ manifest.

Focused7file158PASS+23subtests (exit0); artifact probes cuối6PASS (exit0),83binding. Probe đầu5PASS/1FAIL vì truyền SimpleNamespace thay NoteScope, sửa input helper đúng contract; giữ cả XML. FE21PASS, npm build gồm Vite+tsc --noEmit PASS, Ruff4/Biome6LF PASS. Full một lần2429PASS/18FAIL/17SKIP/23subtests, exit1/447,46s: exact mọi ID/status/cause nền556 lịch sử,0added/removed/change/newfailure. Không gọi full PASS.

Lỗi helper được ghi commands: bootstrap import order cycle trước writes; helper sau POST200 so dry-run envelope có timestamp khác nên dừng, không resend; readback đầu so Python projection với persisted JSON thay vì so stored trước-sau, đã sửa phép kiểm và full integrity guard giữ nguyên. Không sửa app/checksum để che lỗi. Một lệnh chẩn đoán cú pháp không thực thi, không ảnh hưởng DB.

## Dọn dẹp và bàn giao

Test trong DB nonce/comment riêng, LocalStorage riêng, MinIO/Qdrant/Redis127.0.0.1:1, migrate/seed=false. DB test đã drop và xác nhận vắng. Runtime mới context548-runtime-f955f82ab0f0 còn491file/7892907byte,0links/0tracked/0process: guarded Remove-Item bị automatic approval review `blocked by policy`; không bypass, không chạm các thư mục cũ đã chặn. Checkpoint/canonical/audit giữ để đọc lại.

Người dùng đăng nhập, mở đúng source/revision, xem12quan hệ/18issue và từng evidence, chọn xác nhận hoặc yêu cầu sửa khi cần. Không tự approval/apply/publish/index/commit/push/deploy/migration/config/model changes.

[Review ready](../bao_cao/context557/REVIEW_READY.md), [revision](../bao_cao/context557/REVISION_CREATION_REPORT.md), [validation](../bao_cao/context557/VALIDATION_REPORT.md), [receipt](../bao_cao/context557/staging-receipt.json).
