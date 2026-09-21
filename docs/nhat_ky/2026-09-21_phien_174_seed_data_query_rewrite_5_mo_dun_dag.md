# NHẬT KÝ LÀM VIỆC — PHIÊN #174
**Ngày**: 2026-09-21 | **Thời gian**: 14:32 (UTC+7)  
**Tiêu đề**: Bổ Sung Node Query Rewrite Vào Seed Data Của Cả 5 Mô Đun Quy Trình DAG

---

## 1. Bối Cảnh & Yêu Cầu

Sau khi tách node `query.rewrite` thành một building block dùng chung mở hoàn toàn (không còn hardcoded 5 mô đun ở cấp code Python), người dùng yêu cầu cập nhật seed data của toàn bộ 5 quy trình nghiệp vụ chính thức trong hệ sinh thái QNU AI Platform để mỗi quy trình đều có sẵn node `query_rewrite` cùng prompt instruction được viết đo ni đóng giày theo đúng chức năng nghiệp vụ của quy trình đó.

---

## 2. Chi Tiết Thực Hiện

### 2.1. Cấu hình Prompt Chuyên Biệt Cho 5 Quy Trình (`configs/workflows/*.json`)

1. **Tuyển sinh (`admissions-assistant`)**:
   - Vị trí: Giữa `condition_route` và `knowledge_answer`.
   - Prompt: Chuẩn hóa câu hỏi tuyển sinh, điểm chuẩn, ngành học (sửa trượt phím Telex "ngày" $\rightarrow$ "ngành", "học bà" $\rightarrow$ "học bạ", mở rộng CNTT, QTKD, ĐGNL, THPT, KTX, viết hoa đúng tên ngành).

2. **Quy chế học vụ (`regulations-assistant`)**:
   - Vị trí: Giữa `chat_input` và `knowledge_answer`.
   - Prompt: Chuẩn hóa câu hỏi quy chế học vụ, đào tạo tín chỉ (sửa "tín chì" $\rightarrow$ "tín chỉ", "học phầm" $\rightarrow$ "học phần", "rèn luyên" $\rightarrow$ "rèn luyện", mở rộng ĐRL, GPA, CTĐT, CTSV, PĐT, NCKH).

3. **Thư viện & NCKH (`library-assistant`)**:
   - Vị trí: Giữa `chat_input` và `knowledge_answer`.
   - Prompt: Chuẩn hóa tra cứu thư viện, giáo trình và tài liệu (sửa "giáo trinh" $\rightarrow$ "giáo trình", "tài liêu" $\rightarrow$ "tài liệu", "luận văn", mở rộng CNTT, QTKD, SP, KHCN, NCKH, viết hoa chuẩn tên tác giả và sách).

4. **Soạn thảo NĐ 30 (`drafting-assistant`)**:
   - Vị trí: Giữa `chat_input` và cả 2 nhánh downstream `extract_fields` và `sample_retrieval`.
   - Prompt: Chuẩn hóa yêu cầu soạn thảo văn bản hành chính theo Nghị định 30 (sửa "tờ trinh" $\rightarrow$ "tờ trình", "kế hoach" $\rightarrow$ "kế hoạch", "quyết đinh" $\rightarrow$ "quyết định", mở rộng Nghị định 30/2020/NĐ-CP, BGH, ĐHQG, UBND, PĐT, TCHC, CTSV).

5. **Khảo thí & Ngân hàng đề thi (`question-bank-assistant`)**:
   - Vị trí: Giữa `chat_input` và `knowledge_answer`.
   - Prompt: Chuẩn hóa khảo thí, ngân hàng câu hỏi, ma trận đề thi (sửa "ma trân" $\rightarrow$ "ma trận đề thi", "ngân hang" $\rightarrow$ "ngân hàng câu hỏi", "thang đo blom" $\rightarrow$ "thang đo Bloom", mở rộng CLO, PLO, CĐR, ĐCHP, KTĐG, TNKQ).

### 2.2. Nâng Cấp Idempotent Workflow Seeder (`service.py`)
- Phương thức `sync_default_workflows` được nâng cấp để khi cấu hình JSON trong `configs/workflows/` có thay đổi, hệ thống sẽ tự động cập nhật:
  * `WorkflowDefinition.dag_spec`
  * `WorkflowDraft.dag_spec` (tăng revision)
  * `WorkflowVersion.dag_spec` (phiên bản v1.0.0 chính thức kèm content_hash mới)
- Chạy lệnh CLI: `uv run python -m app.cli db seed --workflows` đồng bộ thành công cả 5 quy trình vào PostgreSQL.

### 2.3. Cập Nhật Tài Liệu Quy Trình
- Bổ sung **Mục 13** trong [`docs/quy_trinh/04_dieu_phoi_tro_ly_dag.md`](../quy_trinh/04_dieu_phoi_tro_ly_dag.md) ghi nhận kiến trúc node dùng chung và bảng cấu hình chi tiết cho 5 mô đun.

---

## 3. Kết Quả Kiểm Thử

- **Kiểm Tra Trực Tiếp CSDL**: Xác nhận 5/5 quy trình (`admissions-assistant`, `drafting-assistant`, `library-assistant`, `question-bank-assistant`, `regulations-assistant`) đều chứa node `query.rewrite` với độ dài instruction từ 310 đến 471 ký tự.
- **Backend Tests**: `uv run --extra dev pytest tests/test_workflows.py tests/test_query_rewrite_node.py -v` $\rightarrow$ **31/31 passed (100%)**.
- **Backend Linter**: `uv run ruff check .` $\rightarrow$ **0 lỗi**.
- **Frontend Linter & Typecheck**:
  * `npm run lint` $\rightarrow$ **0 lỗi**.
  * `npm run typecheck` $\rightarrow$ **0 lỗi**.
