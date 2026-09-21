# Nhật Ký Làm Việc — Phiên #176
**Ngày thực hiện**: 2026-09-21
**Mục tiêu chính**: Triệt tiêu toàn bộ mẫu văn bản tĩnh (hardcoded templates), năm cũ ghim cứng và ký tự emoji cho cả 5 mô đun trợ lý, hoàn thiện No-Answer Policy đa phòng ban và đạt chuẩn Zero-Emoji 100%.

---

## 1. Bối Cảnh & Vấn Đề Xử Lý

Sau khi khắc phục hiện tượng regex chào hỏi hijacking và triệt tiêu hardcode của Trợ lý Tuyển sinh trong phiên #175, người dùng đặt yêu cầu:
> *"Triệt tiêu toàn bộ Hardcode cũ của tuyển sinh vậy còn các mô đun còn lại bạn có xử lý luôn không ?"*

Qua kiểm toán toàn diện hệ thống:
1. **No-Answer Policy RFC 7807 bị thiếu hụt ở 3 mô đun**:
   - `backend/app/modules/rag/citation_guard.py` trước đây chỉ định nghĩa thông báo từ chối cho `admissions` và `regulations`. Ba mô đun còn lại (`library`, `drafting`, `question_bank`) rơi vào fallback chung sơ sài, không có hotline, email hay địa chỉ phòng ban cụ thể của ĐH Quy Nhơn.
2. **Năm cũ bị ghim cứng trong câu hỏi mẫu**:
   - `backend/app/modules/assistants/seeder.py` còn chứa câu hỏi ghim cứng quá khứ: `"Điểm chuẩn ngành Sư phạm Toán học và Công nghệ thông tin năm 2024 là bao nhiêu?"` trong Tuyển sinh và `"Soạn thông báo tổ chức Hội nghị Nghiên cứu Khoa học sinh viên năm học 2024-2025."` trong Soạn thảo văn bản.
3. **Emoji còn sót lại trên giao diện Frontend**:
   - Trong `frontend/src/components/ai/chat-message.tsx`, nút bấm gợi ý câu hỏi liên quan tiếp theo hiển thị ký tự `💡 {q}`, vi phạm quy chuẩn AGENTS.md Quy tắc 4.8 (*Cấm tuyệt đối Emoji trong giao diện quản trị*).
4. **Phân loại ý định đa miền**:
   - Node `condition_route_node.py` cần bảo đảm nhận diện chính xác danh xưng và từ khóa của cả 5 mô đun để bảo vệ các câu hỏi nghiệp vụ không bị điều hướng nhầm vào lời chào.

---

## 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Technical Changes)

### 2.1. Cập Nhật Từ Điển No-Answer Đa Phòng Ban (`backend/app/modules/rag/citation_guard.py`)
- Mở rộng `NO_ANSWER_MESSAGES` định hình chính xác thông tin liên hệ và 3 nhóm chủ đề tra cứu chuẩn cho từng mô đun:
  * **`admissions`**: Hotline Ban Tư vấn Tuyển sinh `0256.3846.156`, Email `tuyensinh@qnu.edu.vn`.
  * **`regulations`**: Bàn tiếp sinh viên - Phòng Đào tạo (Tín chỉ, cảnh báo học vụ, chuẩn đầu ra VSTEP).
  * **`library`**: Trung tâm Thông tin - Thư viện QNU, Hotline `0256.3846.888`, Email `thuvien@qnu.edu.vn` (ScienceDirect, IEEE, Turnitin, lưu chiểu).
  * **`drafting`**: Phòng Hành chính - Tổng hợp (Soạn thảo tờ trình, kế hoạch, quyết định theo Nghị định 30/2020/NĐ-CP).
  * **`question_bank`**: Phòng Khảo thí & Đảm bảo chất lượng giáo dục (Ma trận Bloom 4 mức độ, ngân hàng câu hỏi, CLO/PLO, xuất Excel).

### 2.2. Mở Rộng Nhận Diện Danh Xưng & Từ Khóa Nghiệp Vụ (`backend/app/modules/workflows/nodes/condition_route_node.py`)
- Mở rộng `_INQUIRY_KEYWORDS` bao phủ đầy đủ thuật ngữ của 5 lĩnh vực.
- Cập nhật `_TITLE_PATTERNS` bóc tách danh xưng của cả 5 Trợ lý và các đơn vị chuyên môn (`Trợ lý Tuyển sinh`, `Trợ lý Quy chế Đào tạo`, `Trợ lý Thư viện & Học liệu Số`, `Trợ lý Soạn thảo Văn bản`, `Trợ lý Ngân hàng Câu hỏi & Đề thi`, `Phòng Đào tạo`, `Trung tâm Thư viện`, `Phòng Hành chính - Tổng hợp`, `Phòng Khảo thí`).

### 2.3. Chuẩn Hóa Cấu Hình DAG Của Các Trợ Lý (`configs/workflows/*.json`)
- Cập nhật node `no_answer_output` trong:
  * [`regulations-assistant.v1alpha1.json`](file:///d:/DuAnPhanMem/qnu-ai-platform/configs/workflows/regulations-assistant.v1alpha1.json)
  * [`library-assistant.v1alpha1.json`](file:///d:/DuAnPhanMem/qnu-ai-platform/configs/workflows/library-assistant.v1alpha1.json)
  * [`question-bank-assistant.v1alpha1.json`](file:///d:/DuAnPhanMem/qnu-ai-platform/configs/workflows/question-bank-assistant.v1alpha1.json)
- Loại bỏ toàn bộ năm cũ và nội dung ngắn cụt ngủn, thay bằng mẫu hướng dẫn chi tiết, chuyên nghiệp.

### 2.4. Khử Hardcode Năm Cũ & Đồng Bộ CSDL (`backend/app/modules/assistants/seeder.py`)
- Chuyển đổi các câu hỏi mẫu sang dạng thường trực (evergreen):
  * `"Điểm chuẩn ngành Sư phạm Toán học và Công nghệ thông tin các năm gần nhất là bao nhiêu?"`
  * `"Soạn thông báo tổ chức Hội nghị Nghiên cứu Khoa học sinh viên cấp Trường."`
- Bổ sung cơ chế đồng bộ `config` (sample questions và guardrails) cho các bản ghi Trợ lý đã tồn tại trong PostgreSQL khi chạy seed.

### 2.5. Thay Thế Emoji Bằng Lucide Icon Chuẩn Hóa (`frontend/src/components/ai/chat-message.tsx`)
- Nhập `Lightbulb` từ `lucide-react` (sắp xếp đúng thứ tự alphabet).
- Thay thế `💡 {q}` bằng `<Lightbulb className="size-3 text-primary shrink-0" /> <span>{q}</span>` với `inline-flex items-center gap-1.5`.

---

## 3. Kết Quả Kiểm Thử (Verification)

1. **Đồng bộ dữ liệu CSDL**:
   - `uv run python -m app.cli db seed --assistants --workflows`: Hoàn tất đồng bộ 5/5 Trợ lý và 5/5 DAG workflows.
   - Script kiểm tra CSDL xác nhận 100% mẫu câu hỏi và thông điệp từ chối trên PostgreSQL đã được cập nhật sạch.
2. **Backend**:
   - `uv run ruff check .`: 0 lỗi linter.
   - `uv run --extra dev pytest tests/test_assistants.py tests/test_workflows.py tests/test_node_catalog.py tests/test_query_rewrite_node.py tests/test_rag.py`: **62/62 passed (100%)**.
   - `uv run --extra dev pytest`: Toàn bộ **341/341 passed (100%)** trong 58.05s.
3. **Frontend**:
   - `npm run lint`: Biome check 168 files -> **0 lỗi**.
   - `npm run typecheck`: TypeScript `tsc --noEmit` -> **0 lỗi**.
   - `npm run build`: Vite build thành công bundle production trong 10.36s.
