# Phiên 436 Phân biệt giới hạn ngữ cảnh và max tokens

Ngày 2026-10-14. Người dùng hỏi liệu thiếu ý trong lượt kiểm thử 435 có do context hoặc giá trị 5000 trên UI. Chỉ chẩn đoán từ cấu hình, mã đang dùng và artifact test, không gửi thêm câu hỏi hay sửa runtime.

## Kết luận và chứng cứ

`model_policy.max_tokens=5000` là ngân sách sinh token gửi qua adapter, không phải cửa sổ ngữ cảnh. `resolve_evidence_request` lấy giá trị này từ DB cho RAG trực tiếp; DAG chuyển từ model policy. Evidence structured_call áp dụng min với ngân sách riêng: planning1000, proposal4000, verification2400. Tăng UI5000 không tăng các cap này và không tăng ngân sách context.

Chính sách evidence trong snapshot test có candidate_limit24, context_limit10, max_context_chars36000; reranker AIserver top_k5. Context packing tính JSON EvidenceBlock gồm nội dung và metadata, không phải36000tokens; mười block có thể gồm heading/fact/bối cảnh cha, không đồng nghĩa mười tài liệu. Cửa sổ thực tế và truncation ở upstream9router/Ollama chưa được xác nhận từ lượt này.

Câu6RAG: context/quote đã chứa cả53 đầu mùa và56 mã xét tuyển, prompt proposal8012tokens/completion549; verification8593/473. Publicanswer chỉ53. Đây là thiếu coverage/suy diễn ở proposal-verifier, không có chứng cứ output hết ngân sách. Câu19quotes có loại điểmTHPT, điều kiện/ngoại lệ nhưnganswer chỉ15/30. Câu11DAG selection chứa nhóm2025 và sourcepreferred2026trang10, không đoạn trực tiếp từnguồn mới: selection/packcontext là một nguyên nhân khác. Câu16RAGquotePT3ĐGNLđúng nhưnggánTHPT/verified: lỗi entailment khônggiải quyếtchỉbằngtăngcontext.

Đề xuất giữ max_tokens hiện tại khi sửa completeness/qualifier/relations; tối ưu chọn/pack context theo coverage, token budget và ghi nhận lý do bỏ block. Chỉ tăng context/cap khi có số đo chứng cứ đúng bị loại do budget và xác nhận window upstream; không đưa toàn kho vào prompt hoặc hardcode đáp án.

## Tệp và kiểm chứng

Đọc `evidence_policy.py`, `evidence_model.py`, `evidence_claims.py`, `evidence_pipeline.py`, `evidence_runtime.py`, `rag_answer_node.py`, adapter và kết quả435. Skills qnu-rag-pipeline/qnu-modelops-resilience dùng cho phân biệt tầng giới hạn. Không runtime/test/build/DB/config/index/backup mutations. Tạo journal436, snapshot436, cập nhật indexes/memory/worklog. Không công bố finish_reason=length hay số window model vì artifact không cung cấp chúng.
