# Context581 — Nạp lại PDF; benchmark64 đang bị chặn bởi Quality Gate

Đã thực hiện lại intake/import PDF qua API thật và kiểm tra kết quả. **Chưa chạy benchmark64** vì revision PDF mới còn `NEEDS_ATTENTION`, chưa nạp vector hoặc xuất bản. Không có điểm benchmark mới và không dùng điểm DOCX cũ làm kết quả PDF.

## Dữ liệu DOCX và phạm vi

DOCX kiểm thử trong Knowledge đã được purge ở Context578. Preflight hiện tại xác minh binding `bnd_fa71a57c9cf1` là tombstone `detached`, không có revision/chunk/fact còn lại hoặc chỉ mục hoạt động; các index cũ `pruned`, 0 point. Do đó không xóa lại audit/tombstone và không xóa file DOCX local hay Repository.

Kho `col_admissions` trước lượt này có 0 chunk, 0 fact, 0 vector đang giữ dữ liệu; còn PDF revision cũ chờ đối soát. Chỉ nạp lại đúng PDF được giao, tạo revision mới trên binding PDF hiện có; các bản nguồn cũ giữ lịch sử. Không dọn toàn kho hoặc các collection khác thêm lần nữa.

## Runtime và nạp thật

Preflight xác minh development, PostgreSQL/MinIO/Qdrant/Redis loopback, quyền actor hiện có và source SHA256. DB chỉ đọc trong các bước kiểm tra; không gọi migration/seed hoặc đổi config/model.

Worker ARQ local đang chạy từ trước bản sửa parser. Đã xác minh toàn hệ thống không có JobRecord queued/running và queue Redis rỗng. Các khóa cron còn TTL được kiểm là khóa giữ sau khi hoàn tất theo cơ chế `keep_cronjob_progress`, không phải job người dùng đang chạy. Sau kiểm identity process theo helper repo, chỉ reload worker checkout này bằng `scripts/start-worker.ps1` ở chế độ ẩn. Không chạy lệnh restart BE/FE/DB/MinIO/Qdrant. Worker startup hiện có không chạy migration/seed. Không sửa cấu hình đang chạy.

| Bước | Kết quả thật |
| --- | --- |
| `POST /documents/intake` | HTTP202; dedup đúng tài liệu PDF hiện có |
| Repository document | `rep_doc_acef7b5efd8b` |
| `POST /knowledge/collections/col_admissions/imports` | HTTP201; batch `imp_batch_928bb61f08d3` |
| Worker | Job `job_60f38f075fae` completed; batch review_required |
| Binding | `bnd_12190866d5ec` |
| Revision PDF mới | `ks_rev_d495e1fe0477`, revision2 |
| Normalizer | `pdf-b62c983b8905d420caeed4c3be96`, bản sửa PDF mới |
| PDF | 18 trang, 648851 bytes; hash nguồn giữ nguyên |

SHA256 PDF: `082c412e145a9ef39ae50110ae16cc80c17d612e2f0e00f9d16ee78c7c1c3b02`.

## Kiểm chứng artifact đã nạp

Không dùng kết quả offline580 thay cho revision này. Đã tải lại chính artifact mới qua StorageDriver/API và kiểm:

- Bytes snapshot/source hash, cặp Markdown/JSON hash, cú pháp QNU RAG Markdown v1.0 và projection binding: PASS.
- Endpoint tải MD, JSON và reader: HTTP200, khớp artifact đã lưu.
- Bảng1 thực tế trong revision mới: 16×12, 3 tầng header, 192/192 vị trí ô khớp DOCX nguồn sau bỏ khác biệt khoảng trắng.
- Bảng3 trang12 thực tế: một cột.
- 12 phần bảng vật lý, 104 table_row; 632 trường literal: 622 present, 7 blank, 3 ambiguous. Bản chiếu có 415 facts ứng viên, **chưa phải dữ liệu đã index hoặc được phục vụ**.
- Hash row Repository đã có, ModelOps/assistant và dữ liệu ngoài phạm vi được đối chiếu trước/sau: không thay đổi.

Artifact và receipts riêng ở `backend/storage/context581/`. Không đưa corpus/raw OCR vào Git. [Bản đọc mới](../../../backend/storage/context581/reader.md), [Markdown chuẩn](../../../backend/storage/context581/standard.md), [JSON](../../../backend/storage/context581/structured.json).

## Vì sao chưa chạy được64 câu?

Quality Gate hiện ghi **70 mục chặn**, giảm từ1541 mục của revision PDF cũ. Đây là các mục sinh theo block/cột, không phải70 lỗi mất dữ liệu độc lập.

| Nhóm mục chặn | Số lượng |
| --- | ---: |
| Heading được suy luận kiểu chữ, chưa có proof bỏ chặn | 35 |
| Vùng hình chưa chép nội dung | 14 |
| Native/OCR chưa khớp | 8 |
| Dòng gộp chưa xác minh vai trò | 4 |
| Bảng nối trang cần đối soát | 2 |
| Native header cần review | 2 |
| Header chưa rõ | 2 |
| MISSING_COLUMN_HEADER | 2 |
| Footnote cần đối soát | 1 |

Ngoài ra có10 source limitations (7 ô trống, 3 ambiguous) được giữ riêng, không tự đổi thành0.

Đã thử yêu cầu nạp vector đúng revision bằng API chính thức, generation `vg_a6e3190d11af`. API trả **HTTP404 / SOURCE_NOT_FOUND**, thông báo “Nguồn không thuộc kho hoặc không hoạt động.” Trong trường hợp này binding có tồn tại nhưng đang `pending`: Quality Gate chưa cho nó hoạt động. Không phải mất file hoặc sai collection. Handler kiểm trạng thái binding trước khi đến bước dựng index, không tạo job index nào. Không sửa status DB hoặc ép source active để vượt guard.

Kết quả cuối: **0 index mới, 0 vector mới, chưa xuất bản**, không có nguồn PDF hợp lệ để chatbot dùng. Publication không được gọi khi nguồn chưa đủ điều kiện.

## Bộ benchmark và model

Giữ nguyên bản câu hỏi64 đã chốt, kiểm đủ64 ID duy nhất: 60 câu tri thức +4 social. SHA/IDs được ghi ở `benchmark-blocked.json`; bản gold DOCX chỉ là reference, chưa nhận làm nhãn fact ID cho PDF. Khi có index PDF hợp lệ cần map gold source/fact IDs sang PDF bằng nội dung/role/provenance, giữ nguyên câu hỏi, giá trị kỳ vọng và rubric, không chấm bằng ID nguồn cũ.

Model hiện tại đọc từ cấu hình thật: primary `cx/gpt-6-luna`, fallback `qwen3.5-9b`; temperature0.2, max_tokens5000, thinking_budget0. Không đổi cấu hình model hoặc provider.

**64/64 NOT RUN; 0 lượt gọi model cho benchmark.** Không ghi0% vì chưa đo, không dùng benchmark nguồn rỗng hoặc DOCX đã gỡ để báo kết quả PDF. Đây là blocker nguồn/index, không phải timeout/context của Luna hoặc Qwen.

Muốn tiếp tục đến benchmark cần kiểm chứng các mục còn lại bằng bằng chứng source-bound hoặc sửa nguyên nhân nếu là lỗi bóc tách, sau đó nạp vector/xuất bản qua cơ chế hiện có. Không bỏ cờ, tự duyệt semantic proposal hoặc hạ Quality Gate để đạt trạng thái sẵn sàng.

## Kiểm tra và giới hạn

- Preflight/đối soát source và API tải artifact: exit0/PASS.
- Live cell verification: exit0/PASS.
- Yêu cầu nạp vector: HTTP404/BLOCKED, không phải PASS.
- Benchmark64: NOT RUN.
- Không sửa app nên không chạy lại Ruff/full pytest. Kết quả Context580 gồm124 parser tests+23subtests PASS và full18FAIL nền vẫn là lịch sử, không phải test mới của lượt này.
- Không tạo conversation/KnowledgeGap test vì chưa chạy chat; không có dữ liệu benchmark cần xóa. Job import và revision PDF là dữ liệu người dùng yêu cầu giữ lại.
- Không commit/push, không áp proposal, không chỉnh model/config/schema hoặc tự publish. Giữ thay đổi578–580 và file nguồn local.

[Mở revision PDF mới](http://localhost:3000/knowledge/col_admissions/sources/bnd_12190866d5ec?revision=ks_rev_d495e1fe0477&tab=content).
