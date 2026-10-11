# Phiên #345 — Review khôi phục Studio OCR và RAG/DAG

## Phạm vi

Review read-only production sau phiên #344. Sử dụng clean-code, ingestion, RAG và admin-frontend-design để đối chiếu contract/provenance/trạng thái FE–BE. Không sửa mã nghiệp vụ, qnu-sso, migrations, credentials; không reset DB/restart/inference thật. Chỉ cập nhật nhật ký theo quy định.

## Kết luận

Đã có API Studio/image/reparse theo snapshot độc lập và Paddle adapter lưu dimensions/blocks, phân tách layout/text confidence. Tuy nhiên chưa thể nghiệm thu luồng khôi phục hoàn chỉnh; báo cáo #344 mô tả mức hoàn thành cao hơn bằng chứng code hiện tại.

## Findings OCR/Studio

1. **P1 — Tọa độ FE không khớp contract**. `document-studio-workspace.tsx:257` đọc `coordinates.x/y`, nhưng Paddle adapter trả `left/top` theo normalized_percent. Vì vậy vị trí về mặc định 10%, dù width/height được nhận. Mapper vẫn dùng khổ 800/1131 và heuristic phân loại/điều chỉnh/xóa vùng, không bảo toàn chính xác bbox/label của backend. Canvas không khôi phục được tọa độ đã mất ở mapper. Cần dùng coordinate_system rõ ràng, dimensions thật; không sửa bbox bằng heuristic từ vựng.
2. **P1 — Duyệt sai revision và trạng thái thành công giả**. Workspace dòng 621–640 chọn `revs[0]` thay vì revision đang hiển thị; update tạo revision mới nhưng response bị bỏ, review vẫn dùng ID cũ. Dòng 672 ép status/indexStatus ready; progress timer mô tả embedding/Qdrant dù nhánh ADR-012 chỉ save/review, không build/publish. Cần pin displayed revision, dùng response revision mới, lấy trạng thái server và tách save/review khỏi index/publish.
3. **P1 — Reparse không có khóa chống trùng thực sự**. `source_ingestion_service.py:803` SELECT extracting/queued rồi OCR ngay; chỉ tạo revision tại dòng 959, không persist trạng thái đang chạy hay khóa binding. Hai request có thể cùng qua kiểm tra, OCR trùng và cùng chọn revision_no; unique index khiến một request lỗi thay vì 409 trước OCR. Extraction chạy trong HTTP request, không durable job; lỗi OCR không được lưu revision thất bại riêng. Cần atomic claim theo binding và durable job, cùng cơ chế giải phóng/recovery.
4. **P2 — Hiệu đính mất manifest khung**. Dòng 475 normalize chỉ từ Markdown, dòng 499 ghi đè manifest; dimensions/blocks/has_tables không được bảo toàn. Probe không ghi dữ liệu xác nhận manifest trước có blocks/dimensions, sau chỉ còn page/chars. Cần bảo toàn layout của snapshot theo trang và đánh dấu text alignment cũ khi chỉnh sửa, không tự tạo bbox mới.
5. **P2 — Bản chờ duyệt bị che bởi bản active**. `source-detail-page.tsx:111` và Studio service mặc định ưu tiên active_source_revision. Sau reparse warning, bản active cũ vẫn tồn tại nên màn hình tiếp tục hiển thị/duyệt bản cũ; lịch sử không có lựa chọn revision. Cần selector/deep link bản sửa đổi với candidate khác published/active.
6. **P2 — Confidence/layout refresh không trung thực**. Mapper dòng 310–318 bỏ layout_confidence/text_confidence/reading_order và dùng content_snippet thay vì toàn vùng; Inspector fallback về generic confidence. `handleRescanLayout` nhánh Knowledge chỉ GET Studio, không phân tích lại nhưng toast thông báo đã tính lại khung. Cần DTO typed bảo toàn metadata và đổi nhãn thành tải lại dữ liệu; bóc tách lại phải là thao tác riêng có chủ đích.

Lưu ý bổ sung: ảnh snapshot được trả `Cache-Control: public` dù endpoint yêu cầu quyền xem. Cần đánh giá private cache/vary và immutable revision URL; không coi authenticated image là tài nguyên công khai.

## RAG/DAG nên xử lý tiếp

- **Ưu tiên 1 — Scope xuyên suốt**: WorkflowContext chưa có workspace_id; RAGAnswer tạo AskRequest không truyền workspace nên mặc định workspace_qnu. RAG `_generate_with_fallback` không truyền tenant_id cho hai LLMGenerateRequest nên ModelOps nhận qnu-default. Cần scope actor → run/checkpoint/resume → RAG/ModelOps nhất quán, test tenant/workspace khác mặc định.
- **Ưu tiên 2 — Provider policy**: `llm_generate_node.py:64` chỉ lấy provider từ config node, không dùng policy trợ lý; temperature/max_tokens cũng chưa có thứ tự override nhất quán. Cần thống nhất resolver với RAG node, pin provider/model được chọn và trace đầy đủ, không hardcode.
- **Ưu tiên 3 — Failover/error semantics**: RAG service dòng 437/458 catch mọi exception, rồi dòng 465 trả trích đoạn như đáp án bình thường khi ModelOps không hoạt động. Cần phân biệt no-answer (thiếu chứng cứ) với provider unavailable (lỗi inference); không nuốt lỗi permission/quota/config thành answered. Nếu cần extractive mode phải cấu hình rõ và báo degraded/source mode, không fallback im lặng.

Hai điểm join/routed inputs sửa ở #343 vẫn có regression tests đạt, không kết luận toàn DAG đã hoàn thiện.

## Kiểm chứng

- Pytest source page provenance, Paddle adapter, source ingestion và DAG routing: **28 passed**.
- Ruff ba tệp backend OCR/source liên quan: đạt.
- Frontend `npm run build` (Vite + TypeScript): exit 0.
- Probe manifest thuần hàm tái hiện mất blocks/dimensions khi hiệu đính.
- Chưa chạy browser OCR/reparse/save-review E2E hoặc gọi AI server trong phiên review này. Tests hiện có không bao phủ concurrency reparse, FE coordinate mapping, chọn/duyệt revision mới; build/test pass không thay thế các ca đó.

## Đề xuất thứ tự

Sửa OCR findings 1–3 trước, sau đó 4–6 trong cùng đợt nối contract; test FE–BE scan hai trang, edit → warning → approve đúng revision, reparse đồng thời, lỗi OCR giữ bản đang phục vụ. Tiếp theo sửa scope/provider/failover RAG/DAG; không cần thay kiến trúc hybrid retrieval hay viết lại toàn pipeline.
