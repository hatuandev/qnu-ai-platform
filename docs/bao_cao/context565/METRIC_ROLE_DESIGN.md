# Context565 — Đại lượng, năm và đơn vị

## Phân biệt vai trò

`knowledge/metric_roles.py` bổ sung giải nghĩa tổ hợp trong đường dẫn header: quota, recorded count, estimate và rate; tái dùng các contracts cutoff, tuition, combos, methods hiện có. Không có từ khóa/tên/mã riêng của tài liệu demo.

Header nhiều tầng và raw column coordinates vẫn là bằng chứng gốc. `Số lượng` đứng riêng giữ unknown; ngữ cảnh quota xung đột với recorded/estimate không được quyết định bằng thứ tự keyword. Không suy năm từ tên file/ngày ban hành, không điền giá trị trống hoặc ký hiệu thành 0.

New derivatives dùng extractor version `structured-source-v8-quantity-roles`. `cell_context` giữ temporal status hiện hành; recognized role không đồng nghĩa semantic approval. Phương thức trong ngoặc của cutoff (THPT/Học bạ) không được ghi thành đơn vị số lượng. Legacy `FactExtractor` vẫn giữ bare quantity dưới nhãn nguyên bản/unknown thay vì làm mất raw value.

## Đọc snapshot đã xuất bản

Đối chiếu source binding/index/hash, source row, column ID/index/header segments và literal value trước khi diễn giải lại nhãn dẫn xuất. Việc này tạo deep-copied view trong request, không mutate ORM/artifact/manifest, không thay fact_set_hash.

Human override `context_review.status=verified` giữ metric/year/qualifiers đã lưu; resolver không dùng header để ghi đè quyết định đó. Source unknown/ambiguous vẫn unknown. `source_resolution.policy=source-literal-coordinates-v1` là dấu vết kiểm tra kỹ thuật, không phải chứng nhận phê duyệt.

Để tránh lọc mất record đã mang nhãn cũ, SQL eligibility dựa trên tọa độ column có metric mới đã được đối chiếu nguồn, hoặc human override có hiệu lực. Cả identity và metric eligibility đều trước LIMIT; không mở rộng toàn bộ limit vô điều kiện.

## Lựa chọn đáp án

Temporal selection kiểm code + metric + data year + unit/qualifiers + source scope. Missing year/metric, ambiguous temporal role, field blank/not_stated hoặc sai đơn vị không được mượn cột bên cạnh. Các giá trị xung đột không chọn tùy thứ tự.

Current user metric/unit được lưu trong private request constraint. Khi rewrite vô tình giữ quota cũ nhưng current turn hỏi recorded count, constraint mới được dùng cho lookup và temporal decision. Không thay Memory/Intent Router hoặc thêm prompt ép model.

Materialized fact selection vẫn phải chứng minh nguồn và closure. Không gọi mọi literal fact là “đã được người dùng duyệt”; trace phân biệt origin, trạng thái review được giữ và việc không thay approval. Nhóm vượt budget bị loại toàn nhóm, không hạ guard.

## Kiểm chứng

Tách quota/recorded count cùng năm; đổi năm; gần mã; unknown metric/year; wrong unit; cutoff method; giữ human override; cross hash/revision và current metric vượt stale rewrite. Giá trị demo lấy từ source tại thời điểm chạy, không lấy fixture trong prompt làm gold.

