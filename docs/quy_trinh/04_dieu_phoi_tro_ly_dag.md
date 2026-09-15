# QUY TRÌNH 04: ĐIỀU PHỐI 05 TRỢ LÝ AI QUA ĐỒ THỊ DAG (WORKFLOW DAG ENGINE FLOW)

Tài liệu này đặc tả quy trình điều phối hội thoại của 05 Trợ lý AI chuyên trách chuẩn QNU thông qua động cơ thực thi đồ thị tuần tự có hướng (**Workflow DAG Runtime Engine**).

---

## 1. Sơ Đồ Khối Thực Thi Đồ Thị DAG (Workflow Execution Graph)

```mermaid
flowchart TD
    REQ([Yêu cầu từ Client: Assistant Code + Tin nhắn]) --> ASST_SVC[Assistant Service: Lookup Workflow ID]
    ASST_SVC --> ENGINE[Workflow DAG Engine: Khởi tạo WorkflowContext]
    
    subgraph DAG_EXECUTION [Chuỗi Thực Thi Đồ Thị Topo]
        ENTRY[1. Entry Node: input.chat] --> N_INPUT[Làm sạch câu hỏi, kiểm tra độ dài & sanitize]
        N_INPUT --> N_ROUTE{2. Node: condition.route}
        
        N_ROUTE -->|Ý định: Chào hỏi / Giao tiếp thông thường| N_GREET[3A. Node: output.chat<br>Template chào mừng chuẩn văn hóa QNU]
        N_ROUTE -->|Ý định: Nghiệp vụ Tra cứu / Tri thức| N_RAG[3B. Node: core.knowledge.answer<br>Kích hoạt Pipeline Hybrid RAG]
        N_ROUTE -->|Ý định: Tác vụ thay đổi dữ liệu nhạy cảm| N_APP{3C. Node: condition.approval}
        
        N_APP -->|Chưa có token phê duyệt của cán bộ| N_PAUSE[4A. Tạm dừng quy trình (paused_for_approval)<br>Trả về Checkpoint ID cho Cán bộ thẩm định]
        N_APP -->|Đã phê duyệt| N_TOOL[4B. Node: tool.invoke<br>Kích hoạt Tool Function Calling]
        
        N_RAG --> N_OUTPUT[5. Node: output.chat<br>Đóng gói Answer, Trích dẫn & Gợi ý câu hỏi]
        N_TOOL --> N_OUTPUT
        N_GREET --> N_OUTPUT
    end

    N_PAUSE --> RES_PAUSE([Phản hồi trạng thái chờ duyệt])
    N_OUTPUT --> RES_OK([Phản hồi kết quả hoàn tất cho Sinh viên / Giảng viên])
```

---

## 2. Hệ Sinh Thái 05 Trợ Lý AI Chuyên Trách Chuẩn QNU

05 Trợ lý được gieo mầm tự động qua Seeder (`STANDARD_ASSISTANTS`):

| Mã Trợ Lý (`code`) | Tên Trợ Lý | Workflow Ràng Buộc | Chuyên Môn Nghiệp Vụ | Công Cụ Gắn Liền |
| :--- | :--- | :--- | :--- | :--- |
| **`admissions`** | **Trợ lý Tuyển sinh QNU** | `admissions-assistant` | Đề án tuyển sinh, điểm chuẩn, chỉ tiêu, học phí, KTX | `lookup_admission_score` |
| **`regulations`** | **Trợ lý Quy chế Học vụ** | `regulations-assistant` | Quy chế đào tạo tín chỉ, chuẩn đầu ra, học bổng, kỷ luật | `ClauseBasedChunker` |
| **`library`** | **Trợ lý Thư viện & Học liệu Số** | `library-assistant` | Tra cứu giáo trình, sách chuyên khảo, bài báo khoa học | Tra cứu tài nguyên số |
| **`drafting`** | **Trợ lý Soạn thảo Văn bản** | `drafting-assistant` | Hỗ trợ soạn thông báo, tờ trình, kế hoạch theo Nghị định 30 | `export_administrative_document` |
| **`question_bank`**| **Trợ lý Ngân hàng Đề thi** | `question-bank-assistant`| Phân loại câu hỏi theo 4 mức Bloom, xuất ma trận đề thi | `export_exam_matrix` |

---

## 3. Các Đặc Tính Kỹ Thuật Đột Phá Của DAG Engine

### 1. Bảo vệ ranh giới từ tiếng Việt an toàn (Word Boundary Safeguard)
Trong `ConditionRouteNodeHandler`:
- Khi so khớp ý định (Intent Matching), hệ thống tự động bọc regex với ranh giới từ `(?:^|\W)(?:pattern)(?:\W|$)`.
- **Triệt tiêu lỗi ngớ ngẩn**: Ngăn chặn từ khóa con tiếng Anh như `"hi"` vô tình bị kích hoạt khi người dùng gõ từ tiếng Việt chứa chuỗi `"hi"` (ví dụ: *"Học phí bao n**hi**êu tiền?"* sẽ không bao giờ bị hiểu nhầm thành lời chào *"hi"*).

### 2. Chốt chặn phê duyệt của con người (Human-in-the-Loop Node)
Trong `HumanApprovalNodeHandler`:
- Đối với các tác vụ nhạy cảm (ban hành quyết định điểm, cấp học bổng, xóa dữ liệu), DAG sẽ lập tức chuyển trạng thái sang `paused_for_approval`.
- Chỉ khi nhận được request kèm xác thực phê duyệt từ cán bộ có thẩm quyền (`is_approved: true`), quy trình mới tiếp tục thực thi các bước tiếp theo.
