# Prompt triển khai FE ModelOps: thêm model không bắt nhập giới hạn token

Triển khai trực tiếp trong `frontendV1/` của QNU AI Platform. Backend đã bổ sung hợp đồng ở phiên791 và kiểm tra API/DB cô lập; chỉ sửa FE và test FE, không sửa backend, DB hoặc cấu hình phiên E2E đang chạy. Đọc hợp đồng backend thực tế trước khi bắt đầu; không tự tạo endpoint giả khi chưa có.

## Mục tiêu

Người dùng thêm nhà cung cấp bằng tên, URL, API key được bảo vệ; chọn/nhập model và chức năng. Không cần biết context/input/output. Model không công bố thông số vẫn được lưu và sử dụng ngân sách vận hành tạm tính do backend quyết định. Phải phân biệt thông số model với ngân sách ứng dụng; không hiển thị đã xác minh khi chưa có bằng chứng.

## Đọc trước và giới hạn phạm vi

- Đọc `AGENTS.md`, `frontendV1/AGENTS.md`, `docs/memory/PROJECT_CONTEXT.md`, Git status/diff và các file thực tế. Bảo toàn thay đổi chưa commit, kể cả thay đổi BE đang đồng thời thực hiện.
- Áp dụng skill `qnu-clean-code-architect`, `qnu-frontend-architect`, `qnu-modelops-resilience` và `.agents/rules/ui-standards.md`.
- Tìm code trong `frontendV1/src/features/modelops/`: connections/model-form, import-models-dialog, connection-form, model-test-modal, provider-form-dialog, capacity-patch, capacity-badge, diagnostics-panel, types, schemas, requests và queries. Đọc các consumer assistant/compiler đang dùng dữ liệu capacity.
- Giữ React/TypeScript/TanStack Query/Form và primitives hiện có, semantic tokens, master/detail/deep link. Không thêm UI library; không sửa `routeTree.gen.ts`.
- Không restart/cleanup/init/reindex/publish/gọi model thật/đổi quota hoặc key. Secrets vẫn gửi qua API ModelOps, không log hay lưu browser storage. Ngoại lệ E2E bootstrap không được mở rộng thành runtime `.env` fallback.

## Hợp đồng BE phải dùng

Prefix `/platform/v1alpha1`. Các endpoint hiện có:

1. `POST /modelops/connections`: tạo nhà cung cấp; lưu khóa qua endpoint keys hiện có.
2. `POST /modelops/connections/{connection_id}/test` hoặc discovery hiện có: nhận danh sách model và `model_metadata`. Đây là thông số server công bố, không chứng minh inference thành công.
3. `POST /modelops/connections/{connection_id}/models`: `{model_name, capabilities}` là đủ cho phần giới hạn token. `token_limits` và `embedding_dimension` tùy chọn; `discovery_check_id` tùy chọn. Không gửi đồng thời thông số tay với discovery_check_id. Khi không gửi các trường tay/id, BE có thể lấy snapshot discovery mới nhất còn hợp lệ, đúng nhà cung cấp/model. Không có snapshot phù hợp vẫn được tạo, không buộc discovery thành công.
4. `GET /modelops/connections/{id}/models`, provider detail/list: trả thông số thật và trường bổ sung `operational_budgets`.
5. `PATCH /modelops/providers/{model_id}`: bỏ hẳn `token_limits` khi không chỉnh; `token_limits: null` nghĩa là chủ động xóa khai báo để dùng ngân sách tự động. Đổi tên/timeout không được tự xóa giới hạn đã lưu. Giữ API sync-capacity hiện có cho cập nhật thông số server có chủ đích, stale snapshot phải được lấy lại.

Thông số thật giữ nguyên:

```typescript
capacity_status: "unknown" | "configured" | "stale";
capacity_basis: "operator_configured" | "server_reported" | null;
token_limits: ModelTokenLimits | null;
```

Không đổi `capacity_status` thành configured chỉ vì có mặc định. Trường bổ sung:

```typescript
type BudgetSource = "operator_configured" | "server_reported" | "application_default";
type OperationalBudget = {
  version: "qnu.operational-budget/v1";
  status: "declared" | "provisional" | "blocked";
  token_limits: ModelTokenLimits | null;
  sources: Record<string, BudgetSource>;
  reason_code: string | null;
};
// ProviderResponse và ProviderSummaryItem
operational_budgets: Partial<Record<"chat" | "embedding" | "rerank" | "ocr", OperationalBudget>>;
```

Ví dụ model chat chưa công bố capacity: token_limits=null, capacity_status=unknown; operational_budgets.chat.status=provisional, token_limits.context_window_tokens=32768/max_output_tokens=4096, sources đều application_default. Các số này chỉ là chính sách BE v1. FE không hardcode chúng, không điền ngược vào form hoặc gửi lại như thông số thật.

BE vẫn chặn stale (`model_token_limits_stale`). Khi chưa có cách đếm token ảnh, OCR có thể blocked (`model_input_budget_unknown`); dimension embedding vẫn cần căn cứ đúng model. Không được giả thành đã sẵn sàng cho mọi chức năng.

## Giao diện cần hoàn thiện

1. Luồng mặc định gọn: nhà cung cấp → khóa → chọn model/chức năng → lưu. Các số context/input/output chuyển vào vùng “Nâng cao” thu gọn; không required trong chế độ thông thường. Cho nhập model tùy chỉnh khi discovery không hỗ trợ; giữ lỗi kết nối thật và khả năng sửa URL/key.
2. Hiển thị theo từng chức năng: “Dùng thông số đã khai báo”, “Đang dùng ngân sách tạm tính”, hoặc “Cần bổ sung thông tin”. Đối với thông số công bố, nói “Server công bố”; operator “Khai báo thủ công”. Không gộp thành badge “Đã kiểm chứng”.
3. Trong chi tiết nâng cao, phân biệt “Giới hạn đã biết của model” và “Ngân sách đang áp dụng”. Hiển thị ô chưa biết là “Chưa công bố”, không 0/unlimited. Đơn vị token, không ký tự. Mỗi trường lấy nhãn nguồn từ `sources` và giá trị từ BE.
4. Sửa tay là tùy chọn nâng cao; gửi PATCH chỉ các trường thực sự thay đổi. Khi người dùng chọn xóa khai báo, giải thích ngắn và dùng xác nhận hiện có trước PATCH null. Không xóa dữ liệu cấu hình khi chỉ đóng/mở form hoặc chỉnh nhãn.
5. Import nhiều model: mặc định dùng metadata server; chưa có metadata vẫn cho thêm bằng auto. Không mở dialog nhập capacity bắt buộc; không lấy limit của model khác hoặc đổi preferred provider/model.
6. Kiểm tra kết nối/model là hành động có trạng thái loading/success/failed/stale thật. Pass probe nhỏ chỉ chứng minh request mẫu; không sửa capacity/provisional thành verified. Quota/429, token budget, malformed response và timeout có thông báo riêng; không biến lỗi thành “không có dữ liệu”.
7. Rà consumer assistant/compiler: không chặn chỉ vì capacity_status=unknown nếu `operational_budgets[capability]` có declared/provisional; blocked phải hiển thị lý do. FE không tính ngân sách thay BE, không tự giảm output, cắt evidence hay retry model để qua bước. Nếu phiên server chưa có trường mới, hiện chưa có thông tin, không tự suy mặc định.
8. Một primary CTA; thao tác phụ của dòng/model gom vào một menu ⋯, không double-border/box trong box. Ẩn ID nội bộ, mã lỗi chỉ trong phần chi tiết phù hợp. Giữ 14px, responsive, dark mode, label/focus/keyboard và thông báo screen reader.

## Kiểm thử và nghiệm thu

- Test tạo model không token_limits; discovery chỉ có id; discovery đủ/thiếu metadata; các trạng thái declared/provisional/blocked/stale.
- Test model tùy chỉnh, validation giới hạn thật; partial values/unknown khác 0; không copy ngân sách tạm vào request.
- Test PATCH omission vs null, đổi tên/timeout giữ limits; không trộn discovery_check_id và manual values.
- Test server errors, quyền hạn và không rò API key. Mock đủ auth/query/scope provider hiện có, không nới guard để xanh test.
- Test consumer không chặn unknown+provisional; vẫn chặn stale/OCR thiếu image bound và giữ model selection.
- Chạy targeted Vitest, Biome file sửa, `npm run build`, E2E typecheck nếu chạm runner. Full frontend suite một lần cuối; báo đúng FAIL và exact IDs lỗi nền nếu còn, không retry hoặc đổi assertion để làm xanh.
- Kiểm tra giao diện desktop/mobile/light/dark nếu có công cụ; build không chứng minh layout đúng. Không giả PASS cho live chưa chạy.
- Cập nhật journal/index/WORK_LOG/PROJECT_CONTEXT/snapshot theo workflow; chọn số phiên chưa dùng, không ghi đè phiên 791 của BE.
- Bàn giao file sửa, hợp đồng request/response, kết quả thật và phần chưa kiểm. Không sửa backend hay kết luận toàn bộ workflow production đã đạt chỉ từ test FE.
