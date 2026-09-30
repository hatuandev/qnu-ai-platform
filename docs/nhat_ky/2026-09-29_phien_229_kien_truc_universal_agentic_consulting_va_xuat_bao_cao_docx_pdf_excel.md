# Nhật Ký Phát Triển — Phiên 229 (29/09/2026)
## Kiến Trúc Nền Tảng Universal Agentic Consulting & Xuất Báo Cáo Đa Định Dạng (Excel, Word, PDF)

### 1. Bối cảnh & Yêu cầu của Người dùng
- Người dùng đặt câu hỏi và yêu cầu nâng cấp:
  1. Đánh giá hiện trạng quy trình DAG và kho tri thức của Chatbot Tuyển sinh.
  2. Nâng cấp Chatbot từ mô hình hỏi-đáp thụ động thành một **Cán bộ Tư vấn Tuyển sinh Thông minh (Admissions Consulting Agent)** có khả năng chủ động phân tích hồ sơ, tính điểm, so sánh đa ngành.
  3. Bổ sung hệ thống Kỹ năng (Skills) và khả năng tạo tệp kết xuất đa định dạng: **Excel (.xlsx), Word (.docx), PDF (.pdf)** cho người dùng tải về trực tiếp.
  4. **Yêu cầu cốt lõi**: Phải thiết kế giải pháp mang tính **nền tảng chung cho toàn bộ Chatbot trên hệ thống** (Tuyển sinh, Quy chế học vụ, Thư viện, Soạn thảo, Khảo thí), không làm riêng lẻ cho một module; cam kết trung thực 100%, không báo cáo giả, không che giấu lỗi bằng mock ảo.

---

### 2. Các Thành Phần Kỹ Thuật Đã Triển Khai

#### A. Tầng Xuất Tệp Nền Tảng Dùng Chung (`UniversalReportExporter`)
- File: [`backend/app/modules/tools/universal_report.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/universal_report.py)
- **Excel (.xlsx)**: Xây dựng bằng `openpyxl`, thiết kế bảng màu thương hiệu QNU Academic Teal (`#0D7E8A`), viền mỏng (`#CBD5E1`), co dãn cột tự động (`auto_fit_columns`), hỗ trợ nhiều Sheet dữ liệu và tô màu nổi bật các vùng cơ hội (Xanh lá - An toàn, Vàng - Mục tiêu, Cam - Thử thách).
- **Word (.docx)**: Xây dựng bằng `python-docx` với tiêu đề Quốc hiệu/Tên trường chuẩn, thẻ thông tin đối tượng (Metadata card), đoạn văn đánh giá chiến lược và các bảng biểu đóng khung chuẩn mực.
- **PDF (.pdf)**: Chuyển đổi DOCX sang PDF qua Gotenberg LibreOffice API (port 3001) với cơ chế fallback tự động an toàn (không làm gián đoạn trò chuyện nếu Gotenberg offline).
- Lưu trữ tệp qua `storage_service.save()` và trả về danh sách `artifacts` tương thích 100% với giao diện chat frontend.

#### B. Nâng Cấp Hệ Thống Kỹ Năng & Kết Nối Fact Layer Thực Tế
- File: [`backend/app/modules/tools/builtin/admission_score_tool.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/builtin/admission_score_tool.py)
- **Truy vấn Fact thật**: Kết nối trực tiếp vào bảng `knowledge_facts` của PostgreSQL để bóc tách điểm chuẩn các năm, chỉ tiêu, tổ hợp môn, học phí.
- **Thuật toán tính điểm xét tuyển chuẩn Bộ GD&ĐT**:
  - Tính tổng điểm 3 môn tổ hợp.
  - Điểm ưu tiên: Khu vực (KV1: 0.75, KV2-NT: 0.5, KV2: 0.25, KV3: 0.0) + Đối tượng ưu tiên (Nhóm 1: 2.0, Nhóm 2: 1.0).
  - Áp dụng công thức giảm trừ lũy tiến khi tổng điểm $\ge 22.5$:
    $$\text{Điểm ƯT Thực Tế} = \left[\frac{30 - \text{Tổng điểm}}{7.5}\right] \times \text{Mức Điểm ƯT Quy Định}$$
- **Phân loại vùng cơ hội trúng tuyển**:
  - 🟢 **Vùng an toàn (Safe Zone, $\Delta \ge +1.5$)**: Cơ hội $\ge 90\%$.
  - 🟡 **Vùng mục tiêu (Target Zone, $-0.5 \le \Delta < +1.5$)**: Vừa sức, cơ hội $65\% - 85\%$.
  - 🔴 **Vùng thử thách (Reach Zone, $-1.5 \le \Delta < -0.5$)**: Đặt NV1 thử vận may.
- Tự động gọi `export_universal_report` tạo tệp tải về khi có yêu cầu.

#### C. Bộ Điều Phối Ý Định Tư Vấn Toàn Nền Tảng (`AgenticConsultingDispatcher`)
- File: [`backend/app/modules/tools/consulting_dispatcher.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/tools/consulting_dispatcher.py)
- Tự động phát hiện ý định: Tính toán điểm thi, So sánh ngành, Xuất file tải về (.xlsx, .docx, .pdf).
- Bóc tách tham số từ câu hỏi tự nhiên: Điểm 3 môn, Mã tổ hợp (A00, A01, D01...), Khu vực (KV1, KV2-NT...), Ngành đào tạo quan tâm, Tên thí sinh.
- Hỗ trợ toàn bộ các module:
  - `admissions`: Phân tích điểm, gợi ý ngành, xuất phiếu tư vấn và kế hoạch nguyện vọng.
  - `regulations`: Bóc tách quy chế từ DB và xuất Sổ tay quy chế học vụ (.xlsx, .docx, .pdf).
  - `library`: Xuất Danh mục tài liệu tham khảo theo chuyên đề (.xlsx, .docx, .pdf).

#### D. Tích Hợp Vào Workflow DAG & RAG Pipeline
- File: [`backend/app/modules/workflows/nodes/rag_answer_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/rag_answer_node.py)
- Kích hoạt `consulting_dispatcher` trước khi gọi RAG; tự động bổ sung ngữ cảnh số liệu chính xác vào Prompt và gắn danh sách `artifacts` vào `context.node_data` và `context.outputs`.
- Downstream `output_chat_node.py` chuyển tiếp `artifacts` sang `AssistantChatService`, phát SSE `event: artifact`, và giao diện chat Frontend tự động hiển thị các thẻ tải tệp (Word xanh dương, Excel xanh lá, PDF đỏ).

#### E. Tinh Chỉnh System Prompt Trợ Lý Tuyển Sinh Chuẩn Mực
- File: [`backend/app/modules/assistants/seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/assistants/seeder.py)
- Định vị vai trò: Cán bộ Tư vấn Tuyển sinh chuyên nghiệp của QNU, bóc tách điểm thi, phân nhóm vùng an toàn/mục tiêu, hướng dẫn tải tệp báo cáo và đề xuất câu hỏi gợi ý tương tác 1-click.

---

### 3. Kết Quả Kiểm Thử Toàn Diện (100% Pass)
1. **Kiểm thử Đơn vị & Tích hợp Backend (Pytest)**:
   - `tests/test_universal_report.py`: 3/3 passed (Excel openpyxl multi-sheet, Word docx styling, Gotenberg PDF conversion).
   - `tests/test_admission_score_tool.py`: 4/4 passed (MOET score reduction rule, zone classification, live facts, report export).
   - `tests/test_consulting_dispatcher.py`: 4/4 passed (Intent detection, parameter extraction, multi-module dispatching).
   - `tests/test_assistants.py`: 12/12 passed (Lifecycles, streaming, injection guard, permissions).
   - `tests/test_admissions_agentic_flow.py`: 1/1 passed (End-to-end chat flow trả lời và tự động đính kèm artifacts).
   - **Tổng cộng**: **24/24 tests passed (100%)** trong 5.48 giây.
2. **Kiểm tra Linter Python**:
   - `uv run ruff check`: **All checks passed (0 errors)**.
3. **Kiểm tra Biên dịch Frontend**:
   - `npm run build` (tại `frontend/`): **Vite build thành công (0 lỗi, exit code 0)**.
   - `npm run build` (tại `frontend2/`): **Vite build thành công (0 lỗi, exit code 0)**.
