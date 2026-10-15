# Phiên 474 — Rà hội thoại liệt kê tổ hợp và câu nối tiếp

## Phạm vi

Người dùng yêu cầu xem hội thoại xuất17:39:17 (`hoi_thoai_admissions_2026-10-15 (1).md`), chưa yêu cầu sửa thêm. Dùng skill qnu-rag-pipeline, đọc mã và PostgreSQL bằng transaction READ ONLY. Không gọi model, không test chat mới hoặc đổi runtime.

## Bằng chứng trực tiếp

- Hội thoại `conv_fb6db7f15e7a` khớp cả ba câu và thời điểm17:36–17:39.
- Lượt1 điểm chuẩn đã trả bốn ô đúng2024/2025, còn hai dòng SPToán2023/2024 cũ và tiêu đề nguồn lặp ba lần. Export gọi7trích đoạn là7nguồn nhưng thực tế chỉ2văn bản khác nhau.
- Lượt2 “tổng hợp các ngành có tổ hợp môn toán, lý, hóa giúp tôi” trả7ngành. Ngay citations có Hóa học và Công nghệ thực phẩm nhưng nội dung không liệt kê hai ngành đó: thiếu coverage ngay cả với chứng cứ đã có.
- Quét canonical của nguồn đang xuất bản, kiểm tra ba môn cùng một tổ hợp bằng `count_subject_matches`, gắn mã7chữ số: cẩm nang2025 có33mã ngành khác nhau phù hợp (chưa tách chương trình/định hướng chung mã, không phải tổng duy nhất toàn kho). Nguồn2025 khác32mã, `Thông tin TSĐH cập nhật.pdf`18mã. Đây là số đếm source canonical hiện có, không phải suy luận số lượng đúng cho năm2026 từ tài liệu2025; chưa đối chiếu ảnh tài liệu gốc.
- Phân loại câu tổ hợp: mixed/factfirst=true, subject_names=[toán,lý,hóa], subject_combinations, không target entity. Chạy đúng lookup với scope publication hiện tại trả5facts, đều match3môn; không phải do không nhận ra tổ hợp.
- Usage đúng conversation: lượt điểm chuẩn có3Qwen calls; lượt liệt kê chỉ có successful usage của fallback `@cf/meta/llama-3.1-8b-instruct`, 4716prompt/512completiontokens lúc10:38:20UTC. Không có JSON/finish_reason của lượt đó để kết luận bị cắt ở512 hay xác định chính xác lỗi primary.
- Lượt3 “sao ít thế”: classifier narrative, keywords/subjects/entity/metric đều rỗng; không có usage model sau user message10:39:12UTC. Không có bằng chứng đây là timeout model ở câu nối tiếp.

## Nguyên nhân qua mã

1. Đây là truy vấn LIỆT KÊ/TẬP HỢP, nhưng service dùng lookup_limit5 cho mixed; facts chỉ overfetch15rồi cắt về5, sau đó RAG dùng topK/rerank hữu hạn. Luồng này phục vụ tìm vài đoạn liên quan, không có contract chứng minh đã quét đủ các bản ghi thỏa điều kiện. Tăng output tokens không phục hồi những ngành không được truy hồi.
2. Bộ sinh văn xuôi bỏ sót ngành đã có trong citations. Kiểm tra hiện tại có numeric/citation/refusal gates, không kiểm tra đầy đủ tập entity cần liệt kê. Chưa có trace prompt của lượt cũ nên không khẳng định mỗi ngành trong đáp án đã được hậu thuẫn ở prompt.
3. Đáp án không ghi rõ năm mặc dù citations cẩm nang2025. Query không chỉ định mùa, không được mặc định coi toàn bộ là2026 hoặc gộp các phiên bản khác năm thành một danh sách hiện hành.
4. History được tải và chỉ đưa vào chat prompt sau retrieval. Retrieval/facts vẫn dùng nguyên câu hiện tại. Câu nối tiếp ngắn được bỏ qua semantic cache, nhưng chưa resolve “sao ít thế” thành yêu cầu rà đủ danh sách tổ hợp trước đó. Nếu retrieval/facts rỗng, service No-Answer trước khi model đọc history. Bằng chứng code và không có usage phù hợp với từ chối sớm này; reason trace của lượt cũ không được lưu nên không tuyên bố đã quan sát trực tiếp search result rỗng.

## Hướng xử lý đề xuất, chưa triển khai

- Tách enumeration khỏi retrieval topK: lọc từng tuple tổ hợp (ba môn phải cùng nhóm, không OR giữa các nhóm), duyệt theo trang trong scope nguồn/năm đã xuất bản, hợp nhất theo mã ngành/chương trình/năm/phương thức, theo dõi đã duyệt hết và tổng kết quả.
- Render danh sách từ records xác minh, kiểm tra tập entity/coverage và citations, không nhờ model tùy chọn vài ví dụ rồi nói là toàn bộ. Giữ phân biệt ngành/chương trình cùng mã.
- Khi chưa rõ năm: hỏi làm rõ hoặc trình bày riêng từng năm; không lấy năm trên tên file làm data-year override. Không trộn2025/2026 âm thầm.
- Resolve câu nối tiếp bằng history có giới hạn TRƯỚC retrieval, giữ câu gốc làm authority; xác minh đứng đúng chủ đề và cho phép chuyển chủ đề. Không hardcode riêng “sao ít thế”.
- Làm gọn output: chỉ liệt kê tên/mã + tổ hợp được hỏi, không dump mọi tổ hợp khác; dedupe scope hiển thị và đếm nguồn theo source_revision thay vì số citations.
- Regression cần so exact set với toàn bộ nguồn đã xác minh, negative cùng môn rải ở ba tổ hợp khác nhau, hai năm khác nhau, chương trình trùng mã và followup ngắn/chuyển chủ đề. Chưa sửa runtime hoặc chạy bộtest trong phiên chẩn đoán này.

## Trạng thái bàn giao

Đây là lỗi enumeration coverage và conversational retrieval khác với lỗi header/cell query đã sửa phiên473. Dữ liệu có nhiều hơn đáp án. Không push/restart/reset/reindex/publish/model/config/OCR; không sửa các thay đổi phiên473 đang có.
