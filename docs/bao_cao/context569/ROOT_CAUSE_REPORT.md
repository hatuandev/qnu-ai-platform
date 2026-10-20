# Context569 — Đối soát 13 câu RAG từng thất bại

Ngày: 20/10/2026. Phạm vi: bước 1, điều tra và báo cáo; chưa sửa ứng dụng.

**Chưa có bằng chứng rằng phải bổ sung Hybrid Fact Extraction để xử lý toàn bộ 13 câu.** Snapshot đã giữ những nội dung cần thiết. Những điểm đứt quan sát được nằm ở chọn bảng/hàng, đưa bằng chứng vào context, giữ đủ điều kiện, kiểm chứng câu trả lời và giải thích việc từ chối.

Hai phát hiện cần ưu tiên trước khi mở rộng Extraction:

- **P07:** cả hai model bỏ điều kiện áp dụng nhưng bộ kiểm tra nội bộ vẫn chấp nhận, mặc dù trích dẫn bao phủ toàn đoạn có điều kiện. Đây là khoảng hở chất lượng câu trả lời.
- **P06:** bằng chứng trả lời nằm trong danh sách rerank, nhưng bước đóng gói chọn một nhóm rộng khác rồi dừng. Tái hiện thuần bộ nhớ khớp đúng IDs đã lưu. Đưa hai đoạn đúng lên trước vẫn vừa giới hạn cũ; không cần tăng context để chứng minh chúng có thể cùng được đưa vào.

## Phạm vi bằng chứng và baseline

Đọc hai lượt cuối đã chốt, không chọn đáp án tốt từ các lượt khác:

| Lượt lịch sử | Tri thức | Có đáp án | Từ chối/làm rõ | Xã giao |
|---|---:|---:|---:|---:|
| Qwen, Context567 benchmark-3 | 51/60 | 44/50 | 7/10 | 4/4 |
| Luna, Context568 | 51/60 | 43/50 | 8/10 | 4/4 |

Mỗi lượt có 9 FAIL. Hợp hai tập có **13 IDs**, gồm **5 IDs cùng FAIL**, 4 chỉ Qwen FAIL, 4 chỉ Luna FAIL. Đã xem đủ **26 cặp câu/model**, trong đó 18 cặp FAIL và 8 cặp PASS để đối chứng. Điểm benchmark và nhãn cũ giữ nguyên.

- Nguồn mô phỏng: `bnd_fa71a57c9cf1`, revision `ks_rev_ca1e7f16d9e0`, index `idx_rev_967891af9d5d`.
- Canonical SHA256: `d466b624e1f873d0aae89ef319dc3d745088dfd9e9aeaa87fd09b61e799a604b`.
- Query/gold SHA256: `44f56799e5a07ccba7e8711c1a1cd66e99beec18a60458e1ee509cde2167d235`.
- Bằng chứng lưu: 272 canonical blocks, 368 Facts; hai lượt có cùng canonical/Facts/query-gold.
- Kiểm lại 33 gold spans của 13 câu khớp nguyên văn vị trí nguồn; 30 citations cuối của 26 cặp đều khớp hash/revision/span/quote.
- Các file ứng dụng được pin trong manifest vẫn khớp hiện tại. Không kết luận rằng cấu hình hoặc nguồn live đã được đọc lại trong phiên này: phiên này không kết nối DB/API.

Đây là tập phát triển đã dùng sửa mã, chưa phải holdout và chưa có người duyệt gold độc lập. Qwen dùng TCP; Luna dùng handler ASGI thật. Kết quả này không phải phép so hiệu năng được kiểm soát hoàn toàn hoặc chứng minh ưu thế chung của model.

## Bảng kết luận đủ 13 câu

PASS/FAIL bên dưới là kết quả lịch sử, không phải kết quả sau sửa.

| ID | Qwen | Luna | Điểm đứt đã quan sát | Mức kết luận và hướng xử lý tiếp |
|---|---|---|---|---|
| N19 | PASS | FAIL | Luna trả `ROW_SELECTION_MISSING`; fallback loại hàng CT-01 khỏi kênh bảng nên thiếu bằng chứng số 0 và ý nghĩa. | Xác nhận hàng/giá trị nguồn còn nguyên và đường loại bảng. Chưa có raw hai selector để xác định vì sao lần chọn đầu từ chối. Sửa chọn hàng/phục hồi có kiểm chứng. |
| M05 | PASS | FAIL | Nhánh liệt kê toàn bộ nguồn không tạo kết quả ở Luna; fallback không trả đủ 12 cặp mã/tên. Payload chọn schema của Bảng 1 có `source_context=[]`, không mang caption chứng minh số bảng. | Xác nhận code thuần đọc được đủ 12 cặp và gap payload. Chưa xác định selector thứ nhất, thứ hai hay guard nào trả `None`. Cần trace hẹp và bổ sung căn cứ chọn schema. |
| P03 | FAIL | PASS | Qwen fallback chọn đúng câu thứ tự nhưng bỏ hạn chế bản tổng hợp không vượt chứng cứ gốc; kiểm chứng vẫn đánh dấu đủ. | Xác nhận thiếu nghĩa ở đầu ra và lọt kiểm tra đầy đủ. Cần giữ điều kiện gắn với quy tắc, không cần tạo thêm số liệu. |
| P06 | FAIL | FAIL | Nhóm 11 blocks về Bảng 1 được đóng gói trước và làm kết thúc lượt chọn; nội dung ngoại lệ E-A bị bỏ dù nằm trong rerank. | Tái hiện đúng context IDs cả hai lượt. Ưu tiên đóng gói/bao phủ bằng chứng và liên kết phạm vi; Facts mới chưa phải yêu cầu đã được chứng minh. |
| P07 | FAIL | FAIL | Cả hai trả biên bản/30 ngày/an toàn nhưng bỏ điều kiện cơ sở tạm đóng, nhật ký, xác nhận cùng kỳ và giới hạn nhóm A. Audit báo `accepted=true`. | Xác nhận lỗi sinh câu trả lời và kiểm tra thiếu điều kiện. Có toàn đoạn nguồn trong citation. Đây là rủi ro phải xử lý trước mở rộng tự động hóa ngữ nghĩa. |
| P08 | FAIL | FAIL | Hai hàng Bảng 9 không tới fallback. Selector scope không xử lý được truy vấn về quy tắc mã. Kênh bổ sung hàng chỉ dò nhãn cột đầu, trong khi mã và quy tắc nằm ở các cột sau. | Xác nhận không phải chỉ do tắt cờ bảng: cờ thực tế đã bật, bật lại vẫn không lấy được hàng. Cần định tuyến quy tắc và tìm bằng chứng theo ô/quan hệ có nguồn. |
| P10 | PASS | FAIL | Luna có chú giải dấu gạch trong context nhưng thiếu hàng CT-01; fallback bị chặn kênh bảng sau `ROW_SELECTION_MISSING`. | Xác nhận thiếu một vế so sánh ở context; verifier sau đó báo thiếu ý nghĩa số 0. Không được dùng thông báo từ chối cũ để kết luận chú giải không tồn tại. |
| P11 | FAIL | PASS | Fallback Qwen có cả hai hàng cần so sánh nhưng yêu cầu thêm các chỉ tiêu/khoảng ngưỡng khác không được hỏi. | Xác nhận phạm vi kiểm chứng bị mở rộng và từ chối quá mức; nhánh ban đầu còn vấn đề ghép bằng chứng. Giữ tuple chủ thể/đơn vị/toán tử và giới hạn đúng yêu cầu. |
| P15 | FAIL | PASS | Qwen nêu đúng ngày nhưng thêm tuyên bố sắp xếp tăng dần, trong khi thứ tự ngày thực tế sai; audit chấp nhận. | Xác nhận lỗi quan hệ/thứ tự trong câu sinh thêm. Không phải thiếu ngày nguồn hoặc cần trích thêm Facts. |
| P16 | PASS | FAIL | Luna có quy tắc/khối mã tương đương trong context nhưng chọn đoạn chính nói về tỷ lệ chứng cứ để chứng minh tình huống thiếu A/B/C; claim bị loại. | Xác nhận lý do từ chối ở binding/verification; đoạn 14.1 trực tiếp còn chưa tới context. Cần nối đúng dẫn chiếu và chọn đúng proof; không tắt kiểm chứng. |
| X05 | FAIL | FAIL | Nhánh Facts loại đơn vị không tương thích đúng, nhưng gộp thành `NO_COMPATIBLE_FACT_EVIDENCE` và trả câu chung. | Tái hiện bằng hàm quyết định thuần với Facts gắn nguồn. Cần giữ lý do SV khác lớp và không có quy đổi, không cần LLM Extraction. |
| X08 | FAIL | FAIL | Nhánh Facts không dùng ước tính 2027 như ghi nhận đã nghiệm thu, nhưng làm mất lý do cụ thể. | Tái hiện cùng câu từ chối. Cần giải thích vai trò dự kiến/đã nghiệm thu từ metadata/nguồn, không đổi giá trị dữ kiện. |
| X09 | FAIL | PASS | Qwen bị numeric gate chặn `90`; fallback có quy tắc thiếu biến nhưng completeness/topic audit chưa chấp nhận kết luận; Luna chọn đúng quy tắc và trả được. | Xác nhận các cổng và bằng chứng hiện hữu. Chưa lưu raw câu trước numeric gate nên chưa thể khẳng định phép chặn `90` tự nó sai. Cần phân biệt đầu vào tình huống và fact nguồn, đồng thời kiểm đúng kết luận không tính được. |

Chi tiết nguồn, các tầng đã quan sát và giới hạn từng câu: [CASE_MATRIX.md](CASE_MATRIX.md).

## Luồng thực tế liên quan

Luồng có nhánh, không phải mọi câu đều đi qua cùng một pipeline tuyến tính:

1. Phân loại yêu cầu, chuẩn bị scope và snapshot đã xuất bản.
2. Yêu cầu liệt kê mã/tên có đường chọn schema hai lượt rồi đọc toàn bộ hàng bằng code.
3. Yêu cầu số liệu rõ có đường resolve định danh/Facts, kiểm năm/metric/đơn vị rồi có thể trả ngay. X05/X08 kết thúc tại đây.
4. Các đường khác dùng hybrid retrieval, chọn hàng/cột hoặc sinh câu trả lời từ excerpts.
5. Numeric gate và visible-answer audit có thể chặn câu sinh. Khi đủ điều kiện, fallback tìm canonical prose/bảng bổ sung.
6. Fallback: tạo recovery plan → tìm/rerank → đóng gói nhóm bằng chứng → chọn source passages → bind → verifier → whole-answer audit/topic/scope gates → trả câu có nguồn hoặc giữ kết quả từ chối ban đầu.

Các điểm mã đã đối chiếu: [service.py](../../../backend/app/modules/rag/service.py), [source_identity_enumeration.py](../../../backend/app/modules/rag/source_identity_enumeration.py), [temporal_answer.py](../../../backend/app/modules/rag/temporal_answer.py), [prose_fallback.py](../../../backend/app/modules/rag/prose_fallback.py), [source_labels.py](../../../backend/app/modules/rag/source_labels.py), [evidence_blocks.py](../../../backend/app/modules/rag/evidence_blocks.py), [evidence_dependencies.py](../../../backend/app/modules/rag/evidence_dependencies.py), [response_audit.py](../../../backend/app/modules/rag/response_audit.py), [evidence_claims.py](../../../backend/app/modules/rag/evidence_claims.py), [evidence_verification.py](../../../backend/app/modules/rag/evidence_verification.py).

## Phân biệt nguồn, Facts và context

Không có Fact riêng cho một đoạn văn **không có nghĩa parser đã làm mất đoạn đó**. Canonical prose và bảng nguyên văn vẫn là bằng chứng hợp lệ. P07 có 3 Facts gắn hàng tóm tắt nhưng toàn điều kiện ở đoạn văn; P06 cũng có 3 Facts tóm tắt. M05 đã có 118 Facts gắn 12 hàng và đủ mã/tên để đọc trực tiếp.

Các tình huống cần phân biệt:

- **Mất nguồn khi bóc tách:** chưa phát hiện bằng chứng cho việc này trong phạm vi các spans đã kiểm; không suy thành parser toàn tài liệu đã hoàn hảo.
- **Thiếu biểu diễn có cấu trúc:** một số điều kiện/ngoại lệ chưa có Fact riêng. Đây là cơ hội nghiên cứu, chưa chứng minh là điều kiện bắt buộc để sửa các ca trên.
- **Nguồn có nhưng không tới context:** P06 và các vế bảng của P08/P10 có bằng chứng trực tiếp.
- **Nguồn tới hoặc được trích dẫn nhưng đầu ra vẫn sai:** P03/P07/P15; P11/P16/X09 cho thấy thêm rủi ro từ chối/ghép proof.
- **Từ chối đúng giới hạn nhưng giải thích thiếu:** X05/X08. Hai ca FAIL vì lý do trả lời chưa đạt rubric, không phải hệ thống đã phát ra giá trị sai.

Các gold spans là căn cứ đối soát, không phải danh sách mọi block bắt buộc phải xuất hiện. Bằng chứng tương đương có thể đủ: P11 dùng hai hàng có đơn vị/toán tử; P16 có khối mã cùng nguồn giải thích tình huống thiếu biến. Không tính vắng một gold block là lỗi retrieval nếu đã có bằng chứng tương đương.

## Phạm vi sửa đề xuất cho bước 2

1. **Giữ đầy đủ điều kiện và kiểm quan hệ trong đầu ra:** P07/P03 trước; kiểm P15 để không chấp nhận quan hệ thời gian sinh thêm sai. Tiêu chí kiểm phải tổng quát, không từ điển tên điều khoản hoặc expected answer của từng câu.
2. **Giữ bằng chứng đúng qua lựa chọn/đóng gói:** tái hiện P06 thành regression, rồi phân biệt truy vấn quy tắc với truy vấn số liệu ở P08/P10/N19. Mọi phục hồi bảng vẫn cần kiểm đúng scope và provenance; không bật bảng vô điều kiện sau một row audit thất bại.
3. **Làm rõ quyết định chọn schema:** M05 cần caption/locator có nguồn và trace lý do từng gate; giữ kiểm số lượng, code dạng chuỗi và tính toàn bộ tập.
4. **Thu hẹp kiểm chứng đúng yêu cầu và proof:** P11/P16/X09; không bỏ negative verdict hoặc chuyển thiếu bằng chứng thành PASS.
5. **Bảo toàn lý do không tương thích:** X05/X08 trả lý do theo đơn vị/vai trò thật từ nguồn, không mở rộng quyền dùng dữ kiện khác phạm vi.

Đây là đề xuất, chưa sửa hoặc nghiệm thu các hành vi trên. Không cam kết sau sửa sẽ hết 13 FAIL hoặc vượt một tỷ lệ chưa được đo.

## Quyết định về Hybrid Fact Extraction

Nên giữ hướng nghiên cứu, nhưng MVP sau này phải chứng minh thêm giá trị so với sửa đường bằng chứng hiện tại. Các quy tắc có điều kiện/ngoại lệ như P07 phù hợp làm ứng viên POC. Mọi Candidate Fact vẫn phải giữ điều kiện và proof của từng phần; việc chia một quy tắc thành nhiều Fact rời có thể tái tạo chính lỗi đang gặp.

Chưa cần thay model, tăng 32K lên 64K, reindex hoặc xuất bản lại để hoàn thành bước đối soát này. P06 đủ hai bằng chứng trong cùng giới hạn khi thử thứ tự oracle trong bộ nhớ; phép thử đó chỉ chẩn đoán khả năng chứa bằng chứng, không phải thuật toán ranking triển khai hay benchmark PASS mới.

## Kiểm chứng và giới hạn

- Không gọi LLM mới; không gọi API, chạy benchmark lại hoặc kết nối database.
- Helper probe có một lần import khởi tạo client Qdrant và thử kiểm compatibility; network guard chặn trước kết nối ra ngoài. Kiểm tra “không có ý định I/O” **FAIL**, không được báo PASS. Không có inference hay truy cập DB từ probe.
- Probe đầu: **13 PASS / 3 FAIL, exit 1**. Hai FAIL bác bỏ giả thuyết chỉ bật bảng sẽ chữa P08; một FAIL là import side effect vừa nêu. Bằng chứng ban đầu được giữ nguyên.
- Follow-up thuần stdlib: **4 PASS / 0 FAIL, exit 0**, xác nhận gap caption M05, bác bỏ giả thuyết cờ P08 và code khớp manifest. Không ghi đè ba FAIL trước.
- Collector đối soát 13 IDs/26 cặp/33 spans/30 citations và bảo toàn hashes: PASS sau sửa helper; lịch sử lỗi helper được ghi ở [VALIDATION_REPORT.md](VALIDATION_REPORT.md).
- Không sửa application code/tests, DB/model configuration, source, Facts, vector, publication hoặc runtime đang chạy. Chỉ tạo báo cáo, memory và helper/bằng chứng ignored.
- Không full Pytest/Ruff/FE build trong task điều tra. Full Context567 có 18 FAIL là kết quả lịch sử; không phải full PASS hiện tại.
- Không có raw payload/kết quả mọi selector hoặc đoạn trả lời trước từng gate trong log đã lưu. Các điểm thiếu trace được ghi UNKNOWN, không dùng suy đoán làm nguyên nhân xác nhận.

Kết quả của bước 1 là bản đồ nguyên nhân và phạm vi sửa có căn cứ; chưa có cải thiện chất lượng mới được đo.
