# Context Builder Review — phiên 547

## Audit trước thay đổi

Đường gọi hiện tại: API semantic-proposals → source lock/idle/quyền/revision →
verify cặp MD/JSON → proposal_base từ authority đợt 1 → ModelOps session riêng →
semantic_catalog → model chép evidence_quote → stage/validator → proposal pending.
Opt-in enrichment và runner offline cũng gọi cùng propose_source_semantics.

Catalog hiện tại gồm bảng/column IDs/raw values/states và prose unit ID/text.
Thiếu vị trí logic, parent/heading IDs, origin role, adjacency, provenance,
explicit reference trace và khả năng yêu cầu mở rộng. Tất cả bảng/prose đi vào
một request, ngưỡng 100.000 ký tự; vượt ngưỡng chỉ báo input budget, chưa chia
theo đối tượng. Catalog là view dẫn xuất, không phải authority mới.

Trên cùng fixture DOCX SHA-256
`58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`:
10 bảng, 103 dòng, 111 prose units; catalog cũ 62.168 ký tự / 75.884 UTF-8 bytes.
Đo một lần build trước sửa khoảng 4,91 ms; không coi một phép đo là benchmark
khẳng định hiệu năng chung. Toàn bộ số đo máy nằm trong dossier ignored.

Lỗi thật cuối phiên 546: ModelOps custom/gpt-6-luna trả output, validator báo
`Scope evidence must be an exact quote from source prose`. Chỉ giữ metadata an
toàn, không giữ raw response cũ. Vì vậy không thể khẳng định chính xác từng ký
tự quote do model trả ở lần đó. Không dựng lại một quote giả rồi gọi nó là
response thật. Regression kiểm soát trong phiên này lấy source quote thật rồi
đổi khoảng trắng, tái hiện cùng ranh giới từ chối; backend giữ bản nháp nguyên.

Nguyên nhân hợp đồng: model phải tái tạo text thay vì chọn evidence gắn danh tính
nguồn. Khác biệt format cũng bị từ chối như trích dẫn bịa. Validator hiện tại
đang làm đúng việc bảo vệ exact quote; giải pháp thay đầu ra model và cách bind,
không đổi thành fuzzy matching hoặc tự chuyển sang unit khác.

## Thiết kế triển khai

- Context package theo bảng và cửa sổ dòng, giữ đủ cột/header cha; lân cận và
  heading dùng làm candidate context, không tự cấp phạm vi chú thích.
- Related context chỉ qua context_refs/parent đã có hoặc nhãn cấu trúc khớp
  chính xác, duy nhất. Trùng nhãn/thiếu metadata giữ unresolved; không nearest
  name matching hoặc giải nghĩa luật bằng heuristic.
- Expansion có visited set, số round/call/unit và byte budget; thiếu budget
  phải ghi coverage thiếu, không cắt text rồi báo đủ.
- Backend cấp evidence ID có source unit, cell coordinate nếu có, span code
  point và hash. Model chọn ID, source unit, target, scope và reason; không
  được ghi evidence_quote thay backend.
- Backend lấy nguyên văn từ unit/raw field đã đối chiếu Structured Document,
  ghim input/revision/content hash; sau đó vẫn chạy validator note/cell/scope
  hiện có và human review. Mỗi span chỉ thuộc một unit, không nối nhiều unit
  thành một quote giả.
- Wire schema mới khác payload annotation lưu: backend bind về NoteScope,
  CellMeaning và SourceLimitation hiện hữu; thêm provenance cần thiết. Không
  tạo resolver hoặc persistence song song, không thay policy unknown đợt 2.

## An toàn môi trường theo yêu cầu người dùng

Đã kiểm cấu hình và transaction READ ONLY: DB ứng dụng local qua 127.0.0.1:5432,
MinIO local :9000, Qdrant local :6333. Cờ dev auto migration/seed đang bật ở app;
không dùng cấu hình đó để chạy tests. Docker local infrastructure đã xác minh.

Tạo database test riêng có nonce và ownership comment; tạo bảng chỉ trong DB
mới. Schema ORM có ba index khai báo trùng giống hệt: harness bỏ bản khai trùng
trong metadata tạm, không sửa models hoặc schema ứng dụng. Test child dùng
ENVIRONMENT=test, migration/seed false, StorageDriver local trong runtime folder
riêng; MinIO/Qdrant/Redis trỏ 127.0.0.1:1. Không gọi migration/DDL ở DB ứng dụng.

Cấu hình chat/credential mã hóa chỉ sao chép sang DB test từ SELECT READ ONLY,
không log secret; inference và accounting thử nghiệm dùng DB test. Sau task
phải xác minh ownership rồi xóa đúng DB test và runtime folder, giữ báo cáo
JUnit/log/machine report đã che bí mật. Không thay model/provider/endpoint.

## Trạng thái kiểm chứng

Kết quả cuối, phạm vi thực chạy và giới hạn được ghi trong
[VALIDATION_REPORT](VALIDATION_REPORT.md). Thiết kế không chứng minh một quan hệ
ngữ nghĩa đúng khi chỉ có quote; phạm vi chưa thể xác minh vẫn cần human review.
