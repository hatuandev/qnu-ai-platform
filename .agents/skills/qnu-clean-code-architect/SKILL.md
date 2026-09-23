---
name: qnu-clean-code-architect
description: >-
  Use this skill ONLY when explicitly requested by the user (or via $qnu-clean-code-architect) for deep architectural reviews, major refactoring audits, or code quality retrospectives across Frontend and Backend. Routine code tasks already enforce basic clean code standards via AGENTS.md.
---

# Hướng Dẫn Kỹ Thuật Clean Code Khi Vibe Coding (QNU AI Platform)

Tài liệu này là cẩm nang bắt buộc dành cho mọi AI Agent và lập trình viên khi tham gia phát triển dự án **`qnu-ai-platform`** theo phương pháp **Vibe Coding**.

> **Định nghĩa Tôn chỉ**: *Vibe Coding là sự thăng hoa về tốc độ và tư duy kiến trúc cùng AI, NHƯNG tuyệt đối KHÔNG ĐƯỢC để lại rác kỹ thuật. Tốc độ cao phải đi cùng sự chuẩn mực (Speed + Craftsmanship).*

---

## 1. Mười Điều Răn Clean Code Bắt Buộc (The 10 Commandments)

```text
┌────────────────────────────────────────────────────────────────────────┐
│               10 ĐIỀU RĂN CLEAN CODE KHI VIBE CODING                   │
├────────────────────────────────────────────────────────────────────────┤
│ 1. The Boy Scout Rule      │ Để lại file sạch hơn lúc tìm thấy        │
│ 2. Zero Dead Code & Junk   │ Xóa thẳng tay code cũ & console.log rác   │
│ 3. Zero 'any' Type Safety  │ 100% Typed, cấm bypass compiler           │
│ 4. Self-Documenting Naming │ Tên nói lên mục đích (is/has/fetch/format)│
│ 5. Single Responsibility   │ Hàm < 40 dòng, 1 việc duy nhất            │
│ 6. Early Return Pattern    │ Triệt tiêu lồng ghép if/else đa tầng      │
│ 7. No Swallowed Exceptions │ Cấm catch rỗng, luôn fallback/toast/log   │
│ 8. Clean-As-You-Go Loop    │ Lint & Typecheck 0 lỗi trước khi trả lời  │
│ 9. Zero Hardcoded Data     │ Cấm fake submit, cấm gán chết mock cũ     │
│ 10. Zero Mojibake          │ 100% UTF-8 NFC, triệt tiêu vỡ font tiếng Việt│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Chuẩn Mực Frontend (React 19, TypeScript, Biome, Tailwind v4)

### 2.1. Đặt Tên Biến & Hàm Chuẩn Mực (Self-Documenting)
- **Boolean States**: Bắt buộc có tiền tố biểu thị trạng thái:
  - `isLoading`, `isSubmitting`, `isOpen`, `hasError`, `canEdit`, `shouldFallback`
  - ❌ *Tránh*: `loading`, `open`, `status1`, `flag`, `check`
- **Action Handlers**: Bắt đầu bằng `handle` hoặc `on`:
  - `handleFileSelect`, `handleSubmitIngestion`, `handleCopyChunk`, `handleToggleProvider`
  - Event props nhận vào: `onSuccess`, `onClose`, `onSelectProvider`
- **Data Transforms & Utilities**: Bắt đầu bằng động từ:
  - `formatFileSize`, `calculateElapsedMs`, `extractSectionTitle`, `parseOcrResponse`

### 2.2. Không Dùng `any` — Khai Báo Type Chặt Chẽ
```typescript
// ❌ CẤM TUYỆT ĐỐI (Làm suy yếu Type System):
const handleResponse = (data: any) => {
  console.log(data.models[0].name);
};

// ✅ CHUẨN MỰC (Explicit Types hoặc Generic):
interface ProviderModelItem {
  id: string;
  name: string;
  contextWindow?: number;
}

interface ProviderResponse {
  providerId: string;
  models: ProviderModelItem[];
}

const handleResponse = (data: ProviderResponse): string | null => {
  return data.models[0]?.name ?? null;
};
```

### 2.3. Tối Giản State & Tránh Đồng Bộ Thừa Trong `useEffect`
- **Nguyên tắc**: Nếu một giá trị có thể tính toán được từ `props` hoặc `state` hiện có, **KHÔNG tạo state mới và KHÔNG dùng `useEffect` để gán lại**:
```typescript
// ❌ Xấu (Đồng bộ thừa, dễ gây re-render loop & stale state):
const [query, setQuery] = useState("");
const [filteredDocs, setFilteredDocs] = useState<Document[]>([]);
useEffect(() => {
  setFilteredDocs(docs.filter(d => d.title.includes(query)));
}, [query, docs]);

// ✅ Đẹp (Derived State với useMemo):
const [query, setQuery] = useState("");
const filteredDocs = useMemo(() => {
  if (!query.trim()) return docs;
  const lower = query.toLowerCase();
  return docs.filter(d => d.title.toLowerCase().includes(lower));
}, [docs, query]);
```

### 2.4. Tránh Lồng Ghép If-Else Phức Tạp (Guard Clauses / Early Return)
```typescript
// ❌ Xấu (Pyramid of Doom):
function renderDocumentBadge(doc: KnowledgeDocument | null) {
  if (doc) {
    if (doc.status === "completed") {
      return <Badge variant="success">Hoàn tất</Badge>;
    } else {
      if (doc.status === "processing") {
        return <Badge variant="warning">Đang xử lý</Badge>;
      } else {
        return <Badge variant="danger">Lỗi</Badge>;
      }
    }
  }
  return null;
}

// ✅ Đẹp (Guard Clauses & Lookup Record):
const STATUS_BADGE_MAP: Record<string, { variant: "success" | "warning" | "destructive"; label: string }> = {
  completed: { variant: "success", label: "Hoàn tất" },
  processing: { variant: "warning", label: "Đang xử lý" },
  failed: { variant: "destructive", label: "Lỗi" },
};

function renderDocumentBadge(doc: KnowledgeDocument | null) {
  if (!doc) return null;
  const config = STATUS_BADGE_MAP[doc.status] ?? { variant: "warning", label: doc.status };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
```

### 2.5. Tách Component Nhỏ Gọn (Sub-Component Extraction)
- Nếu một thẻ JSX hoặc đoạn lặp danh sách dài quá 30 dòng, hãy tách thành sub-component riêng (trong cùng file hoặc file riêng nếu dùng chung):
  - Ví dụ: `ChunkCardItem`, `FactTableRow`, `StageProgressStep`.
### 2.6. Tận Dụng Component UI Có Sẵn & Chỉ Tạo Mới Khi Chưa Tồn Tại (Component Reuse First)
- **Luôn tìm và dùng lại component trong `@/components/ui/`**:
  - ❌ *Cấm dùng HTML thô*: Không viết `<input type="checkbox">`, `<button className="...">`, `<select>` hay tự vẽ điều khiển form thuần.
  - ✅ *Dùng component chuẩn*: Nhập `Checkbox`, `Switch`, `Button`, `Input`, `Dialog`, `Select`, `Badge`, `Card`, `Tabs`, `Table`, `Sheet` từ `@/components/ui/`.
- **Nguyên tắc tạo mới**:
  - Chỉ tạo component mới khi và chỉ khi trong `@/components/ui/` **hoàn toàn chưa có thành phần tương đương**.
  - Component mới phải đặt tại `src/components/ui/<name>.tsx`, dựng trên Radix UI / shadcn, hỗ trợ `forwardRef`, đầy đủ TypeScript types, tuân thủ token màu OKLCH (`border-primary`, `bg-primary`, `text-primary-foreground`), và export dùng chung.


---

## 3. Chuẩn Mực Backend (FastAPI, Python 3.14, Pydantic v2, Ruff)

### 3.1. 100% Asynchronous & Type Annotated
- Mọi hàm trong service, router, database query đều có type hints và `async/await`:
```python
# ✅ Chuẩn mực:
async def get_collection_documents(
    db: AsyncSession,
    collection_id: str,
    limit: int = 50,
) -> list[DocumentSchema]:
    stmt = select(DocumentModel).where(DocumentModel.collection_id == collection_id).limit(limit)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [DocumentSchema.model_validate(r) for r in records]
```

### 3.2. Không Nuốt Exception & Mã Lỗi Chuẩn RFC 7807
```python
# ❌ CẤM (Nuốt lỗi, khó debug):
try:
    await do_ingest()
except Exception:
    pass

# ✅ Chuẩn mực (Ghi log ngữ cảnh & Ném AppException):
try:
    await do_ingest()
except S3StorageError as exc:
    logger.warning("MinIO S3 storage failed for file %s: %s", file_name, exc)
    raise StorageUnavailableException(detail=f"Không thể kết nối MinIO lưu trữ: {exc}") from exc
```

### 3.3. Dọn Dẹp Imports và Tự Động Định Dạng Bằng Ruff
- Trước khi hoàn thành, kiểm tra và dọn dẹp định dạng có phạm vi trong các tệp vừa sửa:
  ```bash
  uv run ruff check <tệp_hoặc_thư_mục_vừa_sửa> --fix
  ```
  *(Lưu ý: Chỉ chạy trên phạm vi tệp/thư mục thuộc task hiện tại, tránh dùng cờ `--fix` trên toàn bộ repository `.` gây sửa lan ngoài ý muốn).*

---

## 4. Bảng Tra Cứu Anti-Patterns & Cách Khắc Phục

| Anti-Pattern Thường Gặp | Hậu Quả | Cách Sửa Chuẩn Clean Code |
| :--- | :--- | :--- |
| Comment out code cũ | Gây nhiễu code, hiểu lầm | Xóa bỏ hoàn toàn (Git đã lưu lịch sử) |
| `console.log("data", res)` | Ô nhiễm console browser, lộ data | Dọn sạch trước khi submit |
| `catch (e) {}` | Lỗi biến mất bí hiểm | Thêm log, toast, hoặc fallback value |
| `as any` trên biến lạ | Mất type check, runtime crash | Khai báo interface hoặc `unknown` + type guard |
| Hardcode màu `bg-blue-600` | Gãy nhận diện Teal, lỗi Dark Mode | Dùng `bg-primary`, `text-primary`, `border-border` |
| `key={idx}` trên danh sách | Render sai vị trí khi sort/filter | Dùng ID duy nhất (`key={item.id}`) |
| Hàm dài > 80 dòng | Khó đọc, khó test, vi phạm SRP | Tách nhỏ hàm, tách sub-components |
| Hardcode giá trị form / Mock cũ | Up file mới nhưng luôn ra file cũ | Khởi tạo rỗng, truyền động `file` & `docId` |
| `setTimeout` rồi gọi cứng ID cũ | Bẫy Fake Submit, liệt tính năng | Gọi API thật hoặc tạo state động từ tệp mới |
| Mojibake / Vỡ font tiếng Việt | Xuất hiện ký tự rác `?`, `\ufffd`, vỡ chữ | Luôn mã hóa UTF-8 NFC, open(..., encoding="utf-8"), charset trong Blob |

---

## 5. Checklist Tự Kiểm Toán Clean Code (Self-Audit Checklist)

Mỗi lần AI Agent chuẩn bị trả kết quả cho người dùng, hãy rà soát danh sách 7 câu hỏi:
- [ ] 1. Tôi đã xóa toàn bộ code comment thừa và `console.log` debug chưa?
- [ ] 2. Tôi đã xóa các `import` và biến khai báo nhưng không dùng chưa?
- [ ] 3. Mã nguồn có sử dụng `any` không? Có hardcode màu sắc thô không?
- [ ] 4. Đã chạy `npm run lint` và `npm run typecheck` đạt 0 lỗi chưa?
- [ ] 5. Tôi có đang **hardcode dữ liệu mẫu vào form, fake submit bằng `setTimeout` trỏ ID cũ, hay clone đè dữ liệu cũ lên file mới của người dùng** không?
- [ ] 6. Mã nguồn và dữ liệu có bị **lỗi vỡ font tiếng Việt (Mojibake, ký tự rác `\ufffd`, `?`, thiếu UTF-8)** không?
- [ ] 7. File này có sạch sẽ, dễ đọc hơn lúc tôi bắt đầu chạm vào không?
