# Phiên #426 — Ổn định ModelOps đa provider

Ngày: 2026-10-13. Yêu cầu: rà soát và sửa `/models` cho nhiều provider/model; giữ công việc backup tạm dừng.

## Kết quả và quyết định kiến trúc

Luồng kiểm tra model dùng vai trò đã khai báo thay vì suy đoán endpoint từ tên. Kết quả phân biệt kiểm chứng inference, danh mục OCR và health dịch vụ; HTTP200 một mình không chứng minh model chạy được. Model ID, provider và endpoint được giữ theo cấu hình; không fallback sang model khác để làm test thành công.

Probe Chat bắt đầu32 tokens, chỉ tăng một lần tới256 khi response hợp lệ nhưng bị cắt trước phần trả lời. Thương lượng tham số chỉ dựa trên lỗi HTTP400 cụ thể và vẫn có giới hạn số request. Runtime không tự tăng ngân sách hoặc phát lại câu trả lời. Suy luận nội bộ không được dùng làm nội dung trả lời.

Probe lấy khóa từ bảng relational trước, tôn trọng trạng thái/quota/cooldown; nhóm khóa không khả dụng không rơi về primary secret cũ. Đây là lựa chọn chỉ đọc, không xoay khóa hay ghi health/quota trong các diagnostic live của phiên này. API test thông thường chỉ lưu observations không chứa khóa, gắn đúng provider/model/endpoint.

Batch giới hạn hai lượt đồng thời và120 giây kể cả thời gian đợi; từng Chat probe có deadline theo provider. 401/403 là lỗi xác thực,400 là request bị từ chối,404 là không tìm thấy,402/410/429/503 có trạng thái riêng; timeout/protocol/budget không bị gán404.

## Thay đổi Backend

- `providers/chat_contract.py`, `services/chat_probe.py`: bounded retry empty+length, lỗi ngân sách riêng, status/deadline/elapsed thực, thương lượng unsupported temperature value/parameter, kiểm tra usage object.
- `services/capability_probe.py` mới: embeddings cần vector số hữu hạn không rỗng, rerank cần index/score hợp lệ, OCR catalogue exact-ID; Gemini native embedding/catalogue, Cloudflare REST embedding/rerank và OpenAI-compatible transports. Vai trò chưa hỗ trợ báo rõ, không giả thành công.
- `services/probe_credentials.py` mới: khóa relational có ưu tiên, trạng thái khả dụng; không dùng legacy secret khi toàn nhóm đã vô hiệu hóa.
- `providers/anthropic_adapter.py` mới: Claude native dùng Messages và headers Anthropic. Chat qua gateway phải chọn Custom, không gửi OpenAI protocol tới Anthropic native. Stream adapter này hiện buffered, không cam kết native SSE.
- `providers/gemini_adapter.py`: tôn trọng Base URL và model resource, bỏ đổi `gemini-flash-latest` ngầm, không tự nâng maxOutputTokens theo tên, không đưa thought vào đáp án, dùng khóa trong header.
- `providers/mistral_adapter.py`: explicit stream=false và shared validated completion contract.
- `providers/cloudflare_adapter.py`: thiếu credential/account báo lỗi thay vì fabricated response; reject error body/empty output, không ước lượng token như số đo thực.
- `providers/__init__.py`: custom/vLLM/TEI cần endpoint rõ ràng; không append `/v1` vào đường dẫn gateway tùy chỉnh đã có; Claude native adapter riêng.
- `services/provider_service.py`, `services/chat_capabilities.py`: gỡ các nhánh probe cũ suy đoán tên/HTTP200/mock-key bypass; DB outage báo503 thay vì catalogue trống. Lưu vai trò per-model, sửa primary khi xóa model, quan sát connection latency thực thay cho95/105/110ms cố định. UUID provider tránh trùng khi tạo cùng giây và phù hợp độ dài DB36. Snapshot endpoint/type/timeout trước probe, observations cập nhật row-lock giữ cấu hình khác.
- `schemas.py`, `router.py`, `service.py`: DTO vai trò, scope, mã lỗi, dimension; validate Base URL HTTP/HTTPS không nhúng credentials/query/fragment, model IDs trim/dedup có giới hạn100 ký tự, timeout5–120 giây.
- `services/model_catalog_service.py`: model capability khai báo ưu tiên legacy heuristic trong danh sách lựa chọn; dimension lấy từ kết quả đã kiểm chứng và resolver đọc metadata mới.
- `services/chat_routes.py`, `assistants/model_readiness.py`: runtime/readiness tôn trọng vai trò khai báo; thêm Ollama/Ollama Cloud vào nhóm Chat. Không gọi embedding/reranker như Chat chỉ vì alias có dạng bất kỳ.

## Thay đổi Frontend

- `add-custom-model-dialog.tsx`: chọn rõ Chat/Embedding/Reranker/OCR, giữ exact ID; phản hồi muộn bị bỏ qua sau đổi ID/role/đóng dialog. Lưu bất đồng bộ, chỉ đóng khi thành công; nếu lưu model được nhưng đặt mặc định lỗi thì báo đúng trạng thái. Tái sử dụng ResponsiveDialog, Select/Switch/Button; body cuộn riêng, footer truy cập được trên mobile.
- `models-grid.tsx`, `probe-result.ts`: trạng thái theo DTO không parse nội dung lỗi để đoán404; phân biệt catalogue/health với inference; thêm sửa vai trò model đã có. Grid/filter dùng metadata/default đã khai báo. Bỏ gợi ý model tĩnh cho Custom/vLLM/TEI để không gợi ý alias sai gateway.
- `provider-detail-page.tsx`, `modelops-page.tsx`: lưu và refetch trước đặt mặc định; detail loại kết quả test khi config thay đổi, chặn test single/bulk chồng nhau, route keyed theo provider. Giữ embedding dimension khi sửa metadata mà chưa test lại. Lỗi tải catalogue không mô tả như provider bị xóa.
- `provider-detail-header.tsx`: latency chưa đo hiển thị “Chưa đo”.
- `types/modelops.ts`, `services/modelops-api.ts`, route detail: DTO thống nhất, truyền probe role và capability metadata, giữ lỗi API thực; malformed provider catalogue không bị biến thành danh sách rỗng.

## Kiểm thử

Regression ban đầu:7 fail/4 pass đúng các lỗi budget/probe status/Gemini đổi model/khóa authoritative. Sau sửa, các test cũ dựa vào production mock được thay bằng HTTP fixtures có ca lỗi; không khôi phục fabricated responses để làm test xanh.

- Focused final:118 pass,77.39s (`pytest426_focus_delivery.log`), gồm ModelOps/probe/contracts/runtime route/RAG ModelOps/key rotation.
- PostgreSQL thật opt-in:1 pass,0.89s; tạo provider UUID thử, roundtrip role/dimension17, giữ capability khi lưu observation, xóa primary và clear list; outer rollback và readback xác nhận không còn fixture.
- Frontend:5 tests trạng thái/capability đạt; Biome10 file đạt; Vite5112 modules + TypeScript đạt, build cuối5.46s. Full FE lint vẫn13 lỗi baseline schema/format ngoài phạm vi, không sửa lan.
- Ruff toàn Backend đạt; một warning quyền đọc thư mục storage cũ, không có lỗi source.
- Full gate mã chốt:1148 pass/11 baseline fail/12 skip,191.47s (`pytest426_final_gate.log`); không có failure mới ở ModelOps/adapters/runtime role. Các11 baseline thuộc consulting export, publishing/GC/canary, reconciliation, session-cookie auth và universal tools. Fresh basetemp không còn38 lỗi quyền temp của lượt trước; Windows asyncpg teardown còn warning cũ.

### Kiểm chứng provider thật

Diagnostic sử dụng prompt ngắn hoặc dữ liệu `ping`, đọc cấu hình/khóa DB trong bộ nhớ; không gửi corpus, xuất secrets, lưu model mới hay đổi policy.

| Provider/model | Kiểm chứng | Kết quả |
| --- | --- | --- |
| qnu-9router `gh/gpt-5.4-mini` | Chat, exact alias | Thành công, served `gpt-5.4-mini`, khoảng3002ms |
| qnu-9router `gh/gpt-6-luna[1m]` | Chat, exact alias | Thành công, served `gpt-6-luna`, khoảng1537ms |
| qnu-9router `ollama/gpt-oss:120b` | Chat với retry giới hạn | Thành công, served `gpt-oss:120b`, khoảng3440ms |
| AI server `bge-m3` | Vector thực | Thành công HTTP200, khoảng238ms |
| AI server `bge-reranker-v2-m3` | Rerank thực | Thành công HTTP200, khoảng86ms |
| Gemini `gemini-2.5-flash` | Model đã cấu hình trong DB | Thành công, đúng served model, khoảng1491ms |

Kết nối AI server bị chặn trong sandbox; kiểm tra chỉ đọc ngoài sandbox HTTP200 và probes thật đều đạt. Không kết luận server lỗi từ giới hạn của môi trường công cụ.

## Hướng dẫn sử dụng và giới hạn

Khởi động lại Backend và worker để nhận adapters mới; tải lại Frontend. Chọn đúng provider: Claude native cho API Anthropic, Custom cho gateway tương thích OpenAI. Thêm/sửa model giữ nguyên alias/prefix và chọn vai trò; bấm Kiểm tra rồi Lưu. Với model embedding mới, lần test thành công cung cấp dimension để dùng cho kho tri thức. Nút sửa bên từng card cập nhật vai trò mà không xóa model.

Không cần reset DB/migration; metadata mới nằm trong JSONB existing. Không đổi primary/fallback, thêm model thật, publish/reembed, restart dịch vụ thay người dùng, reset DB hay tiếp tục backup. Thành công probe không thay thế kiểm thử chất lượng chatbot hoặc tải thật. Native Anthropic/Mistral/Cloudflare và một số loại lỗi được kiểm chứng bằng HTTP fixtures, không tuyên bố đã gọi live mọi provider/model. OCR health/catalogue không chứng minh bóc tách; UI đăng nhập/mobile/dark chưa nghiệm thu bằng browser.

Nguồn protocol: [Gemini generateContent](https://ai.google.dev/api/generate-content), [OpenAI Chat](https://developers.openai.com/api/reference/resources/chat), [Anthropic Models](https://platform.claude.com/docs/en/api/models/list). Quyết định triển khai dựa trên contract và phản hồi; không hardcode tên model để quyết định transport.

Bài học: kiểm tra danh mục, xác thực khóa, đúng vai trò và đầu ra hợp lệ là những bằng chứng khác nhau. Giữ contract riêng cho native providers và dùng lỗi có cấu trúc để tránh “model chết” giả khi budget, account hoặc mạng gặp vấn đề.
