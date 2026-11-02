---
name: qnu-knowledge-ingestion
description: Implement or review QNU PDF, DOCX, XLSX and OCR extraction, table reconstruction, canonical evidence, chunking and publication-safe indexing. Use for source processing and provenance; not ordinary chat routing.
---

# Ingestion và bằng chứng tài liệu

Đọc luồng thật ở `backendV1/qnu/domains/knowledge`, `backendV1/qnu/domains/ocr`, các adapter/storage port và model/index publication liên quan. Tuân [workflow](../../rules/workflow-and-memory.md) và [gate](../../rules/verification.md).

1. Lưu nguồn qua StorageDriver trước xử lý; checksum/dedup phải tính cả collection và tenant/version cần thiết. Giữ local/S3 parity, retry/idempotency và trạng thái tiến trình trung thực.
2. Giữ nguyên bytes nguồn, raw OCR JSON, thứ tự trang/block, bbox, bảng/ô, rowspan/colspan, footnote và config/model parser. Mọi bản clean/canonical/record/chunk là dẫn xuất có source revision/hash và mapping ngược.
3. Unicode NFC chỉ chuẩn hóa biểu diễn, không khôi phục chữ đã OCR sai. Không xóa ký tự/ngắt dòng/header rồi mất bằng chứng. Lưu raw span, correction và lý do; cảnh báo text hỏng thay vì thay số bằng phỏng đoán.
4. Tái dựng bảng bằng tọa độ, quan hệ ô/hàng/cột, typography và tính liên tục trang. Header có thể nhiều tầng, ô rỗng, số, đơn vị hoặc ký hiệu. Không áp ngưỡng hình thái học cứng cho mọi loại bảng hay vá bằng từ điển gõ tay. Heuristic phải có fixture đa dạng và kiểm tra không mất ô số.
5. Bảo toàn header cha/con, metric, đơn vị, chú thích và ô dữ liệu cùng nguồn. Không gán cùng scope cho mọi ô chỉ từ tên file, ngày ký hoặc trang đầu. Dữ liệu nhiều năm trong một bảng cần year scope theo ô/cột; không có chứng cứ thì unknown.
6. Chunk theo cấu trúc phù hợp nguồn: điều/khoản, đoạn, bảng hoặc record. Không cắt rời dòng số khỏi header/chú thích; giữ parent/source mapping và token budget. Chunk size/overlap là cấu hình cần đo, không chuẩn chung.
7. Facts chỉ dùng giá trị trích được và provenance tới ô/block; tách published/verified/draft/conflict. Cờ review không đồng nghĩa đã duyệt; không lấy nhãn benchmark hoặc output LLM làm căn cứ chính thức.
8. Kiểm tra revision/hash giữa extraction, review, indexing và publication. Thay đổi parser/model phải tạo dẫn xuất/generation tương thích; không ghi đè canonical đang phục vụ. Backfill, active switch, publish và rule activation là các hành động riêng, chỉ thực hiện trong phạm vi được phép; có rollback giữ nguồn cũ.
9. Với thay đổi dữ liệu phức tạp, giải thích nguyên nhân, thuật toán, phạm vi cô lập và kiểm thử trước khi triển khai. Đã được giao triển khai thì tiến hành trong phạm vi đó, không hỏi lại từng bước thông thường.

Kiểm thử: DOCX table và PDF text không hồi quy; OCR raw artifacts; header nhiều tầng/nối trang; missing block order; footnote; dấu tiếng Việt; date conflict; bảng nhiều năm; ô 0/dấu gạch; retry/duplicate; draft không lọt retrieval; tenant isolation và citation đọc được sau publish. Fixture giả không chứng minh OCR dịch vụ thật đã đạt.
