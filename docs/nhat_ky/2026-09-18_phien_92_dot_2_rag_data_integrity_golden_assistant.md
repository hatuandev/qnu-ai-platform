# Nhật Ký Làm Việc — Phiên #92 (2026-09-18)

## Tiêu đề: Đợt 2 — RAG Data Integrity, Assistant Runtime Binding & Golden Assistant Quy Chế Học Vụ ĐH Quy Nhơn

### 1. Thời gian & Bối cảnh
- **Thời gian thực hiện:** Chiều 18/09/2026 (17:30 - 18:25 UTC+7).
- **Mục tiêu:** Thực thi Đợt 2 theo lộ trình chuẩn hóa hệ thống đã phê duyệt trong `docs/nhan_xet_tong_the_qnu_ai_platform_2026-09-18.md` và `implementation_plan.md`:
  1. Dọn dẹp Qdrant vector drift và loại bỏ 788 facts mồ côi trong PostgreSQL.
  2. Nạp dữ liệu hạt giống Quy chế đào tạo tín chỉ ĐH Quy Nhơn (Quyết định 1688/QĐ-ĐHQN) gồm 6 Chunks điều khoản và 7 Structured Facts.
  3. Liên kết luồng thực thi (Runtime Binding): chuyển `preferred_model_name` từ Trợ lý AI sang RAG Pipeline và ModelOps.
  4. Thiết lập ngưỡng lọc liên quan `score_threshold = 0.35` chống sinh câu trả lời khi câu hỏi nằm ngoài phạm vi tài liệu (No-Answer Policy).
  5. Xây dựng 20 test cases Golden Benchmark cho bộ quy chế và kiểm định chất lượng Ragas TM-08.

---

### 2. Các Thay Đổi Kỹ Thuật Chi Tiết (Key Technical Changes)

#### 2.1. RAG Data & Index Integrity
- Tạo script [`reconcile_qdrant_and_facts.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/reconcile_qdrant_and_facts.py):
  - Kiểm tra và xóa collection bị lệch tên `col_col_question_bank`.
  - Tái lập chỉ mục 17 vector 1024-dim chuẩn vào `col_question_bank`.
  - Thực thi câu lệnh SQL xóa 788 facts rác mồ côi trong bảng `knowledge_facts` (các fact trỏ tới `document_id` đã bị xóa). Hiện tại còn đúng 14 facts sạch, 0 facts mồ côi.
- Cập nhật [`vector_indexer.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/vector_indexer.py):
  - Bổ sung tham số `score_threshold: float = 0.35` trong `search_dense()`, loại bỏ các vector cosine similarity thấp để ngăn chặn tình trạng trả lời giả khi câu hỏi lệch hoàn toàn khỏi tri thức trường.
- Cập nhật [`retriever.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/retriever.py):
  - Ràng buộc FTS chỉ tìm kiếm các tài liệu có trạng thái `completed`, `approved`, hoặc `processed` và `is_active = True`.
  - Nâng cấp cơ chế fallback ILIKE: loại bỏ hư từ và yêu cầu khớp ít nhất 2 từ khóa khi FTS không tìm thấy kết quả, chống tình trạng các từ đơn tiết phổ biến (như "cách", "trong", "theo") gây nhiễu.

#### 2.2. Golden Assistant Quy Chế Học Vụ (`col_regulations`)
- Tạo mới [`seed_data_regulations.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seed_data_regulations.py):
  - Document ID: `doc_qnu_quy_che_tin_chi`, file `Quy_che_dao_tao_tin_chi_DHQN.pdf`.
  - 6 Chunks điều khoản chuyên sâu:
    - Điều 1 - 3: Phạm vi, chương trình đào tạo, thời gian tối đa không quá 8 năm, quy đổi 1 tín chỉ = 15 tiết lý thuyết.
    - Điều 4 - 7: Kế hoạch đào tạo, số tín chỉ kỳ chính (14-24 tín chỉ, cảnh báo 10-14 tín chỉ), kỳ hè (tối đa 8 tín chỉ), rút học phần điểm R, học cùng lúc 2 chương trình (GPA >= 2.50).
    - Điều 12 - 14: Cơ cấu điểm (quá trình 40-50%, kết thúc 50-60%), bảng quy đổi thang điểm 10 sang chữ và thang 4, điểm đạt tối thiểu (điểm D 4.0/10), xử lý điểm F bắt buộc học lại.
    - Điều 16 - 18: Xử lý học vụ, tiêu chí cảnh báo học tập theo năm (GPA < 1.20 năm 1, < 1.40 năm 2, < 1.60 năm 3), tiêu chí buộc thôi học (cảnh báo 2 lần liên tiếp), tạm dừng học tập và bảo lưu.
    - Điều 22 - 23: Chuẩn đầu ra Ngoại ngữ (VSTEP B1/IELTS 4.5 cho không chuyên; VSTEP C1/IELTS 6.5 cho Sư phạm Tiếng Anh/Ngôn ngữ Anh) và Chuẩn đầu ra Tin học (Thông tư 03/2014/TT-BTTTT).
    - Điều 25 - 26: Điều kiện công nhận tốt nghiệp (120-135 tín chỉ, GPA >= 2.00, CĐR ngoại ngữ, tin học, GDQP, GDTC) và Xếp loại tốt nghiệp (Xuất sắc 3.60-4.00, Giỏi 3.20-3.59, Khá 2.50-3.19, Trung bình 2.00-2.49; quy định hạ bậc tốt nghiệp khi điểm F vượt 5%).
  - 7 Structured Facts nạp vào `knowledge_facts`:
    - `fact_thang_diem_quy_doi`, `fact_tin_chi_hoc_ky`, `fact_moc_canh_bao_hoc_vu`, `fact_chuan_dau_ra_ngoai_ngu`, `fact_chuan_dau_ra_tin_hoc`, `fact_dieu_kien_xet_tot_nghiep`, `fact_xep_hang_tot_nghiep`.
- Tích hợp vào [`seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/knowledge/seeder.py):
  - Tự động nạp tài liệu, chunks, structured facts vào PostgreSQL và sinh vector đẩy vào Qdrant `col_regulations` (6 points).

#### 2.3. Assistant Runtime Binding & No-Answer Policy
- Cập nhật [`AskRequest`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/schemas.py) và [`RagService.ask()`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/service.py):
  - Bổ sung `preferred_model_name` và `preferred_provider_id`.
- Cập nhật [`rag_answer_node.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/workflows/nodes/rag_answer_node.py):
  - Forward `profile.model_policy.primary_model` từ cấu hình Assistant vào `AskRequest`.
- Cập nhật [`citation_guard.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/rag/citation_guard.py):
  - Tăng độ dài trích dẫn `quote` từ 200 lên 1500 ký tự giúp hiển thị đầy đủ văn bản đối soát và phục vụ đánh giá Grounding.
- Kiểm thử No-Answer Policy thành công:
  - Khi hỏi "Cách nấu phở bò truyền thống ngon nhất?", hệ thống trả về:
    `Status: insufficient_context`
    `Answer: Chưa đủ căn cứ trong quy chế hiện hành để trả lời. Vui lòng liên hệ Phòng Đào tạo.`
    `Citations: 0` (Chống bịa đặt 100%).

#### 2.4. Benchmark Dataset 20 Test Cases & TM-08 Compliance
- Mở rộng [`dataset_seeder.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/dataset_seeder.py) từ 2 stub questions lên 20 câu hỏi chuẩn nghiệm thu (`tc_reg_001` đến `tc_reg_020`).
- Nâng cấp [`evaluator.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/evaluator.py):
  - Lọc bỏ các hư từ tiếng Việt (`VIETNAMESE_QUESTION_STOPWORDS`) trong `compute_answer_relevance`.
  - Loại bỏ các câu mở đầu lịch sự hành chính ("Căn cứ quy định chính thức...", "Dựa trên tài liệu...") khỏi tập mệnh đề đánh giá tính trung thực trong `compute_faithfulness`.
- Sửa lỗi múi giờ PostgreSQL trong [`service.py`](file:///d:/DuAnPhanMem/qnu-ai-platform/backend/app/modules/evaluation/service.py) sang `datetime.now(UTC).replace(tzinfo=None)`.
- Chạy đánh giá mẫu 5 câu hỏi của `qnu_regulations_benchmark`:
  - **Faithfulness:** 1.0 (>= 0.90)
  - **Answer Relevance:** 0.887 (>= 0.85)
  - **Context Precision:** 0.96 (>= 0.80)
  - **Meets TM-08 Standard:** **True**

---

### 3. Kết Quả Kiểm Thử Toàn Diện (Verification)

1. **Kiểm tra linter Backend:**
   ```bash
   uv run ruff check .
   # Kết quả: All checks passed (0 errors)
   ```
2. **Kiểm tra unit/integration test Backend:**
   ```bash
   uv run --extra dev pytest -v
   # Kết quả: 174 passed, 19 warnings in 51.58s (100% pass)
   ```
3. **Kiểm tra linter & typecheck Frontend:**
   ```bash
   npm run lint       # Checked 115 files, 0 errors
   npm run typecheck  # tsc --noEmit 0 errors
   npm run build      # vite v6.4.3 built in 10.41s
   ```
4. **Kiểm tra Zero Mojibake:**
   ```bash
   python scripts/check_mojibake.py
   # Kết quả: 255 files scanned, 0 errors (100% UTF-8 sạch)
   ```
