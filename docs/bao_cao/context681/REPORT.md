# Context681 — Bổ sung FE theo ưu tiên F1–F3

## Phạm vi và kết quả

Người dùng đồng ý triển khai đề xuất sau kiểm kê680. Phạm vi của phiên này
là ba ưu tiên đầu: phân trang danh sách/lịch sử, chọn tài liệu cho tìm kiếm
và đánh giá, mở lại kết quả kiểm tra chính tả. Không triển khai F4–F6.

F1: dùng phân trang server cho Compiler, tài liệu, phiên bản, lịch sử xuất
bản, review Compiler và index generations. Giữ trang/kích thước trang trên
URL, review được chọn trên URL và đặt lại trang khi đổi tab/kích thước.
API mảng dùng dòng nhìn trước để xác định còn trang; không bịa tổng số.
Kích thước100 gọi100+1 ở hai offset, giữ giới hạn server. List Compiler BE
nhận offset, giữ mặc định, thứ tự ổn định và authorize_collection hiện có.

F2: bộ chọn theo tiêu đề/key có phân trang, tối đa100 tài liệu, chặn trùng
và không xóa lựa chọn khi tải lỗi. Search gửi document_ids tường minh và bỏ
kết quả muộn sau khi đổi lựa chọn. Evaluation chọn phạm vi từng câu trong
manifest; tìm gold và đánh giá cùng phạm vi, từ chối hit ngoài phạm vi,
đổi lựa chọn xóa gold/human ack cũ. CSV bổ sung document_ids, JSON giữ body.

F3: URL ghim revision/run/checkId và tab hậu OCR; mở lại dùng GET biên nhận,
chỉ poll khi running, không tự POST chạy model. Kết quả có đoạn văn, từ gốc,
đề xuất, lý do, trạng thái và version. Khác version/hash hoặc span đã đổi
không được áp dụng; phiên đăng nhập và run được tách state. Áp dụng vào nháp
và lưu qua cơ chế optimistic concurrency cũ, giữ OCR gốc và tạo dẫn xuất.

## Bằng chứng mã và kiểm tra

Artifact local: `storage/artifacts/context681-fe-completion/`. Baseline912
tệp source/test được sao lưu trước sửa; sau batch917 tệp,27 tệp cũ thay đổi,
5 tệp mới,0 bị xóa. Không sửa test cũ. Mã ứng dụng gồm28 source FE và2 source
BE; thêm1 tệp test FE và1 tệp test BE. Chỉ BE list Compiler đổi hành vi server.
Đối chiếu baseline không có thay đổi auth, ModelOps, style hoặc module BE khác.

Các lệnh chạy ở `frontendV1/` bằng runtime/gói đã có:

- `npm test -- --reporter=json --outputFile=.../fe-final-verified.json`:311PASS,
  0FAIL/0SKIP; giữ đủ287ID cũ và thêm24ID. Trọng tâm681:24PASS.
- Biome có phạm vi và `npm run lint`:546tệp, không lỗi/cảnh báo hay fix ngoài
  phạm vi. `npm run build`:PASS, bao gồm TypeScript; còn cảnh báo bundle lớn
  như trước. Không coi build là bằng chứng hình ảnh.
- Probe674 độc lập11PASS, probe676 độc lập8PASS; bundle/template sau build11PASS.

Ở root, dùng `backendV1/.venv/Scripts/python.exe -X utf8
backendV1/scripts/run_isolated_tests.py ...`, không chạy vào DB phục vụ:

- Trọng tâm `tests/integration/test_compiler_pagination_681.py -q`:3PASS.
  Kiểm105 lượt, trang sau100 không trùng, default20, collection scope,
  non-member404 và input âm/vượt limit422.
- Recovery666 riêng trên Windows default loop:4PASS.
- Hai test queue thực Redis644/645:2PASS, queue có tên duy nhất, Redis loopback.
- Ruff check và format-check:3 tệp BE đạt.
- Hồi quy BE tổng hợp đủ655ID đạt:335PASS từ phần log trước khi ngắt,
  314PASS/0FAIL ở lượt chạy tiếp cuối,4recovery và2Redis riêng. Ba ca phân
  trang mới nằm trong335ID đầu. Hai skipRedis ở lượt đầu đã được chạy riêng
  đạt, không còn ca chưa kiểm tra. Không có một exit code full không gián
  đoạn: lượt đầu bị ngắt ở52%; kết quả ở đây là coverage tổng hợp các nhóm.
  Lượt chạy tiếp trước đó313PASS/1FAIL vì TEST_REDIS_URL thiếu; giữ trạng thái
  FAIL của lượt đó, bổ sung cấu hình thử rồi chạy lại toàn314ID đạt, không
  sửa app hoặc nới assertion.

Hệ thống thử tạo DB qnu_v1_test_* riêng, chặn network ngoài loopback, lưu
blob ở thư mục thử và dọn DB sau chạy. DB migration chỉ áp vào DB thử, không
áp vào DB phục vụ. Biên nhận dọn DB/sentinel phải đối chiếu ở verification.json.

Kiểm tra browser trên component thật với API/auth fixture tổng hợp, trang
riêng ở port3020; không gọi backend/model thật.9 ảnh trong artifact: bộ chọn
trang2, chính tả trước/sau áp dụng, mismatch, tên dài, màn hình390px nền tối và bảng
trang cuối desktop/mobile. Màn hẹp có sheet, footer wrap và bảng cuộn ngang
trong khung. Đã đóng tab thử và dừng đúng helper riêng; không restart dịch vụ.

Các lượt FAIL giữ log: BE đầu thiếu credential test do cwd; sau đó assertion
fixture403 được sửa thành404 đúng privacy contract đã đọc, không nới quyền.
FE đầu một test gọi sai signature hook, đã sửa fixture; full kế tiếp vướng
guard cấm tên fetch ngoài client vì callback mang tên fetch, đã đổi tên
callback thành loadRows, giữ nguyên guard và transport. Biome yêu cầu tên
component test viết hoa và Ruff format tệp test mới; đã xử lý đúng phạm vi.
Lượt tiếp bị giới hạn độ dài commandline Windows206 đã được dọn DB và dùng
pytest@argfile. Log lỗi TEST_REDIS_URL có dump môi trường do pytest; đã xóa
giá trị nhạy cảm khỏi artifact sở hữu, giữ testID/cause/status. Không đưa
giá trị bí mật vào báo cáo.

## Giới hạn

Chưa nghiệm thu với model/SSO/corpus thật hoặc đo chất lượng RAG/latency.
Không thay provider/credential, source/canonical/MD/JSON đang phục vụ,
migration phục vụ, index, auth bypass, runtime config; không reindex,
restart, deploy, commit hoặc push.

Phân trang offset có thể dịch hàng khi dữ liệu thay đổi; chưa có total/cursor.
Document selection ở biểu mẫu chưa bền vững qua F5. CheckId chưa có màn danh
sách tất cả check; cần giữ URL của lần kiểm tra. Bỏ qua đề xuất là state cục
bộ, không lưu quyết định. Chính tả chỉ dựa văn bản, chưa đối chiếu ảnh.

Collection answers playground, raw review, dashboard QNU và lịch sử evaluation
bền vững còn theo inventory680. Không coi thiếu API streaming/feedback/share/
full restore web là FE đã quên nối.

[Quy trình36](../../quy_trinh/36_frontend_phan_trang_pham_vi_tai_lieu_va_chinh_ta.md).
[Kiểm kê680](../context680/FE_BE_INVENTORY.md).
