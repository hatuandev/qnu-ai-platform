# Context614 — Ngữ cảnh mục, bảng, header, ô và chú thích

## Phạm vi

Hoàn thiện đầu vào compiler trên ba DOCX 2024–2026 đã dùng ở Context613. Giữ bytes nguồn, canonical Markdown/JSON, Quality Gate, cấu hình ModelOps mặc định và vector. Không sửa parser, reindex, xuất bản, restart hoặc thao tác Git ghi.

Lượt thực nghiệm tiếp tục dùng `ollama/gpt-oss:120b`, reasoning medium, output 8.192 trong tiến trình riêng, qua ModelOps hiện có. Primary của ứng dụng vẫn là `gh/gpt-6-luna`. Ngân sách workflow 24.000 là giới hạn bảo thủ đang dùng, không phải context model được khám phá/xác nhận từ provider.

## Nguyên nhân

Catalog cũ giữ trích đoạn và provenance, nhưng transport chủ yếu chỉ gửi quote và source revision. Liên kết context một bước không biểu diễn đủ vai trò mục, vị trí hàng/cột và phạm vi chú thích.

Trong canonical hiện có, có tiêu đề mục là paragraph; có bảng có header khai báo rỗng và hàng tên cột nằm trong body. Không thể đổi các hàng ấy thành header chỉ dựa vào nội dung chữ hoặc kiểu dữ liệu. Model có thể thấy đúng số nhưng gán nhầm cấp đào tạo hoặc loại chỉ tiêu.

## Cách thực hiện

- `compilation_structure.py`: tạo navigation dẫn xuất từ manifest đã kiểm tra. Giữ proof ID và quote gốc; không tạo fact hoặc semantic approval.
- Section: theo heading/path/parent đã khai báo; mẫu đánh số tổng quát chỉ tạo `section_candidates`, không chứng nhận ý nghĩa mục. Không dùng từ điển ngành, chỉ tiêu hoặc từ khóa benchmark.
- Table: giữ table ID, locator hàng, proof header, header path và preamble nguyên văn. Header cần locator duy nhất và khớp layout nguyên văn; thiếu, trùng hoặc bất đồng thì `unresolved`.
- Cell: giữ chỉ số cột, ID trường, literal, trạng thái và header path riêng. Metadata trường không khớp literal thì giữ literal, đánh dấu alignment chưa xác định. Không chuyển dấu chưa rõ thành 0.
- Note: tái dùng context refs/field refs của nguồn. Không tạo liên kết chỉ vì hai chú thích giống chữ, gần nhau hoặc ở cùng tài liệu. Chú thích trường được ghi theo đúng field ID.
- Header rỗng: đưa hàng body đầu vào như ứng viên có proof; giữ tất cả hàng dữ liệu. Không tự lấy Alpha/North hoặc dòng số làm tên cột.
- Lan truyền: cùng gói bằng chứng và navigation được dùng ở chọn chủ đề, trích xuất, kiểm chứng, coverage, synthesis và cross-source review. Không cắt qualifier để vừa request.

## Ngân sách request

Metadata bảng chung được gửi ở proof header; tuple ô giữ vị trí, còn literal chỉ cần xuất hiện trong quote gốc. Header path riêng của ô vẫn có override. Nhãn authority của temporal navigation được gửi một lần, không lặp ở từng proof.

Planner đo cả source hashes và temporal navigation của request trích xuất. Planner chọn chủ đề đo cả request đầu và request kiểm chứng có `prior_selection`; giới hạn danh sách lấy từ schema. Bỏ reserve sửa định dạng cố định ở hai bước này; mỗi request thực, kể cả một lần sửa định dạng đã được phép, vẫn được đo đầy đủ và chặn khi vượt ngân sách. Không tăng context/output hoặc bỏ review.

Giới hạn vận hành số packet giữ mặc định 30; schema cho phép server cấu hình tối đa 256, vẫn chịu tổng ngân sách call và thời gian. Fixture chạy ba nguồn dùng tối đa 128 packet/512 call để tránh giới hạn cố định 30 gói; đây là giới hạn vận hành trong tiến trình thử, không đổi model, context, output hoặc Quality Gate của ứng dụng.

Sau lượt chọn chủ đề hoàn tất rồi dừng ở giới hạn packet, fixture mới chỉ nhập lại các cặp `TopicSelection` đã hoàn tất, kiểm tra chính xác request/instruction/raw source/model configuration. Không nhập 145 fact cũ hoặc biến job bị chặn thành job đã duyệt; trạng thái job cũ giữ nguyên. Đây không phải chức năng migration checkpoint production.

Audit và repair coverage là bước bổ sung tùy chọn: nếu request đầy đủ vẫn không vừa sau factoring, không gửi inference hoặc cắt raw context. Giữ assertion cũ, giữ missed/required proof trong `remaining_evidence_ids` và `review.missed_evidence_ids`, ghi `audit_capacity` hoặc `repair_capacity` có `status=NOT_RUN` với budget thật; complete vẫn false. Các gói khác có thể tiếp tục; đây không phải biến lỗi thành PASS.

`request_budget` tiếp tục đo đúng request thực, bảo toàn contract cũ. `planned_request_budget` cộng phong bì JSON lỗi tối thiểu được đo thật để bảo đảm một lần correction có chỗ; không đặt reserve token lớn tùy ý. Packet, topic verifier có prior selection, review, synthesis và cross-source planning dùng cùng nguyên tắc này. Request đã có feedback không dự phòng lần thứ ba.

Phần giải thích review có giới hạn storage 4.096 ký tự thay cho 400. Đây là diagnostic, không phải bằng chứng; regression xác nhận lý do dài vẫn không thể làm entity_scope=false thành supported/complete. Vẫn giữ nguyên enum, source refs, verdict, scope/year/condition và số lần correction.

Fixture sau cùng kiểm lại immutable Storage receipts của các lượt đã chạy trong Context614. Chỉ replay đầu ra hoặc lỗi format đã biết khi wire request/schema/instruction trùng chính xác và provider/default seal, model, thinking, output, nguồn còn khớp. Alias proof/object được ánh xạ lại; mỗi receipt chỉ được dùng một lần, kể cả hai audit độc lập có request giống nhau. Không replay call đang chạy hoặc chưa có kết quả; lỗi đã biết vẫn được replay như lỗi, không như output hợp lệ. ModelOps chỉ gọi thật cho request mới; báo cáo tách actual call, cache receipt và logical stage count. Không áp cơ chế fixture này lên checkpoint production.

## Tính toàn vẹn và tương thích

`evidence_catalog` và snapshot proof nguồn giữ nguyên. `source_structure`/`structure_protocol` là phần riêng của bundle; đọc lại phải tái dựng khớp với nguồn. Source-context drift cũng bị chặn. Protocol và instructions tham gia configuration hash; gói ngữ cảnh đổi không được tái sử dụng kết luận cũ như thể đã kiểm chứng bằng đầu vào mới.

Bundle cũ chưa có cấu trúc mới vẫn đọc theo validation cũ; không migrate hay giả mạo checkpoint. Authorization, idempotency, uncertain/no-resend, manifest, unknown, source hash và publication guard hiện có được giữ.

## Giới hạn

Navigation không thay thế hiểu ngữ nghĩa. Một mục đánh số có thể là danh sách; một hàng đầu có thể là dữ liệu. Chỉ review độc lập từ raw proof mới đánh giá assertion được hỗ trợ hay chưa. Kết quả tạo được bundle không tự đồng nghĩa `APPROVED`, và không phải chứng nhận lại toàn luồng ingestion/serving.

Các thay đổi ứng dụng nằm trong compiler runtime policy/catalog/coverage/engine/transport/validation/modelops configuration hash và module structure mới. Test integration chỉ bổ sung prefix database Context614, giữ các guard host, environment và ownership.
