# Context575 — Sửa kiểm chứng phạm vi và điều kiện của RAG

Thay đổi tập trung vào cách sử dụng bằng chứng đã có trong nguồn: bảo toàn điều kiện của một quy tắc, phân biệt phạm vi từng hàng với vị trí bảng, và trả lời đúng khi tài liệu xác nhận dữ kiện chưa xác định. Không sửa parser vì đối soát Context574 không phát hiện mất nội dung liên quan tám câu lỗi.

## Các cơ chế được bổ sung

1. **Điều kiện đi cùng quy tắc.** Khi trích một phần của một mục danh sách, giữ toàn mục đó cùng giới hạn của nó; không kéo sang mục kế tiếp. Audit xem cả phần nguồn cùng quy định và các liên kết điều kiện, không chỉ những câu proposer chọn. Liên kết được theo đến hết trong đúng revision/hash, bất kể thứ tự các block.
2. **Phạm vi kiểm chứng đủ hẹp.** Mệnh đề có vai trò ngày khác nhau được tách riêng. Trường ngày có nhãn có thể được trình bày bằng dấu hai chấm hoặc từ “là” nếu giữ nguyên nhãn và giá trị; đổi vai trò, ngày hoặc phủ định đều không được coi tương đương. Thông tin thuộc mục không liên quan không tự trở thành điều kiện bắt buộc.
3. **Hàng bảng và quy định đầy đủ cùng có mặt.** Câu hỏi đòi giải thích điều kiện, ngoại lệ hoặc ký hiệu chuyển qua luồng kiểm chứng quy tắc. Hàng tóm tắt có thể chứng minh một giới hạn, còn phần văn bản chứng minh các điều kiện khác. Cả hai phải vừa ngân sách đang cấu hình; không tăng K hay cửa sổ context để che lỗi chọn bằng chứng.
4. **Phân biệt vị trí với phạm vi.** Ngữ cảnh gửi model có thêm header/cell nguyên văn của hàng bảng và chỉ rõ section là vị trí trong tài liệu. Tên mục bao quanh bảng không được mặc định ghi đè đối tượng ghi rõ trong từng hàng. Quy định nguồn xác định phạm vi vẫn có hiệu lực; không dùng metadata mới để miễn audit hoặc áp chéo nhóm.
5. **Mã chú thích cũng là điểm neo tìm kiếm.** Đoạn văn mang đúng mã được người dùng gọi đích danh được giữ trước các hàng chỉ khớp một phần định danh. Dùng quy tắc hình dạng mã hiện có, không thêm từ điển tên/mã của tài liệu kiểm thử.
6. **Unknown trả lời được một câu hỏi có tiền đề sai.** Khi có trích dẫn nguồn xác nhận ký hiệu/đầu vào chưa định nghĩa, câu trả lời không tính được giá trị có thể đủ căn cứ. Không được suy ra kết luận này từ kết quả tìm kiếm trống; không đổi unknown thành 0.
7. **Phục hồi có giới hạn.** Tối đa một lượt phục hồi ngữ nghĩa trong prose fallback trên cùng tập bằng chứng đã chốt. Nếu chỉ thiếu điều kiện đã có ID và span nguồn, server chép đúng điều kiện đó rồi kiểm chứng lại. Trường hợp khác chọn lại passage một lượt rồi kiểm chứng. Mâu thuẫn, ID lạ, quote ngoài nguồn, lỗi provider và kết quả kiểm chứng vẫn thiếu đều tiếp tục chặn.
8. **Liệt kê là thao tác trên nguồn.** Hai bộ chọn schema độc lập phải thống nhất đủ hàng/chỉ định danh. Contract từ chối trạng thái selected mâu thuẫn với các cờ đó. Server đếm, kiểm các mã/tên và xuất nguyên văn; hàng thiếu ô, thiếu mã/tên, trùng mã hoặc sai số lượng yêu cầu không bị âm thầm bỏ qua.
9. **Điều kiện năm cần đúng claim sở hữu.** Khi audit bỏ trống liên kết đến claim nhưng điều kiện đã hiện nguyên văn, server tìm đúng claim có cùng source/revision/hash và span bao chứa. Điều kiện năm tiếp tục qua kiểm tra vai trò năm trên chính claim đó. Không mượn năm của claim bên cạnh, không lấy ngày ban hành làm năm dữ liệu và không ghi đè temporal scope mâu thuẫn. Nếu người dùng chưa hỏi năm cụ thể, chỉ kiểm năm giới hạn được nguồn nêu; không suy một năm dữ liệu để trả lời.

## Phạm vi mã

Các file dưới `backend/app/modules/rag/` được sửa có mục đích liên quan: `evidence_audit.py`, `evidence_claims.py`, `evidence_context.py`, `evidence_indexed_audit.py`, `evidence_model.py`, `evidence_passages.py`, `evidence_validation.py`, `evidence_verification.py`, `prose_fallback.py`, `response_audit.py`, `row_answer.py`, `row_answer_contract.py`, `service.py`, `source_identity_enumeration.py`, `source_locators.py`, `source_scope_audit.py`. File mới `source_row_context.py` cung cấp header/cell cho ngữ cảnh model.

`service.py` tăng version cache đáp án thành `verified-answer-v10` để phân biệt hành vi mới. Không flush cache chung. Metadata cấu trúc chỉ được tạo lúc đọc, không ghi đè nguồn hoặc sửa schema DB. Frontend và parser giữ nguyên trong phiên này; các diff từ phiên trước được bảo toàn.

## Phòng hồi quy

File mới `backend/tests/test_source_answer_scope_575.py` dùng tên, mã, năm và số liệu khác benchmark. Bao gồm: phần giới hạn bị bỏ sau một câu trong list; không kéo mục kế tiếp; điều kiện khác owner/revision; liên kết nhiều bước ngược thứ tự; heading thiếu định danh; phụ lục nhiều tầng; dấu thập phân; vai trò ngày; phủ định; zero/không công bố/không áp dụng; ID và quote giả; kiểm chứng lại sau phục hồi; mâu thuẫn; hàng thiếu/trùng mã; mask ưu tiên khi đóng gói; bảng nhiều đối tượng dưới một tiêu đề vị trí; header thiếu/sai số cột; mã chú thích gần giống.

Các kiểm thử fixture/mocked contract chứng minh hành vi nội bộ, không thay kết quả gọi model thật. Đối soát benchmark, số test và các giới hạn được ghi riêng trong báo cáo nghiệm thu.

## Giới hạn vận hành

Nguồn xuất bản, index phục vụ, model mặc định và fallback giữ nguyên. Phép so sánh thực tế tiếp tục dùng policy giới hạn chat chỉ Luna như baseline; không bật Qwen để che lỗi trong điểm so sánh. Revision mới đang staging tiếp tục chưa xuất bản. Không commit, push, restart hoặc deploy.

Đây là bộ cải thiện từ một tài liệu phát triển và benchmark đã dùng để phân tích. Bộ test mở rộng giảm các khoảng hở đã xác định nhưng không chứng nhận mọi tài liệu hoặc mọi câu diễn đạt đều đạt. Độ trễ và số lời gọi model cần đọc từ kết quả quan sát, không giả định phục hồi sẽ miễn phí hoặc làm nhanh hơn.
