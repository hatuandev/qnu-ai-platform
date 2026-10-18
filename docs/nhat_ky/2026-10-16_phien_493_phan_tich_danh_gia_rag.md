# Phiên 493 — Phân tích và đánh giá RAG hiện tại

Ngày: 2026-10-16.

## 1. Mục đích và giới hạn

Lưu lại đánh giá RAG theo yêu cầu của người dùng trong lúc một phiên khác đang triển khai tiếp batch năm luồng.

- Đây là rà soát tĩnh mã nguồn kết hợp đối chiếu artifact đã có của phiên 490 và 492; không phải benchmark mới hoặc nghiệm thu bản đang vibe.
- Không sửa mã ứng dụng, nguồn tài liệu, vector, cấu hình DB, provider/model hoặc preset Top K.
- Không gọi model, chạy benchmark, migration, restart, deploy, commit hoặc push.
- Working tree có nhiều thay đổi chưa commit. Các đường dẫn và số dòng nêu dưới đây chỉ vị trí tại thời điểm rà soát; cần đối chiếu lại sau khi phiên triển khai khác hoàn tất.

## 2. Kết luận tổng thể

Nền tảng RAG đã có nhiều thành phần cần thiết, nhưng chất lượng trả lời chưa ổn định. Điểm nghẽn chủ yếu nằm ở điều phối các nhánh, hợp đồng bằng chứng, cách quyết định đủ/thiếu căn cứ và độ ổn định khi gọi model; không đơn thuần là thiếu BM25 hoặc Top K chưa đủ lớn.

Chưa có cơ sở kết luận hệ thống đạt 80% hoặc đã sẵn sàng nghiệm thu. Không đồng nhất có kết quả truy hồi, có citation, trạng thái `answered`, test đơn vị xanh và câu trả lời đúng.

Đánh giá dùng hướng dẫn RAG, đánh giá chất lượng, Backend/ModelOps và UI của dự án để tách độ đúng dữ kiện, khả năng vận hành và cách trình bày; không lấy báo cáo cũ làm bằng chứng cho mã chưa kiểm chứng.

## 3. Những phần đang đi đúng hướng

1. Đường chat được kiểm tra gọi RAG trực tiếp, không thực thi DAG/workflow để trả lời thông thường.
2. Có ràng buộc collection, binding, revision và trạng thái xuất bản; snapshot và nguồn trích dẫn giúp truy vết bằng chứng.
3. Có tìm kiếm ngữ nghĩa kết hợp từ khóa, hợp nhất kết quả, reranking và mở rộng truy vấn có trọng số.
4. BM25 đã xuất hiện trong các nhánh bằng chứng/văn bản. Nhánh lexical chính dùng PostgreSQL FTS; không gọi toàn bộ hệ thống là BM25.
5. Đã có kiểm chứng ô bảng, phạm vi năm, dữ kiện số và công cụ quy đổi điểm có kiểm soát, thay vì để LLM tự tính hoặc tự đoán.

## 4. Sáu nhóm vấn đề cần theo dõi

### 4.1. Dùng chung AsyncSession trong các truy vấn đồng thời

**Bằng chứng mã:** `backend/app/modules/rag/retriever.py`, khoảng dòng 652–685. Truy vấn lexical gốc và các biến thể được đưa vào `asyncio.gather` với cùng đối số `db`.

SQLAlchemy AsyncSession không an toàn khi nhiều tác vụ dùng đồng thời. Nhánh biến thể bắt lỗi rồi trả danh sách rỗng kèm degradation, nên lỗi truy vấn có thể biểu hiện thành thiếu nguồn thay vì một lỗi rõ ràng với người dùng.

**Mức xác nhận:** rủi ro cấu trúc đọc được từ code; chưa tái hiện bằng kiểm thử runtime mới. Không quy sáu lỗi provider trong log phiên 492 cho nguyên nhân này.

**Hướng xử lý:** tuần tự hóa phần SQL dùng chung session, hoặc dùng session riêng cho từng tác vụ DB khi thực sự cần song song. Giữ cùng ràng buộc snapshot/publication; vẫn có thể chạy lời gọi vector độc lập song song.

### 4.2. Hợp đồng chọn ô bảng còn dễ thất bại dù có nguồn

**Bằng chứng:** Q17 trong artifact nghiệm thu phiên 492 trả `ROW_AUDIT_INVALID_CELLS`. `backend/app/modules/rag/row_answer_contract.py` dùng danh sách chuỗi cho các ID ô/context; `row_answer.py`, khoảng dòng 237–241, từ chối ID ngoài catalog nhưng nhánh này chưa trả đủ chẩn đoán ID sai.

Đây không phải bằng chứng rằng tài liệu không có đáp án. Cần phân biệt model chọn sai ID, danh mục ô thiếu hoặc ngữ cảnh không đủ.

**Hướng xử lý:** siết lựa chọn theo tập ID do server sở hữu, kiểm tra tính tương thích schema với provider, bổ sung chênh lệch ID vào diagnostics an toàn. Không bỏ guard năm, scope, conflict hoặc ô để tăng số câu được chấp nhận.

### 4.3. Quyết định đủ căn cứ chưa thống nhất giữa các nhánh

**Bằng chứng mã:** `backend/app/modules/rag/service.py` điều phối nhiều nhánh: evidence pipeline, liệt kê, fact/temporal, bảng, tổng hợp và prose recovery. Các nhánh dùng lớp audit và điều kiện chấp nhận khác nhau; xem thêm `evidence_verification.py`, `prose_fallback.py`, `response_audit.py`.

Một số bước đánh giá lại coverage có thể thay kết luận thiếu trước đó. Điều này có thể đúng nếu bộ kiểm tra trước tự thêm yêu cầu ngoài câu hỏi, nhưng cần hợp đồng rõ để không bỏ mất ý thực sự được hỏi. Không sửa bằng cách máy móc AND mọi cờ `complete`, vì có thể làm tăng false-partial.

**Hướng xử lý:** ánh xạ từng yêu cầu gốc sang bằng chứng đã xác minh; ghi rõ phần thiếu, phần mâu thuẫn và lý do loại bỏ yêu cầu không liên quan. Trả phần đúng kèm giới hạn cụ thể, tránh kết luận chung gây hiểu nhầm rằng toàn bộ nội dung phía trên sai.

### 4.4. Nhiều lần gọi model và trạng thái chờ chưa rõ

**Bằng chứng mã:** một số đường đi trong `service.py` có thể qua sinh đáp án, audit rồi prose recovery với khoảng sáu lượt gọi model trước repair/retry; không phải câu nào cũng đi đủ các bước này.

`backend/app/modules/assistants/services/assistant_rag_chat.py`, khoảng dòng 83–104, phát một trạng thái tìm kiếm rồi chờ xử lý toàn bộ trước khi phát nguyên đáp án. Cách này ngăn bản nháp chưa kiểm chứng ra trình duyệt nhưng dễ tạo cảm giác đứng im. Chưa thấy deadline tổng cho toàn bộ đường `ask` trong phạm vi mã đã đọc; timeout riêng ở recovery không tương đương timeout toàn lượt.

**Hướng xử lý:** giảm bước gọi trùng, có ngân sách thời gian/lượt gọi cho toàn câu hỏi và trạng thái tiến trình trung thực. Không stream dữ kiện chưa kiểm chứng để tạo cảm giác nhanh. Phân biệt lỗi provider/hạ tầng với thiếu bằng chứng.

Context cũng cần được đóng gói theo ý hỏi và quan hệ phụ thuộc nguồn. Giới hạn ký tự ở recovery không phải giới hạn token của model; tăng `max_tokens` đầu ra không tự giải quyết thiếu bằng chứng đầu vào.

### 4.5. Liệt kê và hội thoại tiếp nối chưa có kết quả đã xác minh để tái sử dụng ổn định

**Bằng chứng mã:** `combination_enumeration.py` và `conversation_acts.py` dựng lại records/phạm vi từ snapshot. Lịch sử hội thoại dạng văn bản không phải trạng thái bằng chứng đã xác minh. Truy vấn tiếp nối có thể phụ thuộc thêm các lượt gọi model và việc suy lại scope.

Q15 ở lượt cuối phiên 492 còn partial; tên/mã chưa chuẩn hóa vẫn có thể nằm trong bảng chính rồi mới được cảnh báo. Đếm bản ghi hoặc cặp mã/tên nguyên văn không tương đương đếm ngành duy nhất đã xác minh.

**Hướng xử lý:** cân nhắc tham chiếu kết quả có cấu trúc do server sở hữu, gắn collection/snapshot/revision/filter/ID đã được chấp nhận và kiểm tra độ mới khi tái dùng. Tách mục đã xác minh khỏi mục cần đối chiếu; giữ nguồn OCR gốc, không tự sửa tên hoặc gộp gần giống thành sự thật. Trả lời “sao nhiều/ít thế” theo phạm vi lượt trước, không lặp cả bảng.

### 4.6. Nhãn Faithfulness trên UI không phải số đo thật

**Bằng chứng mã:** `frontend/src/features/assistants/assistant-playground-tab.tsx`, khoảng dòng 284–290, hiển thị nhãn xanh cố định `Faithfulness ≥ 0.90`; không liên kết với một phép đo của câu trả lời hiện tại.

Không dùng nhãn này để chứng minh chất lượng câu trả lời.

**Hướng xử lý:** hiển thị “chưa đo” khi chưa có đánh giá; chỉ hiển thị điểm khi có kết quả đo thật và định nghĩa rõ phép đo. Phân biệt trạng thái kiểm chứng nguồn, đủ/thiếu ý và lỗi chạy; không biến citation hoặc cờ boolean thành điểm faithfulness giả.

## 5. Kết quả lịch sử dùng để đối chiếu

Nguồn: `backend/storage/quality_490/review.json`.

| Profile | Đạt | Một phần | Không đạt | Lỗi chạy |
| --- | ---: | ---: | ---: | ---: |
| Legacy | 5 | 5 | 9 | 1 |
| Configured Top K | 6 | 5 | 8 | 1 |

Đây là AI review đối chiếu nguồn, không phải bộ gold được người phụ trách xác nhận. Mẫu 20 câu không chứng minh tỷ lệ đúng trên mọi chatbot hoặc Top K tối ưu. Hai profile chỉ cải thiện một câu trong mẫu; không suy rằng mọi lỗi còn lại do retrieval limit.

Nguồn: `backend/storage/quality_492/acceptance/results.json`.

- Sáu câu lỗi `ALL_PROVIDERS_UNAVAILABLE`: Q03, Q05, Q08, Q11, Q16, Q18.
- Q10 chạy xong qua prose recovery; chạy xong không tự đồng nghĩa đạt chất lượng.
- Q15 chạy xong nhưng partial; Q17 còn `ROW_AUDIT_INVALID_CELLS`.
- Q19 trả thiếu bằng chứng phù hợp phạm vi; không mặc định lấy dữ liệu năm khác làm đáp án cho năm được hỏi.

Không coi bốn lượt completed là bốn câu đúng. Không quy lỗi provider thành “không có dữ liệu”. Các số trên là lịch sử phiên tương ứng, không phải kiểm thử mã đang được phiên khác sửa.

## 6. Thứ tự đề xuất sau batch đang triển khai

1. Hoàn tất năm luồng đã được giao trong phiên đang vibe; không sửa chồng vào cùng vùng code từ báo cáo này.
2. Đối chiếu bản chốt với các vấn đề trên, ưu tiên concurrency của session DB và hợp đồng ID ô bảng.
3. Chuẩn hóa quyết định đủ/thiếu căn cứ; kiểm soát số lượt gọi, thời gian và trạng thái chờ.
4. Bổ sung trạng thái bằng chứng hội thoại phù hợp, trình bày liệt kê rõ phần đã xác minh và cần đối chiếu.
5. Sửa nhãn chất lượng UI để phản ánh số đo thật hoặc chưa đo.
6. Kiểm tra trọng tâm sau code, rồi đánh giá tập nhỏ cố định; không cần chạy 82 câu để lưu hoặc xác nhận báo cáo này.

Chưa đề xuất thêm GraphRAG, agent vòng lặp hoặc nhiều tầng mở rộng truy vấn. Trước hết cần sử dụng đúng nguồn đã tìm thấy, thống nhất kiểm chứng và làm rõ nguyên nhân lỗi. Không cần upload lại tài liệu chỉ để sửa lỗi routing/contract; chỉ xử lý nguồn khi có bằng chứng lỗi ingestion cụ thể.

## 7. Phương pháp, kiểm tra và bàn giao

- Đã đọc mã liên quan, context và Git status/diff; dùng tìm kiếm văn bản và đọc artifact cục bộ, không gọi dịch vụ ngoài.
- Lệnh đọc chính: `git status --short`, `git diff --stat`, `rg -n`, `Get-Content`; không lưu corpus, secret hoặc câu trả lời nội bộ vào báo cáo này.
- Đã tạo báo cáo và cập nhật mục lục/memory theo workflow. Không đổi luồng nghiệp vụ nên không thêm quy trình mới.
- Kiểm tra tài liệu: đọc lại UTF-8, kiểm tra file/liên kết và diff của các mục bổ sung. Kết quả cụ thể xác nhận ở lượt lưu tài liệu, không thay thế kiểm thử ứng dụng.
- Kiểm thử ứng dụng, benchmark mới, DB/runtime hiện tại: **NOT RUN**.
- Phần cần tiếp tục: review diff bản vibe đã chốt và kiểm chứng theo rủi ro trước khi tuyên bố vấn đề đã được sửa.
