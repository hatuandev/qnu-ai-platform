# Phiên682 — Frontend hỏi đáp thử, review gốc và dashboard QNU

## Yêu cầu và cách làm

Người dùng yêu cầu tiếp tục mục4–6 sau phiên681. Phạm vi theo kiểm kê680:
collection answers playground, tải raw review Compiler và dashboard QNU.
Đọc PROJECT_CONTEXT, AGENTS root/FE, Git, inventory680, quy tắc verification/
workflow/security và mã API thật trước sửa. Dùng các skill clean code, frontend
architect và admin frontend design, đã thông báo trong commentary.

Không tạo subagent. Chỉ triển khai FE bằng primitives, TanStack và API client
hiện có, không thêm package. Giữ dashboard KTX làm mẫu; `/dashboard` chuyển
sang QNU V1SessionGate, mẫu cũ ở `/reference-dashboard`. Không sửa auth bypass
hoặc coi quyền demo là quyền QNU. Workspace vẫn do server kiểm tra.

## Kết quả

- Kho có lối vào trang hỏi đáp thử riêng. Chọn model/policy RAG/tài liệu/năm
  và hiệu lực; mặc định giữ dense/context0/judge off. POST answers đúng contract
  phẳng; không tạo hội thoại hay retry giả. Kết quả có từng ý, nguồn kiểm lại
  publication/version, trace và usage sinh riêng với kiểm chứng.
- Khối tải review hiện cho raw ở completed/failed/uncertain nếu server có tệp.
  Markdown chỉ completed. Tải nguyên bytes qua client/helper chuẩn; lỗi không
  thành tệp tải về, scope/session đổi bỏ phản hồi muộn. Giữ accessible label
  Markdown cũ; không sửa test cũ cho vừa implementation.
- Dashboard QNU có chọn workspace theo URL/phân trang, totals server, preview
  kho và đường dẫn sâu. Summary/usage chỉ cho admin/editor/reviewer, readiness
  chỉ admin. Không bịa trend24 giờ, unknown giữ unknown và lỗi hiển thị thật.

Baseline917tệp source/test →928tệp,8cũ đổi (gồm1generated do Vite),11mới gồm
9source/2test,0xóa. Không sửa backendV1 hay test cũ; auth/SSO/devbridge, ModelOps,
style, serving config/migrations và feature KTX cũ giữ hash. Reference dashboard
route giữ nguyên nội dung cũ ngoài route factory. Diff và hash ghi ở artifact.

## Kiểm chứng thực chạy

Cwd `frontendV1/`, runtime/dependency đã cài:

- Boundary trước sửa1FAIL/4PASS chứng minh dashboard ngoài gatev1; sau5PASS.
- Trọng tâm37PASS; nhóm cũ679/68154PASS.
- Full cuối `npm test -- --maxWorkers=2 --reporter=json ...`:348PASS/0FAIL/
  0SKIP, giữ311ID cũ+37mới, mất0; không đổi test timeout.
- Biome cuối557tệp0error/0warning/0info; `npm run build` gồm TS đạt exit0.
  Cảnh báo bundle lớn cũ giữ nguyên.
- Probe67411PASS, probe6768PASS, bundle/template sau build11PASS.
- Browser11ảnh component thật với API/auth tổng hợp: desktop/390px sáng/tối,
  answer→nguồn, raw download, member, lỗi summary và empty. Body375/375 không
  tràn ngang; tệp raw155byte tải thật qua browser khớp fixture. Tab/helper3021
  đã dọn. Console helper có warning createRoot khi HMR sau sửa fixture.

Lượt lỗi được giữ trong log: fixture escape/number/Blob jsdom; missing search
defaults trong link TS; ARIA/key và orphan mới; full đầu346PASS/2FAIL do nhãn
Markdown cũ chưa giữ và caps20questions timeout khi chạy cạnh build. Giữ nhãn
truy cập cũ, dùng2worker cho test để giảm cạnh tranh tài nguyên, không sửa
assertion/timeout cũ. Full cuối chạy lại toàn348 đạt. Không gọi các lượt FAIL
là PASS hay bỏ qua test.

BE suite NOT RUN vì không đổi server;655ca phiên681 là lịch sử, không phải
đã chạy lại ở682. Không gọi model/SSO/corpus thật, không benchmark chất lượng.

## Bàn giao và giới hạn

Hỏi thử độc lập, biểu mẫu/kết quả không bền vững quaF5; rời trang không hủy
xử lý server, mất kết nối có thể còn xử lý. Raw có thể chưa tồn tại/chưa hợp
lệ. Dashboard chỉ dùng số liệu API có sẵn theo workspace, không phải global
analytics. Chưa thêm evaluation history/streaming/feedback/share/full restore
web khi BE chưa có contract tương ứng.

Không đổi credential/provider, raw/canonical phục vụ, migration/index/runtime;
không reindex, restart dịch vụ, deploy, commit hoặc push. Kiểm UI là fixture,
không dùng để kết luận model thật hoặc chất lượng RAG đã được nghiệm thu.

[Báo cáo682](../bao_cao/context682/REPORT.md),
[kiểm chứng](../bao_cao/context682/verification.json),
[quy trình37](../quy_trinh/37_frontend_hoi_dap_thu_review_goc_va_dashboard_qnu.md).
