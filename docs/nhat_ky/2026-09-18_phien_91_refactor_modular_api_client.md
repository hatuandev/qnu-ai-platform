# NHẬT KÝ LÀM VIỆC — PHIÊN #91 (2026-09-18)
## Tái Cấu Trúc Phân Rã api-client.ts Thành Kiến Trúc Modular Domain Services & Facade Pattern

---

### 1. Thông Tin Phiên Làm Việc
- **Ngày thực hiện**: 2026-09-18
- **Thời gian bắt đầu/kết thúc**: 16:55 – 17:15 (UTC+7)
- **Kỹ sư phụ trách**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Mục tiêu chính**: Phân rã tệp nguyên khối `frontend/src/services/api-client.ts` (trên 2.070 dòng) đang vi phạm nguyên tắc "Zero Big-Ball-of-Mud" và "Single Responsibility Principle" (SRP) của `AGENTS.md`, tổ chức lại thành các module chuyên biệt theo đúng Domain Driven Design, đồng thời áp dụng **Facade Pattern** để bảo đảm **Zero Breaking Changes (100% tương thích ngược)** cho toàn bộ 25 component/trang trong dự án.

---

### 2. Vấn Đề Kỹ Thuật Trước Tái Cấu Trúc
Tệp `frontend/src/services/api-client.ts` qua nhiều đợt phát triển đã phình to tới **2.074 dòng code**, gộp chung:
1. **38 TypeScript Interfaces**: Nằm chen chúc giữa các API calls (từ Health, Assistant, Knowledge, OCR, ModelOps, Token Quota, Evaluation, Tool...).
2. **Datasets tĩnh lớn**: Mảng `ADMINISTRATIVE_TEMPLATES` (văn bản mẫu NĐ 30) và `UIS_MAJORS_DATABASE` (danh mục 40 ngành đào tạo ĐH Quy Nhơn) chiếm hơn 300 dòng code tĩnh.
3. **Quá nhiều trách nhiệm**: Hơn 45 methods phục vụ 8 phân hệ khác nhau nằm chung trong một đối tượng `apiClient` khổng lồ, gây khó khăn cho việc review code, bảo trì và tối ưu bundle tree-shaking.

---

### 3. Kiến Trúc Sau Tái Cấu Trúc (Target Modular Architecture)

Hệ thống được tái cấu trúc thành 4 tầng rõ ràng:

```
frontend/src/
├── constants/                   # 1. Tầng dữ liệu danh mục tĩnh
│   ├── administrative-templates.ts   (Mẫu văn bản hành chính NĐ 30)
│   ├── uis-majors.ts                 (CSDL ngành đào tạo ĐH Quy Nhơn)
│   └── index.ts                      (Barrel export)
│
├── types/                       # 2. Tầng TypeScript interfaces theo domain
│   ├── common.ts                     (BackendHealth, NodeManifest)
│   ├── assistants.ts                 (AssistantItem, LifecycleConfig)
│   ├── knowledge.ts                  (Collection, Document, IngestionTask, BoundingBox)
│   ├── modelops.ts                   (Provider, ApiKey, ModelOption, Quota)
│   ├── tools.ts                      (ToolItem, ExecuteRequest/Response)
│   ├── evaluation.ts                 (EvaluationMetrics, RunItem, GapInbox)
│   ├── workflows.ts                  (WorkflowRun, ExecuteRequest)
│   ├── domain-templates.ts           (AdministrativeTemplate, UisMajorInfo)
│   ├── studio-ocr.ts                 (StudioOCRRegion, StudioOCRDocument)
│   └── index.ts                      (Barrel export)
│
└── services/                    # 3. Tầng Domain API Services & Facade
    ├── http-client.ts                (BASE_URL & isJsonObject helper)
    ├── system-api.ts                 (Health & Node catalog)
    ├── knowledge-api.ts              (Collections & Documents API)
    ├── jobs-api.ts                   (Background Ingestion Jobs API)
    ├── modelops-api.ts               (Providers, Presets, Keys, Quota API)
    ├── tools-api.ts                  (Tool listing & execution API)
    ├── evaluation-api.ts             (TM-08 Metrics & Benchmark Runs API)
    ├── workflow-runs-api.ts          (Workflow Run History & Execution API)
    ├── ocr-studio-api.ts             (Document Studio & Verification API)
    ├── assistants-api.ts             (Assistants CRUD & Lifecycle API)
    └── api-client.ts                 # 4. Facade tổng hợp (57 dòng)
```

---

### 4. Chi Tiết Các Thay Đổi (Key Changes)

1. **Tạo mới `frontend/src/constants/`**:
   - [`administrative-templates.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/constants/administrative-templates.ts): Tách mảng mẫu văn bản hành chính Nghị định 30.
   - [`uis-majors.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/constants/uis-majors.ts): Tách danh mục 40 ngành tuyển sinh ĐH Quy Nhơn.
   - [`index.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/constants/index.ts): Barrel re-export.

2. **Tạo mới `frontend/src/types/`**:
   - Phân loại toàn bộ 38 TypeScript interfaces vào các tệp: `common.ts`, `assistants.ts`, `knowledge.ts`, `modelops.ts`, `tools.ts`, `evaluation.ts`, `workflows.ts`, `domain-templates.ts`, `studio-ocr.ts`.
   - [`index.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/types/index.ts): Re-export toàn bộ kiểu dữ liệu.

3. **Tạo mới các Domain API Services**:
   - [`http-client.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/http-client.ts): Khai báo `BASE_URL` và type-guard `isJsonObject`.
   - [`system-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/system-api.ts): 40 dòng, chứa `getHealth()`, `getNodeCatalog()` và type-guard `isNodeManifest`.
   - [`knowledge-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/knowledge-api.ts): 215 dòng, quản trị kho tri thức, upload, parse preview, approve tài liệu.
   - [`jobs-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/jobs-api.ts): 110 dòng, quản trị các tác vụ nền bóc tách ingestion.
   - [`modelops-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/modelops-api.ts): 260 dòng, quản trị LLM providers, presets, key rotation, default models, token quota.
   - [`tools-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/tools-api.ts): 50 dòng, cung cấp API tools, mẫu văn bản, tra cứu ngành UIS.
   - [`evaluation-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/evaluation-api.ts): 75 dòng, API đo lường Ragas TM-08, chạy benchmark, gap inbox.
   - [`workflow-runs-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/workflow-runs-api.ts): 50 dòng, API chạy workflow và xem lịch sử thực thi.
   - [`ocr-studio-api.ts`](file:///d:/DuAnPhanMem/qnu-ai-platform/frontend/src/services/ocr-studio-api.ts): 130 dòng, API phục vụ Document Verification Studio.

4. **Tái cấu trúc Facade `frontend/src/services/api-client.ts`**:
   - Thu gọn từ 2.074 dòng xuống chỉ còn **57 dòng**.
   - Re-export toàn bộ types từ `@/types` và constants từ `@/constants`.
   - Xuất đối tượng tổng hợp `apiClient` kết hợp từ các domain APIs (`...systemApi, ...assistantsApi, ...knowledgeApi, ...jobsApi, ...modelopsApi, ...evaluationApi, ...toolsApi, ...workflowRunsApi, ...ocrStudioApi`).
   - Xuất các domain API riêng lẻ để các component trong tương lai có thể import trực tiếp (tree-shaking tối ưu).

---

### 5. Kết Quả Kiểm Thử (Verification)

| Công cụ / Lệnh | Kết Quả | Chi Tiết |
| :--- | :---: | :--- |
| `npm run lint` | ✅ **0 Lỗi** | Biome linter quét 115 files (152ms), sạch sẽ 100% |
| `npm run typecheck` | ✅ **0 Lỗi** | `tsc --noEmit` hoàn thành mã 0, không có bất kỳ lỗi type mismatch nào |
| `npm run build` | ✅ **Thành công** | Vite build đóng gói bundle thành công trong 9.50s |
| `uv run ruff check .` | ✅ **0 Lỗi** | Backend Ruff linting hoàn toàn sạch |
| `uv run --extra dev pytest tests/test_rag.py tests/test_assistants.py tests/test_evaluation.py -v` | ✅ **27/27 Pass** | 100% test backend vượt qua (5.75s) |
| `python scripts/check_mojibake.py` | ✅ **0 Lỗi** | Quét 253 files toàn dự án, không có lỗi font hay ký tự rác UTF-8 |

---

### 6. Đánh Giá & Lợi Ích
1. **Tuân thủ quy định Clean Code của dự án (`AGENTS.md`)**:
   - Xóa bỏ triệt để file "quái vật" 2.000 dòng (`Zero Big-Ball-of-Mud`).
   - Đảm bảo tính đơn trách nhiệm (`Single Responsibility Principle`): mỗi service file có độ dài từ 40 đến 260 dòng, tập trung duy nhất vào 1 domain.
2. **Zero Breaking Changes**: Toàn bộ 25 components/trang hiện hữu không cần chỉnh sửa bất kỳ đường dẫn import nào, vẫn chạy mượt mà.
3. **Mở đường cho kiến trúc mở rộng**: Các tính năng mới có thể import theo từng domain client cụ thể (`modelopsApi`, `knowledgeApi`,...) mà không phải kéo theo toàn bộ monolithic client.
