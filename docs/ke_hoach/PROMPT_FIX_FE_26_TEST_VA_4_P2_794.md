# Prompt sửa 26 test FE cũ và 4 lỗi P2 ModelOps

Bạn làm việc trong repo `D:/DuAnPhanMem/qnu-ai-platform`. Hãy trực tiếp điều tra, sửa và kiểm chứng cho đến khi hoàn tất phạm vi dưới đây. Không dừng ở kế hoạch hoặc báo đã sửa khi chưa chạy kiểm tra.

## 1. Mục tiêu và phạm vi

1. Sửa cả 4 P2 của FE ModelOps792 được review độc lập ở phiên793.
2. Sửa đủ 26 test FE đang FAIL trong 8 file, bảo toàn hành vi mà các test cần kiểm tra. Đây là 26 test thất bại, chưa đồng nghĩa với 26 lỗi sản phẩm độc lập; nhiều test có thể cùng lỗi fixture/context.
3. Đưa full suite `frontendV1` về không còn FAIL; giữ các test đang PASS và bổ sung regression thực chất cho 4 P2.
4. P2 catalog và nguồn dữ liệu có thể cần thay đổi nhỏ, có kiểm quyền ở `backendV1/`. Đây là phạm vi được phép của prompt; không cố chữa hợp đồng server chỉ bằng type hoặc mock ở FE.

Đọc `AGENTS.md`, AGENTS ở thư mục con, `docs/memory/PROJECT_CONTEXT.md`, Git status/diff và source thực tế. Giữ mọi thay đổi chưa commit của người dùng, bao gồm BE791/FE792. Áp dụng các skill clean-code, frontend, backend khi sửa BE và ModelOps của repo; tuân thủ `.agents/rules/ui-standards.md`, verification và workflow/memory. Không tự refactor lân cận.

Tài liệu bàn giao cần đối chiếu:

- `docs/nhat_ky/2026-11-01_phien_793_review_fe_modelops_tu_dong.md`.
- `docs/quy_trinh/V1_MODELOPS_NGAN_SACH_TU_DONG.md`.
- `docs/ke_hoach/PROMPT_FE_MODELOPS_TU_DONG_791.md`.

Chỉ chạy kiểm tra offline/fake HTTP/DB test riêng. Không restart, cleanup/init phiên E2E, deploy, Git push, reindex, publish, gọi model thật, sửa corpus/key/quota hoặc thay cấu hình ModelOps đang chạy. Giữ phiên `93faa11f0caf`, lịch sử benchmark và lượt uncertain789; không gửi lại inference chưa rõ kết quả. Không đọc/in secret hoặc đưa LLM key vào runtime `.env`.

## 2. Baseline đã kiểm chứng, phải tái xác minh

Phiên793 thực chạy:

- 10 file test ModelOps: 53 PASS.
- Build (Vite + TypeScript) và Biome trên 21 file: PASS.
- Full FE: **611 PASS, 26 FAIL**, exit 1. So exact IDs với phiên 790: không có ID FAIL mới, 7 test 705 đã xanh.
- Sáu probe riêng đã tái hiện 4 P2. Probe PASS nghĩa là xác nhận hành vi lỗi, không phải nghiệm thu tính năng.

Artifact tham khảo nếu còn: `tmp/review793-full-vitest.json`, `tmp/review793-failure-comparison.json`, `tmp/review793-probes-final.log`, `frontendV1/tmp/review793-probes.test.tsx`. Không phụ thuộc các file ignored này để hoàn thành; danh sách lỗi và tình huống đã nằm trong prompt.

Đừng dùng danh sách nhóm test lỗi trong nhật ký792 làm baseline: một số tên file được ghi sai. Chạy baseline hiện tại, lưu JSON/log mới riêng và so exact file+test name. Nếu mã đã thay đổi, ghi rõ khác biệt; không ghi đè log cũ hoặc mặc định mọi lỗi hiện tại đều là lỗi nền.

## 3. Sửa 4 P2 theo thứ tự sau

### P2-1 — Nối dữ liệu ngân sách thật từ catalog BE sang consumer FE

Source cần kiểm tra:

- `backendV1/qnu/domains/modelops/router.py::catalog`.
- `backendV1/qnu/domains/modelops/schemas.py::CatalogItem`.
- ModelOps capacity service/automatic, catalog service và provider payload.
- `frontendV1/src/features/modelops/types.ts`, requests/queries và capacity-badge.
- Consumer ở Assistant, Compiler/auto-review, OCR, Index và Defaults.

Hiện FE thêm trường optional vào type, nhưng `/modelops/catalog` chỉ trả id/name/model_name/capabilities/default_capabilities. Do đó consumer không nhận capacity/budget/dimension, helper trả missing_info rồi notice trả null. Chỉ sửa TypeScript hoặc truyền Provider giả trong test không giải quyết vấn đề.

Yêu cầu:

1. Bổ sung projection catalog additive, typed và an toàn chứa các trạng thái/giới hạn/dimension/ngân sách cần để consumer quyết định và hiển thị. Tái dùng logic BE791; không nhân bản phép tính hoặc hardcode giá trị mặc định ở FE.
2. Giữ kiểm tra membership/grant/capability/trạng thái active của model và nhà cung cấp. Model bị thu hồi, ngoài workspace hoặc bị tắt không được xuất hiện. Workspace_id từ client không chứng minh quyền.
3. Chỉ xuất các trường được phép; không dump extra_config, credential, cấu hình nội bộ hoặc URL có dữ liệu nhạy cảm. Không buộc user thường gọi API provider detail dành cho admin.
4. Consumer phải hiện đúng provisional/blocked/stale và lý do. Nếu server cũ thật sự thiếu metadata, hiện trạng thái chưa có thông tin phù hợp; không tự giả ready hoặc tự suy capacity.
5. Khi ô model để trống, xử lý model mặc định theo routing thực tế hiện có. Không chọn phần tử đầu tiên hoặc hiển thị một model khác với model backend sẽ dùng. Nếu chưa xác định được default, nói chưa xác định thay vì gắn trạng thái của model đoán.
6. Giữ lựa chọn preferred provider/model, contract request, quota và guard BE. Không cắt evidence hoặc tự giảm output để chạy qua bước.

Regression bắt buộc:

- Qua API thật và DB test riêng: catalog cho thành viên hợp lệ trả đủ dữ liệu; outsider/disabled/revoked không đọc được hoặc không được liệt kê.
- Test consumer với đúng response catalog nhận được, không chỉ test resolver bằng Provider tự dựng. Bao phủ chat provisional, chat stale/blocked, OCR thiếu image budget, embedding thiếu dimension và default selection.

### P2-2 — Xác nhận mọi đường xóa khai báo token

`frontendV1/src/features/modelops/provider-form-dialog.tsx` tạo patch bằng `buildProviderPatch` rồi gửi ngay. Với model đã có limits: mở Nâng cao, xóa trắng context/input/output, Lưu ⇒ `{token_limits:null}` được gửi mà không xác nhận. Nút Xóa riêng có ConfirmDialog nhưng chưa bao phủ đường Lưu.

Yêu cầu:

- Khi patch sẽ xóa token_limits, giữ pending patch và yêu cầu xác nhận trước bất kỳ HTTP mutation nào; có thể dùng chung một flow cho nút Xóa và form Save.
- Cancel phải không gửi request, giữ draft và các thay đổi khác. Confirm gửi đúng một request, bảo toàn những thay đổi tên/timeout/capability cùng patch; chặn double submit khi pending.
- Omit trường không sửa; không biến unknown/provisional thành declaration, không tự xóa embedding dimension. Khi chỉ đổi nhãn/timeout phải giữ nguyên limits đã lưu.
- Đổi model/endpoint vẫn giữ cơ chế vô hiệu hóa cấu hình cũ phía BE; không tự tái khai báo số cũ để né stale.

Regression: xóa từng trường/nhóm giới hạn rồi Save; explicit clear; cancel/confirm; pending/double-click; lỗi mutation giữ draft; rename/timeout đơn thuần; model unknown có ngân sách tạm. Dùng hành vi click/request payload thật của component, không chỉ helper.

### P2-3 — Map đúng mã lỗi backend đang phát

`capacity-badge.tsx::describeDiagnosticFailure` chưa nhận `chat_output_truncated`; `invalid_response` không khớp `provider_response_invalid` hoặc `chat_response_invalid`. Cả ba bị phân loại general. Test792 dùng mã malformed khác nên không bắt được lỗi.

Yêu cầu:

- Đọc adapter chat/diagnostics và các consumer error formatter thật. Xây mapping rõ ràng cho mã thực tế; tái dùng phần hợp lý, tránh thêm nhiều bộ mapping khác nhau.
- Phân biệt output bị cắt, input/context vượt ngân sách, lỗi JSON/schema, 429/quota, auth, unavailable và timeout/uncertain.
- `chat_output_truncated` nghĩa là đầu ra chưa đầy đủ; không khẳng định input vượt context hoặc tự suy giới hạn model. Một HTTP400/422 bất kỳ không được mặc định là lỗi token.
- `chat_provider_uncertain`/timeout phải giữ trạng thái chưa rõ kết quả và không tự gửi lại inference. Không biến lỗi provider thành no-answer hoặc không có dữ liệu.
- Detail công khai vẫn an toàn; không đưa raw upstream body, key hoặc prompt vào toast/log/DOM.

Regression: ít nhất ba mã đã nêu, các mã BE thực tế khác liên quan, HTTP422 không rõ nguyên nhân, HTTP200 nhưng finish_reason=length, malformed response, quota và timeout. Có test lấy kết quả từ decode/contract thực tế rồi đi qua UI; không chỉ tự đặt mã giả để assertion PASS.

### P2-4 — Hiển thị đúng nguồn từng giới hạn

`provider-detail.tsx::CapacityPanel` phần Giới hạn đã biết dùng capacity_basis chung cho từng dòng. Sau sync context/output từ server và giữ input do operator đặt, input bị gắn nhãn Server công bố; phần ngân sách bên dưới lại ghi Khai báo thủ công cho cùng giá trị.

Yêu cầu:

- Dùng provenance đã lưu theo từng trường; tận dụng source thực sự có trong operational_budgets hoặc bổ sung projection nguồn khai báo từ capacity service nếu cần. Không suy nguồn từ tên trường, tên model hay từ giá trị số.
- Phân biệt declaration với application_default: số tạm tính không được chép vào phần Giới hạn đã biết hoặc gửi lại thành khai báo tay.
- Legacy thiếu nguồn từng trường phải hiển thị trung thực mức thông tin hiện có, không tự nâng lên nguồn đã chứng minh.
- Giữ dữ liệu nguồn/provenance khi sync idempotent và khi patch các trường không liên quan.

Regression quan trọng: khai báo max_input=7000 thủ công → sync context/output từ discovery → mở UI và kiểm tra input vẫn ghi Khai báo thủ công, context/output ghi Server công bố; declaration chưa biết vẫn chưa biết. Kiểm cả API projection và DOM, không chỉ label helper.

## 4. Sửa đúng 26 test cũ trong 8 file

Đọc test, production tree và failure stack trước khi sửa. Thông tin nguyên nhân dưới đây là đầu mối từ793, không thay thế tái hiện hiện tại.

### A. `frontendV1/tests/final-functions-ui-682.test.tsx` — 10 lỗi

Đầu mối: Dashboard dùng FeatureScopeProvider nhưng fixture chưa cấp context tương ứng.

```text
dashboard uses real scoped totals and preserves unknown costs instead of KTX or invented trends
a member can view collections but never requests operational summary or readiness
an editor gets operations summary without the admin-only readiness request
a summary outage shows an error instead of zero job counters
dashboard workspace chooser is paged and sends the new URL selection through the callback
an explicit inaccessible workspace 403 is not replaced by the first allowed one
an explicit inaccessible workspace 404 is not replaced by the first allowed one
suspended workspace stays suspended without loading its collections or operations
empty workspace list is an honest empty state with no synthetic counters
switching workspace removes the previous workspace data and ignores a late summary
```

Sửa harness đúng cấu trúc auth/query/feature scope đang được app dùng. Giữ kiểm chứng role, request không được phép, 403/404 không fallback, workspace suspension, empty/error trung thực và late-response isolation. Không xóa provider requirement trong production để chiều test.

### B. `frontendV1/tests/knowledge-actions-708.test.tsx` — 8 lỗi

Đầu mối: PendingSourceDeletions/consumer mới gọi useV1Auth nhưng fixture thiếu V1AuthProvider hoặc mock chưa đầy đủ.

```text
source menu exposes recoverable delete for admin with exact source target
member source menu keeps read actions without delete
stage compiler links to its working page
stage publication links to its working page
stage serving links to its working page
folder error is visible rather than displayed as an empty directory
table view has the same document management menu
editor may archive sources but cannot delete them
```

Giữ phân quyền admin/editor/member, exact source target, menu chung ở grid/table, route thật và folder fetch error. Không mock bỏ cả subtree cần kiểm tra hoặc mặc định actor luôn admin.

### C. `frontendV1/tests/navigation-scope-692.test.tsx` — 2 lỗi

Đầu mối: thiếu `[data-testid="scope"]` sau render; kiểm stack/error boundary và dependency QueryClient/Auth/FeatureScope mới trước khi đoán lỗi selector.

```text
scope follows chooser URL, keeps collection within workspace, clears across sessions and workspace changes
closing and reopening mobile navigation preserves the shell selection
```

Giữ kiểm chứng scope theo URL, collection không rò qua workspace/session, mobile navigation đóng/mở không mất chọn. Không thay bằng snapshot hoặc chỉ assert component tồn tại.

### D. `frontendV1/tests/workspace-sidebar-689.test.tsx` — 2 lỗi

Đầu mối: mock auth thiếu export hasV1Permission.

```text
without workspace the available actions guide the user to workspace selection
workspace shortcuts use the selected workspace and operations view
```

Ưu tiên partial mock giữ helper permission thật, hoặc wrapper có actor hợp lệ. Không định nghĩa permission luôn true; vẫn cần negative case.

### E. `frontendV1/tests/sidebar-navigation-691.test.tsx` — 1 lỗi

```text
clicking the sidebar opens the chosen feature selection page
```

Đầu mối: không tìm thấy link Biên soạn sau render. Kiểm tra permission mock/export, route tree và context trước khi sửa label hoặc bỏ assertion. Đích navigation phải khớp luồng hiện tại.

### F. `frontendV1/tests/rag-ui-674.test.tsx` — 1 lỗi

```text
F3: a failed publication fetch must not claim the document has no publication
```

Đầu mối: useV1Auth thiếu provider trong nhánh useIndexRunsQuery/CompiledDocumentDetail. Sửa fixture đủ dependencies, giữ yêu cầu phân biệt fetch failed với không có publication. Không biến lỗi thành mảng rỗng để xanh test.

### G. `frontendV1/tests/lifecycle-operations-ui-678.test.tsx` — 1 lỗi

```text
admin readiness stays distinct from live inference and blocks uncertain job recovery
```

Đầu mối: không tìm thấy text Chưa có nguồn để kiểm tra đọc tệp. Điều tra request fake, quyền hiện hành, dữ liệu readiness và lifecycle UI. Chỉ cập nhật selector/microcopy nếu thay đổi giao diện là hợp lệ và vẫn chứng minh: dependency/config readiness không phải live inference PASS, uncertain job không được gửi lại. Không bỏ hai bất biến này hoặc bật recovery chỉ để vượt test.

### H. `frontendV1/tests/maintenance-evaluation-ui-679.test.tsx` — 1 lỗi

```text
evaluation caps the editable question list at twenty
```

Đầu mối: timeout5000ms, nguyên nhân chưa kết luận. Tái hiện riêng, kiểm fake timers, async state, handler, re-render, cleanup và chi phí20 câu. Phải kiểm tối đa20 câu và payload không vượt20; không chỉ tăng timeout, giảm số lần tương tác hay bỏ kiểm tra giới hạn. Chỉ điều chỉnh timeout sau khi chứng minh ngưỡng cũ không phản ánh hành vi hợp lệ và ghi bằng chứng.

## 5. Quy tắc sửa fixture và code

- Có thể sửa fixture đã lỗi thời khi production tree/contract chứng minh cần thay; giải thích rõ vì sao, giữ hoặc tăng mức kiểm tra hành vi gốc.
- Có thể thêm test helper chung cho auth/query/feature scope nếu có lặp thực sự; không tạo framework test mới hay mock toàn bộ ứng dụng. Reset cache/session giữa test, dispose client/timers, giải phóng deferred promises.
- Không dùng skip/todo/only, xóa test, đổi câu hỏi hoặc expected output cho hợp kết quả sai, nới guard, ép permission/fallback thành công, tăng timeout chung hoặc retry test cho tới xanh.
- Không chỉ đảo assertion trong các probe793 rồi coi là regression: chuyển tình huống thành test kỳ vọng đúng, đúng hợp đồng và kiểm tới handler/API/DOM cần thiết.
- Không dùng any/as never để che type errors mới. Nếu gặp workaround kiểu ép cast đang tồn tại trong vùng sửa, xử lý theo nguyên nhân đúng phạm vi.
- Tái dùng primitives, semantic tokens và một menu ⋯ cho thao tác phụ. Không bọc hộp chồng hộp, lộ ID kỹ thuật, fake success/progress hoặc thêm library.
- Không thay cách xử lý OCR, RAG ranking/prompt hay giới hạn model chỉ để giải quyết lỗi UI/test này.

## 6. Thứ tự thực hiện và kiểm chứng

1. Đọc state/diff và lập baseline hiện tại. Lưu exact IDs, log và số test; không ghi đè baseline793.
2. Thêm regression kỳ vọng đúng cho 4 P2, xác nhận RED đúng nguyên nhân. Kiểm ở ranh giới API/handler cho catalog/quyền và hành vi submit/DOM cho FE.
3. Sửa P2-1 → P2-2 → P2-3 → P2-4. Chạy kiểm tra trọng tâm sau mỗi batch có thay đổi; không chạy full suite liên tục.
4. Xử lý các nhóm 26 test, ưu tiên context/mock dependencies chung rồi hai ca lifecycle/evaluation chưa rõ nguyên nhân. Phân biệt lỗi harness với lỗi sản phẩm bằng bằng chứng.
5. Khi code ổn định, chạy một lượt full frontend suite và xuất JSON. Đối chiếu đủ 26 ID cũ đã PASS, giữ 7 test 705 đã xanh, giữ 53 test ModelOps cũ; các regression mới phải PASS, không thêm skip/todo.
6. Chạy Biome file FE sửa, `npm run build` trong frontendV1; chạy `npm run test:e2e:typecheck` nếu sửa type/API ảnh hưởng E2E. Không chạy live E2E tự ý.
7. Vì có sửa BE catalog/provenance: Ruff file BE sửa, targeted unit/API regression và full Pytest cuối batch theo verification. API dùng PostgreSQL test riêng tên `qnu_v1_test_*`, không dùng DB phiên live; cleanup chỉ tài nguyên test do lượt này sở hữu. Dùng mock HTTP/server loopback cho provider. Thiếu hạ tầng phải báo NOT RUN và giữ phần kiểm chưa xong, không đổi persistence thành fake để báo PASS.
8. Backend full hiện có một lỗi cũ `tests/unit/test_source_purge_716.py::test_accept_rechecks_publication_after_preview_before_preparing_purge` do invalid_identity401 trong fixture. Không tự mở rộng sửa purge/auth ngoài task này. Nếu còn đúng lỗi đó, báo full BE FAIL kèm exact ID và kết quả regression mới riêng; không tuyên bố toàn repo xanh.
9. Kiểm giao diện ModelOps và consumer thay đổi trên desktop/mobile/light/dark nếu có môi trường phù hợp; không khởi động/restart live chỉ để có ảnh. Nếu chưa kiểm hình ảnh, ghi NOT RUN. Build không chứng minh layout.
10. Review diff, quyền, secret, UTF-8 không BOM/LF và Git diff --check. Cập nhật journal/index/WORK_LOG/PROJECT_CONTEXT/snapshot, chọn số phiên chưa dùng; không ghi đè794 của prompt này.

Lệnh FE trọng tâm có thể bắt đầu bằng:

```powershell
cd D:\DuAnPhanMem\qnu-ai-platform\frontendV1
npm exec -- vitest run tests/final-functions-ui-682.test.tsx tests/knowledge-actions-708.test.tsx tests/navigation-scope-692.test.tsx tests/workspace-sidebar-689.test.tsx tests/sidebar-navigation-691.test.tsx tests/rag-ui-674.test.tsx tests/lifecycle-operations-ui-678.test.tsx tests/maintenance-evaluation-ui-679.test.tsx
```

Sau khi sửa ổn định, full suite và build:

```powershell
npm test -- --run --reporter=json --outputFile=../tmp/fix794-full-vitest.json
npm run build
```

Nếu có lỗi mới hoặc test đang chạy dở, tiếp tục điều tra và sửa trong phạm vi. Rerun targeted sau một sửa đổi có lý do là được; lặp cùng một lượt không thay đổi chỉ để lấy kết quả PASS thì không được.

## 7. Điều kiện hoàn thành và báo cáo

Chỉ coi mục tiêu FE hoàn thành khi full suite hiện tại không còn FAIL, không vô hiệu hóa 26 test cũ, các regression cho 4 P2 đạt và build/Biome đạt. Không trộn số liệu các lần chạy hoặc chỉ trích targeted PASS khi full còn đỏ.

Bàn giao ngắn, có chứng cứ:

1. Từng P2: nguyên nhân → file sửa → hành vi sau sửa → test tái hiện đã chuyển sang kỳ vọng đúng.
2. Bảng 8 nhóm/26 test: số lỗi baseline, số đã sửa, exact IDs còn lỗi nếu có, nhóm nào sửa fixture và nhóm nào sửa production.
3. Contract catalog/provenance BE–FE và negative tests quyền truy cập.
4. Lệnh/cwd/exit code, số PASS/FAIL/SKIP và đường dẫn report. Ghi đúng full BE nếu còn lỗi716.
5. Giới hạn kiểm chứng, phần visual/live NOT RUN và xác nhận không thay phiên93faa11f0caf hoặc gửi lại uncertain inference.

Không dừng bằng câu "đã fix xong" nếu chưa đạt hoặc chưa kiểm đủ; nêu chính xác phần còn thiếu và tiếp tục những việc không bị chặn.
