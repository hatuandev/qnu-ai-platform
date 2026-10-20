# Context569 — Kiểm chứng bước đối soát

Phạm vi: báo cáo 13 câu, không sửa ứng dụng. CWD mọi lệnh bên dưới: root repository. Python dùng `backend/.venv/Scripts/python.exe`.

## Những kiểm tra đã chạy

| Kiểm tra | Kết quả | Exit code | Ý nghĩa/giới hạn |
|---|---|---:|---|
| Đọc Git status/diff và quy tắc/skill | Hoàn tất | 0 ở các lần đọc hợp lệ | Giữ thay đổi Context568 đang có; một số tìm kiếm đường dẫn phỏng đoán không tồn tại được sửa bằng đọc file thực, không coi là test ứng dụng. |
| Collector `backend/storage/context569/collect.py` cuối | PASS | 0 | Cùng query/gold/Facts/canonical, đủ 13 IDs/26 cặp; 33 spans và 30 citations checked. |
| Probe `backend/storage/context569/probes.py` | **13 PASS / 3 FAIL** | **1** | Hai giả thuyết P08 bị bác; một kiểm tra không có ý định I/O thất bại do import client. Không đổi assertion để che kết quả. |
| Follow-up `backend/storage/context569/followup.py` | **4 PASS / 0 FAIL** | 0 | Gap caption M05; cờ bảng P08 không giải quyết candidate; các code hashes pin trong manifest khớp. Thuần stdlib, không thay kết quả probe đầu. |

### Probe đầu: giữ đủ 16 test IDs

| ID | Status |
|---|---|
| D569-M05-IDENTITY-ROWS | PASS |
| D569-X05-REFUSAL-REASON | PASS |
| D569-X08-REFUSAL-REASON | PASS |
| D569-P06-PACK-qwen567 | PASS |
| D569-P06-GOLD-FIRST-qwen567 | PASS |
| D569-P06-PACK-luna568 | PASS |
| D569-P06-GOLD-FIRST-luna568 | PASS |
| D569-P08-TABLE-ADMISSION-qwen567 | **FAIL** |
| D569-P08-TABLE-ADMISSION-luna568 | **FAIL** |
| D569-P10-TABLE-ADMISSION-qwen567 | PASS |
| D569-P10-TABLE-ADMISSION-luna568 | PASS |
| D569-N19-TABLE-ADMISSION-luna568 | PASS |
| D569-P03-ACCEPTED-INCOMPLETE | PASS |
| D569-P07-ACCEPTED-INCOMPLETE | PASS |
| D569-P15-ACCEPTED-INCOMPLETE | PASS |
| D569-OFFLINE-ISOLATION | **FAIL** |

Các PASS là kiểm tra **giả thuyết chẩn đoán**, không phải 13 ca benchmark vừa được sửa. Gold-first là oracle dùng để đo khả năng đóng gói, không được dùng gold khi chạy production.

Hai FAIL P08 cho thấy ngay cả khi cho phép bảng, các hàng quy tắc vẫn không được chọn. Đây là kết quả hữu ích bác bỏ một hướng sửa quá đơn giản; benchmark P08 vẫn FAIL ở cả hai model.

Một FAIL isolation: import package khởi tạo Qdrant client để kiểm compatibility và phát sinh một ý định network. Helper đã đặt guard socket trước import, chặn truy cập; SQLAlchemy Engine/AsyncEngine connect cũng bị chặn. Có warning compatibility, không có kết nối thành công, không inference, không DB read/write. Không mô tả probe là hoàn toàn không có side effect khởi tạo client. Follow-up sử dụng stdlib để tránh lặp import này; không chạy lại model, Qdrant hoặc DB.

### Follow-up: 4 test IDs

- D569-M05-SCHEMA-CAPTION-GAP: PASS.
- D569-P08-FLAG-ONLY-HYPOTHESIS-REJECTED-qwen567: PASS.
- D569-P08-FLAG-ONLY-HYPOTHESIS-REJECTED-luna568: PASS.
- D569-FROZEN-CODE-MATCH: PASS.

### Lỗi helper đã gặp

Lần kiểm tra shape inline đầu đọc một file `handoff-verification.json` không tồn tại trong thư mục con benchmark-3 (file ở thư mục cha); exit 1. Lần collector đầu giả định `source_revision` là object thay vì string; exit 1, chưa ghi kết quả hoàn tất. Sửa đúng helper ignored rồi collector hoàn tất exit 0. Một kiểm tra inline dùng `block_id` cho Citation gặp KeyError; sau đó kiểm citation bằng revision/hash/span/quote và dùng key thực tế, không thay baseline hoặc application schema.

## Bảo toàn và dữ liệu mới

- Bằng chứng đọc: các file frozen của `backend/storage/context567/benchmark-3/` và `backend/storage/context568/`; SHA256 trước/sau được kiểm khi bàn giao.
- Snapshot source/Facts/gold của hai lượt bằng nhau; canonical text và từng block đối chiếu offsets thật, không dùng báo cáo cũ làm proof duy nhất.
- 1.275 file application/tests/scripts/frontend source được hash trước/sau. Chỉ helper/bằng chứng ignored và tài liệu/memory được thêm/sửa trong task.
- Không tạo job, thread, gap record, DB test, runtime Storage phục vụ app hoặc vector point. Không có dữ liệu kiểm thử trong DB cần dọn. Bằng chứng báo cáo được giữ; không xóa thư mục runtime cũ bị policy chặn.
- Không đổi model defaults, assistant policy, source revision, Facts, index hoặc publication. Không stage/commit/push/restart/deploy.
- Xác minh encoding, links, diff và hashes cuối được lưu `backend/storage/context569/handoff-verification.json`.

## NOT RUN và kết luận nghiệm thu

- Benchmark 64 câu mới: NOT RUN. Chỉ phân tích 26 responses cũ; không cộng chúng thành một benchmark mới.
- LLM inference/provider capability/context-window probe: NOT RUN.
- Retrieval mới, Qdrant/API/DB live readback: NOT RUN.
- Full Pytest, focused application tests, Ruff, FE build: NOT RUN vì không sửa mã ứng dụng.
- Full Context567 2785 PASS / 18 FAIL / 17 SKIP là lịch sử, tổng suite vẫn FAIL; không được dùng làm full PASS hiện tại.

**Bước đối soát hoàn tất với các giới hạn trace đã nêu.** Các lỗi sản phẩm vẫn tồn tại; chưa có bản sửa được triển khai hoặc tỷ lệ cải thiện mới.
