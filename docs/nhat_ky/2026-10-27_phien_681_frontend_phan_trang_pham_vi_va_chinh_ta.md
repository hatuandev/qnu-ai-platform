# Phiên681 — Phân trang FE, chọn tài liệu và mở lại chính tả

## Yêu cầu và phạm vi

Người dùng đồng ý triển khai đề xuất sau kiểm kê680, sau đó yêu cầu tiếp tục.
Giữ phạm vi F1–F3: phân trang kiến thức/lịch sử, document picker cho search và
evaluation, đọc lại spelling check đã lưu. Không tự mở rộng sang playground
answers, raw review hoặc dashboard. Dùng skill qnu-clean-code-architect,
qnu-frontend-architect và qnu-backend-architect; đã thông báo khi áp dụng.

Đầu phiên đọc PROJECT_CONTEXT, Git, hướng dẫn root/FE, verification/workflow/
security và file thực tế. Phần lớn v1 chưa tracked nên sao lưu/hash912 tệp
source/test trước sửa; không suy trạng thái từ Gitdiff trống.

## Thay đổi

- BE Compiler list thêm offset>=0, order generation/id; giữ quyền, limit và
  response cũ, không cần migration.
- FE dùng phân trang server/lookahead, URL trang/kích thước/tab/reviewID.
  Tài liệu, Compiler, index, phiên bản, lịch sử xuất bản và review không bị
  giới hạn ở trang đầu. Không suy total từ mảng hay dùng filter trang như tìm
  toàn kho. Trang Compiler lỗi vẫn quay lại được.
- Picker tối đa100 tài liệu, chặn trùng, phân trang/lọc tiêu đề trong trang.
  Search bỏ kết quả muộn khi đổi phạm vi. Evaluation dùng cùng document_ids
  trong search gold và POST đánh giá; giới hạn manifest, đổi scope xóa gold
  và human ack. CSV giữ document_ids; JSON giữ request nguyên trạng.
- OCR URL ghim revision/run/checkId, đọc lại GET và poll running, không tự
  chạy model. Kết quả có văn bản, sai→đề xuất, lý do và trạng thái. Version/
  hash/span/role/base khác chặn áp dụng. Nháp giữ scope phiên đăng nhập;
  lưu vẫn dùng kiểm tra concurrency hiện có và không sửa OCR gốc.

Sau sửa917 tệp,27tệp cũ đổi/5tệp mới,0bị xóa:28sourceFE,2sourceBE và2tệp test
mới. Mọi test cũ giữ bytes. Các vùng auth/ModelOps/style và BE khác giữ hash.
Danh sách đầy đủ và hash ở verification.json, local diff và snapshot gốc ở
`storage/artifacts/context681-fe-completion/`.

## Kiểm chứng

FE: full311PASS/0FAIL/0SKIP giữ287ID cũ+24mới; focused cuối24PASS. Biome toàn
546tệp không lỗi/cảnh báo, build gồm TypeScript PASS, còn cảnh báo bundle lớn
cũ. Probe67411PASS/probe6768PASS; bundle/template11PASS sau build.

BE trọng tâm phân trang105lượt3PASS; reader ngoài workspace404 đúng privacy,
inputâm/vượtlimit422. Recovery4PASS;2queue644/645RedisloopbackPASS vớiqueue
tên riêng. Ruff check+format-check3tệp PASS. Đợt hồi quy toàn BE bị ngắt ở52%
khi chuyển lượt; chỉ335PASSED được giữ làm bằng chứng, không coi full run đó
PASS.337ID đã báo gồm2skipRedis được deselect,314ID còn lại chạy trong DB thử
mới. Lượt tiếp đầu313PASS/1FAIL vì thiếu TEST_REDIS_URL, giữ log FAIL; sau khi
nạp Redis loopback hiện có, chạy lại toàn314ID đạt0FAIL. Tổng hợp đủ655ID có
kết quả PASS, không còn skip chưa chạy:335prefix+314tiếp+4recovery+2Redis.
Không gán exit0 cho lượt full bị ngắt; biên nhận cuối ghi rõ coverage tổng
hợp nhiều nhóm. DB các lượt đã dọn, sentinel/version legacy giữ đúng.

Mọi DB thử qnu_v1_test_* có sentinel/version legacy, blob riêng và network
ngoài loopback bị chặn. Lượt bị ngắt không còn index row, không sessionDB,
sentinel đúng trước khi dọn đúng DB sở hữu. Biên nhận dọn tài nguyên lưu riêng.
Không dọn DB/vector ứng dụng phục vụ.

Browser: component thật, fixture tổng hợp, desktop/390px sáng/tối,9ảnh, chọn
tài liệu sang trang2, lastpage, spellingapply và mismatch. Helper3020 vàtab
thử chính đã đóng; không thay cấu hình dịch vụ. Nguồn và giới hạn ảnh ghi ở
báo cáo. Một tab lỗi kết nối do helper bị ngắt tự đóng theo cơ chế tab tạm;
không điều hướng vượt chặn URLdata của công cụ.

Các lượt FAIL/log được giữ: cwd không nạp credential DB thử; fixture403→404
theo contract đã đọc; gọi sai signature reviewhook trong test mới; guard cấm
callback tênfetch ngoài client (đổi callbackloadRows, không nới guard); format
test mới; Windows206 khi truyền nhiều deselect (dùngpytest@argfile), thiếu
TEST_REDIS_URL ở test heartbeat. Artifact lỗi có dump môi trường do pytest
đã được làm sạch giá trị nhạy cảm, giữ cause và testID. Chỉ kết
quả chạy đạt cuối mới đánh dấu PASS, không ẩn các lượt lỗi.

## Giới hạn và bàn giao

Chưa chạy liveSSO/model/corpusE2E hoặc benchmarkchấtlượng/latency. Không đổi
authbypass/provider/credential, canonical/raw đang phục vụ, migration/config
phục vụ; không reindex/restart/deploy/Gitcommit/push. Offsetcóthểdịchhàng khi
dữ liệu đổi; scope biểu mẫu và bỏ qua gợi ý chưa lưu quaF5. CheckId cần giữURL,
chưa có lịch sử tất cả check. Chính tả chỉ văn bản, chưa đối chiếu ảnh gốc.

[Báo cáo681](../bao_cao/context681/REPORT.md),
[kết quả máy đọc](../bao_cao/context681/verification.json),
[quy trình36](../quy_trinh/36_frontend_phan_trang_pham_vi_tai_lieu_va_chinh_ta.md).
