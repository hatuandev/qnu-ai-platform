# KẾ HOẠCH CHUẨN HÓA & ĐỒNG BỘ TAXONOMY LOẠI VĂN BẢN

> **Dự án đích**: `qnu-ai-platform`  
> **Nguồn tham chiếu**: `D:\DuAnPhanMem\qnu-ai-core`  
> **Ngày lập**: 17/09/2026  
> **Trạng thái**: **Đã triển khai nền tảng taxonomy v1**  
> **Phạm vi phiên này**: Đã triển khai backend, migration, ingestion integration, workflow/exporter và frontend quản trị. Sync runtime lấy catalog đã chuẩn hóa trong Platform, chưa có Core HTTP endpoint riêng vì `qnu-ai-core` hiện không cung cấp endpoint taxonomy.

### Quyết định triển khai

- Giữ nguyên 37 loại và 28 mã NĐ30/2020 làm taxonomy v1.
- Platform lưu runtime source of truth; catalog version/hash là nguồn import tương thích với Core.
- `Ma trận đề thi`, `Nghị định` và `Dự toán` không được đưa vào 37 loại v1; chúng là legacy/artifact và không được dùng làm mã taxonomy mới.
- Cho phép custom type ở cấp Platform; custom type không bị sync Core ghi đè.
- Sync thủ công qua API/UI ở giai đoạn đầu; có thể bổ sung scheduler sau khi có Core contract versioned.

---

## 1. Mục tiêu

Chuẩn hóa danh mục loại văn bản của QNU từ repo `qnu-ai-core`, sau đó đưa vào `qnu-ai-platform` theo một contract ổn định để dùng chung cho:

- Kho tri thức và luồng upload/ingestion.
- Parser/OCR và nhận diện metadata tài liệu.
- Hybrid RAG, structured facts và citation.
- Workflow drafting, template DOCX và artifact export.
- Frontend quản trị `/document-types`.

Kết quả cuối cùng cần đạt:

1. Có một mã định danh ổn định cho mỗi loại văn bản.
2. Không còn dùng lẫn label tiếng Việt, mã tiếng Anh và fallback hardcode.
3. Platform lưu được taxonomy bền vững trong PostgreSQL.
4. Có cơ chế sync idempotent, có version/hash/audit và không làm mất loại custom.
5. Tài liệu cũ vẫn đọc được thông qua lớp mapping tương thích ngược.

---

## 2. Kết quả khảo sát hiện trạng

### 2.1. Nguồn taxonomy trong `qnu-ai-core`

Nguồn danh mục chính nằm ở [`document_taxonomy.py`](D:/DuAnPhanMem/qnu-ai-core/services/platform-api/qnu_ai_platform/control_plane/domain/document_taxonomy.py:1).

Danh mục hiện có **37 loại**, gồm:

| Nhóm | Số lượng | Mã tiêu biểu |
|---|---:|---|
| `legal_internal` | 6 | `quy_che`, `quy_dinh`, `quyet_dinh`, `nghi_quyet` |
| `administrative` | 15 | `thong_bao`, `ke_hoach`, `cong_van`, `to_trinh`, `bao_cao` |
| `academic` | 6 | `giao_trinh`, `bai_giang`, `de_cuong_mon_hoc`, `bai_bao_khoa_hoc` |
| `forms` | 10 | `bieu_mau_hanh_chinh`, `giay_moi`, `phieu_chuyen`, `don_tu_sinh_vien` |

Trong đó có 28 mã được đánh dấu thuộc nhóm hình thức văn bản theo Nghị định 30/2020/NĐ-CP; 9 mã còn lại là nhóm đặc thù đào tạo, nghiên cứu và biểu mẫu của QNU.

### 2.2. API và hạn chế của repo cũ

Repo cũ đã có router [`document_types_router.py`](D:/DuAnPhanMem/qnu-ai-core/services/platform-api/qnu_ai_platform/interfaces/http/document_types_router.py:21) với các endpoint:

```text
GET    /platform/v1alpha1/document-types
GET    /platform/v1alpha1/document-types/{code}
POST   /platform/v1alpha1/document-types
PUT    /platform/v1alpha1/document-types/{code}
DELETE /platform/v1alpha1/document-types/{code}
POST   /platform/v1alpha1/document-types/reset
```

Schema cũ có các trường chính: `id`, `code`, `name`, `category`, `category_name`, `description`, `priority`, `retention_period`, `nd30`, `is_active`, `is_system_default`, `doc_count`, `created_at`, `updated_at`.

Các điểm không nên bê nguyên sang Platform mới:

- Repository cũ là singleton in-memory; phần “JSON file backing” mới chỉ nằm trong docstring, chưa có logic đọc/ghi file.
- Studio có một bản preset trùng lặp trong `services/studio-ui/lib/document-types-data.ts` và fallback bằng `localStorage`.
- `doc_count` là số liệu mẫu/hiển thị, phải được tính từ dữ liệu tài liệu thực tế ở Platform.
- `id`, timestamp và label nhóm không nên được coi là contract nguồn.

### 2.3. Phân biệt AI Core engine và Platform API

AI Core engine lịch sử chủ yếu nhận `document_type` dạng chuỗi theo từng module. Module drafting hiện hỗ trợ một subset 12 mã; parser hành chính chỉ tự nhận một số label như `THÔNG BÁO`, `QUYẾT ĐỊNH`, `CÔNG VĂN`, `TỜ TRÌNH`.

Vì vậy, kế hoạch này xem taxonomy trong lớp `services/platform-api` của repo cũ là **nguồn migration trực tiếp**. Không coi các chuỗi hardcode riêng lẻ trong parser hoặc workflow là nguồn danh mục chuẩn.

### 2.4. Platform mới còn thiếu gì

`qnu-ai-platform` hiện chưa có module backend `document_types` độc lập:

- `KnowledgeDocument` chưa có `document_type_code`, chỉ có `doc_metadata` JSONB.
- `DocumentResponse` chưa trả về loại văn bản.
- Chưa có bảng, router hoặc service CRUD taxonomy.
- `/document-types` trên frontend hiện đang dùng chung `KnowledgePage`, chưa phải trang quản lý riêng.
- Workflow đang dùng các giá trị khác chuẩn: `decision`, `submission`, `notice`, `official_dispatch`, `general_draft`.
- Exporter đang dùng enum label viết hoa và một số default cố định.

Các file YAML hiện có chứa một phần danh mục cho module `regulations` và `drafting`, nhưng backend mới chưa có Module Registry/loader sử dụng chúng làm nguồn runtime.

---

## 3. Nguyên tắc thiết kế được đề xuất

### 3.1. Khóa chuẩn

`code` là khóa nghiệp vụ ổn định, dạng `snake_case` và duy nhất toàn hệ thống. Label tiếng Việt (`name`) chỉ phục vụ hiển thị, tìm kiếm và xuất văn bản; không dùng làm khóa liên kết.

Ví dụ:

```text
quyet_dinh
cong_van
to_trinh
thong_bao
```

### 3.2. Phân biệt loại nguồn và loại artifact

Không dùng một trường cho tất cả ngữ cảnh:

- `document_type_code`: loại tài liệu nguồn trong Knowledge Base.
- `draft_document_type_code`: loại văn bản đang soạn thảo.
- `artifact_type`: loại sản phẩm sinh ra như `question_matrix`, `draft_document`, `report`.

Ví dụ, “Ma trận đề thi” là artifact nghiệp vụ, không nên ép vào taxonomy văn bản hành chính 37 loại.

### 3.3. Phân biệt loại văn bản với `module_code`

`module_code` chỉ biểu thị domain/profile như `regulations`, `admissions`, `library`, `drafting`. Một collection hoặc assistant có thể dùng nhiều loại văn bản; loại văn bản thuộc về từng document và có thể được dùng bởi nhiều workflow.

### 3.4. Quyền sở hữu dữ liệu

Trong giai đoạn chuyển đổi, taxonomy cũ là nguồn import. Sau khi import, Platform nên là **runtime source of truth** vì danh mục có metadata QNU, ưu tiên RAG, retention và liên kết template/workflow.

Nếu vẫn cần Core sử dụng danh mục, Core chỉ đọc qua contract versioned hoặc manifest đã phát hành; không để Core và Platform cùng ghi một taxonomy.

---

## 4. Contract dữ liệu mục tiêu

Manifest/API nên dùng các trường sau:

```json
{
  "taxonomy_version": "qnu-document-types.v1",
  "source_hash": "sha256:...",
  "items": [
    {
      "code": "quyet_dinh",
      "name": "Quyết định",
      "category_code": "legal_internal",
      "description": "Văn bản áp dụng pháp luật...",
      "priority": 9,
      "retention_period": "Vĩnh viễn",
      "is_nd30": true,
      "is_active": true,
      "is_system": true
    }
  ]
}
```

Không đồng bộ trực tiếp các trường dẫn xuất:

- `id`: Platform tự sinh hoặc dùng `code` làm khóa logic.
- `doc_count`: tính từ `knowledge_documents`.
- `category_name`: có thể derive từ bảng/category catalog.
- `created_at`, `updated_at`: Platform tự quản lý.

Platform nên bổ sung metadata đồng bộ: `source_system`, `source_version`, `source_hash`, `synced_at`, `is_custom`.

---

## 5. Kiến trúc đồng bộ đề xuất

```text
Taxonomy manifest/API nguồn
        │
        ▼
Core/Source Client + Schema Validation
        │
        ▼
Document Type Sync Service
        │  idempotent upsert theo code
        ▼
platform_document_types (PostgreSQL)
        │
        ├── KnowledgeDocument.document_type_code
        ├── Drafting/template resolver
        ├── Workflow field extraction
        ├── RAG metadata/filter/priority
        └── Frontend /document-types
```

### 5.1. API Platform dự kiến

```text
GET  /platform/v1alpha1/document-types
GET  /platform/v1alpha1/document-types/{code}
POST /platform/v1alpha1/document-types
PUT  /platform/v1alpha1/document-types/{code}
POST /platform/v1alpha1/document-types/sync
POST /platform/v1alpha1/document-types/{code}/deactivate
```

`DELETE` chỉ được phép với loại custom chưa được tham chiếu. Loại system hoặc loại đã gắn vào document/template phải chuyển sang `is_active = false` để bảo toàn lịch sử.

### 5.2. Module backend dự kiến

Tuân thủ cấu trúc module 4 file:

```text
backend/app/modules/document_types/
├── models.py
├── schemas.py
├── service.py
└── router.py
```

Kèm một Alembic migration tạo bảng `platform_document_types` và các index cho `code`, `category_code`, `is_active`.

---

## 6. Mapping tương thích ngược

| Giá trị cũ | Mã chuẩn | Xử lý |
|---|---|---|
| `decision` | `quyet_dinh` | Alias bắt buộc |
| `submission` | `to_trinh` | Alias bắt buộc |
| `notice` | `thong_bao` | Alias bắt buộc |
| `official_dispatch` | `cong_van` | Alias bắt buộc |
| `QUYẾT ĐỊNH` | `quyet_dinh` | Chuẩn hóa label → code |
| `THÔNG BÁO` | `thong_bao` | Chuẩn hóa label → code |
| `TỜ TRÌNH` | `to_trinh` | Chuẩn hóa label → code |
| `general_draft` | `unknown` hoặc `custom` | Không tự gán thành Công văn |
| `question_matrix` | `artifact_type` | Tách khỏi document taxonomy |
| `DỰ TOÁN` | Chưa quyết định | Không âm thầm map sai |
| `Nghị định` | Chưa có trong 37 loại | Cần quyết định nhóm văn bản pháp luật ngoài QNU |

Parser/OCR nên trả về đồng thời:

```json
{
  "document_type_code": "quyet_dinh",
  "document_type_label": "QUYẾT ĐỊNH",
  "confidence": 0.96,
  "source": "header_parser",
  "evidence": "QUYẾT ĐỊNH Số: 123/QĐ-ĐHQN"
}
```

Nếu không đủ tin cậy, giữ `unknown` và chuyển sang human review; không dùng fallback nghiệp vụ giả.

---

## 7. Lộ trình thực hiện

### Giai đoạn 0 — Duyệt phạm vi và chốt taxonomy ✅

- Xác nhận 37 loại hiện tại có phải danh mục chuẩn ban đầu hay không.
- Quyết định có bổ sung `du_toan`, `nghi_dinh`, `ma_tran_de_thi` hay tách chúng thành taxonomy/artifact khác.
- Chốt Platform là runtime source of truth sau migration.

**Đầu ra**: bản taxonomy v1 được phê duyệt.

### Giai đoạn 1 — Chuẩn hóa contract nguồn ✅

- Tách preset Python thành manifest JSON hoặc endpoint versioned.
- Canonicalize JSON và tạo SHA-256 hash.
- Viết schema validation cho code/category/priority/retention.
- Tạo bảng alias từ label cũ sang code chuẩn.

**Đầu ra**: `qnu-document-types.v1` và mapping legacy.

### Giai đoạn 2 — Xây backend Document Types trên Platform ✅

- Tạo module 4 file `document_types`.
- Tạo bảng PostgreSQL và unique constraint cho `code`.
- Thêm CRUD, filter, search, active-only.
- Thêm sync idempotent theo `code` và `source_hash`.
- Ghi audit kết quả sync: added/updated/deactivated/skipped/failed.

**Đầu ra**: API taxonomy chạy độc lập, dữ liệu không mất sau restart.

### Giai đoạn 3 — Gắn taxonomy vào Knowledge/Ingestion ✅

- Bổ sung `document_type_code` vào `KnowledgeDocument`.
- Upload nhận loại văn bản do người dùng chọn, cho phép bỏ trống để auto-detect.
- Parser/OCR map `document_type_label` sang code.
- Lưu confidence/evidence/source trong metadata.
- Bổ sung filter tài liệu theo `document_type_code`.

**Đầu ra**: mỗi document có loại chuẩn hoặc trạng thái `unknown` rõ ràng.

### Giai đoạn 4 — Gắn vào Workflow/Drafting/RAG 🟡

- Thay `decision`, `submission`, `notice`, `official_dispatch` bằng code chuẩn.
- Drafting resolver nhận `document_type_code` và tìm template theo code.
- Chỉ cho phép template/workflow khai báo loại đang active.
- RAG dùng `priority`/category làm metadata filter hoặc retrieval hint, không biến loại văn bản thành ranh giới dữ liệu.
- Tách `artifact_type` khỏi `document_type_code`.

**Đầu ra**: workflow, drafting và RAG dùng cùng một vocabulary.

### Giai đoạn 5 — Xây frontend `/document-types` ✅

- Tạo trang danh sách riêng, không dùng alias `KnowledgePage`.
- Hiển thị nhóm, mã, trạng thái, NĐ30, priority, retention và số document thật.
- Có trang chi tiết/chỉnh sửa riêng cho từng loại.
- Có thao tác sync/reset theo quyền admin.
- Bỏ fallback localStorage đối với dữ liệu nghiệp vụ; nếu API lỗi phải hiển thị trạng thái lỗi/stale rõ ràng.

**Đầu ra**: quản trị taxonomy bằng Platform API thật.

### Giai đoạn 6 — Kiểm thử và vận hành 🟡

- Backend: Ruff và toàn bộ pytest.
- Kiểm thử sync lặp lại không tạo bản ghi trùng.
- Kiểm thử source thay đổi, source mất kết nối, hash không đổi.
- Kiểm thử không xóa loại đã được document/template tham chiếu.
- Frontend: lint, typecheck, build và E2E CRUD/sync.
- Kiểm tra UTF-8/NFC cho toàn bộ label tiếng Việt.
- Ghi correlation ID, source version và sync result vào structured log.

**Đầu ra**: taxonomy có thể vận hành, khôi phục và kiểm toán.

---

## 8. Tiêu chí nghiệm thu

- [x] API trả đủ 37 loại v1 với code ổn định.
- [x] Không còn route `/document-types` trỏ nhầm vào trang Knowledge list.
- [x] Restart backend không làm mất dữ liệu taxonomy/custom type (startup sync idempotent).
- [x] Sync lần thứ hai không tạo duplicate.
- [x] `KnowledgeDocument` nhận `document_type_code`; tài liệu bỏ trống ghi rõ source `unknown`.
- [x] Không đồng bộ `doc_count` hardcode từ preset; count lấy từ database.
- [x] Các chuỗi cũ được mapping về code chuẩn hoặc được gắn cờ `unclassified`.
- [x] Workflow extractor và exporter dùng mã canonical; exporter tách `document_type_code` khỏi label.
- [x] Không hard-delete system type hoặc type đang được tham chiếu; chỉ deactivate.
- [x] Backend Ruff/pytest và frontend lint/typecheck/build đạt.

Các phần còn lại cho đợt sau: Core phát hành endpoint/manifest versioned để Platform sync qua HTTP, parser/OCR auto-classification có confidence/evidence, E2E CRUD/sync và scheduler sync.

---

## 9. Rủi ro và cách kiểm soát

| Rủi ro | Cách kiểm soát |
|---|---|
| Hai repo cùng sửa taxonomy | Chỉ một nguồn ghi; Platform giữ bản runtime, Core/manifest chỉ phát hành version |
| Label tiếng Việt bị dùng làm khóa | Chỉ dùng `code`; label chỉ là display value |
| Xóa loại đang được dùng | Deactivate/archive, kiểm tra reference trước thao tác |
| Parser nhận diện sai | Lưu confidence/evidence, ngưỡng manual review, không fallback sang loại bất kỳ |
| `doc_count` từ preset bị hiểu là số thật | Tính lại từ database Platform |
| Core API unavailable khi sync | Giữ bản đã sync gần nhất kèm `source_hash`/`synced_at`, báo stale rõ ràng |
| Trộn loại nguồn với loại output | Tách `document_type_code` và `artifact_type` |
| Lệch cấu hình module YAML và DB | YAML chỉ dùng blueprint/import; runtime đọc PostgreSQL |

---

## 10. Các quyết định cần duyệt trước khi triển khai

1. Giữ nguyên 37 loại hiện tại làm taxonomy v1 hay bổ sung ngay các loại đang xuất hiện trong parser/dữ liệu mẫu (`DỰ TOÁN`, `Nghị định`, `Ma trận đề thi`)?
2. Đồng ý để Platform là runtime source of truth sau lần import đầu tiên hay bắt buộc Core tiếp tục là nguồn phát hành chính?
3. `Ma trận đề thi` và các loại sản phẩm tương tự có được tách thành `artifact_type` không?
4. Cho phép custom document type theo từng tenant/workspace hay chỉ admin QNU được tạo?
5. Có cần endpoint sync tự động theo lịch, hay giai đoạn đầu chỉ sync thủ công qua nút admin?

**Đề xuất mặc định của kế hoạch**: dùng 37 loại làm v1; coi Platform là runtime source of truth; tách artifact type; hỗ trợ custom type có kiểm soát; giai đoạn đầu sync thủ công và có thể chuyển sang scheduled sync sau khi contract ổn định.
