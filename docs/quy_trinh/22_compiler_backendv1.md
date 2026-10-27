# 22 — Biên soạn bản nháp trong backendV1

Phạm vi BE: runtime chat ModelOps và Compiler v1, nối sau OCR đã hoàn tất.

```text
OCR đã hoàn tất và ghim revision/hash
→ POST compilation-runs (actor/role + Idempotency-Key)
→ snapshot nguồn + provider/model/capacity đã ghim
→ lưu job → dispatch ARQ sau commit
→ worker kiểm lại quyền/nguồn/model/quota
→ chat một lần → raw bất biến → schema/citation check
→ JSON/Markdown bản nháp có dẫn nguồn và bảng gốc
→ GET trạng thái/kết quả
```

Workspace là biên giới quyền **chỉ trong v1** theo ngoại lệ AGENTS.md. Bản nháp
không tự xuất bản hoặc đi vào retrieval. Nội dung OCR và LLM đều là dữ liệu không
tin cậy; model không quyết định quyền hoặc trạng thái duyệt.

Xem [hợp đồng API và vận hành Compiler](../../backendV1/docs/compiler-v1.md)
và [báo cáo Context645](../bao_cao/context645/REVIEW.md). Các quy trình Compiler
legacy ở mục 18 vẫn là luồng riêng; đợt này không chạy lại hoặc sửa Compiler đó.
