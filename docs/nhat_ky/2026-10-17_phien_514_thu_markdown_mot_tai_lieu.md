# Phiên 514 — Chuẩn bị thử Markdown sạch cho một tài liệu

## Phạm vi và trạng thái

Người dùng yêu cầu bước 2 sau chỉnh prompt: thử một tài liệu, không reset hoặc
nạp lại cả kho. Dùng skill ingestion để giữ nguồn/ô bảng/unknown, RAG pipeline
để kiểm tra chunk preview; không tự coi heuristic sạch là phê duyệt nội dung.

**PARTIAL — đã chuẩn bị gói đối chiếu, chưa nhập app/tạo vector/xuất bản.**
Phát hiện file DOCX mẫu phiên509 không có hash trùng trong RepositoryDocument
hoặc bất kỳ KnowledgeSourceRevision nào. Không thể gán bản dẫn xuất này vào
một nguồn PDF/DOCX khác chỉ vì tiêu đề/nội dung có vẻ giống nhau. Cần người dùng
chọn thêm nguồn thử riêng hoặc đổi sang tài liệu đang có trong kho để so trước/sau.

## Bằng chứng hiện tại

- Kho admissions có 22 nguồn active với revision sẵn sàng, collection epoch4,
  generation `vg_a6e3190d11af`. Không sửa các pointer này.
- DOCX mẫu: `Thong tin tuyen sinh dai hoc 2026_Lan2-1 (1).docx`, SHA256
  `f8163b923bb7e026a4c6067d6b607feebce7164bc9a826f3410b354a8d36bfd0`.
- Tra mọi source revision và kho tài liệu theo hash: đều không có. Điều này
  không chứng minh không có một PDF tương đương nội dung; chưa xác lập quan hệ đó.
- Chạy lại validator509 bằng Python3.12 của backend: exit0, 924 giá trị bảng
  khớp OOXML; giữ 5 bảng có 53/5/5/52/38 dòng, 1.035 source units, nguồn không đổi.
- Cleaner hiện có tạo bản mới: 321 dòng trước/sau; toàn bộ từ và ô bảng không
  đổi, multiset số giữ nguyên. Hai vùng diff giữ nguyên số dòng (53 và 1),
  không tự sửa mã/chỉ tiêu/nhãn lỗi ở nguồn.
- `build_source_artifact(..., page_count=0)` và `structure_chunks` tạo preview
  235 đoạn, tối đa969 ký tự; kiểm tra source spans và page=null ở cả235 đoạn.
  Không gán số trang vật lý/bbox khi chỉ có OOXML mapping.
- Heuristic cấu trúc không phát hiện issue, nhưng nguồn vẫn có mã ngành không
  nhất quán, chỉ tiêu và số/ngày văn bản trống đã ghi ở509. Không coi issue=0
  là đã duyệt hoặc chứng nhận dữ kiện đúng; không tự sửa hay phê duyệt thay người.

## Gói artifact bền vững

Đã lưu bằng S3StorageDriver, từng object đọc lại kiểm tra SHA256. Prefix:

`snapshots/markdown-trials/514/f8163b923bb7e026a4c6067d6b607feebce7164bc9a826f3410b354a8d36bfd0/`

- `source.docx`: nguồn nguyên gốc.
- `md509.md`: mẫu có provenance đúng hash cũ.
- `md509-provenance.json`: mapping OOXML của mẫu509, không tự coi là adapter import.
- `cleaned.md`: bản cleaner hiện tại, SHA256
  `a6ac10f9409bc1ac6d61f020618c2c198d4fad602141491662d1527e5877874a`.
- `chunk-preview.json`: preview offline, không phải chunk set runtime đã duyệt/seal.
- `review-notes.md`: các chỗ nguồn cần người phụ trách xác nhận.
- `report.json`: trạng thái DRAFT_REQUIRES_SOURCE_REVIEW, số lượng và giới hạn;
  SHA256 `f1093d8de5c903d8287fe6c213fdb00485cd9abd68aef79db68fe4349484edb3`.

Artifact không commit vào Git. Đã yêu cầu mở ghi chú local trong panel; trả queued,
không coi là đã kiểm tra UI. Không tạo nguồn trùng trong kho.

## Kiểm chứng và giới hạn

- CWD repo: `backend/.venv/Scripts/python.exe backend/storage/md509/validate_example.py`,
  exit0/PASS.
- CWD backend: inline Python dùng SQLAlchemy read-only đối chiếu hash toàn kho,
  cleaner/artifact/structure preview, StorageDriver save/get/hash: exit0/PASS.
- Inline so sánh words/numbers/table cells/source spans: exit0/PASS. Source,
  pointer/epoch/generation/status của mọi binding trước–sau không đổi.
- Hai lần inventory ban đầu lỗi AttributeError do dùng tên trường binding không
  có; đã sửa truy vấn theo model/snapshot thật rồi chạy thành công; không ghi DB.
- Không sửa source code backend/frontend, không cần full pytest cho artifact
  dữ liệu/tài liệu. Chưa benchmark, live model, embedding, review/publish hay UI.
- Không gọi OCR/cloud, không reset/seed/reindex/restart/deploy/Git. Bước tạo
  staging và xuất bản chưa được thực hiện, không tuyên bố RAG đã cải thiện.

## Cần tiếp tục

Chọn chính xác nguồn: thêm DOCX mẫu riêng trong vùng thử (chưa phục vụ), hoặc
dùng DOCX đang có như `QNU_TuyenSinh_2026_VanBanThuyetMinh.docx` để so sánh
cùng nguồn. Nếu giữ mẫu509, cần xác nhận các mâu thuẫn nguồn trước phê duyệt;
phải tích hợp mapping dẫn xuất vào revision, không upload MD độc lập mất provenance.
