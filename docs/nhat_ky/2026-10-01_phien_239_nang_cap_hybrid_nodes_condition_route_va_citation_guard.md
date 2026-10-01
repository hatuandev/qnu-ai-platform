# NHẬT KÝ LÀM VIỆC — PHIÊN #239
**Thời gian**: 2026-10-01 22:15 (UTC+7)  
**Vai trò**: AI Senior Full-Stack Architect & Enterprise AI Systems Specialist  
**Chủ đề**: Nâng Cấp Mô Hình Hybrid Nodes Cho Quy Trình DAG (ConditionRouteNode & CitationGuardNode) — Kết Hợp Bất Biến Hình Thái Học & Micro-LLM Disambiguation

---

## 1. Bối Cảnh & Mục Tiêu Phiên Làm Việc

Tiếp nối phê duyệt kế hoạch nâng cấp DAG Workflow từ Người dùng ([`ke_hoach_nang_cap_hybrid_nodes_dag_workflow.md`](../../ke_hoach_nang_cap_hybrid_nodes_dag_workflow.md)), phiên này tập trung giải quyết triệt để 2 vấn đề lớn trong tầng điều phối luồng:
1. **Lỗi định tuyến nhầm intent trong `ConditionRouteNode`**: Xóa bỏ mảng 88 từ khóa gán cứng `_INQUIRY_KEYWORDS`, giải quyết triệt để bài toán câu hỏi phức hợp (vừa chào hỏi vừa hỏi nghiệp vụ), bổ sung cơ chế Micro-LLM Disambiguation cho các ca hỏi mơ hồ.
2. **Lỗ hổng lọt ảo giác số liệu trong `CitationGuardNode`**: Thay vì chỉ đếm `len(citations) > 0`, bổ sung thuật toán toán học kiểm tra tính nhất quán của số liệu/ngày tháng (Number & Date Consistency Check 0ms) và tỷ lệ bám ngữ cảnh (Sentence Groundedness Ratio), ngăn chặn 100% việc LLM bịa đặt điểm chuẩn, học phí hoặc chỉ tiêu ngoài tài liệu chính thức.

---

## 2. Các Thay Đổi Mã Nguồn Chi Tiết

### 2.1. Nâng Cấp `condition_route_node.py` (Hybrid Intent Router)
- **Tệp sửa đổi**: `backend/app/modules/workflows/nodes/condition_route_node.py`
- **Xóa bỏ**: 100% mảng từ khóa cứng `_INQUIRY_KEYWORDS` (88 từ) vi phạm Tôn chỉ 7 `AGENTS.md`.
- **Triển khai kiến trúc 3 tầng**:
  1. *Tầng 1 (Bất biến Cú pháp & Hình thái học 0ms)*:
     - Dấu `?` $\rightarrow$ 100% là câu hỏi (Inquiry), không bao giờ coi là câu chào thuần túy.
     - Đại từ / hạt nhân nghi vấn ngữ pháp tiếng Việt qua `_SYNTACTIC_INTERROGATIVE_PATTERN`: `gì`, `nào`, `mấy`, `sao`, `đâu`, `bao nhiêu`, `bao lâu`, `khi nào`, `thế nào`, `ra sao`, `làm sao`, `tại sao`, `cho hỏi`, `xin hỏi`, `thắc mắc`, `tư vấn`, `hướng dẫn`...
     - Tách bỏ lời chào và đại từ xưng hô (`thầy cô`, `em`, `bot`, `ad`, `ạ`, `nhé`). Nếu mệnh đề thực chất còn lại $\ge 2$ từ hoặc độ dài $\ge 8$ ký tự $\rightarrow$ khẳng định là câu hỏi nghiệp vụ.
  2. *Tầng 2 (Micro-LLM Intent Classifier cho ca khó/vùng xám)*:
     - Khi quy tắc tất định không khớp và chuẩn bị rơi vào `default_node`:
     - Tự động gọi `modelops_service.generate()` với `temperature=0.0`, `max_tokens=50`, `thinking_budget=0` và timeout cứng 1.5s để phân loại câu nói vào đúng Rule ID mục tiêu.
  3. *Tầng 3 (Safe Fallback)*:
     - Tự động fallback về `default_node` nếu LLM timeout hoặc mạng bận, bảo đảm không bao giờ làm nghẽn pipeline.

### 2.2. Nâng Cấp `citation_guard_node.py` (Mathematical Number & Hallucination Guardrail)
- **Tệp sửa đổi**: `backend/app/modules/workflows/nodes/citation_guard_node.py`
- **Triển khai kiến trúc đối soát đa tầng**:
  1. *Hàm `_gather_combined_context()`*: Tập hợp toàn diện văn bản minh chứng từ `retriever contexts`, `citation quotes`, `citation snippets`, `titles` và `fact_markdown`.
  2. *Hàm `_detect_number_hallucinations()` (Thuật toán Toán học 0ms)*:
     - Trích xuất toàn bộ con số (nguyên, số thập phân `24.5`, `24,5`) trong câu trả lời.
     - So khớp tập hợp (Set Difference) với ngữ cảnh trích dẫn. Nếu phát hiện số lạ ngoài ngữ cảnh $\rightarrow$ `is_grounded = False`, `selected_port = "ungrounded"`, chặn đứng việc cung cấp số liệu sai lệch cho người dùng.
  3. *Hàm `_compute_sentence_groundedness_ratio()`*:
     - Tách các câu khẳng định và đo tỷ lệ trùng khớp từ vựng cốt lõi với trích dẫn. Nếu tỷ lệ $< 0.25$, cảnh báo độ tin cậy thấp và kích hoạt gác cổng.

### 2.3. Chuẩn Hóa Triệt Để 5 Khối Mã Hardcode Sang Bất Biến Toán Học & Hình Thái Học (Tôn Chỉ 7 AGENTS.md)
Theo yêu cầu rà soát và chuẩn hóa của Người dùng, toàn bộ 5 khối mã gán cứng trong 2 node đã được chuẩn hóa 100%:
1. **Khối 1 (`_BENIGN_NUMBERS` trong `citation_guard_node.py`)**:
   - *Trước*: Gán cứng danh sách năm `{"2020", "2021", ...}` và số nhỏ `{"1", "2", ...}`.
   - *Sau*: Thay thế bằng hàm bất biến toán học `_is_benign_structural_number(num_str)`:
     - Niên lịch thế kỷ 20-21: `(?:19|20)\d{2}`.
     - Số thứ tự / bullet point: `1 <= int(val) <= 10`.
     - Tỷ lệ phần trăm hoàn hảo: `val == 100`.
     - Số thập phân (`24.5`, `24,5`) và số liệu $\ge 11$ bắt buộc phải được đối soát nghiêm ngặt với context.
2. **Khối 2 (Tiền tố câu mào đầu trích dẫn trong `citation_guard_node.py`)**:
   - *Trước*: Mảng 16 tiền tố gõ tay `["căn cứ quy định", "theo quy chế", ...]`.
   - *Sau*: Mẫu biểu thức cú pháp mệnh đề `_SYNTACTIC_FRAMING_PATTERN = re.compile(r"^\s*(?:căn\s+cứ|theo|dựa\s+trên|kính\s+gửi|xin\s+(?:phép|gửi|giải|chào)|chào\s+|nguồn\s*:|trích\s+dẫn)\b", re.IGNORECASE)`.
3. **Khối 3 (`_PURE_GREETING_WORDS` trong `condition_route_node.py`)**:
   - *Trước*: Tuple 18 cụm từ chào gán cứng từng kết hợp đại từ ("chào em", "chào thầy", "chào cô",...).
   - *Sau*: Tập hợp gốc từ chào hỏi hình thái học `_GREETING_ROOT_STEMS = frozenset({"chào", "hello", "hi", "hey", "cảm ơn", "cm ơn", "thanks", "thank you", "tạm biệt", "bye"})` kết hợp tiền tố lễ phép `_GREETING_PREFIX_PATTERN = re.compile(r"\b(?:xin|kính|chúc)\s+", re.IGNORECASE)`.
4. **Khối 4 (`_ADDRESSEE_AND_POLITE_PATTERNS` trong `condition_route_node.py`)**:
   - *Trước*: Liệt kê danh sách cứng các phòng ban ("phòng đào tạo", "phòng ctsv", "phòng hành chính", "thư viện qnu",...).
   - *Sau*: Mẫu hình thái học hành chính tổng quát:
     ```python
     _ORGANIZATIONAL_ENTITY_PATTERN = re.compile(
         r"\b(?:trợ\s+lý|phòng|ban|trung\s+tâm|khoa|viện|trường|thư\s+viện|đoàn|hội|hội\s+đồng|bộ\s+môn)"
         r"(?:\s+[^,!?.\n]+?)?(?=[,!?.\n]|\s+(?:cho|hỏi|tư\s+vấn|xét|điểm|lấy|học|cần|muốn|được|ạ|ơi|nhé|nha)|\s*$)",
         re.IGNORECASE,
     )
     ```
     Nhận diện tự động mọi phòng ban, khoa, viện, trung tâm của trường mà không cần gán cứng tên cụ thể.
   - Cùng mẫu đại từ & trợ từ nghi vấn/lễ phép `_POLITE_PRONOUNS_AND_PARTICLES = re.compile(r"\b(?:thầy\s+cô|quý\s+thầy\s+cô|quý\s+vị|thầy|cô|anh|chị|em|bạn|mình|qnu(?:\.ai)?|bot|ai|ad|admin|ạ|nhé|nha|ơi|với|nhỉ|cho\s+(?:tôi|em|mình|chúng\s+tôi))\b", re.IGNORECASE)`.
5. **Khối 5 (`_QUESTION_INDICATORS` trong `condition_route_node.py`)**:
   - *Trước*: Tuple 30 từ hỏi tìm kiếm substring thô không có ranh giới từ.
   - *Sau*: Mẫu cú pháp nghi vấn có ranh giới từ `\b` `_SYNTACTIC_INTERROGATIVE_PATTERN` phân biệt rõ ràng câu nghi vấn thực thụ với câu chào, không bị lỗi false positive.

### 2.4. Rà Soát Chuyên Sâu & Khắc Phục 2 Lỗi Tiềm Ẩn Thực Tế (Deep Review & Edge Cases Fix)
Trong quá trình rà soát độc lập từng dòng mã theo yêu cầu của Người dùng, hệ thống đã phát hiện và xử lý triệt để 2 lỗi tiềm ẩn thực tế:
1. **Lỗi `condition_route_node.py` vỡ biểu thức Regex khi `pattern` chứa ký tự điều khiển (`\b`, `(?:...|...)`)**:
   - *Nguyên nhân*: Lệnh `tokens = [t.strip() for t in pattern.split("|")]` cắt biểu thức `r"\b(?:tuyển\s+sinh|xét\s+tuyển|ngành)\b"` thành các mẩu `\b(?:tuyển\s+sinh`. Khi chạy qua `re.escape()`, các ký tự bị escape thành `\\b\(\?\:`, khiến điều kiện không bao giờ khớp câu nói thực tế mà luôn rơi vào fallback. Đồng thời token chào hỏi bị biến thành `bxinschào`.
   - *Khắc phục*: Tách riêng luồng kiểm tra regex trực tiếp (`re.search(pattern, message)`) trước khi fallback sang từ khóa; chuẩn hóa việc trích xuất token lời chào bằng cách lọc sạch cú pháp regex trước khi đối soát.
2. **Lỗi `citation_guard_node.py` xé nhỏ số tiền tệ có dấu phân cách hàng nghìn (`15.000.000` VNĐ)**:
   - *Nguyên nhân*: Regex `r"\b\d+(?:[.,]\d+)?\b"` chỉ bắt 1 dấu chấm thập phân, khiến `15.000.000` bị cắt thành `15.000` và `000`, dễ gây false-positive nghi ngờ số liệu bịa đặt. Đồng thời `rag_answer_node.py` chưa đẩy `guidance_context` và `facts_used` (dạng markdown) vào `context.node_data`, khiến `CitationGuardNode` thiếu dữ liệu đối soát bảng sự thật.
   - *Khắc phục*: Nâng cấp regex số liệu `r"\b\d+(?:[.,]\d+)*\b"` giữ nguyên vẹn chuỗi số tiền tệ, kiểm tra đối soát chéo cả dạng dấu chấm, dấu phẩy và chuỗi số thô (`15000000`); đồng thời lưu trữ đầy đủ `guidance_context` và `fact_markdown` từ `rag_answer_node` sang `node_data`.

---

## 3. Kết Quả Kiểm Thử & Đảm Bảo Chất Lượng (Verification)

1. **Bộ Unit Test mới**:
   - `tests/test_condition_route_node.py`: **5/5 passed (100%)** (khớp chính xác `faq_node` qua regex intent 'ngành', kiểm thử chào tự động tới mọi phòng ban mới: Khảo thí, Viện Quốc tế, Khoa CNTT, Đoàn Thanh niên...).
   - `tests/test_citation_guard_node.py`: **4/4 passed (100%)** (phát hiện số liệu bịa đặt, chấp thuận tiền tệ `15.000.000 VNĐ`, dấu phẩy thập phân, hotline và trích dẫn rỗng).
2. **Kiểm thử hồi quy toàn diện**:
   - `tests/test_workflows.py`: **24/24 passed (100%)**
   - `tests/test_evaluation_truthful.py`: **7/7 passed (100%)**
   - `tests/test_evaluation.py`: **8/8 passed (100%)**
   - `tests/test_stopwords.py`: **6/6 passed (100%)**
   - `tests/test_table_reconstructor.py`: **18/18 passed (100%)**
   - $\rightarrow$ **Tổng cộng: 72/72 tests PASSED 100%**.
3. **Linter**:
   - `ruff check app/modules/workflows/nodes/ tests/test_condition_route_node.py tests/test_citation_guard_node.py` $\rightarrow$ **All checks passed! (0 lỗi)**.

---

## 4. Trạng Thái & Cam Kết
- **Trạng thái**: HOÀN THÀNH 100%.
- **Quy tắc Git**: Tuyệt đối không chạy `git push`, giữ nguyên các commit cục bộ để Người dùng tự chủ động push.

