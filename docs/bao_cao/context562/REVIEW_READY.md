# Context562 — Bàn giao phân luồng hội thoại

**ROUTING_VERIFIED — LIVE_KNOWLEDGE_E2E_BLOCKED — CLEANUP_PARTIAL**

Đã triển khai prompt Hybrid Intent Routing cùng các bổ sung thống nhất; số phiên đổi từ 559 sang 562 để giữ lịch sử trước đó.

| Mục tiêu | Kết luận / bằng chứng |
|---|---|
| Xin chào, cảm ơn | Đã sửa; ASGI thật, Sandbox, chat public và widget nhúng chạy đạt |
| Social không tốn model/retrieval | Hai lượt handler thật xác nhận 0 model/embedding/reranker/retrieval |
| Mixed không thành SOCIAL | Corpus trọng yếu đạt; lượt Knowledge thật đi tới evidence rồi bị 409, không giả trả lời xã giao |
| Giữ chủ đề qua cảm ơn/chào | 20 gold scenarios, history DB tests đạt; Qwen thật có thanks→môn tự chọn đạt |
| Ngành, mã, năm, năm học, phủ định | Typed referents và negative tests; năm hiện tại ưu tiên, mã có số 0 đầu giữ literal |
| Tham chiếu mơ hồ | Qwen thật và tests hỏi làm rõ; không lấy lời assistant làm source facts |
| Tách phiên | Backend ownership/capability tests; UI A/B và reload xác minh hai server IDs riêng |
| Debug | Chỉ quyền canonical ai.access.admin; public không trả full intent trace |
| Legacy dialogue acts | explain/reformat/recheck/filter giữ; focused và toàn bộ IDs cũ không đổi trạng thái |
| Provider thật | 3 Qwen resolver probes PASS, một call/ca, không fallback |
| Regression | 2666 PASS / 18 FAIL / 17 SKIP +23 subtests; exact 18 lỗi nền, 172 ID mới đều PASS |
| Frontend | 6 behavior tests, Biome 10 file LF, build/TypeScript PASS |
| Kho tri thức | Hash collection/binding/revision/index giữ nguyên; không tải lại hoặc xuất bản |

Chưa nghiệm thu chuỗi Knowledge→thanks→followup hoàn chỉnh với DOCX: lượt Knowledge thật trả `EVIDENCE_CONTEXT_MISSING`. Có probe độc lập chỉ ra packed fact thiếu canonical source row trong hàm đóng gói hiện có; full canonical closure đạt. Cần sửa và kiểm chứng evidence packing riêng, giữ nguyên source/hash/provenance guard. Không chuyển lỗi này thành “không có dữ liệu”.

DB test và 6 hội thoại test trong DB đã dọn; harness widget đã xóa. Runtime Storage 1185 file / 18422741 byte còn vì kiểm duyệt tự động chặn xóa đệ quy (“blocked by policy”). Không retry vượt chặn; private evidence được giữ để đối soát.

Client public tự tích hợp cần echo header `X-Conversation-Token` để tiếp tục phiên. Hook React và widget đã hỗ trợ; phiên cũ thiếu capability bắt đầu server context mới an toàn. Lịch sử local trình duyệt giữ capability theo đúng đoạn chat, không đưa nó vào Markdown export/URL/log/diagnostics.

Không commit/push/stage/reset/restart/deploy; không đổi model defaults, không reparse/index/approve/publish. Các thay đổi trước phiên được giữ nguyên.

Đọc [VALIDATION_REPORT](./VALIDATION_REPORT.md), [REGRESSION_IDS](./REGRESSION_IDS.md), [ROOT_CAUSE_REPORT](./ROOT_CAUSE_REPORT.md) và [USER_GUIDE](./USER_GUIDE.md) để xem kết quả thực tế và giới hạn.
