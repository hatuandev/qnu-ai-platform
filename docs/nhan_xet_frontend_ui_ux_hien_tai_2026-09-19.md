# NHẬN XÉT FRONTEND VÀ UI/UX HIỆN TẠI — QNU AI PLATFORM

> Ngày đánh giá: 19/09/2026  
> Phạm vi: Frontend React/Vite, hệ thống thiết kế, khung điều hướng, các màn hình quản trị AI và trải nghiệm kết nối dữ liệu.  
> Phương pháp: rà soát mã nguồn và cấu trúc giao diện; đối chiếu với quy chuẩn dự án và kế hoạch tái cấu trúc chức năng. Frontend `:3001` và Backend `:8001` không hoạt động tại thời điểm kiểm tra nên chưa thực hiện vòng đánh giá trực quan live trên nhiều kích thước màn hình.

---

## 1. Kết luận điều hành

Frontend hiện tại **đã cải thiện rõ rệt và đủ nền tảng để phát triển thành một sản phẩm quản trị AI nghiêm túc**, không còn mang cảm giác là tập hợp các màn hình demo rời rạc. Điểm mạnh nhất là hệ thống token màu Academic Teal, dark/light mode, bộ component dùng lại, các thành phần dành riêng cho AI và mức độ bao phủ nghiệp vụ tương đối sâu.

Tuy nhiên, chất lượng hình ảnh hiện đang đi trước chất lượng kiến trúc trải nghiệm. Ba vấn đề lớn nhất không phải là màu sắc hay hiệu ứng, mà là:

1. Khung ứng dụng và điều hướng chưa thật sự thích nghi với mobile/tablet và route sâu.
2. Một số trang chi tiết đã tích lũy quá nhiều chức năng trong cùng một file và cùng một mặt phẳng giao diện.
3. Cách biểu diễn trạng thái kết nối, lỗi, dữ liệu trống và chế độ demo/live chưa đồng nhất, có thể làm cán bộ hiểu sai trạng thái thực của hệ thống.

Khuyến nghị chính là **giữ thiết kế hiện tại, cải thiện theo từng lớp**, ưu tiên cấu trúc và tính trung thực trước khi bổ sung thêm hiệu ứng hoặc trang mới.

### Mức trưởng thành hiện tại

| Hạng mục | Điểm tham khảo | Nhận xét ngắn |
| :--- | :---: | :--- |
| Hệ thống thiết kế | 8.0/10 | Token nền tảng tốt, nhận diện QNU rõ, dark mode có chủ đích |
| Tính nhất quán component | 7.5/10 | Có phân tầng UI/Admin/AI; vẫn còn nhiều màu và kiểu trình bày cục bộ |
| Trải nghiệm nghiệp vụ AI | 7.5/10 | Có chat, citation, DAG, OCR, RAG, ModelOps và handoff tương đối đầy đủ |
| Kiến trúc thông tin | 6.0/10 | Sidebar còn dày, ranh giới giữa Assistant/Workflow/Channel/Quality chưa tối ưu |
| Responsive | 5.5/10 | Nhiều trang có breakpoint nhưng App Shell vẫn thiên về desktop cố định |
| Accessibility | 6.5/10 | Radix/shadcn tạo nền tốt; vẫn có vùng click không semantic và chữ quá nhỏ |
| Khả năng bảo trì UI | 5.5/10 | Một số page vượt 700–1.600 dòng, khó sửa an toàn và khó kiểm thử riêng |
| Tính trung thực trạng thái dữ liệu | 5.5/10 | Đã có loading/empty/error nhưng chưa đồng bộ rõ Live, Degraded, Demo và Offline |

**Đánh giá tổng thể:** phù hợp mức **Internal Beta mạnh**. Chưa nên coi là Production UX cho nhiều đơn vị sử dụng cho đến khi hoàn tất responsive shell, route sâu, trạng thái dữ liệu trung thực và tách các trang lớn.

---

## 2. Những điểm đã làm tốt

### 2.1. Nhận diện thị giác đã có bản sắc riêng

- Academic Teal được đưa vào hệ thống token thay vì chỉ tô màu cục bộ.
- Light/Dark mode dùng semantic tokens như `background`, `card`, `foreground`, `muted`, `border`, `primary`.
- Quy chuẩn bán kính, chiều cao control, sidebar và topbar tương đối rõ.
- Giao diện nhìn giống một nền tảng quản trị chuyên dụng cho QNU hơn là template dashboard phổ thông.

Đây là phần nên **giữ ổn định**. Không cần thay đổi palette tổng thể hoặc đưa thêm nhiều màu thương hiệu mới.

### 2.2. Nền component có khả năng mở rộng

Frontend đã hình thành ba lớp tương đối đúng hướng:

- primitives trong `components/ui`;
- helper quản trị trong `components/admin`;
- component nghiệp vụ AI trong `components/ai`.

Các component như empty state, trạng thái, chat message, citation, attachment và DAG canvas giúp giảm nguy cơ mỗi trang tự phát minh một ngôn ngữ giao diện khác nhau.

### 2.3. Trải nghiệm AI có chiều sâu nghiệp vụ

Sản phẩm đã thể hiện được các khái niệm khó bằng giao diện tương đối trực quan:

- Trợ lý có cấu hình model chính/phụ, tri thức, workflow, guardrail và đánh giá.
- Kho tri thức có ingestion, OCR, chunks, facts, trạng thái indexing và đối soát.
- Workflow có canvas, catalog node, inspector và chạy thử.
- Chat có streaming, thinking state và trích dẫn.
- Conversations có bàn giao cán bộ và trạng thái hội thoại.
- ModelOps có provider/model/quota/usage thay vì chỉ là ô nhập API key.

Đây là lợi thế lớn của dự án. Khi tái cấu trúc, cần **gộp trải nghiệm nhưng không làm mất chiều sâu domain**.

### 2.4. Đã có nhiều trạng thái hệ thống cần thiết

Các màn hình đã bắt đầu quan tâm đến loading, empty state, lỗi, toast, confirm và trạng thái xử lý. Đây là bước tiến đáng kể so với UI chỉ hiển thị “happy path”.

### 2.5. Chất lượng kỹ thuật nền đang tốt

Tại thời điểm rà soát:

- `npm run lint`: đạt, 130 tệp được kiểm tra, không có lỗi.
- `npm run typecheck`: đạt, không có lỗi TypeScript.

Điều này cho thấy dự án có nền kỷ luật kỹ thuật tốt để tiếp tục cải thiện UI mà không cần tái xây dựng từ đầu.

---

## 3. Những điểm cần cải thiện theo mức ưu tiên

## 3.1. P0 — Cần xử lý trước khi mở rộng người dùng

### P0.1. App Shell chưa đáp ứng tốt mobile và tablet

`admin-shell.tsx` đang dựa nhiều vào khoảng đệm cố định tương ứng với sidebar thu gọn/mở rộng và vùng nội dung toàn cục `max-w-7xl`. Cấu trúc này phù hợp desktop nhưng dễ gây:

- thiếu không gian cho màn hình nhỏ;
- sidebar che nội dung hoặc làm nội dung bị ép;
- các workspace cần canvas rộng như Workflow/OCR/Chat không tận dụng hết viewport;
- khó triển khai mobile drawer đúng nghĩa.

**Đề xuất:**

- Dưới breakpoint `lg`, chuyển sidebar thành Sheet/Drawer có nút mở trong topbar.
- Tách ba kiểu layout: `standard`, `wide`, `full-bleed`.
- Chỉ dùng `max-w-7xl` cho form/list thông thường; DAG, OCR split-view, chat và conversations nên dùng `full-bleed`.
- Kiểm thử bắt buộc ở 360 px, 768 px, 1024 px và 1440 px.

### P0.2. Trạng thái Live/Degraded/Demo/Offline chưa thành một ngôn ngữ chung

Với nền tảng AI, lỗi kết nối không chỉ là lỗi kỹ thuật; nó quyết định dữ liệu trên màn hình có đáng tin hay không. Nếu mỗi trang tự xử lý khác nhau, cán bộ có thể nhầm dữ liệu mẫu, cache hoặc trạng thái offline là dữ liệu thật.

**Đề xuất:** xây dựng một state contract dùng chung:

| Trạng thái | Cách hiển thị bắt buộc |
| :--- | :--- |
| Loading | Skeleton theo đúng hình dạng nội dung, tránh spinner toàn trang kéo dài |
| Empty | Nói rõ “chưa có dữ liệu” và có hành động tiếp theo |
| Filter empty | Nói rõ bộ lọc không có kết quả, không dùng chung với empty database |
| Error | Hiện nguyên nhân thân thiện, mã tương quan nếu có và nút thử lại |
| Degraded | Cảnh báo dữ liệu/cache nào đang dùng và thời điểm cập nhật |
| Demo/Sample | Badge nổi bật, chỉ bật khi người dùng chủ động chọn xem mẫu |
| Live | Không cần badge ồn ào; chỉ hiện trạng thái kết nối ở vị trí vận hành phù hợp |

### P0.3. Loại bỏ thông tin kỹ thuật/dev khỏi trải nghiệm production

Topbar và sidebar vẫn có những chi tiết thiên về môi trường phát triển như tài khoản quản trị gán cứng, liên kết localhost Swagger/Qdrant, “Backend Connected” và port REST API. Những chi tiết này:

- không có ý nghĩa với cán bộ nghiệp vụ;
- có thể sai với môi trường triển khai;
- làm giảm cảm giác tin cậy của sản phẩm.

**Đề xuất:** chỉ hiển thị các liên kết kỹ thuật trong `DEV_MODE` hoặc khu vực System Diagnostics; thông tin người dùng lấy từ session; trạng thái backend chuyển thành Health Center có dữ liệu thật.

### P0.4. Một số vùng tương tác chưa semantic

Một số card/hàng sử dụng `div` có `onClick` thay cho `button` hoặc `a`, ví dụ trong trang Kho tri thức và Kênh tích hợp. Điều này làm giảm khả năng dùng bàn phím, screen reader và focus ring.

**Đề xuất:**

- Điều hướng dùng `a`/Link.
- Hành động dùng `button`.
- Card có nhiều hành động không nên biến toàn card thành một nút duy nhất.
- Mọi dialog/sheet phải có focus trap, tiêu đề và mô tả truy cập được.

## 3.2. P1 — Cần xử lý để hệ thống dễ hiểu và dễ phát triển

### P1.1. Sidebar đang phản ánh module kỹ thuật nhiều hơn công việc của người dùng

Các mục Assistant, Workflow, Nodes, Channels, Quality và Runs có quan hệ rất gần nhưng đang hiện như các đích đến ngang hàng. Điều này làm cán bộ phải hiểu kiến trúc nội bộ trước khi hoàn thành một công việc.

Nên thực hiện theo [`Kế hoạch 06`](./ke_hoach/06_ke_hoach_tai_cau_truc_chuc_nang_va_dieu_huong.md):

- Gộp trải nghiệm cấu hình Workflow, Playground, Channels, Quality và Runs vào **Assistant Workspace**.
- Gộp trải nghiệm OCR và Loại văn bản vào **Knowledge Workspace**.
- Vẫn giữ domain/backend độc lập để tránh tạo “big ball of mud”.
- Đưa Nodes, Tools và Workflow Library dùng chung vào khu vực Advanced/System.

### P1.2. Route hiện tại khó mở rộng và sidebar active chưa hiểu route con

Điều hướng trong `App.tsx` đang được xử lý thủ công bằng nhiều nhánh điều kiện. Sidebar chủ yếu so khớp đường dẫn tuyệt đối, nên route chi tiết có nguy cơ không giữ đúng trạng thái active.

**Đề xuất:**

- Dùng route config dạng cây làm nguồn duy nhất cho breadcrumb, sidebar, page title và permission metadata.
- Active state dùng prefix/matcher có kiểm soát, ví dụ `/assistants/:id/*` vẫn active “Trợ lý AI”.
- Đưa query/search/filter vào URL để F5, bookmark và chia sẻ được.
- Có redirect tương thích route cũ trong quá trình tái cấu trúc.

### P1.3. Các trang lớn đang trở thành “monolithic page”

Số dòng tại thời điểm rà soát:

| Tệp | Số dòng xấp xỉ | Rủi ro |
| :--- | ---: | :--- |
| `assistant-detail-page.tsx` | 1.601 | Nhiều domain cấu hình và dialog cùng một file |
| `collection-detail-page.tsx` | 1.459 | Documents, chunks, facts, actions và dialogs trộn nhau |
| `modelops-page.tsx` | 1.031 | Provider, model, quota và usage khó tách trách nhiệm |
| `scan-studio-page.tsx` | 919 | Canvas, inspector, toolbar và trạng thái OCR đan xen |
| `assistant-create-page.tsx` | 812 | Wizard, validation và API orchestration chung một scope |
| `dag-canvas-page.tsx` | 723 | Canvas, catalog, inspector và test runner cùng trang |

**Đề xuất cấu trúc:**

- Page chỉ điều phối route, query và layout.
- Feature section tách theo domain: Overview, Knowledge, Models, Workflow, Guardrails, Channels, Quality, Activity.
- Logic API và mutation chuyển vào hooks chuyên biệt.
- Dialog/Sheet lớn thành component riêng.
- Schema và mapper API đặt ngoài JSX.

Mục tiêu hợp lý: page container khoảng 150–300 dòng; section phức tạp có thể lớn hơn nhưng phải có một trách nhiệm rõ ràng.

### P1.4. Typography quá nhỏ ở nhiều khu vực

Có khoảng 210 lần sử dụng `text-[9px]` hoặc `text-[10px]`. Kích thước này có thể phù hợp cho nhãn kỹ thuật phụ trên canvas, nhưng không phù hợp làm thông tin quản trị thường xuyên.

**Đề xuất:**

- Nội dung phụ tối thiểu 12 px (`text-xs`).
- Nội dung bảng/form phổ biến 14 px (`text-sm`).
- Chỉ dùng 9–10 px cho metadata rất phụ, không mang quyết định nghiệp vụ.
- Không dùng uppercase + tracking rộng + 10 px cho đoạn dài.

### P1.5. Màu trạng thái đang được hardcode cục bộ quá nhiều

Rà soát tĩnh ghi nhận khoảng 249 lần dùng trực tiếp các nhóm màu Tailwind như emerald, blue, purple, slate và các biến thể khác. Một phần là màu trạng thái hợp lý, nhưng mật độ lớn tạo ra hai rủi ro:

- light/dark mode không đồng đều;
- cùng một trạng thái có nhiều màu khác nhau giữa các trang.

**Đề xuất:** bổ sung semantic tokens/component variants cho `success`, `warning`, `danger`, `info`, `draft`, `processing`, `ready`, `degraded`, `offline`; page không tự chọn shade.

### P1.6. Mật độ thông tin giữa các màn hình chưa đồng đều

Một số trang dùng nhiều KPI card, badge, icon, tab và toolbar cùng lúc. Khi mọi thứ đều nổi bật, người dùng khó biết việc nào quan trọng nhất.

**Đề xuất:**

- Mỗi trang có một primary action rõ ràng.
- KPI chỉ giữ số liệu dẫn đến quyết định; chỉ số kỹ thuật phụ đưa vào detail/diagnostics.
- Dùng progressive disclosure: tổng quan trước, cấu hình chuyên sâu sau.
- Tránh đặt nhiều badge màu cạnh nhau nếu chúng không biểu diễn trạng thái độc lập.

## 3.3. P2 — Nâng chất lượng sản phẩm sau khi ổn định cấu trúc

### P2.1. Chuẩn hóa motion và feedback

- Dùng transition ngắn cho hover/focus/open-close; tránh animation trang trí không mang thông tin.
- Tôn trọng `prefers-reduced-motion`.
- Mutation chậm cần hiển thị tiến độ hoặc trạng thái nền, không chỉ khóa nút.

### P2.2. Chuẩn hóa bảng và bộ lọc

- Header bảng sticky cho danh sách dài.
- Filter state nằm trong URL.
- Có trạng thái “không có dữ liệu” và “không khớp bộ lọc” riêng.
- Thao tác hàng đặt nhất quán ở cột cuối, destructive action luôn xác nhận.

### P2.3. Thiết lập visual regression

Tạo bộ ảnh chuẩn cho các màn hình trọng yếu ở light/dark và bốn kích thước viewport. Đây là cách bảo vệ chất lượng UI khi nhiều agent/session cùng sửa dự án.

---

## 4. Nhận xét theo nhóm màn hình

### 4.1. Dashboard

**Tốt:** tạo được cảm giác trung tâm vận hành và có khả năng gom KPI hệ thống.

**Cần cải thiện:** chỉ giữ KPI thật sự có hành động tiếp theo. Tránh trộn chỉ số kinh doanh, kỹ thuật và dữ liệu mẫu trong cùng một hàng. Mỗi KPI nên liên kết đến danh sách đã lọc tương ứng.

### 4.2. Trợ lý AI

**Tốt:** đây là domain giàu nhất của sản phẩm; đã có persona, knowledge, models, workflow, guardrails, channels, quality và versioning.

**Cần cải thiện:** biến trang chi tiết thành Assistant Workspace có navigation cấp hai hoặc section routing, thay vì tiếp tục thêm tab/dialog vào file 1.600 dòng. Header cần thể hiện rõ trạng thái Draft/Ready/Published/Degraded và hành động chính tiếp theo.

### 4.3. Kho tri thức

**Tốt:** master-detail, ingestion, chunks, facts và OCR verification là lợi thế nổi bật.

**Cần cải thiện:** tách rõ “Kho”, “Tài liệu” và “Quá trình xử lý”. Khi một tài liệu chưa ready, UI phải nói rõ đang ở bước nào và hành động nào khả dụng. OCR/Loại văn bản nên xuất hiện như khả năng bên trong Knowledge Workspace, không phải sản phẩm rời mà cán bộ phải tự kết nối trong đầu.

### 4.4. Chat/Playground

**Tốt:** có nền streaming, thinking và citation.

**Cần cải thiện:** luôn hiển thị trợ lý/model/version/knowledge scope đang được test. Citation phải mở được đúng nguồn, điều/khoản/trang. Khi RAG không có căn cứ, no-answer state phải khác rõ lỗi kỹ thuật.

### 4.5. Workflow và Nodes

**Tốt:** canvas trực quan và node catalog động là nền tảng mạnh.

**Cần cải thiện:** workflow nên được cấu hình chủ yếu trong ngữ cảnh một trợ lý. Library dùng chung và Nodes nên là khu vực nâng cao. Canvas cần full-bleed, minimap/zoom dễ dùng, keyboard support và cảnh báo node chưa cấu hình ngay trên sơ đồ.

### 4.6. ModelOps/Provider

**Tốt:** có mô hình Primary/Fallback, quota và usage.

**Cần cải thiện:** phân biệt rõ ba lớp Provider → Credential/Key Pool → Model Deployment. Select model trong Assistant phải chỉ hiển thị model khả dụng thật, có trạng thái health và lý do không chọn được. Không để người dùng chọn một ID rồi đến runtime mới phát hiện thiếu credential.

### 4.7. Conversations và Handoff

**Tốt:** master-detail phù hợp nghiệp vụ trực bàn và đã có vòng đời tiếp nhận.

**Cần cải thiện:** dùng layout rộng, giữ danh sách và hội thoại nhìn thấy đồng thời trên desktop; tablet/mobile chuyển sang deep route hoặc Sheet. Cần unread count, SLA timer, assignment owner và optimistic state có rollback khi gửi thất bại.

### 4.8. Channels

**Tốt:** giúp đưa trợ lý ra ngoài nền tảng.

**Cần cải thiện:** Channels nên là một section trong Assistant Workspace. Preview phải ghi rõ môi trường, assistant version và trạng thái publish; mã nhúng không được hiện như đã sẵn sàng nếu endpoint/runtime chưa health.

### 4.9. Evaluation/Quality

**Tốt:** các chỉ số Ragas tạo khác biệt với chatbot demo thông thường.

**Cần cải thiện:** giải thích ý nghĩa chỉ số bằng ngôn ngữ nghiệp vụ, cho phép drill-down từ metric đến test case/câu trả lời/citation sai. Không chỉ hiển thị điểm tổng hợp mà không chỉ ra hành động khắc phục.

---

## 5. Bộ quy chuẩn UI đề xuất bổ sung

### 5.1. Ba loại page layout

| Layout | Dùng cho | Quy tắc |
| :--- | :--- | :--- |
| `standard` | Form, cấu hình, danh sách vừa | Giới hạn chiều rộng, đọc dễ |
| `wide` | Dashboard, bảng, detail 2–3 cột | Rộng hơn, vẫn có gutter |
| `full-bleed` | DAG, OCR studio, chat, conversations | Chiếm viewport còn lại, tự quản lý panel |

### 5.2. Thứ bậc typography

- Page title: 24–30 px, một lần mỗi trang.
- Section title: 18–20 px.
- Card title/body: 14–16 px.
- Metadata phụ: tối thiểu 12 px.
- Không dùng 9–10 px cho nội dung cần đọc hoặc quyết định.

### 5.3. Quy tắc hành động

- Mỗi trang tối đa một primary action nổi bật.
- Secondary action dùng outline/ghost theo mức quan trọng.
- Destructive action không đặt cạnh primary action nếu dễ bấm nhầm.
- Action chưa khả dụng phải disabled kèm giải thích, không để bấm rồi mới báo lỗi chung.

### 5.4. Quy tắc trạng thái

- Một tên trạng thái chỉ có một màu/icon/nhãn trên toàn hệ thống.
- Badge không thay thế cho mô tả lỗi.
- Health kỹ thuật và lifecycle nghiệp vụ là hai trạng thái khác nhau.
- Không hiển thị dữ liệu seed/mock như live data.

---

## 6. Lộ trình cải thiện khuyến nghị

### Đợt 0 — Thiết lập baseline trực quan

- Khởi động Backend/Frontend thật.
- Chụp baseline các trang trọng yếu ở light/dark và bốn viewport.
- Lập danh sách lỗi overflow, focus, contrast, loading và API state.

### Đợt 1 — Responsive App Shell và route foundation

- Mobile sidebar drawer.
- Page layout variants.
- Route config dạng cây, breadcrumb và active matching route con.
- Đưa filter/search state vào URL.

### Đợt 2 — Tái cấu trúc workspace

- Thực hiện Assistant Workspace và Knowledge Workspace theo Kế hoạch 06.
- Giảm sidebar xuống khoảng 7–8 điểm đến chính.
- Giữ route redirect và domain boundary.

### Đợt 3 — Tách các trang lớn

- Ưu tiên `assistant-detail-page`, `collection-detail-page`, `modelops-page`, `scan-studio-page`.
- Tách feature sections, hooks, dialogs và mapper.
- Thêm test theo section/mutation quan trọng.

### Đợt 4 — Semantic status, typography và accessibility

- Chuẩn hóa status variants.
- Giảm hardcoded colors.
- Loại bỏ chữ 9–10 px ở nội dung nghiệp vụ.
- Sửa clickable `div`, keyboard navigation, focus và ARIA.

### Đợt 5 — Production polish

- Health Center và trạng thái degraded.
- Xóa/hạn chế các liên kết dev, identity hardcode.
- Visual regression, E2E viewport, dark mode và reduced motion.

---

## 7. Tiêu chí nghiệm thu UI/UX

- [ ] Sidebar dùng được ở 360 px và không che nội dung.
- [ ] Mọi route chi tiết giữ đúng active navigation và breadcrumb.
- [ ] DAG/OCR/Chat/Conversations dùng được layout rộng hoặc full-bleed.
- [ ] Không có nội dung nghiệp vụ quan trọng nhỏ hơn 12 px.
- [ ] Không còn `div onClick` cho điều hướng/hành động chính.
- [ ] Mỗi trang phân biệt loading, empty, filter-empty, error và degraded.
- [ ] Demo/sample data luôn có nhãn và chỉ xuất hiện khi người dùng chủ động bật.
- [ ] Provider/model không khả dụng bị chặn ngay tại bước cấu hình trợ lý.
- [ ] Các trang lớn được tách thành section/hook có trách nhiệm rõ ràng.
- [ ] Light/dark mode đạt contrast phù hợp ở các trạng thái chính.
- [ ] Không có liên kết localhost hoặc thông tin tài khoản gán cứng trong production UI.
- [ ] `npm run lint`, `npm run typecheck`, `npm run build` đều đạt.
- [ ] Bộ kiểm thử viewport và visual regression đạt cho các màn hình trọng yếu.

---

## 8. Những việc không nên làm

- Không thay toàn bộ design system hoặc palette khi chưa giải quyết cấu trúc.
- Không gộp vật lý Assistant, Workflow, Knowledge và ModelOps thành một module lớn ở backend/frontend.
- Không tiếp tục thêm tab/dialog vào các page trên 1.000 dòng.
- Không dùng animation, gradient hoặc shadow để che mật độ thông tin chưa hợp lý.
- Không tạo thêm một biến thể badge/status cục bộ nếu hệ thống đã có trạng thái tương đương.
- Không dùng mock/seed fallback để làm màn hình “trông có dữ liệu” khi kết nối thật bị lỗi.

---

## 9. Kết luận cuối

Frontend QNU AI Platform hiện có **nền thị giác tốt, bản sắc rõ và phạm vi nghiệp vụ mạnh**. Dự án đã qua giai đoạn cần “làm cho đẹp”; bước tiếp theo là làm cho giao diện **dễ hiểu, trung thực, thích nghi và dễ bảo trì**.

Nếu ưu tiên đúng thứ tự — App Shell responsive, trạng thái dữ liệu, route/workspace, tách page lớn, accessibility rồi mới production polish — chất lượng UI/UX có thể tăng đáng kể mà không làm mất thiết kế hiện tại hoặc sai lệch kiến trúc cốt lõi của dự án.
