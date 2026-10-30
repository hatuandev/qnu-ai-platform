# Phiên733 — Lấy capacity model từ server

Người dùng đã bổ sung metadata vào `/v1/models` và yêu cầu nối QNU. Áp dụng
ModelOps/backend/frontend/clean-code, đọc source/diff/AGENTS scoped. Không sửa
server AI, restart phiên phục vụ, đổi key/default/quota hoặc biên soạn/OCR lại.

## Thay đổi

- Adapter discovery giữ danh sách tên cũ, thêm model_metadata allowlist:
  max_model_len → context_window_tokens, max_output_tokens, embedding_dimension.
  Strict positive integer, dimension≤65536; metadata mâu thuẫn/trùng ID bị từ chối,
  không log/ghi raw response. Thiếu giữ unknown. Discovery và connection test đều
  trả/lưu metadata, không biến thành inference verified.
- Import model mới nhận discovery_check_id, đọc snapshot current trong DB;
  client không tự gắn server_reported bằng capacity trong request. Capacity lưu
  nguồn server_reported và check/time/metadata; manual path tương thích như cũ.
- POST connections/{id}/sync-capacity chỉ admin, chọn model hiện có cùng parent/
  endpoint và latest successful/current discovery. Một transaction cho selection,
  audit theo model/check, cùng snapshot/giá trị idempotent. Snapshot cũ/khóa đổi/
  endpoint đổi/provider tắt bị chặn. Không nhận model_id từ provider khác.
- Giữ input override/OCR accounting khi merge. Conflict trả409 và rollback.
  Dimension mới khác dimension embedding hiện hành bị chặn; không repoint index.
  Không đoán input/output hoặc OCR budget theo model name.
- Dialog Nhập từ /models → Lấy lại → chọn model/capability → Áp dụng; preview
  context/output/dimension, một nút áp dụng chung. Model đã có được sync; model mới
  được tạo kèm thông số server. Nguồn capacity được ghi nhãn đúng ở detail/form.
  Các trường nhập tay vẫn còn cho thông tin server không công bố.

## Kiểm chứng thực chạy

- Adapter và API regression trên PostgreSQL tạo mới qnu_v1_test_capacity_733_*:
  focused72PASS/49,29s/exit0, gồm adapter metadata và connection/capacity/diagnostics
  cũ. Sau bổ sung regression clear-dimension/reapply và audit, API10PASS/15,08s/exit0.
  Hai nhóm có9API case chung; tổng73test ID khác nhau đạt (10API,63regression khác).
  Lần focused đầu có1FAIL do fixture đổi endpoint khi còn model, đúng guard sẵn có;
  đã sửa fixture xóa model trước khi kiểm snapshot stale. Không nới guard.
- Full Pytest đã thử:889collected nhưng tiến trình host Windows access violation
  khi chạy test_answers_api_648::test_invalid_answer_is_an_error_not_no_data
  [truncated-chat_output_truncated], traceback AnyIO/Starlette. Không có kết quả
  full đạt và chưa xác định baseline/root cause. Một lượt q trước đó dừng sau chờ
  không báo tiến độ; dừng đúng pytest sở hữu rồi dọn DB. Lượt verbose cũng kết thúc
  lỗi. Full gate FAIL/chưa hoàn tất; không bỏ test hoặc sửa nhóm hỏi đáp cho task này.
- Frontend Vitest22PASS/3tệp/exit0:4ca sync/preview/import/stale/unknown và18regression
  capacityform+v1contract. Lần đầu1FAIL phát hiện effect đè kết quả mới bằng cache cũ;
  đã sửa dùng state kết quả mới ưu tiên cached check và chạy lại đạt.
- Production build gồm TypeScript exit0. Biome check6tệp và lint API hook exit0;
  Ruff các tệp phạm vi check exit0, format file mới exit0. Giữ format cũ ở các đoạn
  không liên quan trong service/API hook, không refactor chúng.
- Playwright fixture browser trên FE thật: desktop1280×900/mobile390×844, số liệu
  đọc được, footer nằm trong viewport; đã xem ảnh. Chỉ GET fixture, không save runtime.
- Live chỉ GET `/v1/models` từ endpoint QNU với khóa ModelOps đã bảo vệ trong bộ nhớ:
  HTTP200, adapter nhận bge-m3(context8192,dim1024), reranker(context8192),
  qwen(context131072,output16384), nemotron(context16384,output8192). Không inference,
  không lưu capacity lên DB đang phục vụ. Mẫu JSON người dùng khớp response quan sát.
- Các DB test tạo trong task đã DROP sau subprocess, không xóa DB/volume phiên E2E.
  Không migrate DB phục vụ; chỉ migrate schema sẵn có trên DB test mới.

UTF-8 không BOM/LF32tệp và diff-check đạt; liên kết local mới được kiểm riêng.
Các index có liên kết cũ thiếu đích từ trước; không sửa ngoài phạm vi.

## Dùng sau khi nạp mã mới

Khởi động lại API V1 theo runner đang dùng; nếu E2E thì Ctrl+C đúng cửa sổ serve,
chạy serve lại, giữ session (không cleanup/init). Vào Nhà cung cấp → server →
Nhập từ /models → Lấy lại → chọn model → Áp dụng. Sau cập nhật giới hạn chạy probe
lại. Bổ sung OCR accounting/input override khi cần; metadata hiện tại không có hai
phần này. Không đồng bộ ngầm chỉ bởi lấy danh sách, không cấp quyền/default tự động.

[Hợp đồng capacity](../../backendV1/docs/model-capacity.md).
[Hướng dẫn nhà cung cấp](../quy_trinh/42_modelops_nha_cung_cap_va_model.md).
[Snapshot733](../memory/snapshots/2026-10-30_session_733.md).
