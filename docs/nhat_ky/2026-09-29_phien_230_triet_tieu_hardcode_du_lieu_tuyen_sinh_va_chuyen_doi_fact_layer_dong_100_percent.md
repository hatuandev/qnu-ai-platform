# Nhật Ký Phiên Làm Việc #230 — Triệt Tiêu Hoàn Toàn Hardcode Dữ Liệu Ngành & Chuyển Sang Fact Layer Động 100% Từ PostgreSQL Cho Toàn Nền Tảng

- **Thời gian**: 2026-09-29 20:05 (UTC+7)
- **Tác giả**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist
- **Trạng thái**: Hoàn thành xuất sắc, 25/25 tests pass, 0 lỗi linter, 0 lỗi compile

---

## 1. Yêu Cầu & Bối Cảnh Thực Tế

Sau khi rà soát mã nguồn ở phiên #229, Người dùng đã chỉ ra điểm bất cập vi phạm nghiêm trọng tôn chỉ phát triển:
> *"Tôi thấy nó có hardcode điều này không đúng, với lại làm chung nên sẽ không có chuyên biệt riêng được, nếu có riêng nên được điều chỉnh ở web UI, với lại dữ liệu chính là từ kho tri thức nó là dữ liệu động nên không hardcode, bạn hãy điều chỉnh lại."*

### Các vi phạm được nhận diện và cần triệt tiêu:
1. **Hardcode danh mục ngành tĩnh**:
   - `backend/app/modules/tools/builtin/admission_score_tool.py`: Hằng số `QNU_OFFICIAL_MAJORS` chứa mảng 14 ngành học tĩnh với mã ngành, điểm chuẩn, tổ hợp, chỉ tiêu, học phí cố định.
   - Vi phạm Điều 1.7 trong `AGENTS.md` (*Algorithmic-First, Zero-Hardcoded Vocabulary & Propose-Before-Implement*).
2. **Hardcode từ điển aliases tĩnh**:
   - `backend/app/modules/tools/consulting_dispatcher.py`: Dictionary `MAJOR_ALIASES` gõ tay 25 ánh xạ tên ngành viết tắt ("cntt", "ktpm", "qtkd",...).
3. **Hardcode dữ liệu fallback giả (Mock data)**:
   - Các bảng dữ liệu mẫu quy chế học vụ và thư viện được gán cứng khi DB trống, vi phạm quy định Anti-Mock và No-Answer Policy.
4. **Thiếu tính linh hoạt toàn nền tảng (Generic Platform)**:
   - Tool chưa hỗ trợ truyền `collection_id` động theo cấu hình Web UI của Assistant.

---

## 2. Kiến Trúc & Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1. Triệt Tiêu Hoàn Toàn `QNU_OFFICIAL_MAJORS` & Thuật Toán Phân Tích Fact Layer Động (`AdmissionScoreLookupTool`)
- **Xóa bỏ 100%**: Xóa hoàn toàn 141 dòng code khai báo `QNU_OFFICIAL_MAJORS` tĩnh trong `backend/app/modules/tools/builtin/admission_score_tool.py`.
- **Thuật toán `_extract_majors_from_live_facts`**:
  - Đọc động từ bảng PostgreSQL `knowledge_facts` theo `collection_id` (mặc định lấy từ cấu hình Assistant trên Web UI hoặc `col_admissions`).
  - Tự động bóc tách các facts kiểu `cutoff_score` hoặc `major` từ trường cấu trúc `raw_data` (`major_code`, `major_name`, `cutoff_score`, `subject_groups`).
  - Tự động phân tích cú pháp chuỗi tiến trình điểm 3 năm qua regex hình thái học:
    `r"([^:;\n]+?):\s*([0-9]+(?:\.[0-9]+)?)\s*->\s*([0-9]+(?:\.[0-9]+)?)\s*->\s*([0-9]+(?:\.[0-9]+)?)"`
    để trích xuất điểm chuẩn các năm (2022, 2023, 2024) mà không gán cứng tên ngành.
  - Tự động đồng bộ mức học phí và chỉ tiêu từ các facts `tuition_fee`, `admission_quota`, `pedagogy_support` trong CSDL.
- **Cơ chế Chống Bịa Đặt (Zero Hallucination & Anti-Mock)**:
  - Khi người dùng hỏi một ngành chưa có trong Đề án tuyển sinh / Kho tri thức: Trả về trung thực `found = False`, `records = []`, kèm thông báo rõ ràng dữ liệu chưa có trong đề án và hướng dẫn liên hệ Hotline `0256.3846.156`. Tuyệt đối không fallback sang dữ liệu giả!

### 2.2. Triệt Tiêu `MAJOR_ALIASES` & So Khớp Thực Thể Động (`AgenticConsultingDispatcher`)
- **Xóa bỏ 100%**: Xóa bỏ từ điển `MAJOR_ALIASES` gõ tay trong `backend/app/modules/tools/consulting_dispatcher.py`.
- **Truy vấn Thực thể Động & So Khớp Cú pháp**:
  - `candidate_majors`: Tự động nạp danh sách tên ngành có thật trong `knowledge_facts` của `collection_id` tương ứng để so khớp dài nhất trước (longest match first).
  - Trích xuất mã ngành 7 chữ số chuẩn Bộ GD&ĐT qua regex `\b(7\d{6})\b`.
  - Trích xuất cú pháp tự nhiên qua regex ngữ cảnh:
    `r"(?:ngành|nganh|chuyên ngành|khoa)\s+([A-ZÀ-Ỹa-zà-ỹ0-9\s\-]+?)(?:\s*(?:điểm|lấy|chuẩn|xét|khối|tổ hợp|có|học phí|chỉ tiêu|\?|\.|\,|$))"`
    kết hợp tầng lọc loại bỏ các từ nối và lệnh xuất file ("và xuất file...", "nào", "gì", "phù hợp").
- **Loại bỏ Hoàn toàn Fallback Giả cho Quy Chế & Thư Viện**:
  - Đối với `regulations` và `library`, 100% dữ liệu xuất file Word/Excel/PDF lấy trực tiếp từ `KnowledgeFact` của `col_regulations` và `col_library`.
  - Nếu CSDL chưa có facts, hệ thống trả về thông báo trung thực yêu cầu nạp tài liệu vào kho tri thức trước, không tự động sinh bảng giả.

### 2.3. Tích Hợp Cấu Hình Động Theo Web UI & Workflow DAG
- Cập nhật `rag_answer_node.py`: Truyền trực tiếp `collection_id` được gán trên Web UI của Assistant / Node cấu hình vào `consulting_dispatcher.dispatch(..., collection_id=collection_id)`.
- Khi người dùng cấu hình Assistant đổi Kho tri thức sang bộ sưu tập khác trên Web UI, toàn bộ hệ thống tự động tra cứu facts của bộ sưu tập mới đó mà không cần can thiệp mã nguồn.

---

## 3. Kết Quả Kiểm Thử Toàn Diện (100% Pass)

### 3.1. Pytest Suite (25/25 Tests Passed)
```bash
pytest tests/test_universal_report.py tests/test_admission_score_tool.py tests/test_consulting_dispatcher.py tests/test_assistants.py tests/test_admissions_agentic_flow.py -v
```
- `test_generate_excel_report`: PASSED
- `test_generate_docx_report`: PASSED
- `test_export_universal_report`: PASSED
- `test_calculate_moet_admission_score_below_threshold`: PASSED
- `test_calculate_moet_admission_score_above_threshold_reduced`: PASSED
- `test_classify_chance_zone`: PASSED
- `test_admission_score_tool_execution_with_export`: PASSED
- `test_admission_score_tool_unknown_major_returns_honest_no_data`: PASSED *(Kiểm thử ca ngành không tồn tại trả về found=False trung thực, không fallback giả)*
- `test_detect_export_intent`: PASSED
- `test_extract_admission_parameters`: PASSED
- `test_dispatch_admissions_with_export`: PASSED
- `test_dispatch_regulations_with_export`: PASSED
- Toàn bộ 12 test cases của `test_assistants.py`: PASSED
- `test_admissions_agentic_flow.py`: PASSED

### 3.2. Linter & Static Analysis
- `uv run ruff check app tests`: **All checks passed! (0 errors, 0 warnings)**

### 3.3. Frontend Build Verification
- `frontend2` (Vite 6 + React 19): **✓ built in 2.94s (Exit code 0, 0 compile errors)**

---

## 4. Cam Kết & Trạng Thái Bàn Giao
1. Không còn bất kỳ mảng danh mục hay từ điển cứng nào trong mã nguồn Python.
2. Dữ liệu tư vấn tuyển sinh và xuất tệp 100% phụ thuộc vào Fact Layer trong Kho tri thức PostgreSQL.
3. Người dùng tự do nạp/xóa/sửa đề án tuyển sinh và tài liệu trên Web UI, hệ thống tự động thích ứng ngay lập tức.
