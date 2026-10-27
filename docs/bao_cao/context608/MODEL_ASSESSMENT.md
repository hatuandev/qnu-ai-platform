# Context608 — Qwen có phù hợp không?

Đánh giá dựa trên các lượt thực chạy của app, không phải kết luận tổng quát về mọi tác vụ Qwen hoặc bảng xếp hạng model.

Qwen3.5-9B đi qua ModelOps cấu hình hiện tại đã giải quyết đúng ca nguồn thiếu ngày/tháng khi nhiệm vụ và payload tách rõ. Nhánh frozen-empty control cũng đạt qua hai coverage audits, targeted extraction và item review; không bị buộc review một assertion không tồn tại nữa.

Tuy nhiên, lượt compiler ba DOCX hiện tại vẫn bị chặn ở PacketCheck vì reason dài hơn400ký tự sau một bounded correction; trước đó606 đã có length exhaustion, graph/state/schema và temporal-review lỗi. Vì vậy chưa có bằng chứng chấp nhận Qwen làm model duy nhất cho biên soạn/kiểm chứng đa nguồn này. Usage status success chỉ là inference, không chứng minh semantic đúng. Lỗi400ký tự không chứng minh context32K thiếu hoặc parser mất dữ liệu.

Khuyến nghị: thử Luna lại cho bước biên soạn và kiểm chứng phức tạp, tắt Token Saver nếu tuyến9router còn dùng, giữ nguyên nguồn/prompt/policy/budget/rubric để đối chứng. Cần quan sát output và verdict, không chỉ HTTP200. Ở giai đoạn nhận xét chưa đổi model; sau đó người dùng đã cho phép rõ ràng chuyển primary sang gh/gpt-6-luna và chạy lại cùng ba DOCX. Không dùng alias cx cũ hoặc fallback âm thầm.

Luna lịch sử603–604 cũng có lỗi scope nguồn/năm và hướng quan hệ, nên không bảo đảm đổi model là hết lỗi. Các kết quả đó dùng code/guidance khác và có yếu tố Token Saver chưa kiểm soát; chưa phải A/B công bằng với Qwen608. Chưa thể báo một phần trăm cải thiện hoặc quy mọi lỗi trước cho model.

Nếu ngân sách Luna chưa cho phép, vẫn có thể dùng Qwen cho các bước có hợp đồng hẹp/kiểm chứng chặt và giữ lỗi fail-closed, tránh cho dữ liệu chưa kiểm chứng có hiệu lực. Đây là lựa chọn sản phẩm, không có thay đổi config tự động trong608.

## Bổ sung sau chỉ đạo chuyển model

Đã kiểm exact alias gh/gpt-6-luna bằng ModelOps chat probe, HTTP200/available,3313,2ms. Danh mục 9router ban đầu chỉ có cx/gpt-6-luna; thêm gh/gpt-6-luna qua API, giữ alias cũ, provider default model, endpoint, timeout và key. Không seed trạng thái verified giả; metadata chat được bổ sung sau probe thực.

Primary defaults và admissions đổi sang gh/gpt-6-luna/single/no fallback. Probe generic HTTP200/stop/no fallback; provider báo served model gpt-6-luna, khác chuỗi alias trong request. Check so chuỗi tuyệt đối trong helper ban đầu báo FAIL; follow-up read-only xác nhận routing thực vẫn gh/gpt-6-luna. Không relabel rằng upstream trả nguyên alias, không resend mutation. Một kiểm seal của helper cũng FAIL do metadata runtime provider thay đổi; giữ receipt và đối chiếu lại chỉ các row được phép, không bỏ qua nguồn/model khác.

Token Saver tắt theo xác nhận người dùng; chưa đọc config nội bộ9router để chứng nhận độc lập. So sánh lượt Luna hiện tại chỉ phản ánh tuyến/cấu hình quan sát, không suy thứ hạng chung hoặc phần trăm cải thiện khi chưa có đánh giá cuối.

## Kết quả thực chạy Luna

Luna hoàn thành18lượt chọn bằng chứng qua cả ba nguồn, nhưng2PacketDraft trả nội dung không parse được JSON, HTTP502. Metadata hai phản hồi báo0tokens/stop, ngân sách request vẫn fit; chưa có raw body để phân biệt refusal/prose, phản hồi rỗng hoặc lỗi giao thức9router. Không có bundle sau307,09s. Do đó khuyến nghị thử Luna đã được thực hiện nhưng chưa chứng minh cải thiện chất lượng hoặc hết lỗi; ưu tiên kiểm hợp đồng/quan sát output trước khi tiếp tục so năng lực suy luận. Giữ primary gh/gpt-6-luna theo yêu cầu, không tự quay về Qwen.
