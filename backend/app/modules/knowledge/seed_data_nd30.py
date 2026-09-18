"""Seed data for official Decree 30/2020/ND-CP on State Administrative Records Management."""

from __future__ import annotations

from typing import Any

DECREE_30_DOCUMENT_ID = "doc_nd30_van_thu"
DECREE_30_COLLECTION_ID = "col_drafting"
DECREE_30_TITLE = "Nghị định số 30/2020/NĐ-CP về Công tác văn thư"
DECREE_30_FILENAME = "30_2020_ND_CP_Cong_tac_van_thu.pdf"

DECREE_30_CHUNKS: list[dict[str, Any]] = [
    {
        "id": "chk_nd30_1",
        "chunk_index": 0,
        "title": "Chương I: Quy định chung (Điều 1 - Điều 6)",
        "content": (
            "NGHỊ ĐỊNH SỐ 30/2020/NĐ-CP VỀ CÔNG TÁC VĂN THƯ (Ngày 05/03/2020)\n"
            "Chương I - QUY ĐỊNH CHUNG:\n"
            "Điều 1. Phạm vi điều chỉnh: Soạn thảo, ký ban hành văn bản; quản lý văn bản; lập hồ sơ và nộp lưu hồ sơ; quản lý và sử dụng con dấu, thiết bị lưu khóa bí mật trong công tác văn thư.\n"
            "Điều 2. Đối tượng áp dụng: Áp dụng đối với cơ quan, tổ chức nhà nước và doanh nghiệp nhà nước.\n"
            "Điều 3. Giải thích từ ngữ: Văn bản hành chính là văn bản hình thành trong quá trình chỉ đạo, điều hành, giải quyết công việc của các cơ quan, tổ chức. Bản gốc văn bản là bản hoàn chỉnh về nội dung, thể thức văn bản, được người có thẩm quyền trực tiếp ký trên văn bản giấy hoặc ký số trên văn bản điện tử.\n"
            "Điều 4. Nguyên tắc, yêu cầu quản lý công tác văn thư: Soạn thảo đúng thẩm quyền, trình tự, hình thức, thể thức và kỹ thuật trình bày theo quy định.\n"
            "Điều 5. Giá trị pháp lý của văn bản điện tử: Văn bản điện tử được ký số bởi người có thẩm quyền và ký số của cơ quan, tổ chức có giá trị pháp lý như bản gốc văn bản giấy."
        ),
        "metadata": {
            "chapter": "Chương I",
            "articles": ["Điều 1", "Điều 2", "Điều 3", "Điều 4", "Điều 5", "Điều 6"],
            "document_name": DECREE_30_FILENAME,
            "title": DECREE_30_TITLE,
            "page": 1,
        },
    },
    {
        "id": "chk_nd30_2",
        "chunk_index": 1,
        "title": "Chương II - Mục 1: Thể thức & Kỹ thuật trình bày văn bản (Điều 7 - Điều 9)",
        "content": (
            "Chương II - SOẠN THẢO, KÝ BAN HÀNH VĂN BẢN HÀNH CHÍNH\n"
            "Mục 1 - THỂ THỨC, KỸ THUẬT TRÌNH BÀY VĂN BẢN HÀNH CHÍNH:\n"
            "Điều 7. Các loại văn bản hành chính (29 loại): Nghị quyết (cá biệt), quyết định (cá biệt), chỉ thị, quy chế, quy định, thông cáo, thông báo, hướng dẫn, chương trình, kế hoạch, phương án, đề án, dự án, báo cáo, biên bản, tờ trình, hợp đồng, công văn, công điện, bản ghi nhớ, bản thỏa thuận, giấy ủy quyền, giấy mời, giấy giới thiệu, giấy nghỉ phép, phiếu gửi, phiếu chuyển, phiếu báo, thư công.\n"
            "Điều 8. Thể thức văn bản hành chính bao gồm các thành phần chính:\n"
            "a) Quốc hiệu và Tiêu ngữ: CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM / Độc lập - Tự do - Hạnh phúc.\n"
            "b) Tên cơ quan, tổ chức ban hành văn bản: Ví dụ TRƯỜNG ĐẠI HỌC QUY NHƠN.\n"
            "c) Số, ký hiệu của văn bản (ví dụ: .../TTr-ĐHQN, .../TB-ĐHQN, .../QĐ-ĐHQN).\n"
            "d) Địa danh và thời gian ban hành văn bản: Quy Nhơn, ngày ... tháng ... năm ....\n"
            "đ) Tên loại và trích yếu nội dung văn bản (bắt đầu bằng 'Về việc...').\n"
            "e) Nội dung văn bản (trình bày các điều, khoản, mục rõ ràng).\n"
            "g) Chức vụ, họ tên và chữ ký của người có thẩm quyền.\n"
            "h) Dấu, chữ ký số của cơ quan, tổ chức.\n"
            "i) Nơi nhận văn bản.\n"
            "Điều 9. Kỹ thuật trình bày văn bản:\n"
            "- Khổ giấy: A4 (210 mm x 297 mm).\n"
            "- Định lề trang: Lề trên: 20 - 25 mm; Lề dưới: 20 - 25 mm; Lề trái: 30 - 35 mm; Lề phải: 15 - 20 mm.\n"
            "- Phông chữ: Times New Roman, bảng mã Unicode TCVN 6909:2001.\n"
            "- Quốc hiệu: Cỡ chữ 12-13, in hoa đứng, đậm. Tiêu ngữ: Cỡ chữ 13-14, in thường đứng, đậm.\n"
            "- Số trang: Đánh ở giữa mép trên trang giấy bằng chữ số Ả Rập, cỡ chữ 13-14."
        ),
        "metadata": {
            "chapter": "Chương II",
            "section": "Mục 1",
            "articles": ["Điều 7", "Điều 8", "Điều 9"],
            "document_name": DECREE_30_FILENAME,
            "title": DECREE_30_TITLE,
            "page": 2,
        },
    },
    {
        "id": "chk_nd30_3",
        "chunk_index": 2,
        "title": "Chương II - Mục 2: Soạn thảo & Thẩm quyền ký ban hành (Điều 10 - Điều 13)",
        "content": (
            "Chương II - Mục 2 - SOẠN THẢO VÀ KÝ BAN HÀNH VĂN BẢN HÀNH CHÍNH:\n"
            "Điều 10. Soạn thảo văn bản: Xác định đúng tên loại, nội dung, độ mật, mức độ khẩn; soạn thảo văn bản đúng hình thức, thể thức và kỹ thuật trình bày.\n"
            "Điều 11. Duyệt bản thảo văn bản: Bản thảo văn bản phải do người có thẩm quyền ký duyệt.\n"
            "Điều 12. Kiểm tra văn bản trước khi ký ban hành: Đơn vị chủ trì và người có trách nhiệm kiểm tra thể thức, kỹ thuật trình bày trước khi trình ký.\n"
            "Điều 13. Ký ban hành văn bản:\n"
            "- Cơ quan làm việc theo chế độ thủ trưởng: Người đứng đầu có thẩm quyền ký tất cả văn bản; có thể giao cấp phó ký thay (KT.) các văn bản thuộc lĩnh vực phụ trách.\n"
            "- Ký thừa lệnh (TL.): Người đứng đầu có thể giao người đứng đầu đơn vị trực thuộc ký thừa lệnh một số văn bản.\n"
            "- Ký thừa ủy quyền (TUQ.): Giao bằng văn bản có thời hạn và nội dung cụ thể.\n"
            "- Mực ký văn bản giấy: Dùng bút có mực màu xanh, không dùng các loại mực dễ phai.\n"
            "- Văn bản điện tử: Người có thẩm quyền thực hiện ký số theo quy định."
        ),
        "metadata": {
            "chapter": "Chương II",
            "section": "Mục 2",
            "articles": ["Điều 10", "Điều 11", "Điều 12", "Điều 13"],
            "document_name": DECREE_30_FILENAME,
            "title": DECREE_30_TITLE,
            "page": 3,
        },
    },
    {
        "id": "chk_nd30_4",
        "chunk_index": 3,
        "title": "Chương III: Quản lý văn bản đi và văn bản đến (Điều 14 - Điều 24)",
        "content": (
            "Chương III - QUẢN LÝ VĂN BẢN:\n"
            "Mục 1. Quản lý văn bản đi:\n"
            "Điều 14. Trình tự quản lý văn bản đi: Cấp số, thời gian; Đăng ký văn bản; Nhân bản, đóng dấu hoặc ký số; Phát hành và chuyển phát; Lưu văn bản đi.\n"
            "Điều 15. Cấp số và thời gian ban hành: Số và thời gian lấy theo thứ tự liên tiếp từ số 01 vào ngày 01 tháng 01 và kết thúc vào ngày 31 tháng 12 hàng năm. Số và ký hiệu văn bản là duy nhất trong một năm.\n"
            "Điều 18. Phát hành văn bản đi: Hoàn thành thủ tục phát hành trong ngày hoặc chậm nhất ngày làm việc tiếp theo. Văn bản khẩn phải gửi ngay sau khi ký.\n"
            "Điều 19. Lưu văn bản đi: Bản gốc lưu tại Văn thư cơ quan, bản chính lưu tại hồ sơ công việc.\n"
            "Mục 2. Quản lý văn bản đến:\n"
            "Điều 20. Trình tự quản lý: Tiếp nhận; Đăng ký; Trình, chuyển giao; Giải quyết và theo dõi văn bản đến.\n"
            "Điều 21. Tiếp nhận văn bản đến: Văn bản giấy đóng dấu 'ĐẾN'. Văn bản điện tử kiểm tra tính xác thực và toàn vẹn trước khi tiếp nhận trên Hệ thống."
        ),
        "metadata": {
            "chapter": "Chương III",
            "articles": ["Điều 14", "Điều 15", "Điều 18", "Điều 19", "Điều 20", "Điều 21", "Điều 22", "Điều 23", "Điều 24"],
            "document_name": DECREE_30_FILENAME,
            "title": DECREE_30_TITLE,
            "page": 5,
        },
    },
    {
        "id": "chk_nd30_5",
        "chunk_index": 4,
        "title": "Chương IV & V: Sao văn bản & Sử dụng con dấu, Chữ ký số (Điều 25 - Điều 33)",
        "content": (
            "Chương IV & V - SAO VĂN BẢN VÀ QUẢN LÝ SỬ DỤNG CON DẤU, THIẾT BỊ LƯU KHÓA BÍ MẬT:\n"
            "Điều 25. Các hình thức bản sao: Sao y (từ giấy sang giấy, điện tử sang giấy, giấy sang điện tử); Sao lục; Trích sao. Bản sao đúng quy định có giá trị pháp lý như bản chính (Điều 26).\n"
            "Điều 32. Quản lý con dấu: Giao cho Văn thư cơ quan bảo quản an toàn, trực tiếp đóng dấu, ký số vào văn bản đã có chữ ký người có thẩm quyền.\n"
            "Điều 33. Sử dụng con dấu, thiết bị lưu khóa bí mật:\n"
            "1. Dấu đóng phải rõ ràng, ngay ngắn, đúng chiều và dùng đúng mực dấu màu đỏ theo quy định.\n"
            "2. Khi đóng dấu lên chữ ký, dấu đóng phải trùm lên khoảng 1/3 chữ ký về phía bên trái.\n"
            "3. Dấu giáp lai được đóng vào khoảng giữa mép phải của văn bản hoặc phụ lục văn bản, trùm lên một phần các tờ giấy; mỗi dấu đóng tối đa 05 tờ văn bản.\n"
            "4. Văn bản ban hành kèm theo phụ lục: Dấu đóng lên trang đầu, trùm một phần tên cơ quan hoặc tiêu đề phụ lục."
        ),
        "metadata": {
            "chapter": "Chương IV & V",
            "articles": ["Điều 25", "Điều 26", "Điều 32", "Điều 33"],
            "document_name": DECREE_30_FILENAME,
            "title": DECREE_30_TITLE,
            "page": 7,
        },
    },
    {
        "id": "chk_nd30_6",
        "chunk_index": 5,
        "title": "Chương VI & VII: Quản lý nhà nước & Điều khoản thi hành (Điều 34 - Điều 38)",
        "content": (
            "Chương VI & VII - QUẢN LÝ NHÀ NƯỚC VÀ ĐIỀU KHOẢN THI HÀNH:\n"
            "Điều 34. Nội dung quản lý nhà nước về công tác văn thư: Xây dựng văn bản QPPL, quản lý thống nhất nghiệp vụ, nghiên cứu ứng dụng công nghệ thông tin và số hóa.\n"
            "Điều 36. Kinh phí cho công tác văn thư: Bố trí trong dự toán ngân sách hàng năm để mua sắm, nâng cấp hệ thống, hạ tầng kỹ thuật, số hóa văn bản.\n"
            "Điều 37. Hiệu lực thi hành: Nghị định này có hiệu lực thi hành kể từ ngày ký (05 tháng 3 năm 2020). Nghị định số 110/2004/NĐ-CP và Nghị định số 09/2010/NĐ-CP hết hiệu lực từ ngày Nghị định này có hiệu lực pháp luật.\n"
            "Điều 38. Trách nhiệm thi hành: Bộ Nội vụ, các Bộ trưởng, Thủ trưởng cơ quan ngang Bộ, Chủ tịch UBND các tỉnh, thành phố và người đứng đầu các doanh nghiệp, tổ chức chịu trách nhiệm thi hành. Ký thay Thủ tướng Chính phủ: Nguyễn Xuân Phúc."
        ),
        "metadata": {
            "chapter": "Chương VI & VII",
            "articles": ["Điều 34", "Điều 35", "Điều 36", "Điều 37", "Điều 38"],
            "document_name": DECREE_30_FILENAME,
            "title": DECREE_30_TITLE,
            "page": 10,
        },
    },
]

DECREE_30_FACTS: list[dict[str, Any]] = [
    {
        "entity_name": "Nghị định 30/2020/NĐ-CP",
        "attribute_name": "Số lượng loại văn bản hành chính",
        "attribute_value": "29 loại (Nghị quyết cá biệt, Quyết định, Tờ trình, Thông báo, Kế hoạch, Công văn, Giấy mời...)",
    },
    {
        "entity_name": "Nghị định 30/2020/NĐ-CP",
        "attribute_name": "Quy cách căn lề trang A4",
        "attribute_value": "Lề trên: 20-25mm; Lề dưới: 20-25mm; Lề trái: 30-35mm; Lề phải: 15-20mm",
    },
    {
        "entity_name": "Nghị định 30/2020/NĐ-CP",
        "attribute_name": "Phông chữ chuẩn văn bản",
        "attribute_value": "Times New Roman, bảng mã Unicode TCVN 6909:2001",
    },
    {
        "entity_name": "Nghị định 30/2020/NĐ-CP",
        "attribute_name": "Quy tắc đóng dấu lên chữ ký",
        "attribute_value": "Mực dấu màu đỏ, đóng trùm lên khoảng 1/3 chữ ký về phía bên trái",
    },
    {
        "entity_name": "Nghị định 30/2020/NĐ-CP",
        "attribute_name": "Quy tắc dấu giáp lai",
        "attribute_value": "Đóng vào khoảng giữa mép phải văn bản, trùm lên các tờ giấy, tối đa 05 tờ/dấu",
    },
    {
        "entity_name": "Nghị định 30/2020/NĐ-CP",
        "attribute_name": "Màu mực ký văn bản giấy",
        "attribute_value": "Dùng bút có mực màu xanh, không dùng mực dễ phai",
    },
    {
        "entity_name": "Nghị định 30/2020/NĐ-CP",
        "attribute_name": "Ngày ban hành & hiệu lực",
        "attribute_value": "Ngày 05 tháng 3 năm 2020, ký bởi Thủ tướng Nguyễn Xuân Phúc",
    },
]
