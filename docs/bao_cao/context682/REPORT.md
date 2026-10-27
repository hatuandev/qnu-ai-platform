# Context682 — FE mục4–6: hỏi đáp thử, review gốc và dashboard QNU

## Phạm vi và kết quả

Người dùng yêu cầu tiếp tục F4–F6 sau phiên681. Chỉ thay frontendV1, tái dùng
API backendV1; không bổ sung framework, package, endpoint hoặc sửa server.

F4: trang hỏi đáp riêng theo collection, có lối vào từ kho. Biểu mẫu dùng
TanStack Form, cấu hình model từ catalog workspace, policy RAG phẳng, document
picker và metadata filter. Mặc định dense/context0/judge off được giữ. Kết quả
hiện câu hỏi/phạm vi đã gửi, từng statement với nút nguồn, trace và kiểm chứng.
Nguồn dùng inspector hiện có để kiểm lại version/publication. Không tạo hội
thoại giả, tự retry hoặc suy trạng thái thiếu dữ liệu từ lỗi provider/hạ tầng.

F5: khối tải tệp nằm ngoài điều kiện phải có report completed, nên failed/
uncertain vẫn tải được raw nếu BE đã lưu. RequestBlob và downloadBlob giữ
nguyên bytes, xử lý lỗi trước lưu và làm sạch filename; đổi scope/session bỏ
kết quả muộn. Markdown giữ tên truy cập cũ “Tải Markdown báo cáo”, chỉ bật khi
completed. Không sửa test cũ để khớp việc đổi vị trí nút.

F6: `/dashboard` dùng QNU V1SessionGate qua bộ phân loại route hiện có, chuyển
vào nhóm QNU AI. Mẫu KTX được giữ ở `/reference-dashboard`, cùng toàn bộ source
dashboard/student cũ. Dashboard chọn workspace có phân trang20 và URL state,
đọc totals thật của collections/members, sáu kho đầu, tác vụ/usage theo quyền,
readiness chỉ cho admin. Tổng hợp không bịa timeline24 giờ, chi phí/token
unknown không đổi thành0, lỗi không bị che bằng dữ liệu mẫu.

## Bằng chứng mã

Baseline917 tệp source/test được hash và sao lưu trước sửa. Sau batch928 tệp:
8tệp cũ đổi (gồm routeTree do Vite sinh),11tệp mới (9source và2test),0xóa.
Không tệp BE nào đổi, không sửa test cũ, auth/session/SSO/bypass/ModelOps/style/
proxy/config/migration hoặc các feature KTX cũ. Việc đổi endpoint classifier
chỉ thêm dashboard vào v1; các route mẫu vẫn ngoài v1 và API mẫu vẫn bị chặn.

Danh sách đầy đủ/hash và kết quả ở [verification.json](verification.json).
Artifact local: `storage/artifacts/context682-fe-final-functions/`, gồm before
bytes, source diff, logs, test ID comparison và ảnh browser. Không dùng Gitdiff
trống làm bằng chứng vì phần lớn v1 còn untracked.

## Kiểm tra đã chạy

Ở `frontendV1/`, runtime/gói có sẵn, không cài thêm:

- Regression phân loại route trước sửa:1FAIL/4PASS đúng yêu cầu dashboard phải
  qua V1SessionGate; sau sửa5PASS, giữ bốn negative route mẫu.
- Trọng tâm mới37PASS:32UI/contract và5boundary. Luồng cũ679/681:54PASS.
- Full cuối `npm test -- --maxWorkers=2 --reporter=json ...`:348PASS,
  0FAIL/0SKIP; giữ311ID cũ, thêm37ID, mất0. Không tăng test timeout.
- Biome cuối557tệp không lỗi/cảnh báo/info. Build cuối gồm TypeScript PASS,
  exit0; cảnh báo bundle lớn được giữ nguyên.
- Probe674 độc lập11PASS, probe6768PASS; bundle/template sau build11PASS.

Các ca mới kiểm request đúng endpoint/policy/provider/document/year, năm sai
không mở rộng scope, duplicate submit, lỗi403/409/503 không retry, đổi session/
collection, nguồn thu hồi, statement thiếu nguồn, đọc raw failed, raw403/404,
bytes nguyên trạng, queued/running, đổi review khi tải; dashboard totals thật,
member/editor/admin, outage, pagination, URL selection, inaccessible/suspended/
empty workspace và phản hồi muộn.

Các lượt lỗi được giữ: test fixture đầu sai escape khiến transform lỗi; hai
fixture sau dùng ký tự không thể nhập vào input number và Blob.text không có
trong jsdom, đã sửa fixture để kiểm đúng dữ liệu nhập và đọc bằng FileReader.
Build đầu thiếu search defaults ở link, Biome có orphan/ARIA/key và test mới
có lint cảnh báo, đã sửa đúng vùng mới. Full đầu346PASS/2FAIL: nhãn Markdown
cũ chưa giữ, một ca caps20 questions timeout5 giây khi chạy đồng thời build;
giữ nhãn truy cập cũ và chạy toàn suite với2worker, không thay assertion cũ,
timeout hay cấu hình ứng dụng. Chỉ lượt cuối chạy đạt được báo PASS.

BE suite NOT RUN vì không thay contract/hành vi server; hash toàn bộ BE giữ
baseline. Kết quả655ca phiên681 chỉ là lịch sử, không tính thành đã chạy lại.

## Giao diện và giới hạn

Browser kiểm component thật, API/auth tổng hợp ở helper loopback3021. Có11ảnh
desktop/390px sáng/tối, câu hỏi→answer→citation, raw failed, member, summary
error và empty. Body khung hẹp clientWidth/scrollWidth375/375, bảng cuộn nội
bộ. Có một tải tệp raw qua browser,155byte được đối chiếu fixture. Fixture
ban đầu thiếu membership/role, đã bổ sung trong helper; không sửa app để che
lỗi. Console helper có warning createRoot khi HMR sau sửa fixture; không coi
đó là kết quả model hay nghiệm thu console ứng dụng chính. Helper/tab đã dọn.

Chưa live API/model/SSO/corpus, benchmark chất lượng/latency, deploy/reindex/
restart dịch vụ hoặc Git commit/push. Không thêm streaming/evaluation history/
feedback/share/full restore UI. Hỏi thử chưa lưu lịch sử hay hủy xử lý server;
mất kết nối không bảo đảm server đã dừng. Raw có thể chưa hợp lệ hoặc không
tồn tại. Dashboard chỉ có số liệu API hiện cung cấp, không phải global analytics.

[Hướng dẫn37](../../quy_trinh/37_frontend_hoi_dap_thu_review_goc_va_dashboard_qnu.md).
