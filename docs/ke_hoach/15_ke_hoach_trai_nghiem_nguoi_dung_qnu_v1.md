# 15 — Kế hoạch triển khai trải nghiệm người dùng QNU V1

- Ngày lập: 2026-11-08.
- Baseline: `09a173a2`, nhánh `v1.0.3`, đã push tới remote `gitea`.
- Nhánh chuẩn bị triển khai: `feat/v1-user-workflow`, tách từ baseline trên.
- Trạng thái: P1–P6 đã triển khai trên nhánh `feat/v1-user-workflow` (2026-11-08, còn trong working tree). P7 đã có bộ công cụ pilot và gate tự động; môi trường dev đã backup + áp migration `0015`–`0017` (head `0017_answer_review`) và chạy được API/worker/giao diện, nhưng **phiên pilot thực tế NOT RUN** vì chưa chọn đơn vị/người tham gia và workspace pilot chưa có thành viên/trợ lý/tài liệu xuất bản; chưa chốt nghiệm thu pilot.
- Phạm vi hiện tại: P1 (điều hướng/thuật ngữ/thao tác), P2 (read model summary + gắn vào trang nguồn/tài liệu), P3 (preparation intent bền vững + hộp thoại “Chuẩn bị nội dung”), P4 (review submission + trang “Cần xử lý”), P5 (tham chiếu chuẩn bị/xuất bản/phục vụ, thay bản trung thực, lý do nguồn cũ không khả dụng), P6 (form trợ lý cơ bản/nâng cao, phạm vi + readiness, bộ câu hỏi kiểm thử trả lời có nhãn người kiểm tra, phân loại lỗi hội thoại) và P7 (runbook chọn người/kịch bản đo thời gian/ma trận lỗi/nghiệm thu/rollout, gate tự động 43 ca đạt, môi trường dev sẵn sàng; chưa chạy pilot với người thật). Không deploy production, không reindex, không gọi model thật, không thay cấu hình đang chạy; migration chỉ áp trên DB dev sau backup.

## 1. Mục tiêu và ranh giới

### 1.1. Kết quả cần đạt

Cán bộ không chuyên kỹ thuật có thể thực hiện hành trình:

```text
Thêm tài liệu → Chuẩn bị nội dung → Kiểm tra → Gửi duyệt
→ Duyệt → Xuất bản → Đồng bộ → Sẵn sàng tra cứu
```

Người tra cứu chỉ cần chọn trợ lý, hỏi, đọc và mở dẫn chứng. Người quản trị vẫn truy cập được cấu hình, chẩn đoán và tác vụ nâng cao.

Không xây lại backend, không đổi framework, không biến mọi công việc thành một màn hình nhiều tab. Giữ những trang chi tiết chuyên dụng; nối chúng bằng cùng ngữ cảnh tài liệu, trạng thái và hành động tiếp theo.

### 1.2. Nguyên tắc không được đánh đổi

1. Workspace tiếp tục là biên giới quyền; URL, menu và dữ liệu từ model không chứng minh quyền.
2. Không sửa tệp gốc hoặc OCR gốc; hiệu đính và biên soạn là dẫn xuất có provenance.
3. Xử lý xong không đồng nghĩa đã duyệt; xuất bản không đồng nghĩa đã có trong chỉ mục phục vụ.
4. Không tự động duyệt hoặc xuất bản vì job hoàn tất hay không có cảnh báo.
5. Không ép gọi LLM để viết lại mọi tài liệu. Ưu tiên bản nguồn đầy đủ; bổ sung AI là lựa chọn rõ ràng.
6. Không hardcode model hoặc token budget để giấu cấu hình; dùng ModelOps và quyền hiện hành.
7. Không tạo tiến độ, kết quả kiểm tra, thông báo hoặc trạng thái sẵn sàng giả.
8. Không suy năm dữ liệu từ năm ban hành/tên tệp; không mở rộng phạm vi vì ít kết quả.
9. Không tự gửi lại request inference có kết quả chưa xác định.
10. Không tự gộp quyền của editor, reviewer, admin; platform admin được giải quyết theo authority server.

### 1.3. Ngoài phạm vi bản đầu

- DAG builder, marketplace/plugin framework, multi-agent studio.
- Public widget, Zalo/Messenger, chia sẻ công khai hoặc thay kiến trúc đăng nhập.
- Viết lại parser, thuật toán retrieval, embedding hoặc thêm model chỉ để phục vụ redesign.
- Tự công bố kho dữ liệu, backfill toàn bộ, reset DB hay rebuild index hàng loạt.
- Chuyển các màn KTX mẫu thành API V1 thật.
- Tự sửa toàn bộ lỗi baseline. Lỗi cản nghiệm thu được tách rõ và phối hợp với người đang sửa.

## 2. Học từ ba nền tảng, nhưng dùng nền tảng QNU hiện có

| Tham khảo | Bài học áp dụng | Không sao chép |
|---|---|---|
| AnythingLLM | Bắt đầu bằng tài liệu/câu hỏi; ít cấu hình trước khi làm việc | Tải lên là tự động trở thành tri thức chính thức |
| Dify | Tách trải nghiệm người xây dựng, quản lý nội dung, người dùng cuối | Đưa workflow/node/model settings ra trước cán bộ |
| RAGFlow | Hiển thị kết quả đọc tài liệu, chỗ cần đối chiếu và nguồn dẫn chứng | Dùng chunk, parser, index làm mô hình tư duy của người dùng |

Đây là tham khảo tài liệu công khai, không phải kết luận từ chạy thử toàn bộ hay kiểm toán source ba repo. Không đưa mã nguồn từ repo ngoài vào QNU trong kế hoạch này; nếu sau này tái sử dụng mã phải kiểm tra giấy phép của phần cụ thể.

## 3. Hiện trạng đã đối chiếu và phần cần bổ sung

### 3.1. Những năng lực phải tái sử dụng

| Năng lực | Điểm vào hiện hành | Hướng xử lý |
|---|---|---|
| Navigation tập trung và scope | [workspace-features.ts](../../frontendV1/src/navigation/workspace-features.ts), [config.ts](../../frontendV1/src/navigation/config.ts) | Sidebar đã được tinh gọn; điều chỉnh theo vai trò, không khẳng định mọi module đang là menu cấp một |
| Shell, command menu, session | [admin-shell.tsx](../../frontendV1/src/layouts/admin-shell.tsx), [permissions.ts](../../frontendV1/src/app/auth/v1/permissions.ts) | Giữ auth V1/KTX tách biệt, query theo phiên và workspace |
| Kho và trang nguồn | [knowledge-detail-page.tsx](../../frontendV1/src/features/knowledge/knowledge-detail-page.tsx), [source-detail-page.tsx](../../frontendV1/src/features/knowledge/source-detail-page.tsx) | Mở rộng điểm quay về của tài liệu, không tạo studio thứ hai |
| Đọc nguồn, đối chiếu, bảng | [ocr-comparison-view.tsx](../../frontendV1/src/features/knowledge/ocr-comparison-view.tsx), [document-sheet-canvas.tsx](../../frontendV1/src/features/knowledge/document-sheet-canvas.tsx), [original-file-preview.tsx](../../frontendV1/src/features/knowledge/original-file-preview.tsx) | Giữ canvas và bằng chứng; ưu tiên chỗ cần xem |
| Compiler source-first và tiến trình bền vững | [compilation/service.py](../../backendV1/qnu/domains/knowledge/compilation/service.py), [execution.py](../../backendV1/qnu/domains/knowledge/compilation/execution.py) | Dùng lại worker/lease/checkpoint; không dựng compiler khác |
| Theo dõi biên soạn trong phiên | [compilation-activity.tsx](../../frontendV1/src/features/knowledge/compilation-activity.tsx), [compilation-activity-panel.tsx](../../frontendV1/src/features/knowledge/compilation-activity-panel.tsx) | Đã có panel theo phiên; chưa đồng nghĩa có inbox bền vững sau reload/đăng nhập lại |
| Đăng ký và metadata từ nguồn | [publication/service.py](../../backendV1/qnu/domains/knowledge/publication/service.py), [register-document-dialog.tsx](../../frontendV1/src/features/knowledge/register-document-dialog.tsx) | Giữ tự nhận diện, hash, idempotency; không đưa checkbox metadata trở lại |
| Duyệt, xuất bản, thu hồi | [publication/access.py](../../backendV1/qnu/domains/knowledge/publication/access.py), [decisions.py](../../backendV1/qnu/domains/knowledge/publication/decisions.py), [review-gate-dialog.tsx](../../frontendV1/src/features/knowledge/review-gate-dialog.tsx) | Giữ preview/receipt, quyền và version pinning |
| Tự đồng bộ sau xuất bản | [index/sync.py](../../backendV1/qnu/domains/knowledge/index/sync.py), [search-availability.tsx](../../frontendV1/src/features/knowledge/search-availability.tsx) | Mở rộng khả năng giải thích theo tài liệu; không thêm thao tác tạo index cho cán bộ |
| Trợ lý, hội thoại và dẫn chứng | [assistant-detail-page.tsx](../../frontendV1/src/features/assistants/assistant-detail-page.tsx), [chat-view.tsx](../../frontendV1/src/features/conversations/chat-view.tsx), [citation-sheet.tsx](../../frontendV1/src/features/conversations/citation-sheet.tsx) | Tinh gọn cấu hình và kiểm tra câu trả lời, giữ conversation ownership |
| Đánh giá truy xuất | [evaluation/schemas.py](../../backendV1/qnu/domains/evaluation/schemas.py), [evaluation-page.tsx](../../frontendV1/src/features/evaluation/evaluation-page.tsx) | Đã có snapshot/gold chunk; không coi đây là hệ thống chấm câu trả lời nghiệp vụ hoàn chỉnh |

### 3.2. Khoảng trống cần thiết kế rõ

- Publication hiện có `draft`, `approved`, `published`, `superseded`, `withdrawn`; các quyết định là `approve`, `publish`, `withdraw`. Không đổi nhãn mọi `draft` thành “Chờ duyệt”. Gửi duyệt/yêu cầu sửa cần lưu trạng thái bàn giao riêng.
- Upload đã có `auto_extract`: với PDF/DOCX, processing được tạo cùng transaction lưu nguồn rồi dispatch sau commit trong [sources/service.py](../../backendV1/qnu/domains/knowledge/sources/service.py#L205). Không xây lại upload → extraction. `compilation/workflow/automatic.py` là outbox cho AI review, không phải bộ điều phối toàn tuyến; phần cần nối là handoff từ kết quả đọc nguồn đã ghim sang chuẩn bị nội dung theo ý định được chấp nhận.
- Quan hệ nguồn → kết quả biên soạn → tài liệu xuất bản không phải một-một. [CompilationInput](../../backendV1/qnu/domains/knowledge/compilation/models.py#L112) ghim nhiều đầu vào; một nguồn có thể tham gia nhiều kết quả. [CompiledVersion](../../backendV1/qnu/domains/knowledge/publication/models.py#L51) gắn một compilation run duy nhất và một tài liệu đích.
- Chưa xác nhận có API V1 hoàn chỉnh cho inbox nghiệp vụ, giao việc, notification read/unread và feedback câu trả lời. Phải kiểm tra trước khi tạo schema; UI notification KTX không phải bằng chứng các API này tồn tại.
- Thử câu hỏi có chấm câu trả lời là phần bổ sung trên conversation/answer hiện có; không thay thế hoặc làm sai ý nghĩa benchmark retrieval.

## 4. Trải nghiệm và điều hướng đích

### 4.1. Phân tầng theo công việc, không tạo thêm hệ quyền

| Trải nghiệm | Mặc định hiển thị | Hành động theo quyền hiện hành |
|---|---|---|
| Người tra cứu | Trợ lý, hội thoại | Hỏi và xem dẫn chứng được phép |
| Người quản lý nội dung | Tài liệu, Cần xử lý | Admin/editor thêm nguồn, chuẩn bị, đăng ký bản nháp |
| Người duyệt | Cần xử lý với bộ lọc Chờ duyệt | Admin/reviewer duyệt; không mặc định có quyền xuất bản |
| Người xuất bản | Bản đã duyệt và trạng thái phục vụ | Admin xuất bản/thu hồi |
| Quản trị kỹ thuật | Cấu hình AI, Vận hành | Giữ nguyên quyền ModelOps/operations, không suy từ tên vai trò UI |

Bản đầu chỉ tạo một mục “Cần xử lý”, bên trong có bộ lọc “Chờ duyệt”, tránh hai inbox trùng lặp. Một người nhiều quyền thấy các công việc phù hợp; không cần công tắc giả lập role.

Ẩn bớt menu không thu hẹp hay mở rộng quyền API sẵn có. Nếu muốn member không còn đọc được một loại tài nguyên hiện được READ_ROLES cho phép, đó là thay đổi chính sách riêng, không làm ngầm trong redesign.

### 4.2. Trang tài liệu làm điểm quay về

- Header: tên, trạng thái công việc, trạng thái sử dụng, một hành động chính phù hợp quyền.
- Nội dung chính: bản đọc được và đường mở bản gốc; dùng canvas hiện có.
- Thông tin phụ: bản đang phục vụ, bản đang chuẩn bị, nguồn liên quan, lịch sử.
- Chẩn đoán: phần mở riêng cho người có quyền; không rải run ID/hash/provider trên màn mặc định.
- Hành động phụ: một menu chung; không thêm nhiều nút trên từng dòng.
- Tổng hợp nhiều nguồn phải ghi rõ danh sách nguồn và đường trở về; không gán một source làm chủ giả.
- Chưa đăng ký: định danh theo source/revision và preparation intent. Đã đăng ký: dùng compiled document/version và liên kết ngược nguồn. Không đoán tài liệu đích bằng filename hoặc run mới nhất.

### 4.3. Bộ thuật ngữ áp dụng trong phạm vi màn sửa

| Nội bộ | Nhãn thông thường |
|---|---|
| OCR | Đọc chữ từ bản quét / Đọc nội dung, theo cách xử lý thật |
| Compilation source-first | Chuẩn bị nội dung |
| AI supplement | Bổ sung bằng AI |
| Retrieval metadata | Thông tin tài liệu |
| Index sync | Đồng bộ cho trợ lý |
| Published | Đã xuất bản |
| Ready in serving snapshot | Sẵn sàng tra cứu |
| Uncertain | Chưa xác định kết quả |
| Generation/hash/run ID | Chi tiết kỹ thuật |

Không rename enum/API/DB chỉ để đổi nhãn UI. Không dùng “AI đã xác minh” thay cho kiểm chứng bằng nguồn hoặc quyết định con người.

## 5. Hợp đồng trạng thái dùng chung

### 5.1. Không tạo một enum thay mọi trạng thái domain

Read model phải giữ các chiều riêng:

| Chiều | Nội dung tối thiểu |
|---|---|
| Định danh | Workspace, collection, source/revision hoặc document/version; ID giữ trong API, không hiện thô |
| Chuẩn bị | Chưa bắt đầu, queued/running, completed, failed, uncertain, cancelled; phạm vi hoàn tất và vấn đề |
| Bàn giao duyệt | Chưa gửi, đang chờ, yêu cầu sửa, đã xử lý; gắn đúng bản/hash |
| Xuất bản | Trạng thái thật của version và quyết định có thẩm quyền |
| Phục vụ | Chưa có bản phục vụ, đang đồng bộ, có bản hợp lệ, bản mới chưa đồng bộ, bị chặn/thu hồi, lỗi hoặc chưa quan sát được |
| Hành động | Hành động hiện được phép, lý do chưa làm được, tài nguyên đích |
| Thời điểm | Thời điểm quan sát và revision/sequence dùng để xác định stale |

Tên field cụ thể được chốt ở P0 trước code; không phải API đã tồn tại. Backend quyết định tính sẵn sàng và quyền; frontend chỉ ánh xạ nhãn và route đã biết, không tin URL hành động tùy ý từ dữ liệu.

### 5.2. Quy tắc hiển thị bắt buộc

- `completed` nhưng chưa đăng ký/duyệt: “Đã chuẩn bị”, không “Sẵn sàng tra cứu”.
- Chưa gửi duyệt: “Bản nháp”; chỉ có submission thật mới hiện “Chờ duyệt”.
- Đã xuất bản nhưng chưa có snapshot hợp lệ: “Đã xuất bản · Đang đồng bộ”.
- Bản mới đang chuẩn bị: hiển thị song song bản đang phục vụ nếu server xác nhận còn hợp lệ.
- Có vector không đủ chứng minh được phục vụ; phải kiểm publication, scope, binding, snapshot và vòng đời.
- Provider lỗi khác không tìm thấy căn cứ; request uncertain khác thất bại chắc chắn.
- Cảnh báo AI bổ sung chưa xong không mặc định làm mất nội dung nguồn, nhưng không che điều kiện chặn của review gate.
- Không lấy readiness hạ tầng hoặc cờ collection chung để suy mọi tài liệu và mọi trợ lý đều sẵn sàng.

## 6. Các gói triển khai và tiêu chí nghiệm thu

### P0 — Chốt baseline, hợp đồng và kịch bản nghiệm thu

**Mục tiêu:** có phạm vi đủ rõ trước khi nối các domain.

Công việc:

- P0.1: Kiểm tra Git/diff mới trước mỗi batch; baseline đầu là `09a173a2`. Ghi lỗi test có sẵn riêng, không nhận sửa lỗi của phiên khác.
- P0.2: Chốt ma trận màn hình/quyền và từ điển trạng thái ở mục 4–5; xác nhận bằng API hiện hành, không dựa demo role.
- P0.3: Chọn fixture không nhạy cảm: PDF text, PDF scan, DOCX có bảng, nhiều nguồn, bảng nhiều năm, hai phiên bản khác nhau, nguồn lỗi và nguồn thiếu thông tin.
- P0.4: Chốt contract read model, submission và preparation intent; chỉ thêm field/table khi dữ liệu hiện có không biểu đạt được.
- P0.5: Ghi các phép đo pilot ban đầu: bước người dùng phải tự chọn, lần cần dev hỗ trợ, thời gian thao tác chủ động tách thời gian chờ xử lý.

**Đầu ra:** checklist/API contract được cập nhật trong tài liệu này hoặc tài liệu module đang có; danh sách test và fixture. Không dựng framework mới.

**Nghiệm thu:** mỗi nhãn sẵn sàng/quyền/hành động có nguồn dữ liệu server; mọi ghi mới có authority, replay và stale-state policy rõ ràng.

### P1 — Thuật ngữ, menu theo công việc và thao tác tiếp theo

**Phụ thuộc:** P0. **Phạm vi chính:** frontend, không migration.

Công việc:

- P1.1: Điều chỉnh navigation tập trung, workspace sidebar, command menu và breadcrumb cùng một nguồn; duy trì route trực tiếp hiện hành.
- P1.2: Dùng trải nghiệm theo quyền ở mục 4; không dùng quyền platform đơn lẻ để đoán membership.
- P1.3: Tinh gọn labels ở nguồn, biên soạn, đăng ký và xuất bản; giữ thông tin metadata tự động đang có, không thêm lại bước xác nhận từng trường.
- P1.4: Gom thao tác phụ vào menu; một CTA chính, lỗi có hành động tiếp theo. Ẩn phần kỹ thuật mặc định, không xóa khả năng chẩn đoán.
- P1.5: Giữ menu “Cần xử lý” chỉ khi có dữ liệu/API thật ở P4, không tạo trang placeholder giả hoàn chỉnh.

**File/module:** `src/navigation/`, `src/layouts/`, `src/features/knowledge/`, `src/features/assistants/`, các helpers auth V1. Không sửa `routeTree.gen.ts` bằng tay.

**Nghiệm thu:** từng role vào đúng đường dẫn; refresh/back/deep link giữ scope; đổi workspace/logout không lộ dữ liệu cũ; desktop/mobile, sáng/tối, keyboard dùng được. KTX không nhận request nghiệp vụ V1.

### P2 — Read model và trang tài liệu xuyên suốt

**Phụ thuộc:** P0; ghép UI sau P1. **Phạm vi:** read API + frontend.

Công việc:

- P2.1: Mở rộng read service của sources/publication để nối quan hệ qua OCR và CompilationInput; không scan toàn corpus ở trình duyệt.
- P2.2: Tạo summary theo source/revision hoặc document/version. Trả danh sách kết quả có giới hạn; không tùy tiện chọn latest run làm bản đang dùng.
- P2.3: Đưa availability vào summary bằng cách tái sử dụng readiness theo document/version đã có: [index/readiness.py](../../backendV1/qnu/domains/knowledge/index/readiness.py#L35) kiểm active run, eligibility và manifest; [search-availability.tsx](../../frontendV1/src/features/knowledge/search-availability.tsx#L74) đã đối chiếu version/state/hash. Không tạo thuật toán readiness thứ hai; trạng thái sync collection `ready` không chứng minh một tài liệu cụ thể sẵn sàng.
- P2.4: Ghép summary vào source detail và compiled document detail. Giữ các trang OCR/editor/review riêng, có đường quay về đúng tài liệu.
- P2.5: Query key gồm session/workspace/collection/định danh bản; invalidation sau mutation; poll có giới hạn khi có tác vụ đang hoạt động. Không chỉ chờ một lần có data rồi ngừng trước terminal state.
- P2.6: List có pagination server và loading/error/empty riêng; không N+1 request mỗi dòng để dựng trạng thái.

**Contract đề xuất:** resource summary đọc thuần, không tạo run hay tự enqueue khi GET. Có `observed_at`, reference tới bản nguồn/bản biên soạn/bản xuất bản/bản phục vụ và capabilities theo người gọi. Chỉ thêm endpoint scoped tại domain đang có nếu endpoint hiện tại không đủ.

**Nghiệm thu:** một nguồn nhiều run, một bản tổng hợp nhiều nguồn, nhiều phiên bản, không có index, sync lỗi, nguồn archived/deleted, mất quyền giữa hai lần đọc. Không gửi summary của tài nguyên ngoài scope.

### P3 — Nối luồng thêm tài liệu và chuẩn bị nội dung bền vững

**Phụ thuộc:** P2. **Phạm vi:** orchestration tối thiểu + upload/source UI; không đổi engine.

Công việc:

- P3.1: Sau khi lưu nguồn, cung cấp một yêu cầu rõ ràng “Chuẩn bị nội dung” dùng chính sách mặc định được phép. Không tự xử lý mọi tệp chỉ vì người dùng muốn lưu tệp.
- P3.2: Preview/accept intent ghi đúng source revision/hash, collection, actor, cấu hình thực thi và chế độ nguồn/AI. Nếu upload kèm chuẩn bị, UI phải mô tả rõ trước khi người dùng xác nhận.
- P3.3: Giữ upload → extraction hiện có; mở rộng durable intent/outbox cho handoff còn thiếu sang source-first compiler sau khi intent được chấp nhận. Đầu vào phải là revision, processing run, text version/hash đã lưu trên server và evidence locator tương ứng; nếu có hiệu đính chưa lưu thì yêu cầu lưu hoặc bỏ trước. Không lấy nháp trình duyệt, tự chuyển sang latest, hoặc nối bằng `useEffect`/timer. Điểm dừng là kết quả chờ kiểm tra, không tự đăng ký/duyệt/xuất bản.
- P3.4: Ưu tiên artifact tương thích đã hoàn tất; chỉ dùng lại khi revision/parser/config phù hợp. DOCX/PDF text đi theo adapter thật; scan OCR theo chính sách, không gọi OCR/LLM vô ích.
- P3.5: Chế độ “Bổ sung bằng AI” riêng, tuân ModelOps/quota và giữ nguồn. Chế độ nguồn không bị chặn vì AI tùy chọn lỗi nếu contract hiện hành cho phép hoàn tất nguồn.
- P3.6: Khi kết quả đã sẵn sàng, dùng registration service hiện hành sau thao tác người dùng. Không tự đăng ký rồi gửi duyệt/xuất bản chỉ vì worker hoàn tất.
- P3.7: Làm rõ dedup/replay: khóa theo ý định và scope; cùng key/body không chạy lại; đổi body cùng key bị từ chối; trạng thái uncertain không tự resend.

**Dữ liệu có thể cần thêm:** một bản ghi intent chỉ khi không có row hiện hành lưu được chuỗi bước. Nó giữ references, step/checkpoint/lease và request hash; không sao chép toàn bộ trạng thái tất cả job vào một bảng workflow thứ hai. Dùng ARQ/outbox/reconcile có sẵn, không thêm scheduler/framework.

**An toàn:** worker tái kiểm authority từ server, source lifecycle và revision trước bước mới. Thu hồi quyền/hủy công việc chặn bước kế tiếp; không hứa abort được upstream request đã gửi. Ghi nhận usage chưa rõ đúng trạng thái.

**Nghiệm thu:** đóng tab/reload/worker restart không mất intent; enqueue lỗi vẫn có trạng thái durable; duplicate delivery không tạo inference kép; upload lỗi không hiện thành công; hủy/đổi nguồn/mất quyền không phát sinh bước tiếp theo. Golden path không yêu cầu người dùng tự mở module OCR rồi Compiler.

### P4 — Bàn giao duyệt và danh sách Cần xử lý

**Phụ thuộc:** P2; tích hợp P3 khi sẵn sàng. **Phạm vi:** submission riêng + read aggregation + review UI.

Công việc:

- P4.1: Thêm bản ghi bàn giao review gắn document/version/bundle hash; giữ enum publication hiện có. Các trạng thái đề xuất: pending, changes_requested, resolved, cancelled. Không backfill draft cũ thành pending.
- P4.2: Editor/admin gửi bản nháp; reviewer/admin yêu cầu sửa hoặc quyết định duyệt theo gate hiện hành. Người gửi/admin rút yêu cầu chưa xử lý. Thao tác đều có preview/accept, idempotency, sequence và audit theo pattern hiện hành.
- P4.3: Yêu cầu sửa phải có lý do; không sửa nội dung version bất biến. Bản sửa tạo dẫn xuất/phiên bản mới và submission mới; yêu cầu cũ giữ lịch sử.
- P4.4: Xây inbox scoped workspace/collection, phân trang/lọc server: lỗi cần xử lý, chờ duyệt, chờ xuất bản, đồng bộ chưa hoàn tất. Không coi mọi job failed cũ là việc còn mở.
- P4.5: Mỗi dòng có tài liệu, vấn đề, thời điểm, nhóm người có thể xử lý và deep link. Chưa giao cá nhân thì ghi “Chờ người duyệt”, không giả người phụ trách.
- P4.6: Review ưu tiên cảnh báo có căn cứ, thay đổi AI và bản gốc. Vẫn có khả năng đọc toàn bộ; không cảnh báo không chứng minh đúng.
- P4.7: Đánh dấu hoàn tất inbox dựa trên trạng thái tài nguyên/submission thật; không dùng nút dismiss để giả xử lý nghiệp vụ.

**Quyền:** registration admin/editor; approve admin/reviewer; publish/withdraw admin. Không yêu cầu reviewer tự sửa nội dung nếu họ không có quyền editor. Người phê duyệt có thể không phải người xuất bản.

**Nghiệm thu:** draft chưa gửi không vào hàng chờ duyệt; gửi lặp một yêu cầu; hai người quyết định đồng thời không tạo hai trạng thái cuối mâu thuẫn; bản thay đổi làm preview hết hiệu lực; quyền rút giữa chừng bị kiểm lại; approve không tự publish; approved không tự hiện ready.

**Giới hạn bản đầu:** chưa xây task assignment/SLA/email. Existing approved/published tiếp tục đọc được, không bị hồi tố thành chưa gửi duyệt. Quyết định hiện hành xử lý bản có submission phải đóng submission trong cùng transaction khi thích hợp, tránh hàng chờ ma.

### P5 — Xuất bản, cập nhật và trạng thái phục vụ trung thực

**Phụ thuộc:** P2, P4; P3 hoàn tất trước nghiệm thu đầu-cuối.

Công việc:

- P5.1: Sau publish dùng index sync outbox hiện hành; UI theo dõi trạng thái, không yêu cầu tạo index tay.
- P5.2: Hiển thị bản chuẩn bị, bản được xuất bản và bản thật sự được phục vụ như những references riêng.
- P5.3: Với cập nhật không gián đoạn, luồng UI phải gửi revision dạng staged trước khi chuẩn bị bản thay thế: [sources/router.py](../../backendV1/qnu/domains/knowledge/sources/router.py#L247) hiện mặc định `staged=False`, không được mặc định coi mọi revision upload là an toàn cho bản cũ. Tái sử dụng [replacement.candidate](../../backendV1/qnu/domains/lifecycle/replacement.py#L46): bản mới approved, receipt hợp lệ, tài liệu đang published, nguồn dùng chung không xung đột. Preview giải thích ảnh hưởng/điều kiện bị chặn; switch publication/source/index giữ nguyên tính nguyên tử. Không hứa bản cũ tiếp tục dùng trong publish trực tiếp nếu policy không cho phép; không tự mở rộng thay thế hàng loạt.
- P5.4: Khi rebuild/switch thất bại, giữ trạng thái thực tế; chỉ hiện “bản cũ vẫn đang phục vụ” sau xác nhận server. Nếu không còn bản hợp lệ, báo gián đoạn thay vì fallback âm thầm.
- P5.5: Thu hồi/xóa/lưu trữ chặn sử dụng theo lifecycle và quyền ngay tại retrieval; không đợi xóa vật lý vector mới ngừng trả nội dung.
- P5.6: Dẫn chứng hội thoại cũ tiếp tục được kiểm quyền/lifecycle; nếu không còn được xem, hiện lý do thay vì mở artifact bằng đường dẫn bỏ guard.
- P5.7: Chẩn đoán và retry chỉ dành cho người có quyền, qua preview/accept có sẵn; không tạo nút retry đại trà cho mọi lỗi.

**Nghiệm thu:** thử publish → sync chậm/lỗi/thành công; cập nhật khi nhiều publication trong collection; withdraw trong lúc build; switch snapshot đúng bản; không phục vụ draft, withdrawn hoặc nội dung ngoài scope; citation kiểm được đúng bản. Không thay ranking/chunking trong batch này.

### P6 — Trợ lý dễ cấu hình và kiểm tra câu trả lời

**Phụ thuộc:** P2, P5 cho thử nghiệm với dữ liệu phục vụ; phần nhãn/form có thể song song P3–P4.

Công việc:

- P6.1: Form cơ bản chỉ ưu tiên tên, mục đích, kho được phép dùng và hướng dẫn trả lời; giữ advanced model/retrieval theo quyền và default hiện hành.
- P6.2: Từ assistant detail mở thử hội thoại thật, hiển thị phạm vi tài liệu và trạng thái sẵn sàng. Không có nguồn hợp lệ thì giải thích, không dùng kiến thức ngoài để giả đang trả lời từ kho.
- P6.3: Bộ câu hỏi thử nhỏ do người nghiệp vụ nhập; dùng answer/conversation service hiện hành, không viết pipeline mới.
- P6.4: Bản đầu cho thử trên tài liệu đã xuất bản trong workspace thử nghiệm được phép. Chưa có sandbox bản nháp thì không tuyên bố “kiểm thử bản nháp trước xuất bản”; không mở draft vào public retrieval.
- P6.5: Kết quả thử gồm câu hỏi, câu trả lời, dẫn chứng, snapshot/bản nguồn và nhãn người kiểm tra: đúng, thiếu, sai nguồn, sai năm. Không dùng nhãn tự sinh làm gold độc lập.
- P6.6: Giữ benchmark retrieval trong cấu hình kỹ thuật. Nếu lưu test set/answer review cần schema nhỏ riêng hoặc mở rộng evaluation sau khi kiểm tương thích; không nhét answer quality vào `gold_chunk_ids`.
- P6.7: Chat lỗi hạ tầng, không có căn cứ, thiếu quyền và câu hỏi cần làm rõ có thông báo riêng; kiểm citation trên desktop/mobile.

**Nghiệm thu:** hội thoại thuộc đúng actor; query cache không lẫn phiên; dùng đúng assistant binding và snapshot; người kiểm tra mở được nguồn; phân biệt latency/usage quan sát với ước lượng. Live model chỉ dùng provider/corpus được phép.

### P7 — Pilot và đóng phạm vi bản đầu

**Phụ thuộc:** P1–P6 đạt gate trong phạm vi bàn giao.

- P7.1: Chọn một đơn vị, 3–5 người đại diện editor/reviewer/admin/người tra cứu; số lượng là đề xuất pilot, không giả định đã được chọn.
- P7.2: Cho tự thực hiện thêm tài liệu, yêu cầu sửa, duyệt, xuất bản, hỏi và cập nhật bản mới. Ghi thời gian thao tác, thời gian chờ và số lần cần dev hỗ trợ.
- P7.3: Kiểm nhóm tình huống lỗi, thiếu quyền, thiếu cấu hình, nguồn mâu thuẫn, sync chưa hoàn tất. Không chỉ demo golden path.
- P7.4: Sửa các trở ngại trong phạm vi UX trước khi mở rộng tính năng; không biến pilot thành đợt refactor toàn repo.
- P7.5: Chốt nghiệm thu, known limitations và runbook rollout/rollback; không tự triển khai production chỉ vì test đạt.

**Mục tiêu đề xuất, chưa phải số đo:** ít nhất 80% người pilot hoàn tất tác vụ thường gặp không cần dev chỉ đường; tất cả người pilot phân biệt được đã chuẩn bị/chờ duyệt/đang đồng bộ/sẵn sàng; không có tình huống test nào vượt quyền, phục vụ draft/withdrawn hoặc báo ready sai. So sánh chất lượng và latency cùng corpus/model/snapshot phù hợp, không đánh đổi độ đúng để giảm số click.

## 7. Backlog sau bản đầu — không chặn pilot

| Mã | Hạng mục | Thiết kế tối thiểu | Điều kiện làm |
|---|---|---|---|
| E1 | Notification V1 bền vững | Event/recipient/read marker; GET theo actor; replay không tạo trùng; mở link tái kiểm quyền | Pilot cho thấy bỏ lỡ kết quả; không lấy notification KTX làm backend |
| E2 | Phản hồi câu trả lời | Turn reference, loại lỗi, ghi chú, source/snapshot references; quyền owner và quyền xử lý phản hồi tách rõ | Có người tiếp nhận; không tự chia sẻ toàn hội thoại riêng cho reviewer |
| E3 | Người phụ trách/hạn kiểm tra | Actor được phép trong đơn vị, audit đổi người; không tự chọn người từ JWT/AI | Quy trình đơn vị thực sự cần giao việc |
| E4 | Onboarding | Checklist dựa readiness thật: cấu hình, nguồn, quyền, trợ lý; không tự ghi cấu hình | Có số liệu vướng mắc từ người mới |
| E5 | Tệp riêng trong chat | Scope theo hội thoại/actor, retention và xóa; không tự nhập kho chính thức | Chốt chính sách bảo mật và vòng đời trước |
| E6 | Thử bản nháp cô lập | Preview retrieval namespace/snapshot có quyền, hết hạn rõ; không chia sẻ với phục vụ chung | Có yêu cầu kiểm thử trước xuất bản, có test chống lẫn draft |

E1/E2 cần migration nếu không có model phù hợp; chỉ bổ sung khi bắt đầu hạng mục, không tạo trước các bảng chưa dùng. Feedback là báo cáo người dùng, không phải tri thức đã xác minh hay chấp thuận sửa nguồn.

## 8. Thứ tự batch, phân công và ước lượng

### 8.1. Dependency

```text
P0 → P1
P0 → P2 → P3
          └→ P4 → P5 → P6 → P7
P1 + P2 + P3 phải hoàn tất trước gate đầu-cuối P7
E1–E6: sau pilot hoặc có yêu cầu riêng
```

Có thể làm song song UI labels và thiết kế read contract; không cho hai người/agent cùng sửa source detail hoặc publication service trong cùng thời điểm. Người kiểm chứng độc lập đọc diff và chạy hành vi, không chỉ nhận lời người viết.

### 8.2. Ước lượng sơ bộ

| Gói | Ngày công tập trung dự kiến | Nhân sự/chuyên môn chính |
|---|---:|---|
| P0 | 1–2 | Chủ sản phẩm + kỹ sư nắm backend/frontend |
| P1 | 2–4 | Frontend |
| P2 | 3–5 | Backend read models + frontend |
| P3 | 4–7 | Backend worker/data + frontend |
| P4 | 4–6 | Backend publication/RBAC + frontend |
| P5 | 3–5 | Backend lifecycle/index + frontend |
| P6 | 3–5 | Frontend + backend conversation/evaluation |
| P7 | 2–4 | Verifier + người nghiệp vụ |
| Tổng P0–P7 | 22–38 | Không phải cam kết ngày phát hành |

Ước lượng chưa gồm thời gian chờ người duyệt/pilot, lỗi baseline cản đường hoặc hạ tầng thiếu. Cập nhật sau P0; tốc độ AI viết code không thay thế thời gian kiểm chứng dữ liệu/quyền/concurrency.

### 8.3. Batch/commit đề xuất

1. Contract + tests trạng thái/quyền.
2. Navigation/labels không đổi nghiệp vụ.
3. Summary API + list/detail.
4. Preparation intent + worker recovery.
5. Upload/prepare UI và progress.
6. Submission + stale/concurrency tests.
7. Inbox + review UI.
8. Serving/update UI và lifecycle acceptance.
9. Assistant setup + thử câu hỏi.
10. Pilot fixes và tài liệu nghiệm thu.

Mỗi batch có thể tách thành commit nhỏ hơn nhưng phải chạy được. Không gom cả kế hoạch vào một commit lớn. Chỉ commit/push các batch triển khai khi được người dùng yêu cầu; việc push baseline lần này không cấp quyền tự push mọi thay đổi sau này.

## 9. Kế hoạch dữ liệu và API

### 9.1. Giữ nguyên

- Các bảng source/revision/OCR/compilation/publication/index là nguồn sự thật của domain.
- Auth, storage ports, ModelOps resolution, ARQ, publication receipts và index outbox hiện có.
- Các route chi tiết cũ còn giá trị phải hoạt động. Chỉ redirect khi thật sự đổi route, dùng router hiện hành, không dựng compatibility layer không cần thiết.
- Không backfill bản nháp thành đã gửi duyệt, không thay provenance của phiên bản đã đăng ký.

### 9.2. Bổ sung có điều kiện và theo phase

| Dữ liệu/contract | Phase | Nguyên tắc |
|---|---|---|
| Summary và action capabilities | P2 | Read-only; ưu tiên query trên dữ liệu hiện có; batch/pagination, không side effect |
| Preparation intent | P3 | Chỉ thêm nếu thiếu durable handoff; hash/revision/actor/step, không thêm job engine |
| Review submission | P4 | Trạng thái bàn giao riêng, FK scope và bundle hash; event history, idempotency/CAS |
| Test set và answer review | P6 | Phân biệt nhãn con người, output AI và benchmark retrieval |
| Notification/feedback/assignment | E1–E3 | Không tạo schema dự phòng trong P1–P5 |

Mọi endpoint ghi mới phải mô tả request/response, quyền, preview/accept khi áp dụng, replay và lỗi stale trước code. Tên/path endpoint mới trong implementation phải được chốt cùng contract và tests; tài liệu này không tuyên bố các endpoint đề xuất đã có.

### 9.3. Migration và rollback

- P1, phần đọc P2 không mặc định cần migration; chỉ thêm index DB khi query plan chứng minh cần.
- Schema mới ưu tiên additive, FK/unique/check theo workspace và tài nguyên; tránh sửa enum publication để chứa trạng thái bàn giao.
- Thử upgrade trên DB test rỗng và DB test có dữ liệu từ baseline. Không chạy migration trên DB ứng dụng trong lúc lập kế hoạch.
- Dữ liệu cũ vẫn đọc được, submission không tồn tại nghĩa là chưa có bàn giao trong quy trình mới, không suy đã gửi/đã duyệt.
- Rollback code bằng revert commit có chủ đích khi được phép, không reset/force-push. Không drop bảng mới chứa dữ liệu thật như một thao tác rollback tự động.
- Rollback UI không được phục hồi quyền truy xuất nội dung đã thu hồi. Chuyển lại version phục vụ là quyết định nghiệp vụ có authority, không là side effect deploy.

## 10. Ma trận kiểm thử bắt buộc

| Nhóm | Ca tiêu biểu | Bằng chứng |
|---|---|---|
| Điều hướng | Member/editor/reviewer/admin, platform admin, không membership, chưa đăng nhập | API/route guard + browser, không chỉ snapshot menu |
| Session | Logout/login actor khác, đổi workspace, request cũ trả về muộn | Test cache/invalidation và thao tác browser |
| Nguồn | PDF text/scan, DOCX table, nhiều năm, ô 0/dấu gạch, chữ Việt, unsupported/corrupt | Fixture gốc và so sánh bằng chứng dẫn xuất |
| Quan hệ | Một nguồn nhiều run, nhiều nguồn một bản, nhiều phiên bản | API summary + click xuyên suốt |
| Tác vụ | Duplicate, enqueue thất bại, crash/restart, cancellation, uncertain | Integration worker/outbox, fake upstream có kiểm số lần gọi |
| Duyệt | Chưa gửi, gửi lặp, yêu cầu sửa, stale hash, hai reviewer, mất quyền | API real handler trên DB cô lập |
| Xuất bản | Approve không publish; publish chưa sync; lỗi sync | Integration publication/index và UI |
| Cập nhật/thu hồi | Thay thế đang chạy, thu hồi khi build, bản cũ không còn hợp lệ | Snapshot/retrieval/citation regression |
| Trợ lý | Binding không đủ dữ liệu, scope năm, nguồn mâu thuẫn, hỏi ngoài kho | Answer/citation acceptance, không dùng mock làm chứng cứ live |
| UI | 390/768/1280 px, light/dark, keyboard, focus, empty/error/loading | Browser screenshots và hành vi thật |
| Hồi quy | Upload, source review, compiler editor, publication, chat, settings | Suite theo phạm vi và smoke trên các tính năng bị tác động |

Theo [verification.md](../../.agents/rules/verification.md):

- Frontend: `npm exec -- biome check <files>` và `npm run build` từ `frontendV1`; test Vitest đúng phạm vi logic. Start dev server riêng cho kiểm chứng khi triển khai UI; không restart app người dùng tùy tiện.
- Backend: Ruff scoped từ `backendV1`; regression trước với thay đổi quyền/data/concurrency; full Pytest một lần sau batch ổn định qua harness DB cô lập. Kiểm fixture trước, không test trên DB ứng dụng.
- Migration/worker/contract cần integration. Test fake provider không chứng minh OCR/LLM thật đúng.
- Nếu đụng hành vi retrieval/index: so sánh cùng snapshot, nguồn/năm/citation và latency/usage; không nghiệm thu chỉ bằng unit tests.
- Ghi PASS/FAIL/NOT RUN, command/cwd/exit code và exact test IDs lỗi nền. Full suite có lỗi vẫn là FAIL; không sửa assertion hay bỏ guard chỉ để xanh.
- Không chạy test ứng dụng hoặc gọi model cho task chỉ lập tài liệu này.

## 11. Rollout và tiêu chí dừng

1. Phát triển trên nhánh mới, giữ baseline ở `v1.0.3`.
2. Mỗi batch review diff và gate tương ứng; chưa đạt thì không đánh dấu phase hoàn tất.
3. Thử trên môi trường/DB cô lập và corpus được phép; pilot một đơn vị sau gate đầu-cuối.
4. Không thêm feature flag toàn hệ thống chỉ để che implementation dở dang; rollout theo môi trường và phiên bản hoàn chỉnh.
5. Chỉ deploy/migrate/reindex hoặc gọi live model khi được phép cho môi trường/phạm vi đó.
6. Dừng mở rộng nếu có vượt quyền, nguồn bị sửa âm thầm, draft/withdrawn lọt retrieval, ready giả hoặc replay gây inference trùng; sửa trong phạm vi trước khi pilot tiếp.
7. Lỗi baseline trực tiếp chặn golden path phải được giải quyết hoặc ghi rõ chưa nghiệm thu. Không dùng việc người dùng tự sửa lỗi làm lý do báo hoàn tất khi chưa dùng được.

## 12. Checklist bàn giao từng phase

- [ ] Mục tiêu người dùng và phạm vi file/module rõ.
- [ ] Không xây lại năng lực đã có; không sửa ngoài phạm vi.
- [ ] API/data model mới được phân biệt với contract hiện hành.
- [ ] Quyền, scope, revision, lifecycle và idempotency được kiểm chứng.
- [ ] Loading/empty/error/uncertain và next action trung thực.
- [ ] Không có dữ liệu giả, technical ID rò ra màn mặc định hoặc control tự chế.
- [ ] Test và browser gate phù hợp đã chạy; giới hạn được ghi rõ.
- [ ] Tài liệu module và hướng dẫn thao tác được cập nhật khi hành vi thật thay đổi.
- [ ] Git diff chỉ chứa batch được giao; không push/deploy ngoài quyền cho phép.

## 13. Ghi nhận phiên lập kế hoạch

Đã thực hiện trước khi viết kế hoạch:

- Rà diff của 25 tệp thuộc thay đổi người dùng hiện có; không sửa code của chúng.
- `git diff --check` và `git diff --cached --check`: đạt.
- Tạo commit `09a173a2`: `feat: simplify document registration with source-grounded automatic metadata`.
- `git push gitea v1.0.3`: thành công; `git ls-remote` xác nhận cùng SHA.
- `git switch -c feat/v1-user-workflow`: thành công, working tree sạch tại thời điểm tạo nhánh.
- Không push GitHub, không force-push, không deploy. Nhánh mới hiện được tạo local; push baseline không đồng nghĩa nhánh mới đã có trên remote.
- Không chạy lại test ứng dụng trong lượt lập kế hoạch/Git này. Các kết quả lịch sử không được dùng để tuyên bố baseline là bản release đã nghiệm thu.
- Phần chức năng P0–P7 và E1–E6 chưa triển khai. Mốc bắt đầu đề xuất: P0 rồi P1; không tự triển khai chỉ vì đã viết xong kế hoạch.

## 14. Tài liệu tham chiếu

- [Kiến trúc QNU V1](../architecture.md).
- [Quy chuẩn giao diện](../../.agents/rules/ui-standards.md).
- [Kiểm chứng theo phạm vi](../../.agents/rules/verification.md).
- [AnythingLLM repository](https://github.com/mintplex-labs/anything-llm).
- [AnythingLLM: chatting with documents](https://docs.anythingllm.com/chatting-with-documents/introduction).
- [Dify repository](https://github.com/langgenius/dify).
- [Dify: knowledge in application](https://docs.dify.ai/en/cloud/use-dify/knowledge/integrate-knowledge-within-application).
- [RAGFlow repository](https://github.com/infiniflow/ragflow).
- [RAGFlow documentation](https://ragflow.io/docs).
