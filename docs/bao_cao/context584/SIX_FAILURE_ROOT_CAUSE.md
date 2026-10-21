# Context584 — Vì sao 6 câu PDF chưa đạt?

Đã đối chiếu PDF gốc, cặp QNU Markdown/JSON thật trong Storage, projection đang được lập chỉ mục và log Context583. **Không phát hiện mất chữ/số cần thiết cho 6 câu này. Có khoảng hở ở phân loại/liên kết cấu trúc và ở cách RAG xử lý bằng chứng.** Không thể quy cả 6 lỗi cho OCR hoặc dung lượng context.

Kết quả benchmark583 vẫn là **54/60 câu tri thức, 4/4 hội thoại**. Phân tích này không sửa ứng dụng, không gọi lại LLM, không reparse/reindex/publish và không thay điểm các câu đã đo. Việc người dùng yêu cầu đổi timeout và thử lại sau đó được ghi riêng trong Context585.

## Đối chiếu từng câu

| Câu | Nội dung nguồn có còn không? | Nguyên nhân xác định được | Mức chắc chắn |
| --- | --- | --- | --- |
| P01 — giá trị áp dụng của tài liệu | Có: bìa trang 1 và đoạn giới hạn tính chất mô phỏng trang 3, đều có trong JSON/Markdown. | Dòng cảnh báo ở bìa được suy thành `section` chỉ từ cỡ chữ. RAG coi heading là context, không cho làm câu trả lời. Recovery chọn các khối ở bìa, gồm cả chân trang; không lấy đoạn giải thích ở trang 3. Audit câu trả lời ban đầu cũng không buộc được 3 assertion vào nguồn. | Xác minh được phân loại heading, quy tắc loại heading và các ID thực đã chọn. Không giữ raw proposal nên không quy đây là nguyên nhân duy nhất của toàn bộ lượt gọi. |
| P05 — Ước tính 2027/Ghi nhận 2026 | Có: chú thích C-2027 ở trang 6 được lấy **đúng nguyên văn vào ngữ cảnh**, cùng đoạn Điều 5. | Lỗi xảy ra sau retrieval, ở lựa chọn/kiểm chứng điều kiện. Sau repair, trace ghi 3 claim được nhận, `verifier_complete=true`, `audit_complete=true` nhưng kết quả vẫn `PROSE_NOT_FULLY_VERIFIED`, thiếu hai yêu cầu về ước tính và phạm vi Ghi nhận. | Khẳng định không thiếu trích xuất hoặc thiếu đoạn nguồn trong context. Không có raw qualifier roles/`retained_by` và final rejected claims nên chưa xác định chính xác trường nào làm gate từ chối. Không vá gate từ suy đoán. |
| P07 — ngoại lệ nhóm B | Có: đủ ba khoản ở trang 18. | Khoản 1 chứa điều kiện cơ sở tạm đóng/nhật ký/xác nhận giảng viên đã qua rerank (score khoảng 0,506) nhưng bị bỏ vì **giới hạn 5 khối**, không phải tràn token. PDF giữ các khoản 1–2–3 thành các sibling riêng. Recovery focused không gom cả list, và chưa có mandatory closure nối các sibling. Audit chỉ thấy phần context đã chọn nên vẫn chấp nhận câu trả lời thiếu điều kiện. | Xác minh được bằng trace và controlled packing offline: cùng nguồn, bật đóng gói whole list giữ được khoản 1; focused packing hiện tại bỏ khoản 1. Chưa áp dụng thay đổi. |
| P09 — dấu `/` của CT-06 | Có: bảng, đoạn Điều 13, chú giải và footnote trang 13 nói rõ nguồn chưa định nghĩa dấu `/`. | Trạng thái ambiguous là đúng cách giữ unknown. Nhưng `_standard_fields` gặp một ô ambiguous thì ném `ValueError`, làm cả catalog hàng lỗi `ROW_ANSWER_SOURCE_INVALID` trước bước phân loại câu hỏi cần đọc quy tắc. Chưa có cơ hội chuyển sang đọc chú giải. | Tái hiện đúng lỗi qua loader/catalog thật với DB chỉ đọc, không gọi model. Đây là lỗi xử lý unknown của RAG, không phải mất dữ liệu. |
| P10 — phân biệt `–` CT-05 với số 0 CT-01 | Có: hai dòng bảng, chú giải K-05 và footnote trang 13 đều nguyên vẹn. | Có hai lớp: bộ thu định nghĩa ký hiệu chỉ nhận dạng dấu phân cách `:`/gạch sau ký hiệu trong ngoặc, không khớp cấu trúc “Dấu … nghĩa là …” của nguồn; vì vậy CT-05 vẫn ambiguous và chưa có liên kết chú giải tương ứng. Sau đó lỗi catalog giống P09 làm cả lượt hỏi hỏng. | Regex không khớp chú giải thật đã được kiểm tra. Đã tái hiện exact `ValueError: Unresolved standard cell cannot answer`. CT-01, NV-01 là controls hợp lệ và dựng catalog thành công. |
| P16 — thiếu biến A/B/C | Có: công thức/điều kiện trang 14 và trạng thái khi thiếu chứng cứ trang 15 đều có trong MD/JSON. Các câu P12 và X09 đã dùng được quy tắc tương ứng. | Log ghi `ReadTimeout` trên Luna; provider đang cấu hình 15 giây. Sau khi không còn route hợp lệ, hệ thống trả `ALL_PROVIDERS_UNAVAILABLE` sau khoảng 21,8 giây tổng lượt hỏi. Lượt benchmark cố ý chỉ cho Luna để so với DOCX nên Qwen không được chạy fallback. | Xác minh log và timeout persisted. Không có log `MODEL_CONTEXT_EXCEEDED`. Max prompt 9.126 token là số quan sát ở các usage thành công, không phải token count của request timeout. |

## Điều này nói gì về bóc tách PDF?

- **Bảo toàn nội dung** và **khả năng sử dụng nội dung** là hai kiểm tra khác nhau. Cặp MD/JSON qua hash/parity, các chữ và số còn nguyên, nhưng metadata vai trò/phạm vi và dependency chưa đủ để mọi nhánh RAG đọc đúng.
- P01 có lỗi phân loại vai trò của một câu nội dung. Chữ đậm hoặc cỡ chữ lớn không đủ chứng minh đó chỉ là tiêu đề. Không nên chữa bằng cách cho mọi heading trở thành fact.
- P07 cần giữ trọn một quy tắc ngắn gồm đối tượng, điều kiện cho phép và ngoại lệ. Không cần gộp toàn bộ chương hoặc mở context vô hạn; cần đóng gói đúng đơn vị chứng cứ có cùng nguồn và scope.
- P10 cần tìm/link định nghĩa đúng dòng CT-05, tách biệt với CT-06. Không được vì cùng ở một chú thích mà coi `/` cũng đã có nghĩa, hoặc chuyển cả hai ký hiệu thành 0.
- P09 cần cho phép trả lời trung thực rằng nguồn chưa định nghĩa ký hiệu, đồng thời vẫn cấm dùng ô unknown làm dữ kiện định lượng. Không được đánh đồng source unknown với hỏng tọa độ/hash.
- P05 nằm ở khâu dùng/kiểm chứng bằng chứng; chạy OCR lại không giải quyết được việc chú thích đã có trong context mà gate vẫn từ chối.
- P16 nằm ở provider/timeout. Tăng context 32k lên 64k không xử lý lỗi đọc phản hồi quá hạn này.

## Thứ tự xử lý đề xuất

1. Tách lỗi toàn vẹn nguồn thật khỏi ô chưa rõ nghĩa trong row catalog. Giữ raw value/state, không chọn unknown làm số; câu hỏi giải nghĩa đi sang bằng chứng chú giải. Giữ nguyên các guard revision/hash/column/provenance.
2. Sửa phân loại câu bìa/tiêu đề và liên kết chú giải có scope. Tái sử dụng geometry, raw spans, vai trò cấu trúc và bộ máy annotation hiện có; không hardcode mã CT hoặc câu benchmark. Nếu chuyển một diễn giải thành dữ liệu ngữ nghĩa có hiệu lực, vẫn tuân vòng duyệt đã có.
3. Đóng gói đầy đủ list quy tắc ngắn trong cùng mục, rồi kiểm chứng điều kiện trên nguồn trước khi rút câu trả lời. Giữ directed links, không mở chéo bảng hoặc toàn chương. Regression cần cả các list độc lập để tránh gom quá mức.
4. P05 cần trace ngắn gồm retained claim IDs, qualifier role/evidence ID/`retained_by` và lý do gate. Không ghi private prompt/key hoặc toàn corpus vào log. Dùng payload thực để tái hiện trước khi sửa predicate; không chỉ ép `complete=true`.
5. Đối soát timeout provider với thời gian phản hồi thực và tổng budget. Không tự chuyển model để làm xanh benchmark Luna. Timeout được người dùng giao chỉnh sang 30 giây ở Context585; kết quả đo ghi riêng.

Khi triển khai cần regression PDF và DOCX tại nhánh RAG dùng chung; không hạ Quality Gate. Việc áp parser mới vào dữ liệu đang lưu phải là revision/dẫn xuất mới theo quy trình hiện có, không ghi đè nguồn âm thầm.

## Bằng chứng kỹ thuật và kiểm tra đã chạy

- Cặp chuẩn thật được đọc qua `qnu_serving.load_document`: hash MD/JSON, source binding/revision và deterministic pair parity PASS. PDF local khớp SHA256 `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`.
- Đã render và xem trực tiếp đủ các trang liên quan **1, 3, 6, 13, 14, 15, 18** bằng Poppler được cài sẵn; native text chỉ là đối chiếu bổ sung cho quan sát bố cục.
- **19 probe chẩn đoán PASS**, exit0: nội dung nguồn, loại heading, chú thích P05 đã được lấy, đoạn P07 bị drop, whole-list control, audit thiếu đầu vào, hai lỗi catalog và hai hàng controls, regex chú giải và timeout log. Probe PASS là đã xác nhận cơ chế/giới hạn, **không có nghĩa 6 câu benchmark đã sửa xong**.
- Source/index/profile/config trước phần đổi timeout khớp seal Context583; local development, DB/MinIO/Qdrant loopback. Loader/catalog chỉ chạy transaction read-only; không tạo DB test hoặc ghi knowledge.
- Probe offline có network guard. Import Qdrant client đã thử kiểm tra compatibility và bị chặn tại `socket.getaddrinfo`; không có kết nối thành công từ probe, không coi warning đó là Qdrant PASS. Không gọi LLM trong phân tích584.
- Lệnh thật, cwd repository: `backend/.venv/Scripts/python.exe .antigravity-bridge/validation/context584_readonly.py` (exit0); `context584_source.py` (exit0), Poppler render từng trang (exit0); `context584_probes.py` bản cuối (exit0, 19 checks). Helpers và raw artifacts ở thư mục ignored.
- Full Pytest/Ruff/FE build: NOT RUN vì không sửa mã ứng dụng. Full Context582 lịch sử vẫn FAIL18, không đổi thành PASS của phiên này. Không commit/push/reindex/publish/restart/deploy.

Các điểm mã: [phân loại heading](../../../backend/app/modules/knowledge/parsers/pdf_headings.py#L45), [heading chỉ làm context](../../../backend/app/modules/rag/evidence_passages.py#L22), [catalog chặn ambiguous](../../../backend/app/modules/rag/row_answer_contract.py#L129), [catalog chạy trước metric/rules](../../../backend/app/modules/rag/row_answer.py#L365), [regex định nghĩa ký hiệu](../../../backend/app/modules/knowledge/parsers/pdf_structure.py#L273), [focused packing](../../../backend/app/modules/rag/prose_fallback.py#L192), [giới hạn khối](../../../backend/app/modules/rag/evidence_blocks.py#L284), [audit điều kiện](../../../backend/app/modules/rag/evidence_indexed_audit.py#L82).

Bằng chứng riêng: `backend/storage/context584/` gồm `row-reproduction.json`, `source-pair-check.json`, `source-coverage-private.json`, `probes.json`, `offline-boundary.json`, `provider-readonly.json` và ảnh trang. Không đưa corpus/prompt riêng/credential vào Git.
