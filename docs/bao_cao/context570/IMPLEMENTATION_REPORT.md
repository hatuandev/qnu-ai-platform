# Context570 — Sửa các đường lỗi RAG sau đối soát

Đã triển khai bước 2 theo Context569: sửa những điểm đứt ở chọn bảng, giữ điều kiện, đóng gói bằng chứng, kiểm quan hệ và giải thích từ chối. Đây là thay đổi mã và kiểm chứng regression; chưa chạy lại benchmark 64 câu hoặc xác nhận 13 câu đều PASS với model thật.

## Những thay đổi chính

| Nhóm ca | Thay đổi | Giới hạn cần giữ rõ |
|---|---|---|
| P03/P07 | Audit phải phân loại từng mệnh đề trong quy tắc đánh số/có dấu chấm phẩy và chỉ ra public IDs giữ điều kiện thiết yếu. Backend kiểm nội dung điều kiện có được giữ nguyên trong public text; chọn nguồn cho fallback phải giữ cả điều kiện trước và ngoại lệ sau quyền được phép. | Model vẫn xác định mệnh đề nào thiết yếu; không phải chứng minh ngữ nghĩa độc lập bằng code. Paraphrase không giữ nguyên điều kiện sẽ bị từ chối để phục hồi bằng source sentences; có thể tăng từ chối, cần đo ở bước3. |
| P15 | Kiểm quan hệ tăng/giảm trong danh sách ngày được trả lời tuyên bố đã sắp thứ tự; giữ kiểm assertion theo nguồn. | Chỉ áp với danh sách và cách ghi ngày hỗ trợ; không tuyên bố đã có bộ suy luận thời gian tổng quát. |
| P06 | Dừng mở rộng điều khoản đánh số khi gặp bảng/hình, thay vì coi ma trận phía sau là một phần nguyên tử của điều khoản. Vẫn giữ nguyên các dependency explicit và nhóm proof bắt buộc. | Không cắt điều kiện để vừa K. Replay dùng cùng snapshot/rerank đã lưu; không chứng minh reranker/provider hiện tại. |
| P08/P10/N19 | Candidate bổ sung dò literal ở các cột chứa nhãn/mã, không chỉ cột đầu; kiểm số bảng theo caption nguồn khi người dùng nêu số bảng. Phục hồi được xem hàng sau ROW_SELECTION_MISSING, vẫn cấm sau row audit/scope thất bại và truy vấn số liệu có năm không phù hợp. | Chỉ đưa hàng thành candidate; binding, provenance, trạng thái ô, scope và independent audit vẫn quyết định. Không tự đổi unknown thành số0. |
| M05 | Payload chọn schema kèm caption có source ID/quote từ ngay trước header cùng nguồn. Thêm trace trạng thái hai bộ chọn và bước validation; giữ kiểm toàn bộ hàng/code/count. | Không chọn bảng chỉ dựa filename/model memory. Chưa đo lại liệu Luna chọn đúng schema ở lượt mới. |
| P16 | Đưa direct children của mục/điều được hỏi vào ưu tiên context cùng nguồn/revision. | Đây là locator retrieval hint; không tự chứng minh điều khoản nào áp dụng hoặc thay thế điều khoản nào. |
| P11/X09 | Instruction kiểm chứng giữ đúng original question/requested topics, không tự đòi các dòng/chủ đề lân cận; quy tắc thiếu đầu vào có thể trả lời tình huống không tính được. | Không coi số người dùng nhập là fact nguồn, không nới numeric grounding, không tự tính kết quả khi thiếu biến. Cần benchmark model thật để đánh giá. |
| X05/X08 | Giữ riêng SOURCE_UNIT_MISMATCH và SOURCE_METRIC_ROLE_MISMATCH với lý do theo đơn vị/vai trò. Cho phép đọc forecast của đúng identity/year như bằng chứng giải thích từ chối; không dùng nó như giá trị reported. | Không suy quy đổi đơn vị. Giá trị không khớp vẫn không có claim_bindings. |

## Phạm vi mã

17 file ứng dụng trong module RAG: 15 file sửa và 2 helper mới. Không đổi router/API schema, ORM/database schema, parser, frontend hoặc ModelOps config.

- [source_scope_audit.py](../../../backend/app/modules/rag/source_scope_audit.py): clauses có ID, contract phủ đủ IDs, kiểm giữ điều kiện và thứ tự ngày.
- [response_audit.py](../../../backend/app/modules/rag/response_audit.py), [evidence_indexed_audit.py](../../../backend/app/modules/rag/evidence_indexed_audit.py): gắn kiểm source-side condition vào các call audit đã có, không thêm một inference service mới.
- [evidence_claims.py](../../../backend/app/modules/rag/evidence_claims.py), [evidence_verification.py](../../../backend/app/modules/rag/evidence_verification.py): chọn/kiểm đủ quy tắc đúng phạm vi.
- [source_locators.py](../../../backend/app/modules/rag/source_locators.py), [source_identity_enumeration.py](../../../backend/app/modules/rag/source_identity_enumeration.py), [source_rows.py](../../../backend/app/modules/rag/source_rows.py): caption/section locator theo source coordinates.
- [source_labels.py](../../../backend/app/modules/rag/source_labels.py), [prose_selection.py](../../../backend/app/modules/rag/prose_selection.py), [prose_fallback.py](../../../backend/app/modules/rag/prose_fallback.py), [evidence_dependencies.py](../../../backend/app/modules/rag/evidence_dependencies.py): lựa chọn và đóng gói bằng chứng.
- [temporal_answer.py](../../../backend/app/modules/rag/temporal_answer.py), [source_fact_resolution.py](../../../backend/app/modules/rag/source_fact_resolution.py): lý do không tương thích, vẫn giữ tuple và proof gốc.
- [row_answer.py](../../../backend/app/modules/rag/row_answer.py): trace IDs/counter/quyết định, không ghi source prose.
- [evidence_passages.py](../../../backend/app/modules/rag/evidence_passages.py): không tách ordinal như 1. thành một câu số liệu riêng. Cùng sửa ở visible answer splitter để trích nguyên văn danh sách không bị false numeric rejection.
- [service.py](../../../backend/app/modules/rag/service.py): cache code namespace verified-answer-v6 để không phục vụ lại kết quả v5; không flush Redis. Lý do từ chối cuối không tiếp tục khẳng định thiếu bảng/chú giải khi fallback thực tế đã tìm thấy nội dung liên quan.
- [test_context570_evidence_scope.py](../../../backend/tests/test_context570_evidence_scope.py): 25 ca regression từ fixtures độc lập, không hardcode gold IDs/expected answers của corpus riêng.

## Dữ liệu và vận hành

Không gọi model mới, không đổi Luna chính/Qwen dự phòng. Không reindex, xuất bản lại, duyệt proposal, sửa nguồn/Facts hoặc restart BE/worker/FE. Không stage/commit/push/deploy. Nguồn đang phục vụ là tài liệu mô phỏng; không mở rộng kết luận thành độ đúng trên mọi tài liệu.

Đọc DB với SET TRANSACTION READ ONLY: hash từng row của 5 collections, 23 bindings, 2 source revisions, 27 index revisions, 5 assistants và 13 bản ghi cấu hình ModelOps khớp Context568. Bài test chỉ dùng DB riêng và local Storage tạm; MinIO/Qdrant/Redis trỏ port 1, egress test chặn endpoint ngoài phạm vi. Chỉ một dòng metadata mặc định có kiểu được đưa vào DB test; không sao chép provider hoặc credential.

Task không tự restart dịch vụ và chưa xác minh phiên bản mã đang được process ứng dụng phục vụ. Benchmark bước 3 cần xác định process/code snapshot thực sự dùng bản sửa, giữ cùng model/source/gold và chấm từng ID. [Kiểm chứng](VALIDATION_REPORT.md).

## Điều kiện chạy bước3

1. Xác minh lại môi trường local, snapshot nguồn/index và cấu hình model; freeze hash mã mới và giữ nguyên query/gold/rubric của64câu.
2. Dùng handler thật chạy mã mới; không tự restart dịch vụ ngoài phạm vi được giao. Khóa lượt benchmark chỉLuna bằng inference policy có sẵn, giữ cấu hình dùng thường Luna→Qwen.
3. Ghi đủ64responses, mọi error/timeout/schema failure vẫnFAIL; so từngID với Context568, không chọn đáp án tốt từ nhiều lượt.
4. Xác minh citations/hash/span/đủ điều kiện và refusal đúng lý do; không coi schema đúng hoặc internal auditaccepted là correctnessPASS.
5. Kiểm usage thực, nguồn/config/vector seals và dọn đúng conversations/gaps của lượt thử. Báo latency/token thay đổi do audit mới; giữ giới hạn gold chưahuman-signoff/notholdout.

Các việc trên chưa được chạy ở Context570.
