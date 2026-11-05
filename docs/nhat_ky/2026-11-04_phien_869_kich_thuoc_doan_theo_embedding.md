# Phiên 869 — Kích thước đoạn theo model embedding

Người dùng yêu cầu bỏ ngân sách cố định trong vấn đề lập chỉ mục của bản biên
soạn DOCX vừa kiểm tra. Phạm vi thay đổi là chuẩn bị chunk cho generation mới.
Giới hạn đầu vào thực tế của model và cấu hình operator tường minh vẫn được
tôn trọng. Không đổi ngân sách đầu ra Qwen, quyền, quota hay lựa chọn model.

## Nguyên nhân và thay đổi

`INDEX_CHUNK_MAX_BYTES=3000` chặn nhóm hàng dù model embedding đã được cấu hình
đầu vào lớn hơn. Khi bật ngữ cảnh nguồn, code còn trừ cố định tối đa 2.048 byte
hoặc một phần tư ngân sách trước khi chia, làm bảng có thể bị chặn tiếp.

- Settings mặc định `INDEX_CHUNK_MAX_BYTES=None`. Service lấy ngân sách đầu vào
  từ runtime ModelOps được phép dùng, giữ cách ước lượng UTF-8 byte + 32 hiện có.
  Nếu operator khai báo giới hạn riêng, lấy mức nhỏ hơn. Generation lưu mức đã
  tính vào config; idempotency receipt cũ vẫn ghim config cũ.
- Chunker nhận hàm đo kích thước. Khi có ngữ cảnh nguồn, đo chính xác chuỗi sẽ
  gửi đi: nội dung, tiêu đề, metadata theo đúng đơn vị và định nghĩa có căn cứ.
  Chia đoạn và nhóm hàng theo kích thước đó, giữ header/span/footnote/ô/citation.
  Enrichment kiểm tra lại kết quả cuối và lưu riêng nội dung gốc cùng hash.
- Nhóm hàng không thể chia mà vẫn vượt đầu vào model báo lỗi rõ. Không bỏ ô,
  không cắt mất dữ liệu hay tự gửi lại inference. Chưa tích hợp tokenizer đo
  chính xác; byte là ước lượng bảo thủ, không phải usage model đã đo.

Các tệp chính: `qnu/platform/config.py`, `qnu/domains/knowledge/index/service.py`,
`chunking.py`, `contextual.py` trong backendV1. Đã bổ sung regression unit/API và
cập nhật tài liệu chỉ mục backend, quy trình 24.

## Đối chiếu cùng bản biên soạn

Đọc DB/storage có kiểm quyền workspace, transaction chỉ đọc. Bản biên soạn nhanh
DOCX hoàn tất trong khoảng 0,94 giây; 18 trang, 11 bảng chuẩn hóa. Các artifact
đối chiếu nằm trong thư mục tạm được Git bỏ qua. Không chép corpus vào báo cáo.

Thử cùng snapshot đã lưu, không gọi model và không ghi index ứng dụng:

| Chuẩn bị | 3.000 byte cũ | 8.160 byte theo runtime hiện tại |
|---|---|---|
| Thông thường | `index_table_group_too_large` | 460 chunk, 18 fragment bảng |
| Có ngữ cảnh nguồn | `index_table_group_too_large` | 460 chunk, 18 fragment bảng |

Cả hai cấu hình mới giữ đủ 11 bảng/660 ô đúng nguyên văn và mọi citation có
trong bản nháp. Kích thước lớn nhất lần lượt 7.946 và 8.133 byte. Đây là kiểm
chứng chuẩn bị chỉ mục; chưa chứng minh chất lượng truy xuất/câu trả lời thật.

Kiểm tra DOCX còn ghi nhận ký tự gạch dưới tách sai trong một bảng trích xuất
trang 17 và một sơ đồ trang 13 chưa có chữ đầy đủ. Hai vấn đề nguồn này chưa
thuộc thay đổi ngân sách được yêu cầu tại phiên này.

## Kiểm chứng và vận hành

- Regression từ root bằng
  `backendV1/.venv/Scripts/python.exe backendV1/scripts/run_isolated_tests.py tests/unit/test_index_budget_869.py tests/unit/test_index_chunking_647.py tests/unit/test_contextual_scope_790.py tests/integration/test_index_budget_869.py tests/integration/test_index_api_647.py tests/integration/test_rag_scope_context_672.py -q`:
  **58 PASS**, 191,74 giây. Kiểm tra default tự động, override tường minh,
  model nhỏ hơn, ngữ cảnh/định nghĩa/metadata, hàng bảng lớn, hàng không thể tách,
  scope và citation. API/storage/PostgreSQL/Qdrant dùng môi trường thử; inference
  trong regression là giả lập. DB `qnu_v1_test_60ccb1c7954b4958` đã dọn.
- Lượt đầu của regression có một fixture khai báo input lớn hơn context bị API
  từ chối đúng schema. Đã sửa fixture thành input nhỏ hơn context; không nới
  validator để làm xanh kết quả.
- Ruff trên sáu tệp Python sửa/thêm: PASS. `git diff --check`, UTF-8 không BOM,
  LF và các liên kết Markdown thêm/sửa: PASS.
- Full gate từ root `make.ps1 test-be` với `PYTEST_ADDOPTS=-x`: **FAIL**, 39 PASS
  trước lỗi nền đã ghi nhận ở phiên 868:
  `tests/integration/test_auto_extraction_710.py::test_docx_table_has_real_structure_and_original_is_unchanged`.
  Pytest dừng ở lỗi đầu sau 304,54 giây, chưa chạy hết toàn bộ ca. Receipt xác
  nhận DB `qnu_v1_test_84d49f1f92a54f36` đã dọn và sentinel legacy được giữ.
  Không sửa lỗi parser DOCX ngoài phạm vi để làm xanh full suite.

Không restart dịch vụ, sửa dữ liệu ứng dụng, đăng ký/xuất bản hay chuyển chỉ mục
đang hoạt động. Sau khi khởi động lại dịch vụ bằng mã mới, có thể dùng lại bản
biên soạn để đăng ký/phát hành và tạo generation mới; không cần upload hoặc
biên soạn lại chỉ vì thay đổi này.
