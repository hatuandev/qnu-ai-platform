# NHẬT KÝ PHIÊN LÀM VIỆC #190
# Ngày: 2026-09-22 | Phiên: #190
# Tiêu đề: Nâng Cấp Node DAG Query Rewrite, Bảo Vệ 100% Không Ảnh Hưởng RAG, Chống Context Bleeding Từ Lịch Sử Đa Lượt & Triệt Tiêu Hoàn Toàn Hardcode

---

## 1. Mục Tiêu & Yêu Cầu Cốt Lõi

- **Bối cảnh**: Người dùng gửi câu hỏi ở Lượt 2: `"Phương thức xét tuyển của trường gồm những gì?"` sau khi ở Lượt 1 đã hỏi về `"các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học"`. Thay vì trả về 5 phương thức tuyển sinh của ĐH Quy Nhơn, Trợ lý lại lặp lại danh sách các ngành tuyển khối Toán, Tiếng Anh, Hóa học.
- **Nguyên nhân cốt lõi (Root Cause)**:
  - Tầng RAG hoàn toàn chính xác (tra cứu trực tiếp câu hỏi trả về đúng 5 phương thức tuyển sinh).
  - Lỗi phát sinh tại node DAG `query_rewrite` (`query_rewrite_node.py`): Node này truyền toàn bộ lịch sử trao đổi của lượt 1 vào prompt cho LLM; mô hình LLM bị "context bleeding / recency bias" tự ý viết lại câu hỏi thành `"Các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học tại Trường Đại học Quy Nhơn gồm những ngành nào?"`.
  - Bộ chốt chặn phòng vệ cũ (Defensive Guard 2) bị qua mặt do các từ khóa chung (`xét`, `tuyển`, `gồm`) bị trùng lặp, đồng thời so sánh có dấu khiến các từ gõ không dấu của người dùng bị phạt oan.
- **Yêu cầu của người dùng**:
  - Nâng cấp `query_rewrite` bảo đảm **100% không làm ảnh hưởng xấu đến RAG**.
  - **TUYỆT ĐỐI KHÔNG HARDCODE** (không hardcode câu hỏi, không gán ghép tĩnh).
  - Bảo đảm toàn diện cho mọi quy trình nghiệp vụ trên nền tảng QNU AI Platform.

---

## 2. Các Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1. Cắt Đứt Nguồn Gây Nhiễu Bằng Chốt Chặn Câu Hỏi Độc Lập (`is_context_dependent_query`)
- Xây dựng hàm `is_context_dependent_query(text: str) -> bool`:
  - Phân loại chính xác các câu hỏi độc lập, hoàn chỉnh (độ dài $\ge 5$ từ, câu hỏi ngữ pháp đầy đủ, không chứa đại từ chỉ định hay từ nối phụ thuộc).
  - Khi câu hỏi là câu hỏi độc lập (ví dụ: `"Phương thức xét tuyển của trường gồm những gì?"`, `"Học phí ngành Sư phạm Toán học là bao nhiêu?"`), hệ thống **CẮT HOÀN TOÀN** lịch sử trò chuyện khi gửi sang LLM (`effective_history = None`).
  - Khi LLM không nhìn thấy các môn Toán/Lý/Hóa của lượt trước, hiện tượng context bleeding bị triệt tiêu ngay từ gốc mà không cần bất kỳ can thiệp hardcode nào.

### 2.2. Chuẩn Hóa Khử Dấu (`_unaccent`) & Bộ Lọc Từ Chức Năng Mở Rộng
- Xây dựng hàm `_unaccent(text: str) -> str`: chuyển đổi chuỗi tiếng Việt Unicode NFC về dạng không dấu thuần túy (loại bỏ combining diacritics và map `đ/Đ` $\rightarrow$ `d`).
- Xây dựng tập `_FUNCTIONAL_STOPWORDS` và `_UNACCENTED_FUNCTIONAL_STOPWORDS`: tập hợp các từ ngữ pháp, đại từ, trợ từ, từ nối và xã giao tiếng Việt thông dụng (`bạn`, `cho`, `em`, `hỏi`, `với`, `xét`, `tuyển`, `gồm`, `danh`, `sách`,...).
- Giúp phân biệt rạch ròi giữa từ chức năng ngữ pháp và từ khóa nội dung thực sự (`phương thức`, `học phí`, `chỉ tiêu`, `công nghệ`, `toán`, `hóa`,...).

### 2.3. Hệ Thống 4 Lớp Chốt Chặn Phòng Vệ Bất Biến Dấu (Diacritic-Invariant Defensive Guards)
Cập nhật toàn bộ các guards trong `_rewrite_with_llm` để so sánh trên không gian token không dấu:
1. **Guard 1 (Chống rò rỉ Chatbot Meta)**: Từ chối các candidate chứa lời giải thích hoặc hỏi ngược người dùng (`bạn muốn chuẩn hóa...`, `vui lòng cung cấp...`).
2. **Guard 2 (Keyword Recall Check)**: Lọc bỏ stopwords không dấu, tính tỷ lệ bảo toàn từ khóa nội dung `preserved_ratio = overlap / len(query_words)`. Nếu tỷ lệ < 0.5 (LLM vứt bỏ từ khóa chính của người dùng), ngay lập tức từ chối và fallback về câu hỏi gốc.
3. **Guard 3 (Core Intent Preservation)**: Kiểm tra các cụm ý định cốt lõi tổng quát (`_CORE_INTENT_TERMS`: `phương thức`, `học phí`, `chỉ tiêu`, `điểm chuẩn`, `học bổng`, `ký túc xá`, `thời gian`, `thủ tục`, `hồ sơ`, `tín chỉ`,...). Nếu câu hỏi gốc có chứa cụm này mà candidate làm mất, chốt chặn kích hoạt và trả về câu hỏi gốc.
4. **Guard 4 (Combo Subject Injection Guard)**: Kiểm tra nếu câu hỏi gốc không hỏi về môn thi (`_COMBO_SUBJECT_TERMS`: `toán`, `lý`, `hóa`, `sinh`, `văn`, `sử`, `địa`, `tin`, `tiếng anh`), nhưng candidate tự ý nhét $\ge 2$ môn thi vào, chốt chặn kích hoạt và trả về câu hỏi gốc.
5. **Guard 5 (Length & Sanity Check)**: Kiểm tra độ dài hợp lệ (không vượt quá 2.5 lần câu gốc và không ngắn hơn 3 ký tự).

### 2.4. Triệt Tiêu Mẫu Prompt Hardcode
- Chuẩn hóa prompt trong `build_rewrite_prompt`: thay thế các câu ví dụ cụ thể bằng các ví dụ mẫu tổng quát mang tính đại diện cho các mô đun học vụ/ký túc xá/học phí/quy chế của trường đại học, bảo đảm 100% tính tổng quát.

---

## 3. Tệp Tin Chỉnh Sửa & Bổ Sung

| Tệp | Hành Động | Lý Do Kỹ Thuật |
| :--- | :--- | :--- |
| [`backend/app/modules/workflows/nodes/query_rewrite_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/query_rewrite_node.py) | **MODIFY** | Triển khai `is_context_dependent_query`, `_unaccent`, `_UNACCENTED_FUNCTIONAL_STOPWORDS`, 4 Defensive Guards bất biến dấu và prompt tổng quát không hardcode |
| [`backend/tests/test_query_rewrite_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_query_rewrite_node.py) | **MODIFY** | Bổ sung 3 unit tests mới: `test_is_context_dependent_query`, `test_query_rewrite_standalone_query_not_hijacked_by_history`, `test_query_rewrite_defensive_guard_rejects_dropped_intent` |

---

## 4. Kết Quả Kiểm Thử & Nghiệm Thu

1. **Unit Test Node Query Rewrite**:
   - `uv run --extra dev pytest tests/test_query_rewrite_node.py` $\rightarrow$ **11/11 passed (100%) in 2.61s**.
2. **Regression Test Suites Liên Quan**:
   - `uv run --extra dev pytest tests/test_query_rewrite_node.py tests/test_rag.py tests/test_suggestion_perspective_and_multiturn.py` $\rightarrow$ **46/46 passed (100%)**.
3. **Toàn Bộ Backend Test Suite**:
   - `uv run ruff check .` $\rightarrow$ **0 lỗi (All checks passed)**.
   - `uv run --extra dev pytest` $\rightarrow$ **395/395 passed (100%) in 56.03s**.
4. **Toàn Bộ Frontend Test Suite**:
   - `npm run lint` (Biome) $\rightarrow$ **169 files checked, 0 lỗi**.
   - `npm run typecheck` (tsc) $\rightarrow$ **0 lỗi**.
   - `npm run build` (Vite) $\rightarrow$ **Build thành công bundle production (9.94s)**.
