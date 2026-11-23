# 43 — Bóc tách tự động sau upload trong backendV1

Áp dụng backendV1; frontendV1 chưa thay bố cục trong phiên710 (frontendV1 đã gỡ ngày 2026-11-13; giao diện hiện hành là `frontendV2/`). Workspace là biên
quyền của đơn vị, mọi thao tác vẫn qua `resolve_workspace_access`. Không dùng quy
tắc dữ liệu chung của `backend/` để bỏ kiểm membership/quyền của V1.

## Luồng mặc định

1. Admin/editor tải PDF, DOCX, Markdown, XLSX hoặc PPTX qua API hoặc thêm revision. Backend giữ bytes gốc, SHA256,
   revision và yêu cầu bóc tách trong cùng transaction. Lưu yêu cầu thất bại thì
   không commit nguồn/revision mới. Blob ghi trước transaction có thể còn mồ côi
   khi DB lỗi theo giới hạn lưu trữ hiện có; không tự xóa blob dùng chung.
2. Sau commit, gửi tác vụ vào queue/worker OCR V1 hiện có. Không chờ model trong
   request upload. Queue lỗi giữ run `queued`/`dispatch_pending`; reconcile có
   thể giao lại khi `OWN_RECONCILE` bật, hoặc dùng dispatch API hiện có.
3. Chọn luồng theo định dạng tệp. PDF Inspector đọc PDF theo trang. Các bộ đọc
   trực tiếp xử lý Word, Markdown, Excel và PowerPoint. Có thể rời trình duyệt vì worker giữ trạng thái công việc
   trong PostgreSQL.
4. Tạo canonical JSON, Markdown và manifest có hash. Chỉ `completed` mới có
   `results_ready=true` và tải kết quả được. Lỗi provider/hạ tầng giữ lỗi thật,
   không tạo văn bản giả hay báo thành công toàn tài liệu.
5. Không tự Compiler/review/approve/publish/index. Bóc tách hoàn tất chỉ có nghĩa
   kỹ thuật; chưa khẳng định đúng ngữ nghĩa hoặc đã được duyệt.

## Chọn native hoặc OCR

| Loại nội dung | Hành vi |
|---|---|
| PDF có chữ dùng được, không ảnh | PDF Inspector đọc chữ. PyMuPDF đo tọa độ. Không gọi model/đặt chỗ token |
| DOCX | Docling đọc chữ và bảng trực tiếp từ Word. MinerU xử lý riêng ảnh raster nhúng |
| Markdown / XLSX | Giữ cấp tiêu đề Markdown và phạm vi sheet Excel. Bảng Excel giữ dẫn chứng theo lưới ô |
| PPTX | Đọc chữ, bảng và ghi chú bằng `python-pptx`. Mỗi khối giữ số slide và mã shape. Slide có chữ kèm ảnh hoặc biểu đồ chưa đọc có cảnh báo. Slide chỉ có đồ họa chưa đọc trả `pptx_slide_requires_review` |
| Trang scan/không có chữ dùng được | Gửi các trang cần OCR qua ModelOps. Với MinerU, số trang của tệp gửi được ánh xạ lại về số trang nguồn |
| Chữ và ảnh tách vùng | Giữ chữ native. MinerU OCR riêng ảnh raster nhúng và trả dẫn chứng về vùng ảnh nguồn |
| Chữ nằm chồng ảnh/lớp chữ ẩn của scan | Giữ snapshot native để đối chiếu, dùng một layout OCR trang để tránh nối trùng hai lớp chữ |
| Trang trắng đo được | Giữ trang trắng, không gọi OCR |

Không phân loại logo/biểu đồ bằng từ khóa hoặc tự suy số liệu từ hình. Ảnh có
`requires_review`; diễn giải của model không trở thành dữ kiện đã xác minh.
Kết quả native có `origin=native`, evidence trỏ `native_page`; OCR trỏ raw provider
`raw_response`. Không tạo raw response giả cho trang native, không sửa raw OCR.

Bảng PDF dựa trên đường kẻ/cell rectangle, giữ ô trống, 0, dấu gạch và spans
đo được. Vùng bảng được đọc trước dòng chữ để tránh tranh ký tự ở vùng chồng nhau.
Khi hai bộ đọc khác nhau ngoài khoảng trắng, giữ lớp chữ gốc theo vùng đo được và
ghi cảnh báo `pdf_inspector_native_regions_recovered` kèm số vùng. Markdown của
Inspector lưu riêng trong artifact theo trang để đối chiếu.
Bảng DOCX lấy từ lưới Word, giữ ô gộp, header và giá trị hiển thị đã
lưu của trường công thức. Giữ riêng vị trí ô bị khuyết trong `source_mapping`.
Thứ tự đọc dùng cắt khoảng trắng theo hình học, không từ điển theo tài liệu test.

Các lượt DOCX cũ có thể chứa `docx.table-fragments/v1` gắn các mảnh bảng trên PDF
dàn trang. Dẫn chứng của lượt mới trỏ theo `source_locator` trong tệp Word gốc.

Compiler tra `source_image_asset_no` đúng ảnh, trang và tài liệu. Ảnh gốc không
có text nhưng có text OCR con được ghi “đã có văn bản OCR”, kèm citation của ảnh
và các khối con; chưa khẳng định đầy đủ hay đúng ngữ nghĩa. Ảnh không có text
liên kết vẫn giữ cảnh báo chưa đọc. Không sửa nguồn/canonical của các lượt cũ;
muốn có header/liên kết mới, tạo lượt bóc tách mới rồi biên soạn từ lượt đó.

Từ phiên870, native v2 đọc lại chữ trong từng cell theo vị trí glyph. Chỉ dùng
thứ tự này khi số lượng từng ký tự không trắng khớp hoàn toàn với kết quả bảng;
không tự thêm/bỏ dấu nối, số 0 đầu hay đoán tên trường. Khi gắn được bảng DOCX
nguồn duy nhất, cả cấu trúc bảng và text dẫn xuất dùng chung các cell đó.

### Chữ bên trong ảnh nhúng với MinerU

- Bổ sung cho trang PDF hybrid và ảnh raster nhúng trong Word. PDF scan dùng
  layout OCR toàn trang. Chữ native được giữ từ tệp nguồn.
- Mỗi asset ảnh tạo một PDF riêng: trang đầu giữ toàn ảnh; các trang tiếp là
  phần bên trong khung chứa chữ được phát hiện bằng thành phần liên thông và
  hình học. Giữ độ phân giải nguồn khi cắt ảnh, không dùng từ khóa để đoán nhãn.
- Một tác vụ MinerU `ocr_mode=ocr` cho mỗi PDF ảnh. Checkpoint nằm trong
  `config.mineru_image_tasks[asset_no]`; ZIP gốc lưu `provider_document` tại
  asset_no (0 vẫn dành cho ZIP toàn tài liệu). Không thêm migration hay key mới.
- `raw_response.image_ocr` giữ số vùng, bbox theo trang PDF hoặc ảnh nhúng Word, hash PDF/ZIP
  và nội dung trả về nguyên trạng. Canonical đánh dấu `source_image_asset_no`,
  `requires_review=true`; evidence trỏ raw response. Ảnh gốc và source không đổi.
- Giữ lease, quyền, revision/hash và runtime ModelOps trước các thao tác mạng.
  Tiếp tục bằng task ID/checkpoint; không tự POST/PUT lại khi kết quả chưa rõ.
  Phần chữ trùng khớp và trùng vị trí được gộp, ưu tiên bằng chứng OCR vùng ảnh.
- Đây là trích chữ, chưa xác minh ý nghĩa mũi tên hay chứng minh đọc đủ mọi chữ.
  Vùng không ra chữ giữ cảnh báo; lỗi dấu/chữ tiếp tục qua bước rà soát hiện có.

## Contract cho frontend

Prefix `/platform/v1alpha1`. Hai API upload vẫn giữ source/revision và status
`stored`; thêm trạng thái xử lý riêng trong `source.processing`:

- `POST /workspaces/{ws}/collections/{col}/sources`;
- `POST .../sources/{source}/revisions`.

Form `auto_extract=true` mặc định cho PDF/DOCX. `false` chỉ lưu tệp. Đổi lựa chọn
với cùng Idempotency-Key của một upload mới bị conflict; gửi lại cùng bytes/yêu
cầu trả đúng revision/run cũ. Tệp TXT/MD/XLSX vẫn lưu được nhưng chưa tự bóc tách
trong phạm vi này; `processing=null` khi chưa có run.

GET danh sách nguồn và GET nguồn trả `processing` của đúng revision hiện tại,
query theo batch. Trường gồm `id`, `revision_id`, `status`, `strategy`,
`pages_total/done/failed`, `error_code/detail`, `dispatch_pending`, `results_ready`.
FE phải phân biệt “đã tải lên” với “đã bóc tách”; không suy từ status `stored`.

Gọi prefix `R`:

`/workspaces/{ws}/collections/{col}/sources/{source}/revisions/{revision}/processing-runs`.

| API | Công dụng |
|---|---|
| `POST R` với `{"strategy":"auto"}` | Tạo/tái dùng native-first run; mặc định API thủ công vẫn `strategy=ocr` để giữ tương thích |
| `POST R` thêm `force=true` | Chủ động tạo generation mới; không sửa generation cũ |
| `GET R/{run}` | Trạng thái thật |
| `GET R/{run}/document` | Canonical JSON, ghim revision/run |
| `GET R/{run}/markdown` | Markdown dẫn xuất |
| `GET R/{run}/manifest` | Artifact/checks và hash |
| `GET R/{run}/images/{asset_no}` | Ảnh thuộc đúng kết quả, kiểm hash và quyền |
| `GET R/{run}/bundle` | ZIP gồm `document.md`, `document.json`, `images/*` |

Markdown tham chiếu ảnh bằng đường dẫn tương đối tới thư mục `images`; dùng ZIP
để mang ảnh theo tệp. FE xem trước riêng phải ánh xạ ảnh trong JSON tới API ảnh
có xác thực; không đưa token vào URL. Gói ZIP giới hạn 64 MB và tạo ngoài event
loop. Hash ảnh được kiểm trước khi xuất; ZIP không nhận đường dẫn từ client.

## Quyền, model và phục hồi

- Worker kiểm lại quyền và nguồn trước/sau đọc native, giữ lease/fencing cũ.
  Nguồn xóa/lưu trữ hoặc membership thu hồi chặn xử lý/đọc theo resolver V1.
- Native thuần không cần model/quota. Trang cần OCR vẫn dùng model được phép,
  policy fallback, quota và usage của ModelOps; không thêm key vào env hoặc tự
  cấp model. Chưa cấu hình OCR thì run báo lỗi, tệp gốc vẫn giữ.
- Raw, ảnh, native snapshot và kết quả là bất biến theo run/hash. Tác vụ đã
  hoàn tất không thực thi lại; kết quả native tương thích tái dùng không gọi model.
- HTTP chưa rõ kết quả vẫn `uncertain`, không tự gọi model lại để tránh tính phí
  hai lần. Muốn chạy mới phải là yêu cầu chủ động, có generation mới.
- Fingerprint auto ghim version bộ bóc tách, PyMuPDF và PDF Inspector; version đổi thì không
  tiếp tục diễn giải cùng run bằng parser mới. Không tự backfill nguồn cũ.

## Schema và kích hoạt

Migration `0007_native_extraction` chỉ mở rộng constraint artifact thêm
`native_page`/`embedded_image`, không sửa bytes/schema canonical cũ. Downgrade
từ chối để bảo toàn bằng chứng. Baseline0001 và các migration0002–0006 giữ nguyên.

Cần áp migration này vào DB đích trước khi chạy API/worker bản mới. Phiên710 chỉ
migrate DB thử cô lập; không tự migrate/restart dịch vụ đang phục vụ hoặc đổi
model/default/grants/quota. Cách vận hành theo [hướng dẫn38](38_huong_dan_chay_qnu_v1.md).

## Giới hạn

- DOCX dùng `pagination=document` và một đơn vị nội dung logic trong contract
  hiện có. Giao diện mở Word gốc, đối chiếu theo đoạn/bảng. Hình vẽ Word chưa
  đọc được được đánh dấu `docx_drawing_requires_review` để đối chiếu.
- Bảng không đường kẻ, bố cục nhiều cột phức tạp và chất lượng lớp chữ PDF cần
  đối chiếu thực tế; kiểm ký tự hỏng không chứng minh chữ đã đúng ngữ nghĩa.
- Ảnh nhúng raster được tách thành asset; đồ họa vector PDF chưa được phân vùng
  thành asset riêng. Bản gốc và ảnh trang vẫn giữ để đối chiếu; có thể yêu cầu OCR
  toàn trang thủ công khi cần xử lý các vùng đồ họa phức tạp.
- OCR vùng ảnh bổ sung chỉ áp dụng MinerU; đồ thị không có khung rõ vẫn giữ OCR
  toàn ảnh. Phát hiện vùng giới hạn 64 khung/ảnh và 200.000 đoạn nét để giữ bộ
  nhớ; trường hợp vượt giữ toàn ảnh, không coi đây là chứng minh độ bao quát.
- Regression dùng tài liệu tổng hợp/provider giả lập. Phiên870 có đối chiếu thêm
  DOCX thật 18 trang và một sơ đồ qua MinerU thật, không chứng minh mọi corpus
  hoặc mọi sơ đồ đều được OCR chính xác.
