# Phiên 543 — Kiểm thử DOCX đến dữ liệu RAG và citation offline

**Kết luận: NOT READY.** Nội dung trích xuất được bảo toàn trong các đối chiếu đã chạy, nhưng quan hệ chú thích và một số trạng thái ô chưa đạt ngữ nghĩa của chuẩn. Cổng duyệt chặn bản nháp có ô mơ hồ; chưa thể nghiệm thu tìm kiếm/trả lời trên nguồn đã xuất bản.

User giao bước 3 sau khi sửa và kiểm thử ba finding phiên542. Lượt này chỉ kiểm chứng offline bằng tài liệu mẫu thật, không sửa ứng dụng hoặc nạp lại vào kho. Áp dụng skill ingestion, RAG pipeline/evaluation; nhãn đối chiếu lấy từ OOXML gốc và giữ trạng thái draft.

## Nguồn và phạm vi

- DOCX: `docs/tai_lieu/tuyen_sinh/tai_lieu_phuc_tap_kiem_thu_qnu_rag (1).docx`, SHA256 `58b3f7806529e4e506a6e2569a83ac688b8468fba955d0fe6638444a02099274`. Tài liệu giả lập kiểm thử, không phải dữ kiện chính thức QNU.
- Đối chiếu hash với state phiên537. Tái dùng preview PDF 18 trang của cùng lần thử; hash `863bc240276590843e7a42445087799dea9599b3038a830e4479bcfdcb4fbf4e`. Không gọi render/OCR mới. Không tuyên bố xác minh mới mọi bbox bằng mắt.
- HEAD quan sát `27343f8796f8b6e1c0daaaf4f2250e5e212c4b62`. Sáu file trong fingerprint kiểm thử phiên542 giữ hash. Không tự commit hoặc thay đổi các file ứng dụng.
- Luồng thực chạy: DOCX/OOXML + preview đã lưu → Docling/parser hiện tại → cặp QNU MD/JSON qua StorageDriver trong RAM → load_document kiểm hash/identity/parity → project_document → manifest/context graph → structure_chunks → draft EvidenceBlocks → BM25/pack_context/bind_quote. Không tạo bản chỉ mục phục vụ thật.

## Kết quả bảo toàn nội dung và vị trí

| Kiểm tra | Kết quả |
| --- | --- |
| Cặp MD/JSON và ảnh gốc | PASS; ảnh giữ bytes, checksum/archive trong RAM |
| Đoạn văn chính trong OOXML | 183/183 hiện diện nguyên nội dung sau bỏ khác biệt whitespace/NFC |
| Bảng và dòng thân bảng | 10/10 bảng, 103/103 dòng; header Word đối chiếu đúng, bảng Alpha/North không mất dòng đầu |
| Ô nguồn có nội dung | 645/645 giữ trong raw grid; 645/645 hiện diện tại header/hàng tương ứng sau giải mã biểu diễn |
| Footnote | 3/3 giữ nội dung, mỗi note có anchor và được pack cùng anchor |
| Projection nháp | 271 units, 261 chunks, 392 draft facts; không phải counts đã xuất bản |
| Citation | 261/261 khớp exact canonical span; đều có source locator/location; không bịa trang |
| Khối trải trang | Giữ các trang 7–8, 10–11, 15–16 |

Kiểm literal cell đầu tiên chỉ đạt633/645 do các thẻ `<br>` và dấu phân cấp header `/` được renderer thêm vào. Đối chiếu lại sau giải mã GFM và ghép các segment header đạt645/645; không xóa slash khỏi giá trị ô để làm phép so đạt. Đây là kiểm bảo toàn text theo vị trí hàng/header và raw grid, không xác nhận mọi diễn giải nghiệp vụ đã đúng.

Chín khối vẫn chưa rõ trang, năm cờ span cần đối soát, một bảng chưa xác minh vai trò header và một hình chưa xác minh nội dung. Ảnh được giữ không đồng nghĩa nội dung ảnh đã được phiên âm.

## Phần ngữ nghĩa chưa đạt

### 1. Chú thích có chữ nhưng thiếu liên kết bắt buộc

Chọn đúng dòng rồi pack bằng chứng với ngân sách rộng vẫn không kéo được5/5 chú thích theo nhãn nguồn:

- TB1: phạm vi toàn Bảng1, mốc chốt và quy tắc làm tròn.
- D-AM-0007: chỉ riêng dòng AM-0007, không mở rộng sang AM-0070.
- C-2027: ba cột2027 là dự kiến, không phải kết quả nghiệm thu.
- N-II: chỉ NV-16 đến NV-30.
- K-05: chú giải riêng CT-05; không giải nghĩa thay CT-06.

Các đoạn đều tồn tại trong canonical; thiếu ở context graph/phụ thuộc bắt buộc của dòng. Footnote có anchor OOXML đã đóng dependency đúng, còn prose scope chưa có annotation được kiểm chứng. Kết quả này chứng minh khoảng hở đóng ngữ cảnh; chưa gọi model để khẳng định một câu trả lời sai cụ thể. Không vá bằng từ điển các nhãn TB1/N-II hoặc nối tất cả note gần nhất.

### 2. Trạng thái ô chưa đúng ý nghĩa nguồn

CT-01 raw0/present và CT-02 raw rỗng/blank giữ đúng. CT-03 raw “Chưa công bố” vẫn state present, cần not_stated theo nguồn; CT-04 “Không áp dụng” vẫn present, cần not_applicable. CT-06 `/` giữ ambiguous là đúng vì tài liệu nói chưa có ý nghĩa công bố.

Ba ô unresolved của projection: Bảng5/CT-05 `–`, Bảng5/CT-06 `/`, Bảng9/ví dụ trạng thái `/`. Không được ép chúng thành số0 hoặc đổi PASS bằng suy đoán. Chú giải CT-05 cần liên kết đúng phạm vi; các ký hiệu chưa xác định phải giữ unknown và có chính sách không đưa thành fact trả lời khi thiết kế bước tiếp.

### 3. Tìm kiếm từ vựng có ca bỏ sót

Trên20 câu cố định, nhãn là tọa độ bảng/hàng trong OOXML gốc: BM25 draft Hit@5 **17/20 = 0.85**, MRR@5 **0.825**. Ba ca hụt: dòng0 một cột của Bảng3, dòng00027 của Bảng3 và ví dụ0012 tại Bảng9. Văn bản các dòng vẫn có trong nguồn và canonical; đây là thiếu chất lượng xếp hạng/phân biệt ngữ cảnh của phép thử này.

Một tài liệu, query có từ ngữ trùng nguồn, nhãn draft chưa được người dùng duyệt; các chỉ số không phải benchmark production, không đo exhaustive coverage. Không dùng nó để kết luận dense/hybrid/rerank hoặc model thật đã đạt.

## Cổng an toàn và giới hạn

- source_rows từ chối nguồn nháp qua SOURCE_ROW_INVALID.
- Review guard trong RAM từ chối qua QNU_UNRESOLVED_CELLS; không gọi API/DB duyệt nguồn. Không dựng source giả đã ready để bỏ qua cổng rồi gọi đó là end-to-end PASS.
- Quote không tồn tại bị từ chối; không có draft fact năm2029 trong snapshot mẫu; năm chưa duyệt không tự verified.
- Tìm kiếm trên snapshot đã publish, Qdrant/dense/hybrid/rerank, generation/model judge, chat/UI: **NOT RUN**. Answer correctness=null. Không đo latency sản phẩm/cost từ phép thử này.
- Full Pytest/Ruff ứng dụng không chạy lại vì không sửa app. Kết quả542 là lịch sử: focused158PASS/RuffPASS; full vẫn FAIL13/2163PASS/17skip/23subtests.

## Lệnh và bằng chứng

Cwd `D:\DuAnPhanMem\qnu-ai-platform\backend`, môi trường Python hiện có.

```powershell
.\.venv\Scripts\python.exe ../.antigravity-bridge/validation/check_rag543_offline.py
.\.venv\Scripts\python.exe ../.antigravity-bridge/validation/evaluate_rag543_offline.py
```

Runner đầu ban đầu FAIL vì fake StorageDriver thiếu exists; bổ sung đúng interface của fixture, không sửa app. Lần chạy cuối phase1 **exit0**: parser/pair/projection/chunks/citations có đủ báo cáo. Phase2 **exit1**, decision NOT_READY do thiếu dependency/state; không bỏ lỗi ra khỏi mẫu. Đối chiếu cell decoded độc lập exit0 đạt645/645. Các script nằm trong bridge đã ignore; corpus/báo cáo máy ở storage đã ignore.

- [QNU Markdown QA](../../backend/storage/rag543-offline/standard.md), [canonical RAG](../../backend/storage/rag543-offline/canonical.md).
- [Bằng chứng tổng hợp JSON](../../backend/storage/rag543-offline/report.json), [manifest/hash của lần chạy](../../backend/storage/rag543-offline/run-manifest.json).
- Có thêm projection.json/chunks.json và source-map.json trong cùng thư mục để đối chiếu source-coordinate. Không coi artifact QA này là snapshot nguồn đang phục vụ.

Không nạp lại/reparse/duyệt nguồn/index/publish, không DB/model/provider call, restart/deploy/config/Git write hoặc dọn tracked file. Không xác nhận lại live serving pointer vì lượt này không truy vấn DB; chỉ khẳng định không có hành động ghi nghiệp vụ từ runner. Monitor Gemini giữ paused.

Ưu tiên tiếp theo là annotation ngữ nghĩa có quote và scope cụ thể cho prose notes/cell states; kiểm đóng dependency đúng dòng/cột/nhóm, giữ unknown thật, sau đó thử lại các ca hụt của bảng một cột và ví dụ trùng mã. Chưa chuyển sang nạp lại/duyệt nguồn.
