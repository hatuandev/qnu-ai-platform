# Phiên 488 — Quản trị quy đổi điểm và hai luồng RAG

Ngày 2026-10-16. User giao đủ 4 phần: xem quy tắc, tính thử, duyệt/kích hoạt/thu hồi,
chatbot chỉ dùng bộ đã kích hoạt; đồng thời sửa follow-up và năm của dữ liệu tổ hợp.
Skills: backend/clean-code, frontend/admin-design, RAG/ingestion/evaluation đã đọc theo phạm vi.
Không tự reset/migrate/reindex/publish/restart/deploy/Git hoặc duyệt/kích hoạt quy tắc thật.
Giữ các thay đổi tài liệu phiên487, corpus và storage chưa commit của user.

## Cách triển khai

- `score_rule_schemas/router/service`: registry/audit trong JSONB collection hiện có;
  khóa hàng/refresh/OCC, idempotency, xác nhận và lý do; quyền ở router lẫn service.
  ID hỗ trợ Unicode nhưng cấm ký tự đường dẫn. Cấm client tự cung cấp reviewer/status.
- Các bản nháp bất biến; approve → approved; activate → active; deactivate → approved;
  revoke giữ lịch sử. Activate đối chiếu lại nguồn và chặn phạm vi đang trùng.
  Ghi audit cùng transaction, import nhiều mục atomic; không migration bảng mới.
- `score_conversion*`: tách definition khỏi dấu duyệt; preview readonly cờ riêng;
  tái dùng kiểm tra cell/quote/hash/revision và Decimal. Runtime chỉ dùng registry active;
  legacy JSON được giữ nhưng không tự active, CLI activate cũ bị chặn.
- Collection CRUD chặn ghi các key quản trị, khóa/refresh khi merge metadata tránh
  ghi đè duyệt đồng thời. Không thay ModelOps/secret hoặc vai trò người dùng.
- Rà thêm mọi writer metadata: generation/selected publish đã khóa và refresh sẵn;
  bổ sung khóa cho canary/backfill/GC thực thi, populate_existing cho scoped collection
  có FOR UPDATE. GC dry-run không bị thêm khóa ghi. Fixture GC bổ sung kết quả SELECT
  đầu để kiểm tra chính lock/refresh, giữ nguyên assertion pruning/rollback.
- FE: tab `scores`, trang chi tiết deep route, bảng mốc/quote/nguồn, tính thử,
  confirmation/lý do và lịch sử. Import file dùng FileUpload sẵn có; strip dấu duyệt
  từ bản export, API vẫn validate. Combobox có tìm kiếm và ID để Field label truy cập được.
  TanStack Query/Form, semantic tokens, trạng thái lỗi/rỗng thật; không demo rules.
- Follow-up: không nới enumeration guard; explain/reformat nội dung thường tái tra
  antecedent, bỏ prose history khỏi bằng chứng và ép kiểu trình bày ngắn/gạch đầu dòng.
- Năm: phân biệt unknown với không có dữ liệu; tái dùng row selector/auditor. Metric
  candidate phải có năm trong context được chọn của chính bảng trước khi chọn ô.
  Chỉ sau đối soát đầy đủ mới trả giá trị; không sửa raw/fact/year/active source.
- Cảnh báo biến thể giá trị theo tuple ngành/metric/năm/method; giữ khác dấu Unicode,
  không sửa OCR. Mã ngành thiếu được coi là bất định, không gộp ngầm. Cột tổ hợp dùng
  bộ phân loại metric/method hiện có và so nhóm có cấu trúc, không từ điển câu test.

## Kiểm chứng đã chạy

- RED trước triển khai: test quản trị mới không import được module chưa tồn tại;
  sau triển khai dùng test lifecycle/permission/preview/OCC/idempotency/HTTP boundary.
- Focus lớn: 162 pass; nhóm cuối sau sửa cảnh báo: 39 pass rồi 26 pass (row/RAG).
  Ruff scoped: PASS. Kết quả gate tổng thể và giới hạn ghi bổ sung bên dưới.
- Full trung gian đầu có 12 fail/1682 pass/17 skip, thêm một test no-context yêu cầu
  contact policy. Đã khôi phục policy khi thực sự trống, không ghép lời từ chối lặp
  cho trường hợp unknown-year. Full kế: 11 fail/1685 pass/17 skip; gate tiếp theo
  11 fail/1687 pass/17 skip. Các lần chạy lại do thay đổi thực sau probe/edge case,
  không bỏ test/đổi assertion nghiệp vụ để che lỗi.
- FE import3test PASS (Node strip-types + loader hiện có); typecheck PASS, Biome10file
  PASS. Build từng lỗi import đuôi `.ts` trong test; đã dùng resolver test hiện có.
  Build release (`fe-build-488-release.log`) exit0, Vite + TypeScript đạt.
  Không thêm dependency/UI framework mới.
- Một nhóm pytest trong sandbox Windows kẹt ở socketpair/event-loop trước test,
  không phải lỗi app. Đã dừng đúng process test đó và chạy ngoài sandbox, không dừng BE/worker.

## Dữ liệu thật và giới hạn

- Service chat thật qua harness hiện có, chỉ qwen3.5-9b nội bộ; chặn adapter/HTTP
  ngoài, không thay fallback production. Artifact `storage/rag_enumeration_488`, không Git.
- Follow-up cuối trả gạch đầu dòng có5citation, không hỏi lại; 14.58s trong lượt ghi log.
  Thời gian câu hỏi đầu dao động và có lượt132.78s; không coi độ trễ này là đạt chuẩn.
- Câu tổ hợp đã chọn được nguồn TB điểm sàn + flyer từ phạm vi thực2026, 4.84s,
  không lấy bảng2025. Sau audit, phát hiện bản ghi “Tin”/“Tín” khác cách ghi; guard
  bổ sung phải hiển thị SOURCE_VALUE_VARIANTS thay vì âm thầm sửa hoặc khẳng định đầy đủ.
  Đã tái dựng tọa độ đã capture trên nguồn hiện tại để kiểm tra guard, không gọi model mới.
- Một lượt trả lời phương thức phát sinh nhầm nhãn điểm sàn thành “chỉ tiêu” dù có
  citations. Đây là lỗi synthesis/đúng loại chỉ số còn mở, không phải chứng cứ rằng
  3câu đều đúng hoặc model tốt hơn. Không mở thêm batch sửa ngoài 2luồng đã giao.
- Fingerprints config/snapshot/target data/collection metadata/inventory trùng trong
  các probe; không phải full DB fingerprint. Chat tạo conversation/usage/gap như bình thường.
- Preview thật chỉ đọc: A01/780→21.21 và777→21.13, mỗi kết quả11citations,
  source `ks_rev_259de8772948`, is_preview=true, 0ghi/0model. Một lần phát hiện
  ID rule tiếng Việt bị regex ASCII chặn; đã cho phép Unicode word và thêm regression.
- Không nhập draft/approve/activate vào DB thay user. UI thật kiểm tra tab rỗng,
  form nhập và bố cục hẹp; chưa thao tác vòng duyệt/kích hoạt thật trên production.
  Các đường ghi được kiểm chứng bằng service + ASGI tests có I/O controlled;
  chưa kiểm chứng lịch khóa PostgreSQL giữa hai transaction thực hoặc browser E2E đầy đủ.
- Chưa chạy82câu/TM-08/benchmark so sánh; không đổi cấu hình đang chạy, không ghi
  năm vào nguồn cũ, không tự chọn “Tin” thay “Tín”. Cần đối chiếu/duyệt bản nguồn
  nếu muốn bỏ cảnh báo đó. Xem [quy trình08](../quy_trinh/08_quan_tri_quy_doi_diem.md).

## Gate bàn giao

- Full (`pytest-488-locked-delivery.xml/.log`): **1687 passed, 11 failed, 17 skipped**,
  exit1, tổng thể **FAIL**. So XML với `pytest-singleapp-485-final.xml`: exact IDs
  trùng, không có failure mới hoặc mất ID lỗi cũ.
- IDs lỗi nền (không sửa trong batch):
  - `test_consulting_dispatcher.py::test_dispatch_admissions_with_export`
  - `test_consulting_dispatcher.py::test_dispatch_regulations_with_export`
  - `test_publishing_v2_cutover_and_gc.py::test_gc_api_endpoint`
  - `test_publishing_v2_cutover_and_gc.py::test_canary_policy_get_and_update_api`
  - `test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_blocked_when_flag_disabled`
  - `test_publishing_v2_decommissioning_and_system_gc.py::test_direct_upload_allowed_when_flag_enabled`
  - `test_publishing_v2_decommissioning_and_system_gc.py::test_rest_api_system_wide_gc_and_decommissioning_audit`
  - `test_publishing_v2_e2e_canary.py::test_api_routes_canary_and_rollback`
  - `test_rag_data_truth_and_lifecycle.py::test_reconciliation_detects_discrepancies`
  - `test_trust_boundary_and_hitl.py::test_auth_session_cookie_actor_claims`
  - `test_universal_tools.py::test_dispatch_admissions_with_dynamic_facts`
- Sau khi full đã bắt đầu collection, chỉnh nhỏ hash request_id của import batch để
  root dài100 ký tự vẫn tạo được child key hợp lệ. Test quản trị13/13 PASS sau chỉnh;
  không coi full trước đó là test riêng cho edge case mới này.
- Nhóm metadata ban đầu55pass/3fail (1fixture GC mới lệch thứ tự SELECT và2baseline);
  sau sửa fixture, GC dry-run/thực thi2/2 PASS và được bao phủ lại trong full.
  Ruff scoped và `git diff --check` đạt.
- Re-render tọa độ đã capture trên nguồn thật sau guard cuối: insufficient_context,
  SOURCE_VALUE_VARIANTS, 7citations, giữ Tin/Tín nguyên văn; 0model/0writes. Đây không
  phải lượt chat model mới hoặc một benchmark độc lập.
- Kiểm lại sau tests: cả5fingerprints kiểm tra vẫn trùng; registry managed_rules=0.
  Không tự bật tính điểm. Cần BE/worker cùng phiên bản trước khi dùng vòng duyệt thật;
  BE đang reload có thể tự nạp code, worker cần nhận bản mới theo quy trình vận hành.
  Không chủ động restart/push/deploy trong phiên này.
