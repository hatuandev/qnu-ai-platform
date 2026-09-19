# KẾ HOẠCH TÁI CẤU TRÚC CHỨC NĂNG VÀ ĐIỀU HƯỚNG QNU AI PLATFORM

> **Dự án:** `qnu-ai-platform`
>
> **Ngày lập:** 19/09/2026
>
> **Trạng thái:** BẢN KẾ HOẠCH — CHỜ PHÊ DUYỆT TRIỂN KHAI
>
> **Nguyên tắc trung tâm:** Gộp trải nghiệm theo hành trình người dùng, không gộp tùy tiện các domain backend có vòng đời, dữ liệu và cơ chế versioning khác nhau.

---

## 1. Bối cảnh

Sidebar hiện có khoảng 16 mục điều hướng cấp cao, đồng thời trộn ba loại chức năng:

1. Đối tượng nghiệp vụ mà cán bộ thực sự quản lý: Trợ lý AI, Kho tri thức, Hội thoại, Provider.
2. Công cụ nằm bên trong một hành trình lớn hơn: Workflow, Nodes, Tools, OCR, Loại văn bản, Evaluation, Runs.
3. Màn hình kỹ thuật/phát triển: Developer API, Design System.

Hệ quả:

- Người dùng phải chuyển qua nhiều phân hệ để hoàn thiện một Trợ lý.
- Quan hệ Assistant → Workflow → Run → Evaluation không rõ trong điều hướng.
- OCR và Loại văn bản bị trình bày như sản phẩm độc lập, trong khi thực tế là các bước/cấu hình của Knowledge Ingestion.
- Node Catalog và Tool Catalog chiếm vị trí ngang hàng với nghiệp vụ chính dù chủ yếu phục vụ DAG authoring.
- Một số trang lớn đang có xu hướng trở thành monolithic page, khó bảo trì và khó deep-link tới đúng tác vụ.

Kế hoạch này tái cấu trúc kiến trúc thông tin theo hai workspace trọng tâm:

- **Assistant Workspace:** xây dựng, thử nghiệm, kiểm định và triển khai một Trợ lý AI hoàn chỉnh.
- **Knowledge Workspace:** nạp, OCR, đối soát, phân loại, phê duyệt và lập chỉ mục tài liệu.

---

## 2. Mục tiêu

1. Giảm sidebar từ khoảng 16 mục xuống còn 7–8 mục dễ hiểu.
2. Đưa Workflow, Playground, Channels, Quality và Runs vào đúng ngữ cảnh Trợ lý.
3. Đưa OCR và Loại văn bản vào đúng vòng đời Kho tri thức.
4. Gom Nodes và Tools thành khu vực năng lực nâng cao, nhưng giữ model/runtime riêng.
5. Giữ Hội thoại/Handoff, ModelOps và các màn hình vận hành toàn cục ở đúng vai trò độc lập.
6. Bảo toàn URL cũ bằng redirect để không làm hỏng bookmark hoặc liên kết hiện có.
7. Không tạo một trang Assistant khổng lồ; mọi chức năng chuyên sâu phải có child route và page component riêng.
8. Không thay đổi hành vi runtime, dữ liệu, provider key hoặc workflow published trong đợt tái cấu trúc giao diện đầu tiên.

---

## 3. Phạm vi và ngoài phạm vi

### 3.1. Trong phạm vi

- Cấu trúc sidebar và breadcrumbs.
- Route hierarchy và deep linking.
- Assistant Workspace và Knowledge Workspace.
- Các trang tổng hợp vận hành, chất lượng và năng lực nâng cao.
- Redirect URL cũ → URL mới.
- Tách các page lớn thành route-level components.
- Chuẩn hóa quyền sở hữu giữa Assistant, Workflow, Channel và Evaluation.
- Contract cần thiết để pin immutable workflow version khi publish Assistant.

### 3.2. Ngoài phạm vi của đợt UI đầu tiên

- Viết lại Workflow Engine.
- Gộp bảng dữ liệu Assistant và Workflow.
- Thay đổi thuật toán RAG/OCR/chunking.
- Thay đổi Provider credentials, circuit breaker hoặc seed provider.
- Thay đổi nội dung năm Trợ lý QNU đã seed.
- Xóa API cũ ngay lập tức.
- Triển khai RBAC/SSO phức tạp.

---

## 4. Nguyên tắc kiến trúc bắt buộc

### 4.1. Gộp UX, giữ domain độc lập

| Chức năng | Gộp ở giao diện | Gộp backend/database | Quyết định |
|---|---:|---:|---|
| Assistant + Workflow | Có | Không | Workflow là execution engine/versioned asset của Assistant. |
| Assistant + Playground | Có | Không cần | Playground gọi Assistant runtime thật. |
| Assistant + Channels | Có | Không hoàn toàn | Channel có lifecycle triển khai riêng nhưng cấu hình theo Assistant. |
| Assistant + Evaluation | Có theo phạm vi Assistant | Không | Giữ evaluation run/dataset riêng để audit. |
| Assistant + Runs | Có theo phạm vi Assistant | Không | Giữ WorkflowRun/NodeRun riêng. |
| Knowledge + OCR | Có | Không | OCR là chiến lược ingestion, adapter vẫn độc lập. |
| Knowledge + Document Types | Có ở settings | Không | Taxonomy dùng chung cho Knowledge, RAG và Workflow. |
| Nodes + Tools | Có ở thư viện năng lực | Không | Node điều phối; Tool thực thi hành động. |
| Provider + Assistant | Chỉ nhúng selector/readiness | Không | Provider là tài nguyên dùng chung toàn hệ thống. |
| Conversations + Assistant | Chỉ lọc/liên kết | Không | Inbox cần nhìn toàn bộ kênh và trợ lý. |

### 4.2. Không dùng Monolithic Tabbed Page

Không nhồi Workflow Canvas, Chat Playground, Channels, Evaluation và Runs vào một file `assistant-detail-page.tsx`.

Mỗi chức năng chuyên sâu phải có URL và component riêng:

```text
/assistants/:assistantId
/assistants/:assistantId/knowledge
/assistants/:assistantId/models
/assistants/:assistantId/workflow
/assistants/:assistantId/tools
/assistants/:assistantId/playground
/assistants/:assistantId/channels
/assistants/:assistantId/quality
/assistants/:assistantId/runs
```

### 4.3. Một nguồn sự thật cho navigation

- Route metadata, breadcrumb, sidebar visibility và page title dùng chung một cấu hình typed.
- Không tiếp tục mở rộng chuỗi `if (currentPath === ...)` phân tán trong `App.tsx`.
- Nếu chưa chuyển sang router library, phải tạo route resolver tập trung và có test.
- Khuyến nghị dài hạn: sử dụng typed router hỗ trợ nested route và search params; việc thay router không được làm chặn Đợt 1.

### 4.4. Bảo toàn runtime và dữ liệu

- Assistant vẫn tham chiếu Workflow bằng identity rõ ràng.
- Chat production chạy immutable published workflow version.
- Route refactor không được tự động publish draft.
- Không đổi `workflow_id`, assistant code, collection ID hoặc provider ID trong đợt chuyển UI.
- Không dùng mock data khi API lỗi.

---

## 5. Kiến trúc thông tin đích

### 5.1. Sidebar đề xuất

```text
TỔNG QUAN
└── Bảng điều khiển

XÂY DỰNG AI
├── Trợ lý AI
├── Kho tri thức
└── Mô hình & Provider

VẬN HÀNH
├── Hội thoại & Handoff
├── Chất lượng & Lỗ hổng tri thức
└── Giám sát thực thi

HỆ THỐNG
├── Tích hợp & API
└── Nâng cao
    ├── Thư viện Workflow
    ├── Nodes
    ├── Tools
    ├── Loại văn bản
    └── Design System (chỉ development)
```

### 5.2. Quy tắc hiển thị

- Sidebar chính chỉ hiển thị các mục cán bộ sử dụng thường xuyên.
- “Nâng cao” mặc định thu gọn.
- Design System chỉ xuất hiện khi `DEV_MODE=true` hoặc truy cập URL trực tiếp.
- Node Catalog, Tool Catalog và Workflow Library không bị xóa; chỉ chuyển khỏi luồng chính.
- Mỗi Assistant/Collection có local navigation riêng ở trang chi tiết.

---

## 6. Assistant Workspace

### 6.1. Vai trò

Assistant là composition root cho vòng đời bảy lớp:

1. Persona & Scope.
2. Knowledge Binding.
3. ModelOps & Fallback.
4. Guardrails.
5. Tools & Workflow.
6. Output & Citations.
7. Evaluation & Observability.

### 6.2. Route và trang

| Route | Trang | Trách nhiệm |
|---|---|---|
| `/assistants` | Assistant List | Danh sách, tìm kiếm, trạng thái, tạo/nhân bản. |
| `/assistants/new` | Assistant Creation | Wizard bảy bước, tạo draft an toàn. |
| `/assistants/:id` | Assistant Overview | Persona, readiness, trạng thái publish, quick actions. |
| `/assistants/:id/knowledge` | Assistant Knowledge | Chọn collection, retrieval policy, link sang collection detail. |
| `/assistants/:id/models` | Assistant Models | Primary/fallback từ catalog Provider thật. |
| `/assistants/:id/workflow` | Assistant Workflow | DAG Canvas toàn màn hình, draft/version/publish. |
| `/assistants/:id/tools` | Assistant Tools | Allowlist, approval policy, tool readiness. |
| `/assistants/:id/playground` | Assistant Playground | Chat thử runtime thật, citations, tool calls, debug trace. |
| `/assistants/:id/channels` | Assistant Channels | Widget, domain allowlist, deployment version, health. |
| `/assistants/:id/quality` | Assistant Quality | TM-08, golden cases, knowledge gaps, version comparison. |
| `/assistants/:id/runs` | Assistant Runs | Run history đã lọc theo Assistant. |

### 6.3. Workflow ownership

Mặc định mỗi Assistant sở hữu một **private workflow binding**:

```text
Assistant
└── Private Workflow
    ├── Draft
    ├── Published Version
    ├── Runs
    └── Approval Requests
```

Quy tắc:

- Tạo Assistant → tự tạo workflow draft từ template phù hợp.
- Nhân bản Assistant → mặc định fork workflow thành bản riêng.
- Dùng shared workflow chỉ khi người dùng chủ động chọn chế độ nâng cao.
- Publish Assistant → pin `published_workflow_version_id` bất biến.
- Rollback Assistant → khôi phục đúng workflow version trong snapshot.
- Chỉnh draft không làm thay đổi chat production.

### 6.4. Playground và Chat Studio

- Chuyển Chat Studio dùng để thử nghiệm vào `/assistants/:id/playground`.
- Playground bắt buộc dùng assistant code/id từ route, không dùng danh sách hardcode.
- Global `/chat` có thể giữ làm launcher: yêu cầu chọn Assistant rồi redirect vào Playground.
- Nếu sau này có cổng chat dành cho sinh viên, tách URL public khỏi admin Playground.

### 6.5. Channels

- Cấu hình Widget nằm trong Assistant vì mã nhúng luôn gắn với Assistant.
- Trang global Integrations chỉ tổng hợp deployment và trạng thái các kênh.
- Channel config phải lưu bền vững, có domain allowlist và API base rõ ràng.

### 6.6. Quality và Knowledge Gaps

- Mỗi Assistant có trang Quality riêng.
- Global Quality chỉ dùng so sánh toàn bộ Assistant và xử lý backlog chung.
- Knowledge Gap giữ liên kết tới Assistant, collection và conversation nguồn.

---

## 7. Knowledge Workspace

### 7.1. Route đề xuất

```text
/knowledge
/knowledge/collections/:collectionId
/knowledge/collections/:collectionId/ingest
/knowledge/collections/:collectionId/facts
/knowledge/documents/:documentId
/knowledge/documents/:documentId/verify
/knowledge/documents/:documentId/ocr
/knowledge/settings/document-types
/knowledge/settings/document-types/:code
/knowledge/ocr-lab
```

### 7.2. Gộp OCR vào ingestion

Luồng chuẩn:

```text
Chọn Collection
→ Upload và lưu Storage
→ Nhận diện loại tệp
→ Chọn parser/OCR
→ Trích xuất
→ Đối soát Human-in-the-loop
→ Phê duyệt
→ Index Dense/Sparse/Facts
```

- Người dùng không cần rời Collection để mở OCR Studio.
- `/knowledge/ocr-lab` chỉ dành cho thử nghiệm độc lập, có nhãn Lab rõ ràng.
- Original file, extracted artifact và verified revision phải có provenance xuyên suốt.

### 7.3. Đưa Loại văn bản vào Knowledge Settings

- Taxonomy không còn là mục top-level.
- Trang taxonomy vẫn giữ detail page và deep link.
- Cấu hình loại văn bản được dùng bởi upload recommendation, parser/chunker và legal priority.
- Backend document-types vẫn là module độc lập và có contract versioned.

---

## 8. Capabilities và Operations

### 8.1. Thư viện năng lực

```text
/advanced/capabilities
/advanced/capabilities/nodes
/advanced/capabilities/tools
/advanced/workflows
/advanced/workflows/:workflowId
```

- Nodes và Tools nằm chung trong một khu vực điều hướng, không nhập chung model dữ liệu.
- DAG Canvas dùng Node Catalog động và Tool allowlist của Assistant.
- `/advanced/workflows` quản lý template/shared workflow; private workflow ưu tiên mở từ Assistant.

### 8.2. Giám sát thực thi

```text
/operations/runs
/operations/runs/:runId
/operations/approvals
```

- Assistant và Workflow detail chỉ hiển thị run đã lọc theo ngữ cảnh.
- Global Operations hỗ trợ search toàn hệ thống, lỗi, timeout và pending approval.
- Approval Inbox phải xử lý approve/reject, actor, reason và audit trail.

### 8.3. Hội thoại

```text
/conversations
/conversations/:conversationId
```

- Giữ là inbox toàn cục vì cán bộ cần tiếp quản hội thoại từ nhiều Assistant/kênh.
- Hỗ trợ filter bằng search params: assistant, channel, status, assignee.
- Từ Assistant có deep link tới danh sách hội thoại đã lọc.

---

## 9. ModelOps, Integrations và Developer

### 9.1. ModelOps giữ độc lập

```text
/models
/models/:providerId
```

- Assistant chỉ lấy catalog model theo provider active và capability.
- Provider keys, circuit breaker, quota và model health vẫn quản lý tập trung.
- Không đưa form chỉnh API key vào Assistant Workspace.

### 9.2. Tích hợp và API

```text
/settings/integrations
/settings/api-keys
/settings/webhooks
/settings/channels
```

- Chỉ hiển thị chức năng đã có backend thật.
- Developer API key prototype phải được ẩn/ghi nhãn cho tới khi có persistence và authentication tương ứng.
- Design System chuyển thành dev-only route.

---

## 10. Bảng ánh xạ URL cũ → URL mới

| URL hiện tại | URL đích | Cách xử lý |
|---|---|---|
| `/chat?assistant=:code` | `/assistants/:id/playground` | Resolve code → id hoặc hỗ trợ id/code thống nhất. |
| `/channels` | `/settings/channels` | Global overview; cấu hình cụ thể redirect tới Assistant Channels. |
| `/workflows` | `/advanced/workflows` | Giữ redirect và breadcrumb mới. |
| `/workflows/:id` | Assistant workflow hoặc `/advanced/workflows/:id` | Nếu private/bound thì mở trong Assistant; nếu shared/template thì mở Advanced. |
| `/runs` | `/operations/runs` | Redirect giữ query filters. |
| `/evaluation` | `/quality` | Global quality overview. |
| `/ocr` | `/knowledge/ocr-lab` | Giữ Studio độc lập dưới nhãn Lab. |
| `/document-types` | `/knowledge/settings/document-types` | Redirect bảo toàn detail code. |
| `/nodes` | `/advanced/capabilities/nodes` | Catalog nâng cao. |
| `/tools` | `/advanced/capabilities/tools` | Tool registry nâng cao. |
| `/developer` | `/settings/integrations` | Chỉ bật phần có backend thật. |
| `/design-system` | Giữ URL trực tiếp | Ẩn khỏi sidebar production. |

Redirect phải tồn tại tối thiểu một chu kỳ phát hành và có test F5/deep link.

---

## 11. Lộ trình triển khai

### Đợt 0 — Khóa contract và baseline

**Mục tiêu:** Chốt route, ownership và hành vi hiện tại trước khi di chuyển UI.

**Công việc**

- Lập inventory toàn bộ route, links, breadcrumbs và query params.
- Chốt mapping Assistant ↔ Workflow ↔ Published Version.
- Chốt private/shared workflow ownership.
- Ghi baseline E2E cho 5 luồng chính: Assistant, Knowledge ingest, Chat, Handoff, Provider.
- Đánh dấu chức năng prototype chưa có backend thật.
- Không thay đổi sidebar ở đợt này.

**Nghiệm thu**

- Có route map được phê duyệt.
- Có test chứng minh URL cũ hoạt động trước migration.
- Có backup/snapshot workflow và assistant config.

### Đợt 1 — Navigation shell và compatibility redirects

**Mục tiêu:** Giảm độ rối của sidebar mà chưa thay đổi nghiệp vụ.

**Công việc**

- Tạo typed navigation/route metadata.
- Tổ chức sidebar mới theo bốn nhóm.
- Ẩn Advanced và Design System phù hợp môi trường.
- Thêm redirect URL cũ → URL mới.
- Chuẩn hóa breadcrumbs và active state cho nested routes.
- Giữ page hiện tại làm implementation phía sau route mới.

**Nghiệm thu**

- Không có dead link.
- F5 trên tất cả URL mới hoạt động.
- Back/forward browser hoạt động đúng.
- Không thay đổi API payload hoặc dữ liệu.

### Đợt 2 — Assistant Workspace

**Mục tiêu:** Một Assistant trở thành điểm vào duy nhất của vòng đời bảy lớp.

**Công việc**

- Tạo Assistant Workspace layout và local navigation.
- Tách `assistant-detail-page.tsx` thành các route-level pages nhỏ.
- Đưa Workflow Canvas vào `/assistants/:id/workflow`.
- Đưa Playground, Channels, Quality và Runs vào child routes.
- Query mọi dữ liệu theo assistant identity thật.
- Giữ global pages dưới dạng portfolio/operations view.

**Nghiệm thu**

- Cán bộ có thể cấu hình → thử → kiểm định → publish → triển khai kênh mà không rời Assistant Workspace.
- Không có trang component quái vật mới.
- Workflow draft và production published version được phân biệt rõ.

### Đợt 3 — Workflow ownership và publish consistency

**Mục tiêu:** Hoàn thiện quan hệ Assistant–Workflow mà không gộp backend domain.

**Công việc**

- Tạo private workflow khi tạo Assistant.
- Clone Assistant fork workflow theo mặc định.
- Bổ sung ownership metadata `private/shared/template` nếu chưa có.
- Pin `published_workflow_version_id` khi publish Assistant.
- Snapshot/rollback Assistant bao gồm chính xác workflow version.
- Shared workflow thay đổi phải cảnh báo danh sách Assistant bị ảnh hưởng.

**Nghiệm thu**

- Sửa draft không tác động chat production.
- Clone Assistant không vô tình dùng chung mutable workflow.
- Rollback khôi phục đúng cấu hình và DAG version.

### Đợt 4 — Knowledge Workspace

**Mục tiêu:** Nối kín upload → OCR → verify → approve → index trong một workspace.

**Công việc**

- Tạo local navigation cho Collection/Document.
- Chuyển OCR Studio vào document/ingestion route.
- Chuyển Document Types vào Knowledge Settings.
- Giữ OCR Lab cho thử nghiệm chuyên sâu.
- Tách `collection-detail-page.tsx` thành các page/component theo trách nhiệm.
- Bảo toàn provenance và trạng thái job thật.

**Nghiệm thu**

- Người dùng không phải rời Collection trong luồng nạp tài liệu.
- Tài liệu pending/approved/indexed hiển thị đúng trạng thái thật.
- Không có fallback nội dung OCR hoặc document giả trong LiveMode.

### Đợt 5 — Operations, Capabilities và Integrations

**Mục tiêu:** Dọn các màn hình kỹ thuật khỏi hành trình chính nhưng không mất năng lực quản trị.

**Công việc**

- Tạo Operations Runs và Approval Inbox.
- Tạo Advanced Capabilities cho Nodes/Tools.
- Chuyển Workflow Library vào Advanced.
- Tạo Settings/Integrations cho channel overview, API keys và webhooks.
- Ẩn Developer prototype và Design System khỏi production sidebar.

**Nghiệm thu**

- Người dùng nghiệp vụ chỉ thấy chức năng cần thiết.
- Quản trị viên vẫn truy cập đầy đủ Nodes, Tools, shared workflows và run diagnostics.

### Đợt 6 — Dọn tương thích và nghiệm thu cuối

**Mục tiêu:** Loại trùng lặp sau khi route mới ổn định.

**Công việc**

- Đo telemetry hoặc kiểm tra usage của URL cũ.
- Xóa component wrapper không còn dùng, không xóa API/domain.
- Cập nhật toàn bộ docs/quy trình và ảnh hướng dẫn.
- Chạy full Backend/Frontend/E2E suite.
- Kiểm tra accessibility, responsive, dark mode và bundle size.

**Nghiệm thu**

- Không còn navigation item trùng chức năng.
- Không có route orphan hoặc dead component.
- Tất cả quality gates đạt 100%.

---

## 12. Tệp dự kiến tác động khi triển khai

### Frontend trọng tâm

- `frontend/src/navigation/config.ts`
- `frontend/src/App.tsx` hoặc route configuration mới.
- `frontend/src/layouts/app-sidebar.tsx`
- `frontend/src/pages/assistant-detail-page.tsx`
- `frontend/src/pages/assistant-create-page.tsx`
- `frontend/src/pages/dag-canvas-page.tsx`
- `frontend/src/pages/chat-studio-page.tsx`
- `frontend/src/pages/channels-page.tsx`
- `frontend/src/pages/evaluation-page.tsx`
- `frontend/src/pages/runs-page.tsx`
- `frontend/src/pages/collection-detail-page.tsx`
- `frontend/src/pages/scan-studio-page.tsx`
- `frontend/src/pages/document-types-page.tsx`
- `frontend/src/pages/node-catalog-page.tsx`
- `frontend/src/pages/tools-page.tsx`

Các page lớn phải được tách thành thư mục domain và route-level components; không tiếp tục tăng kích thước file hiện tại.

### Backend chỉ khi đến đợt ownership/persistence

- `backend/app/modules/assistants/`
- `backend/app/modules/workflows/`
- `backend/app/modules/conversations/`
- `backend/app/modules/evaluation/`
- Module Channels/Integrations mới nếu được phê duyệt.

Không chỉnh ModelOps credential storage trong kế hoạch UI; việc bảo mật provider key thuộc remediation plan riêng.

---

## 13. Chiến lược kiểm thử

### 13.1. Frontend

- Unit test route resolver/navigation config.
- Test active sidebar và breadcrumbs cho child routes.
- Test redirect giữ path parameter/search params.
- Test Assistant local navigation và deep linking.
- Test empty/error/loading state không dùng mock nghiệp vụ.
- Chạy bắt buộc:

```bash
npm run lint
npm run typecheck
npm run build
```

### 13.2. Backend

- Contract test Assistant → pinned Workflow Version.
- Test private/shared workflow ownership.
- Test clone/fork và rollback.
- Test filter Runs/Evaluation/Conversation theo Assistant.
- Chạy bắt buộc khi có thay đổi backend:

```bash
uv run ruff check .
uv run --extra dev pytest -v
```

### 13.3. E2E tối thiểu

1. Tạo Assistant → sinh private workflow → mở Canvas.
2. Cấu hình Knowledge/Models/Tools → lưu → F5 không mất state.
3. Chat Playground chạy đúng Assistant và published workflow version.
4. Quality hiển thị run/gap đúng Assistant.
5. Channel widget lấy đúng Assistant/API base.
6. Upload tài liệu → OCR → verify → approve → index trong Knowledge Workspace.
7. URL cũ redirect tới đúng màn hình mới.
8. Global Conversation Inbox lọc đúng Assistant.
9. Global Runs mở được Assistant/Workflow nguồn.
10. Design System không xuất hiện trên production sidebar.

---

## 14. Rủi ro và biện pháp kiểm soát

| Rủi ro | Mức độ | Biện pháp |
|---|---:|---|
| Gộp UI thành một file lớn | Cao | Child routes và component SRP bắt buộc. |
| URL/bookmark cũ bị hỏng | Cao | Redirect compatibility + E2E F5. |
| Nhầm draft workflow với production | Cao | Pin immutable version và badge trạng thái rõ. |
| Clone Assistant dùng chung mutable workflow | Cao | Fork private workflow mặc định. |
| Sidebar gọn nhưng chức năng kỹ thuật bị mất | Trung bình | Advanced area và Command Menu vẫn truy cập được. |
| Route refactor làm mất query filters | Trung bình | Typed search params và redirect tests. |
| Thay UI đồng thời thay runtime gây khó rollback | Cao | Đợt 1–2 ưu tiên UI shell; runtime ownership ở Đợt 3 riêng. |
| Session song song sửa cùng file | Cao | Chia ownership theo đợt/tệp, kiểm tra worktree trước patch. |

---

## 15. Chiến lược rollback

- Mỗi đợt là một checkpoint độc lập.
- Giữ navigation config cũ trong lịch sử Git, không comment-out code.
- URL mới ban đầu chỉ là lớp tổ chức lại trên API hiện có.
- Nếu Workspace mới lỗi, redirect tạm về page cũ mà không thay đổi dữ liệu.
- Migration ownership workflow phải có script downgrade và không xóa workflow hiện hữu.
- Không xóa route cũ trước khi E2E và kiểm tra bookmark hoàn tất.

---

## 16. Definition of Done

Kế hoạch chỉ được xem là hoàn thành khi:

- Sidebar production còn tối đa 8 mục chính.
- Assistant Workspace bao phủ đủ vòng đời bảy lớp.
- Knowledge Workspace bao phủ upload → OCR → verification → indexing.
- Mọi trang chuyên sâu có deep route và breadcrumb.
- Provider, Workflow, Tool, Node, Evaluation, Conversation vẫn là domain độc lập.
- Assistant publish pin đúng immutable workflow version.
- Không có mock/fake-success trong LiveMode.
- URL cũ có redirect và test.
- Không có file page mới vượt ngưỡng hợp lý hoặc gom nhiều trách nhiệm.
- Frontend lint/typecheck/build đạt 0 lỗi.
- Backend Ruff/Pytest đạt 100% khi có thay đổi backend.
- E2E các hành trình chính đạt 100%.
- `docs/quy_trinh/`, `docs/memory/`, `docs/nhat_ky/` và `docs/WORK_LOG.md` được đồng bộ.

---

## 17. Thứ tự ưu tiên khuyến nghị

1. Đợt 0 — Route/ownership baseline.
2. Đợt 1 — Sidebar và redirects, rủi ro thấp.
3. Đợt 2 — Assistant Workspace, giá trị UX cao nhất.
4. Đợt 4 — Knowledge Workspace.
5. Đợt 3 — Workflow ownership/publish consistency sau khi UX đã ổn định.
6. Đợt 5 — Operations/Capabilities/Integrations.
7. Đợt 6 — Dọn tương thích và full acceptance.

Đợt 2 và Đợt 4 có thể chia cho hai nhánh phát triển độc lập nếu tránh sửa chung `App.tsx`, navigation config và layout trong cùng thời điểm.

---

## 18. Quyết định cần giữ cố định khi triển khai

1. **Không gộp bảng Assistant và Workflow.**
2. **Không biến Assistant Detail thành trang tab khổng lồ.**
3. **Private workflow là mặc định; shared workflow là chế độ nâng cao.**
4. **Provider và Conversation Inbox vẫn là domain độc lập.**
5. **OCR là một phần của Knowledge Ingestion; OCR Lab chỉ là công cụ nâng cao.**
6. **Nodes/Tools không còn là menu nghiệp vụ chính nhưng vẫn có trang quản trị.**
7. **Design System không xuất hiện trong production navigation.**
8. **Mọi thay đổi route phải backward-compatible trước khi xóa đường dẫn cũ.**

Đây là phương án cân bằng giữa trải nghiệm gọn, cấu trúc code sạch và khả năng vận hành lâu dài của QNU AI Platform.
