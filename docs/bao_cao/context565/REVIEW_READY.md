# Context565 — Bàn giao

Trạng thái: **SOURCE-GROUNDED NUMERIC E2E VERIFIED — NO NEW REGRESSION**. Full backend vẫn **FAIL**: 2747PASS/18FAIL/17SKIP+23subtestsPASS, exit1.18lỗi nền giữ nguyên exactID/cause;54testinstances mới PASS,0changed/removed.

| Câu hỏi nghiệm thu | Kết quả |
|---|---|
| Mã chữ-số/leading zero được nhận và kiểm source? | PASS; candidates khác identity đã xác minh |
| AM-0007 có nhầm AM-0070? | Không trong các ca đã kiểm; DB fact IDs/canonical row/column được audit riêng |
| Quota và recorded count có tách không? | PASS cùng năm, khác năm và qua follow-up đổi metric |
| Row identity có nhầm mã với tên? | PASS fixtures code/name đổi vị trí, code-only và source thực |
| Identity/metric có lọc trước LIMIT? | PASS SQL thật trong DB test,20 hàng khác đứng trước và2 nhãn legacy khác nhau |
| Temporal decision đúng đơn vị/năm/trạng thái? | PASS cases đủ bằng chứng và negative unknown/wrong unit/year |
| Reviewed/materialized Fact proof E2E? | PASS selected fact → canonical row/refs → pack → projection → exact citation |
| Conversation có giữ entity/metric không? | PASS sau sửa current constraint thắng stale rewrite; batch RED vẫn được giữ |
| Có thay publication/source/index/config? | Không; seals trước/sau khớp toàn bộ các bảng được kiểm |
| Focused /Ruff | 253 PASS + orchestration-compat70PASS (có tests trùng);54testinstances mới; Ruff17files PASS |
| Full regression | 2747PASS/18FAIL/17SKIP+23subtestsPASS;exit1;no new regression theo exactIDs/causes |
| Benchmark RAG85% đã đạt? | **NOT RUN**. Có thể chuẩn bị bộ benchmark riêng; E2E hiện tại không chứng minh85% hoặc production readiness |

App/upstream ASGI cuối13/13 và backend TCP8/8 đạt. Scalar numeric answer không cần gọi LLM/dense/reranker; Qwen chỉ dùng khi resolve follow-up. Prose case riêng đã thực gọi embedding/Qdrant/reranker/LLM, final response từ verified canonical fallback.

TCP bổ sung2/2 scalar requests trên mã chốt: public không có trace nội bộ, debug có quyền vẫn đọc được trace. Không thêm LLMcall. Tổng audit23responses đã đối chiếu độc lập exact row/column/value và citation spans.

Một assertion test cũ được đổi theo contract mới: bare `Số lượng` giữ nguyên/unknown, không tạo `Chỉ tiêu`; fixture/value giữ nguyên và thêm negative chống relabel sai. Không đổi test expectation để chấp nhận đáp án sai.

Giới hạn: read-only compatibility cần exact row/column locator; format legacy không đủ căn cứ bị từ chối an toàn. Chưa kiểm mọi loại tài liệu, source đa ngôn ngữ hoặc tải lớn. Không model/semantic approval tự động, không bypass guard hay nâng ngân sách.

[Nguyên nhân](ROOT_CAUSE_REPORT.md) · [Entity](ENTITY_RESOLUTION_DESIGN.md) · [Metric](METRIC_ROLE_DESIGN.md) · [Implementation](IMPLEMENTATION_REPORT.md) · [Tests](VALIDATION_REPORT.md) · [Live E2E](LIVE_RAG_E2E_REPORT.md) · [Exact IDs](REGRESSION_IDS.md).

Không commit/push/deploy/restart/reindex/republish. Dữ liệu source, thay đổi chưa commit của người dùng và các file Context564 được giữ.

DB test đã dọn; xóa runtime Storage riêng bị kiểm duyệt tự động chặn **blocked by policy**. Giữ runtime, không bypass hoặc đổi cách xóa; evidence và usage audit giữ lại.
