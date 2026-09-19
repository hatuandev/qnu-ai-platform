# KẾ HOẠCH TỐI ƯU HỆ THỐNG SKILLS AN TOÀN, KHÔNG GIẢM CHẤT LƯỢNG CODE

> **Dự án**: `qnu-ai-platform`  
> **Ngày lập**: 19/09/2026  
> **Trạng thái**: SẴN SÀNG TRIỂN KHAI — CHƯA SỬA CÁC SKILL  
> **Chiến lược**: Tối ưu bảo thủ; sửa sai lệch và cơ chế kích hoạt trước, không cắt các tiêu chuẩn kiến trúc cốt lõi.

---

## 1. Mục tiêu

Giảm lượng ngữ cảnh skill bị nạp không cần thiết trong mỗi task nhưng vẫn bảo toàn đầy đủ:

1. Kiến trúc Modular Monolith Backend và cấu trúc module chuẩn.
2. Kiến trúc Frontend ba tầng, Design System QNU và Master–Detail Deep Routing.
3. Quy trình bảy bước tạo và vận hành Trợ lý AI.
4. Hybrid RAG, ingestion, ModelOps, guardrails, citation và No-Answer Policy.
5. Clean Code, type safety, UTF-8, chống mojibake và chống dữ liệu giả trong LiveMode.
6. Các quality gate bắt buộc: lint, typecheck, build, Ruff và pytest.

Mục tiêu là **giảm context được nạp cho từng task**, không phải giảm tiêu chuẩn chất lượng hoặc xóa kiến thức chuyên môn của dự án.

---

## 2. Phạm vi an toàn

### 2.1. Trong phạm vi

- Sửa `description` để mỗi skill chỉ kích hoạt đúng domain.
- Sửa đường dẫn repo cũ và thông tin kỹ thuật đã lệch code.
- Giải quyết mâu thuẫn giữa skill và `AGENTS.md`.
- Thêm chính sách invocation cho skill có phạm vi quá rộng.
- Xây dựng ma trận kiểm thử lựa chọn skill trước khi nghiệm thu.
- Chỉ chuyển ví dụ dài sang `references/` sau khi đã kiểm chứng không có regression.

### 2.2. Ngoài phạm vi

- Không thay đổi mã nguồn Backend hoặc Frontend.
- Không thay đổi kiến trúc, schema CSDL, API contract hoặc workflow runtime.
- Không xóa bất kỳ quality gate nào.
- Không làm nhẹ tiêu chuẩn chống hallucination, bảo mật, type safety hoặc UTF-8.
- Không rút gọn `AGENTS.md` trong ba giai đoạn đầu.
- Không tắt toàn bộ skill hoặc buộc người dùng phải gọi thủ công mọi skill.

### 2.3. Nguyên tắc bảo toàn

> Một quy tắc chỉ được di chuyển khỏi `SKILL.md` khi đã xác định rõ nguồn sự thật thay thế và có kiểm thử chứng minh agent vẫn tuân thủ quy tắc đó.

---

## 3. Các tiêu chuẩn cốt lõi phải giữ nguyên

| Nhóm | Quy tắc bất biến | Nguồn sự thật |
| :--- | :--- | :--- |
| Backend | Async I/O, 4-file module, thin router, RFC 7807 | `AGENTS.md` + `qnu-backend-architect` |
| Frontend | React/TypeScript, 3 tầng component, semantic token, deep routing | `AGENTS.md` + `qnu-frontend-architect` |
| Trợ lý AI | Vòng đời bảy bước, guardrails, knowledge binding, evaluation | `qnu-chatbot-builder` |
| RAG | Dense + Sparse, RRF, rerank, facts, citation, no-answer | `qnu-rag-pipeline` |
| Ingestion | Storage trước parse, NFC, parser/chunker strategy, indexing | `qnu-knowledge-ingestion` |
| ModelOps | Adapter, fallback, circuit breaker, quota, cost tracking | `qnu-modelops-resilience` |
| Clean Code | Zero `any`, zero dead code, không nuốt lỗi, không fake data | `AGENTS.md`; skill dùng cho review/refactor sâu |
| Verification | Lint, typecheck, build, Ruff, pytest | `AGENTS.md` và CI/scripts |
| Tài liệu | Memory, snapshot, work log và quy trình đồng bộ | `AGENTS.md` |

Không được triển khai tối ưu nếu bất kỳ quy tắc nào trong bảng trên bị mất nguồn sở hữu rõ ràng.

---

## 4. Hiện trạng và hướng xử lý

| Skill | Dung lượng | Nhận xét | Hướng xử lý bảo thủ |
| :--- | ---: | :--- | :--- |
| `qnu-backend-architect` | 4.391 byte | Gọn; lệnh pytest chưa đồng nhất | Giữ implicit, sửa lệnh kiểm thử |
| `qnu-frontend-architect` | 14.705 byte | Nặng nhất; Offline Seed Fallback xung đột LiveMode | Giữ implicit, sửa trigger và fallback contract |
| `qnu-chatbot-builder` | 7.073 byte | Dễ kích hoạt khi chỉ thảo luận chung | Giữ implicit nhưng thu hẹp theo vòng đời Assistant |
| `qnu-rag-pipeline` | 4.292 byte | Payload và liên kết đã cũ | Giữ implicit, đồng bộ với code hiện tại |
| `qnu-knowledge-ingestion` | 3.999 byte | Ranh giới tương đối tốt | Giữ implicit, sửa liên kết và boundary |
| `qnu-modelops-resilience` | 2.729 byte | Gọn và chuyên biệt | Giữ nguyên implicit |
| `qnu-clean-code-architect` | 9.878 byte | Trigger bao phủ gần như mọi task code | Tắt implicit; vẫn gọi rõ ràng khi review/refactor |

Các sai lệch cần xử lý:

1. Có 10 liên kết `file:///` trỏ về `D:/DuAnPhanMem/DeTaiAI/qnu-ai-platform`.
2. Skill Frontend yêu cầu dùng seed fallback khi Backend lỗi, trái với LiveMode fail-closed.
3. Skill Backend dùng `uv run pytest -v`, trong khi dự án dùng `uv run --extra dev pytest -v`.
4. Skill Clean Code đề nghị `ruff --fix` toàn repo, có thể sửa lan sang session khác.
5. Skill RAG mô tả payload `is_active=true`; code hiện tại dùng `document_status`, `is_retrievable`, `tenant_id` và `workspace_id`.

---

## 5. Kiến trúc hướng dẫn đích

```text
AGENTS.md
│   Quy tắc bất biến luôn áp dụng cho dự án
│
├── qnu-backend-architect
├── qnu-frontend-architect
├── qnu-chatbot-builder
├── qnu-rag-pipeline
├── qnu-knowledge-ingestion
├── qnu-modelops-resilience
└── qnu-clean-code-architect (explicit review/refactor)
        │
        └── references/ (ví dụ dài chỉ đọc khi cần)
```

### 5.1. `AGENTS.md`

- Giữ các rào chắn áp dụng cho mọi task.
- Giữ lệnh kiểm thử và quy tắc an toàn dữ liệu.
- Giữ quy tắc phối hợp session, memory, work log và tài liệu quy trình.
- Không cần sao chép toàn bộ ví dụ domain.

### 5.2. `SKILL.md`

- Xác định thời điểm kích hoạt và ranh giới domain.
- Chứa workflow bắt buộc và checklist chuyên môn.
- Chỉ trỏ tới reference thực sự cần cho task.
- Không sao chép nguyên chương đã có trong `AGENTS.md`.

### 5.3. `references/`

- Chứa ví dụ code dài, sơ đồ, bảng token và tình huống mẫu.
- Chỉ đọc khi bước xử lý cụ thể yêu cầu.
- Không chứa quy tắc bắt buộc duy nhất.

Tham chiếu OpenAI Docs: <https://developers.openai.com/es-419/docs/customization/overview> và <https://developers.openai.com/es-419/docs/build-skills>.

---

## 6. Ma trận định tuyến skill

| Loại task | Skill chính | Skill hỗ trợ tối đa |
| :--- | :--- | :--- |
| Sửa module FastAPI/SQLAlchemy | Backend | Một skill domain liên quan |
| Sửa component/page/hook React | Frontend | Một skill domain liên quan |
| Parser, OCR, cleaner, chunking | Knowledge Ingestion | RAG nếu đổi index contract |
| Retrieval, fusion, rerank, citation | RAG | ModelOps nếu có gọi provider |
| Provider, key pool, quota, cost | ModelOps | Backend |
| Tạo/cấu hình/phát hành Trợ lý | Chatbot | Một trong RAG hoặc ModelOps |
| Review/refactor/cleanup lớn | Clean Code gọi tường minh | Skill domain của code được review |
| Viết tài liệu hoặc nhận xét chung | Không bắt buộc skill QNU | Tối đa một skill domain nếu cần |

Quy tắc chung: **một skill chính + tối đa một skill hỗ trợ**. Chỉ vượt giới hạn khi task thật sự thay đổi contract xuyên ba tầng và phải ghi rõ lý do.

---

## 7. Kế hoạch triển khai

### Giai đoạn 0 — Chốt baseline

- [ ] Ghi lại dung lượng, số dòng và checksum của bảy `SKILL.md`.
- [ ] Lưu ma trận trigger hiện tại và 12 prompt kiểm thử.
- [ ] Kiểm tra working tree để không chạm file do session khác đang sửa.
- [ ] Xác nhận đợt tối ưu không sửa Backend/Frontend runtime.

**Điều kiện hoàn thành**: Có baseline phục vụ đối chiếu và rollback.

### Giai đoạn 1 — Sửa đúng trước khi rút gọn

- [ ] Sửa toàn bộ đường dẫn repo cũ thành đường dẫn tương đối.
- [ ] Sửa Offline Seed Fallback:
  - Demo/Sample Mode chỉ dùng dữ liệu mẫu khi người dùng chủ động chọn.
  - LiveMode phải hiển thị lỗi hoặc empty state; cấm dữ liệu nghiệp vụ giả.
- [ ] Đồng nhất lệnh Backend thành `uv run --extra dev pytest -v`.
- [ ] Thay `ruff --fix` toàn repo bằng targeted fix trong phạm vi task.
- [ ] Đồng bộ RAG payload với code hiện tại.
- [ ] Không xóa hoặc di chuyển quy tắc bắt buộc trong giai đoạn này.

**Điều kiện hoàn thành**: Skill không còn thông tin sai hoặc xung đột với `AGENTS.md`.

### Giai đoạn 2 — Thu hẹp trigger, chưa cắt nội dung

- [ ] Viết lại `description` theo hành động chính, domain và điều kiện không kích hoạt.
- [ ] Giữ implicit invocation cho Backend, Frontend, Chatbot, RAG, Knowledge và ModelOps.
- [ ] Tạo `.agents/skills/qnu-clean-code-architect/agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

- [ ] Kiểm chứng `$qnu-clean-code-architect` vẫn gọi được tường minh.
- [ ] Không thay đổi workflow chuyên môn ở bước này.

**Điều kiện hoàn thành**: Task đơn domain không tự nạp skill không liên quan.

### Giai đoạn 3 — Kiểm thử định tuyến và chất lượng

Chạy tối thiểu 12 tình huống:

1. Sửa một endpoint FastAPI.
2. Sửa một React component.
3. Thêm parser PPTX.
4. Sửa RRF fusion.
5. Cấu hình provider fallback.
6. Tạo Trợ lý mới.
7. Review với `$qnu-clean-code-architect`.
8. Viết báo cáo nhận xét dự án.
9. Sửa Assistant UI nhưng không đổi runtime.
10. Sửa RAG node trong workflow.
11. Chỉ cập nhật tài liệu.
12. Task xuyên Backend + RAG.

Với mỗi tình huống ghi nhận:

- Skill dự kiến và skill thực tế.
- Có nạp quá hai skill hay không.
- Có bỏ sót quy tắc kiến trúc/chất lượng không.
- Token đầu vào ước tính trước và sau.

**Điều kiện hoàn thành**: Ít nhất 11/12 tình huống định tuyến đúng; không vi phạm quality gate.

### Giai đoạn 4 — Progressive disclosure tùy chọn

Chỉ thực hiện sau 5–10 task thực tế không có regression:

- [ ] Chuyển ví dụ dài Frontend sang `references/frontend-examples.md`.
- [ ] Chuyển ví dụ Clean Code sang `references/clean-code-examples.md`.
- [ ] Chuyển sơ đồ/ví dụ Chatbot sang reference nếu không cần trong mọi lần gọi.
- [ ] Giữ checklist bắt buộc và acceptance gate trong `SKILL.md`.
- [ ] So sánh từng mục trước/sau để bảo đảm tương đương ngữ nghĩa.

**Điều kiện dừng**: Nếu agent bỏ sót một quy tắc cốt lõi, rollback phần di chuyển tương ứng.

### Giai đoạn 5 — Theo dõi

- [ ] Theo dõi 10 task tiếp theo.
- [ ] Ghi nhận lỗi kiến trúc, routing và skill bị gọi thừa.
- [ ] Chỉ tối ưu thêm khi không có regression.
- [ ] Không đặt mục tiêu giảm token cứng nếu phải xóa kiến thức quan trọng.

---

## 8. Tệp dự kiến thay đổi khi triển khai

| Tệp/Thư mục | Hành động |
| :--- | :--- |
| `.agents/skills/qnu-backend-architect/SKILL.md` | Sửa trigger và lệnh pytest |
| `.agents/skills/qnu-frontend-architect/SKILL.md` | Sửa trigger và LiveMode fallback |
| `.agents/skills/qnu-chatbot-builder/SKILL.md` | Thu hẹp trigger theo Assistant Lifecycle |
| `.agents/skills/qnu-rag-pipeline/SKILL.md` | Sửa path và payload contract |
| `.agents/skills/qnu-knowledge-ingestion/SKILL.md` | Sửa path và boundary ingestion |
| `.agents/skills/qnu-modelops-resilience/SKILL.md` | Làm rõ boundary; hạn chế thay đổi |
| `.agents/skills/qnu-clean-code-architect/SKILL.md` | Làm rõ explicit review/refactor |
| `.agents/skills/qnu-clean-code-architect/agents/openai.yaml` | Tắt implicit invocation |
| `.agents/skills/*/references/` | Chỉ tạo ở Giai đoạn 4 |
| `AGENTS.md` | Không thay đổi trong Giai đoạn 1–3 |

---

## 9. Tiêu chí nghiệm thu

### 9.1. Bảo toàn kiến trúc

- [ ] Không mất Backend 4-file module.
- [ ] Không mất Frontend 3-tier component và Deep Routing.
- [ ] Không mất Assistant Lifecycle bảy bước.
- [ ] Không mất RAG citation/no-answer/facts contract.
- [ ] Không mất storage-first ingestion và Unicode NFC.
- [ ] Không mất Provider fallback/quota/cost/circuit breaker.
- [ ] Không mất Zero `any`, Zero Mock Trap, Zero Mojibake.

### 9.2. Đúng cơ chế kích hoạt

- [ ] Sáu skill domain vẫn implicit invoke đúng phạm vi.
- [ ] Clean Code không tự kích hoạt trong task thông thường.
- [ ] Clean Code vẫn hoạt động khi gọi `$qnu-clean-code-architect`.
- [ ] Task đơn domain không tự nạp trên hai QNU skill.

### 9.3. Không sai lệch nội dung

- [ ] Không còn đường dẫn repo cũ.
- [ ] Không còn Offline Seed Fallback trong LiveMode.
- [ ] Lệnh kiểm thử thống nhất với `AGENTS.md`.
- [ ] RAG payload mô tả đúng code thực tế.
- [ ] Tệp text UTF-8 không BOM và không mojibake.

### 9.4. Không tác động runtime

- [ ] Không có thay đổi trong `backend/app` hoặc `frontend/src` do tối ưu skill.
- [ ] Không thay đổi seed data, provider credentials, database hoặc Qdrant.
- [ ] Không thay đổi quy trình nghiệp vụ khi runtime không đổi.

---

## 10. Rollback

1. Mỗi giai đoạn là một nhóm thay đổi độc lập.
2. Lưu checksum và diff từng `SKILL.md` trước khi sửa.
3. Nếu routing sai, rollback riêng `description` hoặc `openai.yaml`.
4. Nếu reference làm agent bỏ sót quy tắc, đưa nội dung trở lại `SKILL.md`.
5. Không xóa lịch sử hoặc snapshot cũ.

---

## 11. Kết quả kỳ vọng

- Task đơn domain chỉ nạp một skill chính thay vì nhiều skill chồng lấn.
- Giảm context skill mà không giảm quality gate.
- Giữ nguyên cấu trúc và hành vi runtime QNU AI Platform.
- Agent chọn đúng chuyên môn và ít đọc tài liệu không liên quan.
- Skill không còn đường dẫn hoặc mô tả kỹ thuật lỗi thời.

Mức giảm token là chỉ số phụ. Tiêu chí cuối cùng là **không có regression chất lượng và không làm sai kiến trúc dự án**.

---

## 12. Thứ tự khuyến nghị

1. Thực hiện Giai đoạn 0 và 1.
2. Review diff với chủ dự án.
3. Thực hiện Giai đoạn 2.
4. Chạy ma trận Giai đoạn 3.
5. Vận hành thử 5–10 task.
6. Chỉ khi ổn định mới cân nhắc Giai đoạn 4.

**Điểm dừng an toàn**: Sau Giai đoạn 3. Không bắt buộc rút nội dung nếu mức tiêu thụ token đã phù hợp.
