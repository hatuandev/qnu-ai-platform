# Context565 — Định danh có căn cứ nguồn

## Candidate và identity đã xác minh

`knowledge/entity_codes.py` chuẩn hóa NFC/casing/whitespace ngoài, giữ nguyên zero đầu và dấu phân cách. Không đổi O thành 0, không padding, không fuzzy/prefix match. Candidate chữ-số hoặc mã được nêu qua nhãn chỉ là tín hiệu định tuyến; năm/giá trị tiền/số lượng không tự trở thành code đã xác minh.

Mã số ngành và mã nhiệm vụ cũ giữ khả năng nhận dạng. Marker `certificate_conversion` là chỉ dẫn loại truy vấn, không phải mã entity để áp equality predicate. Khi có mã rõ ràng, ánh xạ tên ngành cũ không được chèn mã khác để thay thế nó.

## Cột mã và tên

`row_identities` dùng header role trong từng nhóm bảng, loại code columns khỏi name candidates, ưu tiên named column độc lập. Không có tên thì dùng nguyên mã làm nhãn có căn cứ; không thêm tên suy đoán. Giữ ranh giới nhóm cạnh nhau và nối trang theo cấu trúc. `clean_cell` chỉ tháo markup bao ngoài, giữ underscore bên trong mã.

## Snapshot cũ thiếu entity_code

`source_fact_resolution.FactScope` dùng tuple `(binding, index_revision, source_unit_id)` để liên kết đúng dòng. Header/cells phải bằng canonical row và đúng source revision/hash. Mã chỉ được lấy từ source-declared code column, không tìm trong ô metric hay note. Vì vậy metadata DB null không buộc phải reindex.

SQL lọc exact row keys và các column IDs đã đối chiếu trước LIMIT, trong collection/index scope hiện hành. Không dùng substring fact value để xác minh. Mã không có trong scope xuất bản không được nới sang tên gần giống hoặc nguồn khác.

Nếu cùng mã có nhiều binding/index phù hợp mà chưa phân biệt, temporal decision trả ambiguous. Source không có row locator đủ chứng minh thì resolver bỏ mapping; không đoán bằng thứ tự hay nội dung gần giống. Tính tương thích read-only đã kiểm trên QNU projection hiện hành; artifact cũ không có row/column locator đầy đủ có thể bị từ chối an toàn, chưa được chứng minh tương thích mọi định dạng legacy.

## Giới hạn và kiểm chứng

Resolver tái dùng ngân sách canonical evidence hiện có (2 triệu ký tự), không tạo global entity DB/cache mới. Chi phí đọc canonical phụ thuộc snapshot; đây chưa phải benchmark tải lớn. Không hardcode IDs nguồn kiểm thử vào ứng dụng.

Tests có mã chữ-số/underscore/zero đầu, case normalization, mã ngành, nhiệm vụ, code/name đổi vị trí, bảng chỉ có code, nối trang, mã gần giống và SQL test với nhiều hàng khác đứng trước exact match. Negative source/binding/index/hash/column/manifest giữ guard. Danh sách IDs ở [REGRESSION_IDS](REGRESSION_IDS.md).

