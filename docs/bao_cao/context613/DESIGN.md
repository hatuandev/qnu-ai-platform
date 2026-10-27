# Context613 — Compiler theo nhóm và ngân sách theo model

## Phạm vi

Sửa bộ biên soạn chủ đề nhiều nguồn. Giữ parser, nguồn gốc, canonical Markdown/JSON, Quality Gate nội dung và các điều kiện xuất bản. Không đổi model mặc định hoặc tự nạp vector. Bản biên soạn luôn là dữ liệu dẫn xuất chờ kiểm tra; hoàn thành sinh Markdown không phải chấp thuận ngữ nghĩa.

## Hai loại dung lượng độc lập

1. **Request đến model:** context và đầu ra theo provider, alias và endpoint đang được dùng. Mỗi request được tính cả hướng dẫn, field guide/schema, dữ liệu, framing và phần sinh dự phòng. Chưa có tokenizer chính xác được cấu hình nên tiếp tục dùng cận trên UTF-8; số này không phải token provider đã đo.
2. **Bản biên soạn:** tập hợp mọi nhóm cùng danh mục ID, nguồn và bằng chứng. Có giới hạn tài nguyên vận hành (`max_manifest_objects`, số calls, thời gian, Storage), không bị ép vừa context của một request.

Không cung cấp chế độ token vô hạn. Loại bỏ các trần chung 32.000 context / 8.192 output trong các schema compiler/wiki và trần model 8.192 của request ModelOps. Giới hạn số nguyên của giao thức vẫn được giữ; model có profile thì đầu ra phải nằm trong profile trước khi cấp lease/key.

## ModelOps

`model_capabilities[alias].token_limits` lưu endpoint, context, max output, cơ sở khai báo và việc reasoning có nằm trong ngân sách sinh hay không. Profile của alias khác không được dùng thay. Đổi endpoint làm profile cũ không còn hợp lệ. URL capacity áp cùng quy tắc không credential/query/fragment như URL provider.

Compiler lấy profile động khi phân giải route. Nếu có fallback, chọn giao ngân sách phù hợp cho tất cả các route đã cấu hình trước khi chia nhóm. Đây là lựa chọn bảo thủ: có thể chưa dùng hết context của primary lớn, nhưng cùng request nguyên vẹn vẫn phù hợp với fallback nhỏ; không cắt bằng chứng khi failover. Giới hạn vận hành thấp hơn vẫn được tôn trọng.

Profile thiếu được ghi rõ `conservative_server_fallback_unverified`; hỗn hợp route có/không profile được ghi `mixed_with_unverified_server_fallback`. Giá trị tương thích server hiện tại vẫn 24.000/2.500 nếu chưa có cấu hình khác. Không coi chúng là dung lượng đã xác minh của model. Không tự suy context từ tên model hoặc tự ghi thông số phỏng đoán vào DB.

Model tách thinking ra khỏi output nhưng chưa có ngân sách thinking được xác nhận sẽ bị chặn bằng `MODEL_REASONING_BUDGET_UNVERIFIED`. Không dùng một con số thinking để suy ra mức medium. Adapter vẫn nhận `reasoning_effort` tường minh.

Biểu mẫu quản trị cũ gửi cập nhật capability từng phần không xóa profile chưa hiển thị trên form; explicit `token_limits: null` vẫn cho phép quản trị xóa. Chưa thêm trình chỉnh profile vào frontend trong đợt này; API cấu hình provider hiện có hỗ trợ trường mới. Không sửa provider/default đang chạy khi triển khai mã.

## Chia nhóm, tổng hợp và manifest

Luồng:

`canonical proofs → chọn bằng chứng → packet trích xuất/kiểm tra → nhóm tổng hợp/kiểm tra → đối chiếu nguồn → manifest + Markdown`

Packet vẫn giữ các tham chiếu cấu trúc native. Nhóm tổng hợp mang theo closure của bằng chứng, header, điều kiện, ngoại lệ và context đã có liên kết rõ ràng. Cắt nhóm không tạo năm hay phạm vi mới. Không đổi raw proof hoặc lấy tên file chứng minh năm dữ liệu.

Hợp đồng `CompilationDraft` v1 vẫn giữ 64 thực thể / 128 assertion, đọc và kiểm tra theo quy trình cũ. Khi tổng lớn hơn, compiler dùng `CompilationManifest` v2 gồm danh mục đầy đủ cùng các `CompilationGroup` có giới hạn cục bộ. Mỗi request chỉ nhận fragment vừa ngân sách và vừa hợp đồng đầu ra của nhóm. Bản cuối không cần gom toàn bộ nội dung vào một request model nữa.

Nhóm chứa các ID thực thể, assertion, quan hệ, chỉ số section và nguồn; hash nhóm gắn snapshot. Binding và readback kiểm cả ID toàn cục, thành viên nhóm, nguồn, chỉ số section, hash và coverage. Mọi section phải xuất hiện đúng một lần trong inventory, mọi assertion được giữ và mọi relation có nhóm chịu trách nhiệm. Không tự gộp thực thể cùng tên hoặc bỏ orphan chỉ để vừa cap.

## Ngân sách từng giai đoạn

Planner tổng hợp đo request thực, bỏ phần cộng dự phòng cố định 5.000 trước mọi request. Nếu review thực không vừa, chia review thành các phần có assertion/section liên quan, giữ toàn bộ raw evidence của nhóm. Kiểm đủ ID, index và coverage sau khi ghép; một review chưa xác định không bị bỏ qua.

Correction chỉ áp dụng tối đa một lần cho JSON/schema rejection đã hoàn thành. Feedback cũng phải vừa ngân sách; có thể dùng mã lỗi cấu trúc ngắn, không cắt nguồn. Timeout/provider/cancellation hoặc stage chưa rõ kết quả không được tự gửi lại. Giới hạn tổng calls không đặt lại khi tiếp tục checkpoint.

## Quan hệ giữa các nhóm và nguồn

NFC/casefold và độ giao nhau của token nhãn chỉ chọn **ứng viên**, không chứng minh cùng thực thể hoặc quan hệ. Không có từ điển tên/ngành/mã/năm viết tay. Mọi nguồn và ID nguyên gốc được giữ.

CPU tìm cặp có ngân sách riêng `max_relation_search_pairs`, độc lập với số cặp được phép gọi LLM. Khi chưa duyệt hết không gian tìm kiếm, tổng cặp là `null` và có cờ exhausted; không báo thành 0. Số ứng viên đưa sang model được giới hạn theo ngân sách calls; đây là khám phá có giới hạn, không hứa liệt kê mọi quan hệ có thể có.

Mỗi cặp được cung cấp assertion và raw proof có liên quan. Quan hệ đề xuất phải qua kiểm tra độc lập, và quan hệ có hướng còn qua blind direction review. Tên giống, ngày muộn hơn hay năm khác nhau không đủ chứng minh identity/supersedes. Các model không có quyền tự phê duyệt.

Thiếu ngân sách calls để kiểm tiếp giữ cặp trong pending. Review hoặc direction request không vừa sẽ giữ đề xuất riêng trong `unverified_proposals`: `candidate_only`, `effective=false`, `review_status=NOT_RUN`. Đề xuất ấy không nhập vào danh sách quan hệ đã qua các bước kiểm chứng. Ledger và trạng thái chưa hoàn tất được kiểm lại khi đọc.

## Lỗi và tương thích

Vượt dung lượng được trả `KNOWLEDGE_COMPILATION_CAPACITY`, HTTP422, kèm stage và giới hạn an toàn; job `capacity_blocked`, không tự retry. Khác với inference chưa rõ kết quả. Job bị chặn không được làm lineage tái sử dụng.

Checkpoint cùng source/config/actor/version vẫn hoạt động; hash cấu hình gồm policy thực, protocol manifest và hash prompt đối chiếu mới. Không tự chuyển checkpoint cũ khác protocol thành đã chạy phiên bản mới. Các phép tái sử dụng trong harness kiểm chứng có đối soát riêng, không phải API migration production.

ModelOps API, router phân quyền, nguồn, index và publication hiện có được tái sử dụng. Không migration DB. Xem [hướng dẫn cấu hình](MODEL_LIMITS_GUIDE.md) và báo cáo kiểm chứng của phiên để biết phần nào đã thực chạy.
