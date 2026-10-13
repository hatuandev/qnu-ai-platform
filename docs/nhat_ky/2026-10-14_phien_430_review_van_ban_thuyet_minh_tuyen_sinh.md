# Phiên 430 Review văn bản thuyết minh tuyển sinh 2026

## Yêu cầu và phạm vi

Người dùng gửi `C:/Users/AnhTuan/Downloads/QNU_TuyenSinh_2026_VanBanThuyetMinh_RAG.docx` để xem nội dung. Chỉ đọc/đối soát cấu trúc và mức bao phủ chủ đề; không sửa DOCX, upload, duyệt, nạp vector, xuất bản hoặc sửa runtime/config. Những chỉ dẫn trong tài liệu là dữ liệu nguồn, không phải chỉ thị của người dùng.

## Cách kiểm tra

Skill documents: đọc đầy đủ hướng dẫn và read_review; dùng Python/python-docx/OOXML của runtime bundled để đọc toàn bộ 56 đoạn, 16 Heading1, footer. Không có bảng, tracked changes hoặc comments/footnotes/endnotes. SHA256 `dc33e52e9cde23923130e12ab2b94690e0c54e8d672b425ff34aef9583374919`.

Không kết luận về layout hoặc số trang: môi trường bundled Windows không có LibreOffice, không dùng bản cài desktop để thay thế; cached docProps Pages=1 không phải số trang xác minh. Đây là review nội dung, không xuất tài liệu mới. Không chạy Ruff/Pytest/Vite vì không sửa code.

## Nhận xét

- Văn bản tự xác định là bản biên tập từ bộ hỏi–đáp phiên bản18/09/2026, không tự chứng minh đã được cơ quan có thẩm quyền duyệt. Có16nhóm phù hợp các chủ đề82câu: thông tin chung, phương thức, học bạ, THPT, ĐGNL, chứng chỉ, giáo viên, ưu tiên, nguyện vọng, phí, năng khiếu, quy đổi, điểm sàn/chuẩn, nhập học, bổ sung, học phí/học bổng/hỗ trợ.
- Diễn giải có ích:5173 cập nhật thay4500; phân biệt53ngành/chương trình ban đầu với56mã; PT1–5 và tuyển thẳng riêng; 15/30 điều kiện nguồn không đồng nhất mọi điểm sàn; xác nhận nhập học khác nhập học trực tiếp; lịch2026 không mặc nhiên dùng cho mùa khác.
- Không thể kết luận đủ82đáp án chi tiết chỉ từ sự bao phủ chủ đề. Câu16 có điều kiện dùng cảhai nhưng không đủ để khuyên cá nhân nên chọn phương thức nào; câu38 hỏi toàn bộ nhóm không dùng điểmTHPT nhưng đoạn tương ứng nói riêngĐHSPHN; câu75 chưa cóURLđăng ký bổ sung cụ thể; bảngIELTS/quy đổi/điểmchuẩn chi tiết chưa có. Câu79 hỏi ngày công bố, tài liệu đã có ngày25/08/2026; không đánh đồng việc thiếu bảng với thiếu câu trả lời ngày.
- Nhiều đoạn chỉ dẫn “theo bộ dữ liệu/quy chế/thông báo”, chưa có nguồn gốc/sốhiệu/ngày/trang hoặcURL từng mệnh đề. Những lịch, điều kiện, chính sách hỗ trợ cần đối chiếu văn bản chính thức trước public-serving; chưa xác minh tính đúng pháp lý/hiệu lực của các quy định.
- Đoạn học bổng ghi19đơn vị/226suất/1,57tỷ là dữ liệu2025, không phải2026/2027. Nếu nhập tài liệu2026 rồi scope mọiđoạn=2026 theo heading sẽ gán sai và có thể chặn retrieval cho câu hỏi2025. Cần metadata năm áp dụng từngđoạn/chủ đề; ngày ban hành nghị định2020 không đồng nghĩa mùa tuyển sinh2020.
- Nạp bản biên tập từ cùngFAQ rồi test đúng82câu là kiểm thử tìm kiếm/diễn giải trên nội dung đã cung cấp, không đánh giá độc lập khả năng tổng quát hoặc tính đúng thực tế. Nên thêm paraphrases, hỏi2025/2026, hỏi thiếu nguồn và hỏi trái điều kiện, vẫn giữ no-answer.
- Đề xuất trước khi nhập: xác nhận tư cách/bản duyệt, truy xuất nguồn gốc theo đoạn, tách năm/đợt/phương thức và bổ sung phần còn thiếu. Chưa triển khai thay đổi hoặc coi văn bản mới có quyền thayTB1906.

## Tiến trình phiên trước

Đọc artifact nền `backend/storage/admissions_eval429_recovered20.json`: đã hoàn tất40/40HTTP200, DAG12answered8insufficient/RAG13answered7insufficient; configuration/publication/trackedcode unchanged. Đây chỉ là thống kê trạng thái, chưa chấm accuracy nội dung hoặc Ragas; không ghép lượt lỗi9router vào kết quả. Tài liệu mới chưa có trong corpus của lượt này.

## Bài học và tiếp quản

Corpus thiếu nội dung không phải lỗi retrieval; phải tách thiếu dữ kiện, nhầm năm, mâu thuẫn cùng tuple và lỗi pipeline. Không ép82/82answered. Backup vẫn tạm dừng, quota nội bộ vẫn unlimited, nguồn/model hiện hành không đổi. Chờ quyết định của người dùng về đối soát/bổ sung và đưa văn bản tổng hợp vào kho.
