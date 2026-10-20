# Phiên562 — Hybrid Intent Routing và ngữ cảnh hội thoại

Ngày 2026-10-20. Người dùng cho triển khai prompt cùng đề nghị bổ sung. Dùng số 562 vì Context559–561 đã tồn tại. Không commit/push/deploy hoặc sửa nguồn tri thức.

## Thực hiện

Fast path toàn thông điệp; sáu intent; một structured call kết hợp resolver/rewrite qua ModelOps hiện hành khi cần. Giữ dialogue acts và input/policy/source guards. Lịch sử hữu ích đúng assistant/config, typed user referents, bảo vệ ngành/mã/năm/phủ định. Debug chỉ admin, continuation capability tách miền chữ ký và kiểm session ownership.

Tích hợp chat JSON/SSE, Sandbox, public chat và JS widget độc lập. Khôi phục session theo đúng đoạn chat, giữ qua reload ở public chat; widget xử lý SSE phân mảnh/UTF-8/error/truncation. Loading trung thực, không khẳng định RAG khi chưa chạy. Client tùy chỉnh cần echo continuation header.

Nhóm file: rag intent/resolver/service/evidence_model/schema; assistants router/history/chat/session; middleware CORS; conversations read authorization; frontend hooks/public chat/Sandbox/inspector/bubble/widget; ba bộ test backend/corpus và frontend route/widget tests. Unit workflow/history mocks cập nhật đúng repository calls, assertions giữ nguyên. Chi tiết tại [IMPLEMENTATION_REPORT](../bao_cao/context562/IMPLEMENTATION_REPORT.md).

## Kiểm chứng thực chạy

- Pytest qua runner isolation, DB nonce riêng, Storage tạm riêng; MinIO/Qdrant/Redis test ở loopback port không phục vụ, không auto migration/seed.
- Red 7 FAIL và ownership red 1 FAIL; focused 277 PASS, compatibility 36 PASS; Ruff 21 file PASS.
- Full đầu 24 FAIL; 5 mock cũ và 1 permission contract sửa đúng scope. Full cuối **2666 PASS / 18 FAIL / 17 SKIP +23 subtests**, exit 1. So Context561: 0 ID chung đổi trạng thái, 0 xóa, exact 18 ID/cause; 172 ID mới đều PASS.
- Frontend 6 behavior tests PASS, Biome 10 file LF PASS, build/TypeScript PASS. VM stream tests không được tính là browser E2E.
- ASGI thật greeting/thanks PASS, 0 model/embedding/reranker/retrieval, khoảng 142–230 ms. Ba Qwen resolver probes thật PASS, một call/ca, 0,7–1,9 giây; không đổi defaults/provider.
- Browser Sandbox/public/widget PASS cho social/meta. Public A/B, chọn lại A/reload: hai server IDs riêng, A giữ 3 lượt/B giữ 1 lượt. Widget hai lượt cùng session. DB xác minh rồi dọn đúng các test threads.
- Knowledge mixed live FAIL HTTP 409 `EVIDENCE_CONTEXT_MISSING`; không gọi chuỗi còn lại là PASS. Full canonical closure đạt, probe packed fact thiếu source row tái hiện cùng lỗi; chưa sửa retrieval/evidence packing ngoài scope routing.

## Bảo toàn và bàn giao

Hash toàn bộ 5 collection /23 binding /2 source revision /27 index revision giống trước/sau. Không reparse/reindex/approve/publish/restart/config writes. Giữ các sửa DOCX và memory có trước phiên.

DB test đã drop, 6 hội thoại test trong DB và trang harness tạm đã dọn. Evidence private ở `backend/storage/context562` giữ có chủ ý. Runtime `context548-runtime-c43bf3e4c096` còn 1185 file/18422741 byte vì auto approval review từ chối xóa đệ quy (“blocked by policy”); không retry qua công cụ khác hoặc tắt bảo vệ. CLEANUP_PARTIAL. Local browser QA history có thể còn để xem lại, server sessions đã xóa.

Trạng thái **ROUTING_VERIFIED / LIVE_KNOWLEDGE_E2E_BLOCKED**, không toàn hệ thống APPROVED. Bước sau trong scope riêng: regression cho evidence packing mang theo source row/dependency đầy đủ, tái hiện stack live và retest Knowledge E2E; không nạp lại tài liệu để che lỗi.

Báo cáo: [REVIEW_READY](../bao_cao/context562/REVIEW_READY.md), [VALIDATION](../bao_cao/context562/VALIDATION_REPORT.md), [đối chiếu IDs](../bao_cao/context562/REGRESSION_IDS.md).
