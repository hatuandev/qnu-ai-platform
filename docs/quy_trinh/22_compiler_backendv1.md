# 22 — Biên soạn bản nháp trong backendV1

Phạm vi BE: runtime chat ModelOps và Compiler v1, nối sau OCR đã hoàn tất.

```text
OCR đã hoàn tất và ghim revision/hash
→ POST compilation-runs (actor/role + Idempotency-Key)
→ snapshot nguồn + cấu hình ModelOps đã ghim
→ lưu job → dispatch ARQ sau commit
→ worker kiểm lại quyền/nguồn/model
→ bản nháp đầy đủ từ nguồn đã lưu, giữ bảng và dẫn chứng
→ chọn nhóm cần bổ sung → AI qua ModelOps → raw bất biến → schema/citation check
→ JSON/Markdown + gợi ý riêng có nguồn để người dùng xác nhận
→ GET trạng thái/kết quả
```

Workspace là biên giới quyền **chỉ trong v1** theo ngoại lệ AGENTS.md. Bản nháp
không tự xuất bản hoặc đi vào retrieval. Nội dung OCR và LLM đều là dữ liệu không
tin cậy; model không quyết định quyền hoặc trạng thái duyệt.

## Biên soạn từ tài liệu đang mở

- Nút **Biên soạn** dùng tên tài liệu và đúng phiên bản văn bản đã lưu đang xem. Hộp thoại không yêu cầu chọn chế độ, model, token hoặc thêm tài liệu.
- API gửi `selective_supplement=true`, `auto_review=false`. Worker tạo bản nền nguyên văn, giữ thứ tự, bảng và dẫn chứng. Bản nền được xem trước trong lúc AI xử lý; chỉ bản hoàn tất mới đăng ký được.
- AI chỉ nhận nhóm văn xuôi liền nhau chưa có tiêu đề hoặc trường định danh văn bản tường minh chưa được quy tắc nguồn giải quyết. Không gửi toàn bộ bảng hay mọi trang qua AI. Nhận diện này có tính bảo thủ; không bảo đảm phát hiện mọi trường metadata. Nếu không có nhóm phù hợp, hoàn tất mà không gọi model.
- Dùng cấu hình ModelOps hiện có, không gán trần output ở giao diện. Lỗi token xác định được chia riêng phần lỗi theo cấu trúc, giữ giới hạn đồng thời và khóa riêng từng phần con. Không chia hoặc gửi lại khi lỗi quyền, hạ tầng hay trạng thái không chắc chắn.
- Gợi ý AI lưu riêng trong `supplement`, không ghi đè bản nền. Loại gợi ý chép nguyên nguồn/tiêu đề đã có. Nếu một nhóm AI lỗi hoặc chưa xác định kết quả, giữ bản nền và gợi ý từ các phần con đã hoàn tất, ghi rõ `incomplete` cùng mã lỗi/phạm vi chưa xong. Không tự gửi lại nhóm đó. Lỗi toàn vẹn nguồn, lưu trữ hoặc đổi cấu hình/model vẫn làm lượt thất bại.
- Khi **Đăng ký thành tài liệu biên soạn**, hệ thống tự nhận diện thông tin từ nguồn đã ghim và lưu cùng bản nháp khi người dùng bấm **Tạo tài liệu/Thêm phiên bản**. Hộp đăng ký không hiện mục **Thông tin tài liệu**, không yêu cầu hiểu metadata hoặc chọn từng đề xuất. **Thêm phiên bản mới** chỉ hiện khi tải được tài liệu đích trong kho; kho chưa có tài liệu thì hiện thẳng biểu mẫu tạo mới. Lỗi tải danh sách có thông báo và nút tải lại, không bị coi là kho trống. Năm ban hành, năm dữ liệu, hiệu lực, ngành và đợt phải đúng vai trò trong nguồn; trường khác lưu dạng thuộc tính JSON khi có cặp nhãn/giá trị tường minh. Không lấy tên tệp làm bằng chứng, không áp năm/ngành/đợt của một đoạn cho cả tài liệu. Giá trị mơ hồ hoặc mâu thuẫn để trống, không cản đăng ký.
- Server kiểm lại đề xuất AI cũ bằng quy tắc hiện hành, kiểm hash của bản xem trước tại thời điểm lưu và ghi nguồn/rules vào provenance. Không gọi thêm model để đăng ký, không sửa OCR hoặc bản biên soạn. API cũ khai báo/chọn thủ công vẫn tương thích; không trộn với chế độ tự nhận diện trong một yêu cầu. Đây là thay đổi được người dùng yêu cầu ở Context896: chỉ tự lưu thông tin nguồn, không thay quyền duyệt/phát hành. Gợi ý cấu trúc vẫn để đối chiếu khi chỉnh sửa; đăng ký, duyệt và phát hành là các thao tác riêng.
- Không tự chạy review toàn tài liệu ở luồng này. Người dùng vẫn có thể yêu cầu **Rà soát & Đánh giá** từ trang kết quả khi cần.

### Theo dõi chạy nền trong giao diện

Bấm **Biên soạn** tạo job như trước rồi giữ nguyên trang tài liệu. Bảng **Biên soạn** ở góc phải dưới dùng API tiến độ để báo trạng thái và số nhóm đã hoàn tất. Có thể thu gọn, chuyển trang trong V1 và bấm tên tài liệu để mở kết quả. Bảng không tự gửi lại công việc khi mất kết nối, không tự duyệt hoặc phát hành; mục hoàn tất có thể ẩn qua menu.

Danh sách theo dõi chỉ ở bộ nhớ phiên đăng nhập, được xóa khi đổi phiên/tài khoản. Tải lại hoặc đóng trang không hủy job backend; mở lịch sử Biên soạn trong kho để xem lại. Phần trăm là tỷ lệ nhóm đã hoàn tất, không dự đoán thời gian còn lại.

Nút **×** đóng toàn bộ bảng và ngừng theo dõi trên giao diện, không dừng hoặc xóa job. Khi bắt đầu lượt biên soạn mới, bảng tự xuất hiện lại.

Luồng nâng cao ở cấp bộ sưu tập và API cũ vẫn hỗ trợ `source_first`, `ai_supplement` hoặc biên soạn AI. Không kết hợp hai cờ đó với `selective_supplement` trong một yêu cầu. Lượt cũ giữ nguyên cấu hình đã ghim.

Xem [hợp đồng API và vận hành Compiler](../../backendV1/docs/compiler-v1.md)
và [báo cáo Context645](../bao_cao/context645/REVIEW.md). Các quy trình Compiler
legacy ở mục 18 vẫn là luồng riêng; đợt này không chạy lại hoặc sửa Compiler đó.
