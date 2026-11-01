# Phiên793 — Review độc lập FE ModelOps792

Ngày01/11/2026. Người dùng yêu cầu xem lại phần FE vừa vibe theo prompt791. Chỉ review và kiểm tra, không sửa application FE/BE hoặc cấu hình live.

## Kết luận

Luồng tạo model không bắt limits, PATCH omission khi đổi nhãn/timeout, import metadata và phân biệt declared/provisional đã đi đúng hướng. Tuy nhiên còn bốn P2, đã tái hiện qua sáu probe độc lập ở tmp:

1. **Consumer chưa được cấp dữ liệu ngân sách từ API catalog.** `frontendV1/src/features/modelops/types.ts:164–169` chỉ thêm trường tùy chọn vào CatalogItem; `useCatalogQuery` vẫn GET `/modelops/catalog`. `backendV1/qnu/domains/modelops/router.py::catalog` và schema CatalogItem chỉ trả id/name/model_name/capabilities/default_capabilities. Consumer ở Assistant/Compiler/OCR/Index nhận thiếu toàn bộ status/budget/dimension. `ConsumerModelBudgetNotice` trả null cho missing_info; không có cảnh báo provisional/blocked dù model thực đang blocked. Cần bổ sung projection catalog có kiểm quyền ở BE rồi kiểm bằng response thật, và resolve cả model mặc định khi người dùng để trống lựa chọn. Không gọi admin-only detail cho user thiếu quyền.
2. **Đường lưu form có thể xóa declaration không xác nhận.** `provider-form-dialog.tsx:145–151` gửi ngay patch từ buildProviderPatch. Với model có giới hạn, mở Nâng cao rồi xóa trắng ba trường context/input/output và Lưu ⇒ mutation `{token_limits:null}` mà không qua ConfirmDialog. Nút xóa riêng có xác nhận nhưng chưa bao phủ đường này. Cần đưa cả PATCH null từ form qua một bước xác nhận trước request, bảo toàn các thay đổi khác.
3. **Classifier bỏ lọt mã lỗi BE thật.** `capacity-badge.tsx:502–525` không nhận `chat_output_truncated`; nhánh invalid_response không khớp `provider_response_invalid`/`chat_response_invalid`. Cả ba rơi vào general. Diagnostics adapter thật phát các mã này, nhiều trường hợp detail đã rút gọn thành lỗi hợp đồng nên UI mất thông tin cần xử lý. Tests792 dùng provider_response_malformed (không phải mã được adapter này phát). Cần bảng mã tương ứng BE và test request/probe contract thực tế; không suy mọi400/422 là token.
4. **Nguồn từng giới hạn bị ghi sai ở phần khai báo.** `provider-detail.tsx:220–225` dùng capacity_basis chung cho max_input và các trường khác. Sau sync server context/output, input thủ công giữ source operator trong operational_budgets nhưng phần "Giới hạn đã biết" lại ghi Server công bố; phần ngân sách ngay dưới ghi Khai báo thủ công cho cùng số. Cần dùng nguồn từng trường có căn cứ; legacy không đủ nguồn phải ghi trung thực mức thông tin đang có.

Không ghi P1 hoặc kết luận lộ secret. Không xem cảnh báo kích thước bundle hiện hữu là regression trong phiên này.

## Kiểm chứng thực chạy

Cwd frontendV1:

- 10 file Vitest ModelOps theo danh sách792: **53PASS**,exit0,24.90s.
- `npm run build` (Vite + TypeScript): **PASS**,exit0; Vite11.29s, còn warning chunk>500kB.
- Biome trên21file sửa/thêm: **PASS**,exit0,không auto-fix.
- `npm test -- --run --reporter=json --outputFile=../tmp/review793-full-vitest.json`: **611PASS26FAIL**,exit1.
- So exact IDs với log790: **0 mới, 7 đã xanh**, cả7 thuộc test_connection_review705. 26 còn lại thuộc8file: final-functions-ui682,knowledge-actions708,lifecycle-operations-ui678,maintenance-evaluation-ui679,navigation-scope692,rag-ui674,sidebar-navigation691,workspace-sidebar689. Danh sách nhóm lỗi trong nhật ký792 không khớp kết quả thật; giữ lịch sử và ghi đính chính ở đây.
- Probe riêng qua Vitest/jsdom: **6/6 tái hiện hành vi lỗi**,exit0,5.88s. Đây là assertion xác nhận khuyết điểm, không phải acceptance PASS. Lần đầu5probe chạy được/1probe thiếu ResizeObserver của jsdom; thêm shim trong probe tmp rồi chạy lại. Không sửa sản phẩm để đổi kết quả.
- `git diff --check -- frontendV1`:PASS; routeTree.gen.ts không đổi. Visual desktop/mobile/light/dark và live inference:NOT RUN.

Logs: `tmp/review793-build.log`, `tmp/review793-full-vitest.log/json`, `tmp/review793-failure-comparison.json`, `tmp/review793-probes.log`, `tmp/review793-probes-final.log`. Probe/config giữ trong `frontendV1/tmp/` (Git ignored), không thêm test hoặc source vào diff ứng dụng.

## Bàn giao

Chưa fix bốn P2; cần nối catalog BE–FE trước, sau đó confirmation, mapping lỗi thật và provenance UI. Giữ nguyên DB/key/quota/ModelOps/corpus/index/publication/phiên93faa11f0caf. Không restart hoặc gọi model thật, không gửi lại lượt uncertain789. Full FE vẫn FAIL dù không thêm ID lỗi nền mới.
