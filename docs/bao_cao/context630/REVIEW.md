# Context630 — Sửa PDF có lớp văn bản

Ngày 2026-10-25. Người dùng yêu cầu ưu tiên PDF text và hỏi so sánh Qwen3.8-27B với GPT-OSS 120B trong khi tự cài Nemotron-3.5-Parse.

**Đã sửa và kiểm chứng các khoảng hở về header, nối bảng, bản chiếu native trùng và metadata OCR.** Giữ QNU RAG Markdown/JSON v1.0, nguồn gốc và Quality Gate. Không đánh dấu toàn bộ tài liệu đã đạt hoặc sẵn sàng xuất bản: ảnh/chữ ký, một số vai trò bảng và công thức vẫn cần căn cứ riêng.

## Kết quả trên nguồn thật

Đối soát offline 4 PDF, tổng 33 trang. Mỗi nguồn được lưu qua LocalStorageDriver trước xử lý; hash gốc, raw layout, bảng, ô và cặp MD/JSON được kiểm. Cùng một lưới nguồn được đối chiếu bằng chính sách header v5 và parser v6; không đổi model để so điểm. Bản cuối ở `backend/storage/context630/replay-release`.

| PDF | Trước → sau | Kết quả và giới hạn |
|---|---|---|
| Thông báo quy đổi QNU 2026, 5 trang | 760 → **0** limitations về ô | Header 2 tầng đúng 23 cột; phụ lục 2 nối trang 4–5; 72 dòng dữ liệu/706 fields. Giữ toàn bộ 760 vị trí raw gồm header. Còn 6 vùng hình chưa được duyệt. |
| Thông báo học phí K49, 3 trang | 570 → **0** limitations về ô | Giữ đủ **56 dòng/560 fields**. Hai phần không lặp header kế thừa có nguồn, không bỏ dòng 17 hoặc 43; gỡ hai cảnh báo nối bảng bằng bằng chứng. Còn 3 vùng hình. |
| Báo cáo tư vấn tuyển sinh 2024, 7 trang | 339 → **184** limitations | Nhận thêm header đủ căn cứ; các bảng chưa phân vai chắc chắn, một nối bảng và 8 vùng hình vẫn giữ nguyên chặn/giới hạn. Không coi 184 limitations là mất 184 ô. |
| PDF mô phỏng phức tạp, 18 trang | **51 → 51** limitations | Lưới của cả 12 phần bảng vật lý và dữ liệu được giữ; không hồi quy theo đối soát này. Tái dùng OCR đã lưu, không gọi OCR lại. Còn các trường chưa rõ và một vùng hình. |

Cả 4 cặp MD/JSON hợp lệ, hash/parity/source replay đạt; mọi grid trước/sau giữ nguyên. Đây là kiểm chứng cấu trúc và bảo toàn dữ liệu đã trích, **không phải chứng nhận toàn bộ ngữ nghĩa hoặc OCR chính xác**. Cả 4 trường hợp vẫn `NEEDS_ATTENTION`; chưa có publication hoặc Compiler bundle mới.

Đầu ra để xem:

- PDF quy đổi: [Markdown dễ đọc](../../../backend/storage/context630/replay-release/pdf-1/reader.md), [QNU Markdown](../../../backend/storage/context630/replay-release/pdf-1/standard.md), [JSON companion](../../../backend/storage/context630/replay-release/pdf-1/structured.json).
- PDF học phí: [Markdown dễ đọc](../../../backend/storage/context630/replay-release/pdf-2/reader.md), [QNU Markdown](../../../backend/storage/context630/replay-release/pdf-2/standard.md), [JSON companion](../../../backend/storage/context630/replay-release/pdf-2/structured.json).
- [Kết quả đủ 4 PDF](../../../backend/storage/context630/replay-release/result.json), [đối soát cặp artifact và v5 thật](../../../backend/storage/context630/artifact-audit.json).

## Nguyên nhân và thay đổi

1. **Header nền trắng.** Trước đây đòi cả chữ đậm lẫn nền màu. Nay dùng dải typography có ranh giới cùng ô cha/con hoặc căn chữ/hình học khác biệt với thân bảng. Tầng header không được kéo dài chỉ vì dòng dữ liệu đầu cũng in đậm; thiếu căn cứ thì giữ raw và unresolved. Không dùng từ điển tên header, mã ngành, năm hoặc nội dung câu hỏi.
2. **Bản chiếu trùng chặn nối bảng.** Với ô gộp dọc, native block của một hàng không bằng chuỗi nối toàn bảng vì thiếu phần chữ thuộc block khác. Nay chỉ chuyển bản chiếu trùng vào provenance khi bbox thuộc bảng và khớp duy nhất một chuỗi **nguyên ô**; không khớp một phần số hoặc text ở ngoài vùng. Giữ raw block, source locations và danh sách ô chứng minh. PDF học phí có 4 bản chiếu như vậy; không xóa bytes nguồn.
3. **Sang trang không lặp header.** Chỉ kế thừa header đã xác minh khi cùng scope, hai trang liền nhau, sát biên trang, lưới đầy đủ/căn cột, không có đoạn mở phạm vi mới, hai dòng cuối/đầu có số thứ tự nguyên liên tục. Lưu lineage/source locations/witness. Mã có số 0 đầu không biến thành ordinal. `header_depth` của trang không in header vẫn là 0; không giả rằng nguồn có một dòng header để bỏ đi. Các ô vẫn trỏ đúng trang và vị trí gốc.
4. **Metadata OCR bị bỏ khỏi Markdown.** Header rescue đọc thêm các block header/text có tọa độ hợp lệ, giữ nguyên raw evidence. Kiểm tính duy nhất trên toàn bộ quan sát trước khi chọn; mâu thuẫn Markdown/raw/native không được tự ưu tiên một phía. Kết quả vẫn là `proposed`, chưa tự xác nhận. Replay phản hồi Paddle thật của Context629 đã tìm được số/ngày cùng block provenance, không gọi upstream mới.
5. **Tương thích dữ liệu cũ.** Parser lên `pdf-evidence-structure/v6`, thay fingerprint riêng PDF. Khi kiểm artifact v5, giữ chính sách header và dựng block v5, không âm thầm áp dụng suy luận mới. Đã kiểm cả fixture lẫn cặp v5 thật của Context628; artifact cũ không bị sửa. Cache DOCX/XLSX không đổi.

Các file app: `pdf_header_roles.py`, `pdf_evidence.py`, `pdf_continuations.py` mới, `pdf_structure.py`, `pdf_tables.py`, `pdf_fidelity.py`, `services/header_rescue.py`. Không sửa DOCX parser, Quality Gate, RAG runtime, ModelOps hoặc database schema. Thêm `test_pdf_text_structure_630.py`; mở rộng trường hợp nền trắng trong test grid hiện có vì giờ đã có bằng chứng ô cha/con thay cho nền màu.

## Kiểm thử và bằng chứng

| Kiểm tra | Kết quả thực chạy | Exit code |
|---|---|---|
| Tái hiện ban đầu trên snapshot trước sửa | 8 FAIL / 12 PASS; lưu exact IDs/cause | 1 |
| Mở rộng rủi ro dòng đầu in đậm | Tái hiện 1 lỗi trong batch trung gian, đã sửa bằng ranh giới ô | 1 trước sửa |
| Nối bảng không header | 2 FAIL / 26 PASS trước sửa; ca caption/gap/axes vẫn giữ chặn | 1 trước sửa |
| Focused cuối PDF/DOCX/serving | **219 PASS**, thêm 23 subtest PASS | 0 |
| Ruff đúng 9 file | **PASS** | 0 |
| Đối soát 4 PDF và replay OCR đã lưu | Hoàn tất, 0 DB/model calls; giữ grid/hash | 0 |
| Đọc lại 4 cặp artifact + artifact v5 thật | **PASS** | 0 |
| Full Pytest cuối, 804,06 giây | **3.833 PASS / 18 FAIL nền / 17 SKIP** | **1 — suite vẫn FAIL** |
| Đối chiếu baseline Context627 | Exact failure IDs và causes đều khớp; **33 test mới PASS**, không thiếu ID hoặc regression mới | 0 |

Các ca mở rộng gồm header nhiều tầng/nền trắng, giữ Alpha/North và số 0 đầu, first body in đậm, nối ba trang, caption khác scope, lệch cột, ordinal ngắt quãng, nguyên ô so với khớp một phần, bbox ngoài bảng, OCR thiếu/sai/NaN/pixel coordinates, role không hợp lệ, duplicate/conflict và native field không bị ghi đè; v5 không tự nhận ngữ nghĩa v6.

[Đối chiếu theo test ID](../../../backend/storage/context630/test-id-comparison.json), [full receipt](../../../backend/storage/context630/checks/full-release-run.json), [Ruff receipt](../../../backend/storage/context630/checks/ruff-final-run.json). Lệnh dùng Python trong `backend/.venv`, cwd `backend`; wrapper và XML/log giữ tại `backend/storage/context630/checks`.

Một lượt full chưa hoàn tất được dừng ở đầu bộ để sửa cờ header proposal dư phát hiện qua replay; không dùng lượt đó nghiệm thu. Full cuối chạy trên batch ổn định, hash app giữ nguyên trong toàn lượt. Lượt replay đầu dừng do harness thiếu hash baseline cho projector; đã bổ sung hash từ bytes thực, không sửa projector để che lỗi. Các lượt trung gian được giữ, không thay thế bằng PASS cuối.

## Giới hạn và bước sau

- Chưa xử lý PDF scan hoặc tích hợp Nemotron. Các vùng hình/chữ ký không tự được xem là trang trí để bỏ chặn. Công thức phân số phức tạp chưa được chứng nhận hiểu đúng hoặc dùng tính toán; giữ glyph/geometry, không tự suy phép toán.
- Báo cáo 2024 còn vai trò bảng chưa đủ căn cứ; không mở rộng tiêu chí chỉ để làm hết cảnh báo. Nên đối chiếu cùng trang qua parser thị giác khi endpoint Nemotron sẵn sàng.
- Không gọi lại LLM, không chạy lại Compiler ba DOCX đã được nghiệm thu, không benchmark64 hoặc tuyên bố cải thiện điểm RAG. Không nạp revision mới vào kho đang dùng.
- [Đánh giá Qwen3.8-27B/GPT-OSS/Nemotron](./MODEL_ASSESSMENT.md): Qwen đáng thử tiếp, chưa có A/B QNU để kết luận hơn GPT-OSS; model mặc định giữ nguyên.

## An toàn và bàn giao

Đã kiểm cấu hình DB/MinIO/Qdrant là local trước tests. DB mới có nonce/comment sở hữu, Storage riêng, chỉ tạo schema trong DB test, endpoint inference vô hiệu và chặn egress. Không migration dữ liệu đang dùng. Chỉ copy metadata defaults định kiểu, không copy credential/provider vào DB tests.

DB thử `qnu_test_context616_73d32960b6a8` đã dọn sau khi kiểm nonce/comment và xác minh không còn. Storage raw/output/runtime giữ theo policy để bàn giao, không tuyên bố đã xóa. Seals collection/binding/source/index/assistant/provider trước/sau khớp; app ngoài đúng 7 file trên giữ nguyên. Không đổi model/config, restart, deploy, reindex, xuất bản, commit hoặc push.
