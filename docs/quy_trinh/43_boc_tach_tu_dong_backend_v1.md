# 43 — Bóc tách tự động sau upload trong backendV1

Áp dụng backendV1; frontendV1 chưa thay bố cục trong phiên710. Workspace là biên
quyền của đơn vị, mọi thao tác vẫn qua `resolve_workspace_access`. Không dùng quy
tắc dữ liệu chung của `backend/` để bỏ kiểm membership/quyền của V1.

## Luồng mặc định

1. Admin/editor tải PDF/DOCX hoặc thêm revision. Backend giữ bytes gốc, SHA256,
   revision và yêu cầu bóc tách trong cùng transaction. Lưu yêu cầu thất bại thì
   không commit nguồn/revision mới. Blob ghi trước transaction có thể còn mồ côi
   khi DB lỗi theo giới hạn lưu trữ hiện có; không tự xóa blob dùng chung.
2. Sau commit, gửi tác vụ vào queue/worker OCR V1 hiện có. Không chờ model trong
   request upload. Queue lỗi giữ run `queued`/`dispatch_pending`; reconcile có
   thể giao lại khi `OWN_RECONCILE` bật, hoặc dùng dispatch API hiện có.
3. Render trang và đo hash ảnh, rồi chọn đường bóc tách cho từng trang. Có thể
   rời trình duyệt; công việc được ghi trong PostgreSQL, không do FE điều phối.
4. Tạo canonical JSON, Markdown và manifest có hash. Chỉ `completed` mới có
   `results_ready=true` và tải kết quả được. Lỗi provider/hạ tầng giữ lỗi thật,
   không tạo văn bản giả hay báo thành công toàn tài liệu.
5. Không tự Compiler/review/approve/publish/index. Bóc tách hoàn tất chỉ có nghĩa
   kỹ thuật; chưa khẳng định đúng ngữ nghĩa hoặc đã được duyệt.

## Chọn native hoặc OCR

| Loại nội dung | Hành vi |
|---|---|
| PDF có chữ dùng được, không ảnh | Đọc trực tiếp text và tọa độ, không gọi model/đặt chỗ token |
| DOCX | Dùng XML→HTML→PDF fixed-layout hiện có; đọc text/bảng trực tiếp từ PDF này, không OCR chữ lần nữa |
| Trang scan/không có chữ dùng được | Gọi OCR trang qua ModelOps hiện có |
| Chữ và ảnh tách vùng | Giữ chữ native và ảnh; OCR toàn trang để có ngữ cảnh, chỉ hợp nhất khối OCR nằm chủ yếu trong vùng ảnh |
| Chữ nằm chồng ảnh/lớp chữ ẩn của scan | Giữ snapshot native để đối chiếu, dùng một layout OCR trang để tránh nối trùng hai lớp chữ |
| Trang trắng đo được | Giữ trang trắng, không gọi OCR |

Không phân loại logo/biểu đồ bằng từ khóa hoặc tự suy số liệu từ hình. Ảnh có
`requires_review`; diễn giải của model không trở thành dữ kiện đã xác minh.
Kết quả native có `origin=native`, evidence trỏ `native_page`; OCR trỏ raw provider
`raw_response`. Không tạo raw response giả cho trang native, không sửa raw OCR.

Bảng PDF dựa trên đường kẻ/cell rectangle; giữ ô trống, 0, dấu gạch và spans
đo được. DOCX chỉ gắn header/spans từ cấu trúc nguồn khi nội dung bảng khớp duy
nhất với bảng đo trên PDF render. Bảng cắt trang/mơ hồ giữ cảnh báo cần review.
Thứ tự đọc dùng cắt khoảng trắng theo hình học, không từ điển theo tài liệu test.

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
- Fingerprint auto ghim version bộ bóc tách và PyMuPDF; version đổi thì không
  tiếp tục diễn giải cùng run bằng parser mới. Không tự backfill nguồn cũ.

## Schema và kích hoạt

Migration `0007_native_extraction` chỉ mở rộng constraint artifact thêm
`native_page`/`embedded_image`, không sửa bytes/schema canonical cũ. Downgrade
từ chối để bảo toàn bằng chứng. Baseline0001 và các migration0002–0006 giữ nguyên.

Cần áp migration này vào DB đích trước khi chạy API/worker bản mới. Phiên710 chỉ
migrate DB thử cô lập; không tự migrate/restart dịch vụ đang phục vụ hoặc đổi
model/default/grants/quota. Cách vận hành theo [hướng dẫn38](38_huong_dan_chay_qnu_v1.md).

## Giới hạn

- DOCX tọa độ/số trang là của PDF trung gian, không phải phân trang Word gốc.
  Header/footer theo section chưa được renderer hiện có hỗ trợ: báo lỗi rõ,
  giữ tệp và yêu cầu PDF phù hợp; không bỏ nội dung âm thầm.
  Ảnh DOCX chưa hỗ trợ cũng báo lỗi thay vì xuất bản bóc tách thiếu ảnh.
- Bảng không đường kẻ, bố cục nhiều cột phức tạp và chất lượng lớp chữ PDF cần
  đối chiếu thực tế; kiểm ký tự hỏng không chứng minh chữ đã đúng ngữ nghĩa.
- Ảnh nhúng raster được tách thành asset; đồ họa vector PDF chưa được phân vùng
  thành asset riêng. Bản gốc và ảnh trang vẫn giữ để đối chiếu; có thể yêu cầu OCR
  toàn trang thủ công khi cần xử lý các vùng đồ họa phức tạp.
- OCR cho ảnh dùng cả trang rồi lọc vùng; chưa có cơ chế OCR từng crop hoặc
  trích số liệu biểu đồ chuyên biệt. Không hứa giảm token theo diện tích ảnh.
- Kiểm thử dùng tài liệu tổng hợp và provider loopback. Không phải nghiệm thu
  chất lượng OCR thật hoặc bằng chứng đã chạy trên corpus của phòng ban.
