# NHẬT KÝ PHIÊN LÀM VIỆC #191
# Ngày: 2026-09-22 | Phiên: #191
# Tiêu đề: Khắc Phục Triệt Để 3 Lỗi RAG Thực Tế: Chống Entity Stickiness Trên Câu Hỏi Toàn Trường, Chặn Lọt Sai Tổ Hợp Môn & Triệt Tiêu Ký Tự Rác `[GIZ]:` / Lặp Gợi Ý

---

## 1. Bối Cảnh & Phân Tích Nguyên Nhân Gốc (Root Cause)

Qua 5 ảnh chụp màn hình hội thoại thực tế của người dùng, hệ thống phát hiện 3 lỗi kỹ thuật cần xử lý dứt điểm:

### 1.1. Lỗi Dính Thực Thể Trên Câu Hỏi Toàn Trường (Turn 5 - Entity Stickiness)
- **Hiện tượng**: Người dùng hỏi câu hỏi tổng quan toàn trường: *"xin chào cho tôi biết phương thức tuyển sinh năm 2026"*. Chatbot lại trả lời: *"Dưới đây là thông tin về phương thức xét tuyển năm 2026 dành riêng cho ngành Công nghệ thông tin (mã ngành 7480201)..."* và hiển thị bảng chỉ gồm 4 phương thức của riêng ngành CNTT.
- **Nguyên nhân**:
  - `QueryClassifier.analyze()` nhận diện từ khóa `phương thức`, `tuyển sinh` và gắn cờ `is_fact_first = True`.
  - Tầng Structured Fact Layer (`lookup_facts` trong `facts.py`) chạy truy vấn SQL tìm các bản ghi có `KnowledgeFact.attribute_name.ilike("%phương thức%")`. Do người dùng không chỉ định ngành (`entity_codes` rỗng), truy vấn quét trúng tất cả các ngành trong cơ sở dữ liệu và lấy ra 5 bản ghi đầu tiên (ngẫu nhiên hoặc theo thứ tự alphabet là ngành *Công nghệ thông tin*).
  - Tầng prompt inject bảng số liệu của CNTT vào `[TẦNG 1 - CƠ SỞ DỮ LIỆU SỰ THẬT TỐI CAO]`, khiến LLM bị ép buộc chỉ trả lời cho ngành CNTT thay vì 5 phương thức tuyển sinh chung của ĐH Quy Nhơn.

### 1.2. Lỗi Lọt Ngành Sai Tổ Hợp Môn (Turn 2 - Multi-Subject False Positive)
- **Hiện tượng**: Người dùng hỏi: *"các ngành xét tuyển tổ hợp môn Toán, Tiếng Anh, Hóa học"*. Chatbot liệt kê các ngành khối kinh tế, nhưng lại đưa ngành đầu tiên là:
  `• Giáo dục Tiểu học (Mã ngành: 7140202) - Tổ hợp môn: (Văn, Anh, Hóa)` (hoàn toàn không có môn Toán!).
- **Nguyên nhân**:
  - Thuật toán `count_subject_matches` cũ quét toàn bộ chuỗi `attribute_value` của ngành. Ngành *Giáo dục Tiểu học* có nhiều tổ hợp: `(Toán, Văn, Anh)` và `(Văn, Anh, Hóa)`.
  - Chuỗi tổng thể chứa cả 3 chữ: `Toán` (ở tổ hợp 1), `Anh`, và `Hóa` (ở tổ hợp 2). Thuật toán cũ cộng gộp lại và chấm điểm 3/3 (Full Match), dù không có bất kỳ tổ hợp đơn lẻ nào chứa đủ cả 3 môn!
  - LLM thấy ngành được chấm điểm cao nên bốc tổ hợp `(Văn, Anh, Hóa)` vào câu trả lời.

### 1.3. Lỗi Lộ Ký Tự Rác `[GIZ]:` & Gợi Ý Lặp Lại Đúng Câu Hỏi Vừa Hỏi (Turn 3 & 4)
- **Hiện tượng**:
  - Ở cuối bảng 5 phương thức (Turn 4) xuất hiện chuỗi rác: `[GIZ]:`.
  - Ở Turn 3, sau khi người dùng hỏi *"Phương thức xét tuyển học bạ của trường áp dụng cho những ngành nào?"*, nút bấm gợi ý 1 hiển thị: `-> Phương thức xét tuyển học bạ áp dụng cho những ngành nào?` (lặp lại nguyên văn 100% câu vừa hỏi).
- **Nguyên nhân**:
  - Mô hình sinh biến thể `[GIZ]:` hoặc cú pháp `[GỢI Ý]:` bị rách trước dòng gợi ý; regex `_EXPLICIT_SUGGESTION_BLOCK` chỉ khớp `[GỢI Ý]` nên bỏ sót `[GIZ]:`, làm lộ thẻ rác vào thân văn bản Markdown.
  - Tầng `extract_suggested_questions` chưa so sánh độ tương đồng giữa câu hỏi gợi ý và câu hỏi hiện tại (`current_query`) của người dùng để lọc bỏ các câu lặp lại.

---

## 2. Các Giải Pháp Kỹ Thuật Đã Triển Khai

### 2.1. Bảo Vệ Câu Hỏi Toàn Trường Khỏi Bị Chiếm Đoạt Thực Thể (`facts.py`)
- Trong `FactLayer.lookup_facts`:
  - Khi người dùng **không chỉ định mã ngành** (`not entity_codes`) và **không hỏi tổ hợp môn** (`not subject_names`), tự động lọc bỏ toàn bộ các bản ghi Fact của các ngành cụ thể (nhận diện qua `mã ngành` hoặc định dạng mã `\d{7}` trong `entity_name`).
  - Khi không bị bảng Fact của ngành CNTT chen vào, RAG tự động chuyển sang bóc tách tài liệu gốc: **Trang 2 của Đề án Tuyển sinh 2026 chứa đầy đủ 5 phương thức tuyển sinh toàn trường** (Mã 100, 200, 402A, 402B, 405) và xét tuyển thẳng.

### 2.2. Thuật Toán Chấm Điểm Tổ Hợp Môn Đơn Lẻ (`count_subject_matches` trong `facts.py`)
- Nâng cấp `count_subject_matches`:
  - Tách riêng từng tổ hợp con trong dấu ngoặc đơn `re.findall(r"\(([^)]+)\)", attribute_value)`.
  - Hỗ trợ từ điển alias đa dạng: `"tiếng anh"` $\leftrightarrow$ `"anh"` $\leftrightarrow$ `"ngoại ngữ"`, `"lý"` $\leftrightarrow$ `"vật lý"`, `"hóa"` $\leftrightarrow$ `"hóa học"`, `"văn"` $\leftrightarrow$ `"ngữ văn"`,...
  - Chấm điểm cho từng tổ hợp riêng biệt và lấy giá trị cực đại (`max_combo_matches`).
  - Kết quả: Ngành *Giáo dục Tiểu học* chỉ đạt tối đa 2/3 môn trong bất kỳ tổ hợp nào, bị xếp dưới các ngành có tổ hợp *(Toán, Anh, Hóa)* thực sự (3/3 môn).
- Bổ sung chỉ dẫn nghiêm ngặt trong `SYSTEM_PROMPT_TEMPLATE` (`composer.py`):
  `"- TRA CỨU TỔ HỢP MÔN: Chỉ liệt kê những ngành/chuyên ngành có MỘT TỔ HỢP CỤ THỂ chứa ĐỦ TẤT CẢ các môn được hỏi. Tuyệt đối không ghép các môn từ nhiều tổ hợp khác nhau của cùng một ngành để trả lời."`

### 2.3. Khử Sạch Chuỗi Rác `[GIZ]:` & Lọc Bỏ Gợi Ý Lặp Lại (`composer.py` & `service.py`)
- Mở rộng regex `_EXPLICIT_SUGGESTION_BLOCK` bao quát `(?:\[(?:GỢI\s*Ý|GIZ|GOI\s*Y|SUGGESTION|...)[^\]]*\]:?)`.
- Bổ sung bộ lọc regex trong cả `extract_suggested_questions` và `sanitize_rag_answer` tự động cắt sạch mọi thẻ đóng dạng `\[[A-Za-zÀ-ỹ0-9_\s]{2,20}\]:?\s*$` ở đuôi văn bản.
- Xây dựng hàm `_is_too_similar_to_query(suggestion, current_query)`: tính độ tương đồng từ vựng không dấu (`_unaccent`). Nếu câu hỏi gợi ý trùng lặp $\ge 70\%$ với câu hỏi người dùng vừa gửi, hệ thống tự động loại bỏ để tránh tạo nút bấm lặp lại.

---

## 3. Tệp Tin Chỉnh Sửa & Bổ Sung

| Tệp | Hành Động | Lý Do Kỹ Thuật |
| :--- | :--- | :--- |
| [`backend/app/modules/rag/facts.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/facts.py) | **MODIFY** | Đánh giá tổ hợp theo từng combo con, bổ sung alias môn thi THPT, loại trừ major facts khi câu hỏi là tổng quan toàn trường |
| [`backend/app/modules/rag/composer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/composer.py) | **MODIFY** | Ràng buộc prompt tổ hợp môn và câu hỏi trường; mở rộng regex `GIZ`; thêm `_is_too_similar_to_query` lọc echo; dọn sạch thẻ rác |
| [`backend/app/modules/rag/service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/service.py) | **MODIFY** | Truyền `current_query=req.question` vào `extract_suggested_questions` |
| [`backend/tests/test_suggestion_perspective_and_multiturn.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/tests/test_suggestion_perspective_and_multiturn.py) | **MODIFY** | Bổ sung 4 unit tests mới: kiểm thử combo con không bị blend, lọc gợi ý trùng câu hỏi, dọn sạch `[GIZ]:`, và chốt chặn loại bỏ major facts khi hỏi chung |

---

## 4. Kết Quả Kiểm Thử

- `uv run ruff check .` $\rightarrow$ **0 lỗi (All checks passed)**.
- `uv run --extra dev pytest tests/test_suggestion_perspective_and_multiturn.py` $\rightarrow$ **13/13 passed (100%)**.
- `uv run --extra dev pytest tests/test_rag.py tests/test_query_rewrite_node.py tests/test_facts.py` $\rightarrow$ **33/33 passed (100%)**.
- Toàn bộ backend test suite: **390/390 passed (100%) in 62.59s**.
- Frontend: `npm run lint` (169 files 0 lỗi) | `npm run typecheck` (0 lỗi).
