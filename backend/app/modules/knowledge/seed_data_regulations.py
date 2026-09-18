"""Seed data for official QNU Academic Regulations (Quy chế Đào tạo Tín chỉ ĐH Quy Nhơn)."""

from __future__ import annotations

from typing import Any

REGULATIONS_DOCUMENT_ID = "doc_qnu_quy_che_tin_chi"
REGULATIONS_COLLECTION_ID = "col_regulations"
REGULATIONS_TITLE = "Quy chế đào tạo trình độ đại học theo hệ thống tín chỉ Trường Đại học Quy Nhơn"
REGULATIONS_FILENAME = "Quy_che_dao_tao_tin_chi_DHQN.pdf"

REGULATIONS_CHUNKS: list[dict[str, Any]] = [
    {
        "id": "chk_reg_1",
        "chunk_index": 0,
        "title": "Chương I: Quy định chung (Điều 1 - Điều 3)",
        "content": (
            "TRƯỜNG ĐẠI HỌC QUY NHƠN — QUY CHẾ ĐÀO TẠO ĐẠI HỌC CHÍNH QUY THEO HỆ THỐNG TÍN CHỈ\n"
            "Chương I - QUY ĐỊNH CHUNG:\n"
            "Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng: Quy chế này quy định về đào tạo trình độ đại học chính quy "
            "theo hệ thống tín chỉ tại Trường Đại học Quy Nhơn, bao gồm: chương trình đào tạo, tổ chức đào tạo, đăng ký học phần, "
            "đánh giá kết quả học tập, xử lý học vụ, chuẩn đầu ra và xét công nhận tốt nghiệp.\n"
            "Điều 2. Chương trình đào tạo và thời gian học tập:\n"
            "- Chương trình đào tạo được xây dựng theo định hướng chuẩn đầu ra, khối lượng học tập từ 120 đến 135 tín chỉ tùy ngành.\n"
            "- Thời gian kế hoạch chuẩn đối với bậc đại học cử nhân là 4 năm (8 học kỳ chính).\n"
            "- Thời gian tối đa để hoàn thành khóa học không vượt quá 2 lần thời gian theo kế hoạch chuẩn (tối đa không quá 8 năm).\n"
            "Điều 3. Học phần và tín chỉ:\n"
            "- Tín chỉ là đơn vị dùng để đo lường khối lượng học tập của sinh viên.\n"
            "- 1 tín chỉ được quy định tương đương với 15 tiết lý thuyết và 30 giờ tự học; hoặc 30 - 45 tiết thực hành, thí nghiệm; "
            "hoặc 45 - 90 giờ thực tập thực tế, làm đồ án/khóa luận tốt nghiệp. 1 tiết học lý thuyết kéo dài 50 phút."
        ),
        "metadata": {
            "chapter": "Chương I",
            "articles": ["Điều 1", "Điều 2", "Điều 3"],
            "document_name": REGULATIONS_FILENAME,
            "title": REGULATIONS_TITLE,
            "page": 1,
        },
    },
    {
        "id": "chk_reg_2",
        "chunk_index": 1,
        "title": "Chương II: Tổ chức đào tạo & Đăng ký học phần (Điều 4 - Điều 7)",
        "content": (
            "Chương II - TỔ CHỨC ĐÀO TẠO VÀ ĐĂNG KÝ HỌC PHẦN:\n"
            "Điều 4. Kế hoạch đào tạo và năm học:\n"
            "- Mỗi năm học có 2 học kỳ chính (học kỳ 1 và học kỳ 2) và 1 học kỳ hè (học kỳ phụ không bắt buộc).\n"
            "- Học kỳ chính có ít nhất 15 tuần học và 3 tuần thi; học kỳ hè có ít nhất 5 tuần học và thi.\n"
            "Điều 5. Đăng ký khối lượng học tập (số tín chỉ):\n"
            "- Trong mỗi học kỳ chính: Sinh viên có học lực bình thường đăng ký tối thiểu 14 tín chỉ và tối đa 24 tín chỉ.\n"
            "- Sinh viên đang trong diện bị cảnh báo học tập đăng ký tối thiểu 10 tín chỉ và tối đa không quá 14 tín chỉ.\n"
            "- Trong học kỳ hè: Sinh viên được đăng ký học lại, học cải thiện hoặc học vượt tối đa không quá 8 tín chỉ.\n"
            "Điều 6. Rút bớt học phần đã đăng ký:\n"
            "- Sinh viên được phép rút bớt học phần đã đăng ký trong thời hạn 2 tuần đầu của học kỳ chính hoặc 1 tuần đầu của học kỳ hè.\n"
            "- Học phần được chấp nhận rút sẽ nhận điểm R (Rút) trong bảng điểm và không tính vào điểm trung bình học kỳ, "
            "nhưng sinh viên không được hoàn trả học phí.\n"
            "Điều 7. Học cùng lúc hai chương trình (Song bằng):\n"
            "- Sinh viên được đăng ký học chương trình thứ hai (song ngành) sau khi đã hoàn thành năm thứ nhất.\n"
            "- Điều kiện: Điểm trung bình chung tích lũy năm thứ nhất đạt từ 2.50 trở lên (theo thang điểm 4) "
            "và không thuộc diện bị cảnh báo kết quả học tập."
        ),
        "metadata": {
            "chapter": "Chương II",
            "articles": ["Điều 4", "Điều 5", "Điều 6", "Điều 7"],
            "document_name": REGULATIONS_FILENAME,
            "title": REGULATIONS_TITLE,
            "page": 2,
        },
    },
    {
        "id": "chk_reg_3",
        "chunk_index": 2,
        "title": "Chương III: Đánh giá học phần, Thang điểm 10 quy đổi thang điểm 4 (Điều 12 - Điều 14)",
        "content": (
            "Chương III - ĐÁNH GIÁ KẾT QUẢ HỌC TẬP VÀ THANG ĐIỂM:\n"
            "Điều 12. Cơ cấu đánh giá điểm học phần:\n"
            "- Điểm đánh giá quá trình/bộ phận (chuyên cần, kiểm tra giữa kỳ, bài tập, thảo luận) chiếm tỷ trọng từ 40% đến 50%.\n"
            "- Điểm thi kết thúc học phần (tự luận, trắc nghiệm hoặc vấn đáp/tiểu luận) chiếm tỷ trọng từ 50% đến 60%.\n"
            "Điều 13. Thang điểm đánh giá và quy đổi (Thang điểm 10 -> Chữ -> Thang 4):\n"
            "- Điểm A (Xuất sắc): 8.5 đến 10.0 -> Quy đổi Thang 4: 4.0\n"
            "- Điểm B+ (Khá giỏi): 7.8 đến 8.4 -> Quy đổi Thang 4: 3.5\n"
            "- Điểm B (Khá): 7.0 đến 7.7 -> Quy đổi Thang 4: 3.0\n"
            "- Điểm C+ (Trung bình khá): 6.2 đến 6.9 -> Quy đổi Thang 4: 2.5\n"
            "- Điểm C (Trung bình): 5.5 đến 6.1 -> Quy đổi Thang 4: 2.0\n"
            "- Điểm D+ (Trung bình yếu): 4.7 đến 5.4 -> Quy đổi Thang 4: 1.5\n"
            "- Điểm D (Yếu - Đạt tối thiểu): 4.0 đến 4.6 -> Quy đổi Thang 4: 1.0\n"
            "- Điểm F (Kém - Không đạt): Dưới 4.0 -> Quy đổi Thang 4: 0.0 (Bắt buộc phải học lại).\n"
            "- Học phần được coi là ĐẠT và được tích lũy tín chỉ khi điểm tổng kết đạt từ điểm D (4.0/10) trở lên.\n"
            "Điều 14. Học lại và học cải thiện điểm:\n"
            "- Học phần bị điểm F bắt buộc phải đăng ký học lại cho đến khi đạt điểm D trở lên.\n"
            "- Sinh viên có học phần đạt điểm D, D+ hoặc C được quyền đăng ký học lại để cải thiện điểm trung bình tích lũy.\n"
            "- Khi học lại để cải thiện, điểm học phần được ghi nhận là điểm cao nhất giữa các lần học."
        ),
        "metadata": {
            "chapter": "Chương III",
            "articles": ["Điều 12", "Điều 13", "Điều 14"],
            "document_name": REGULATIONS_FILENAME,
            "title": REGULATIONS_TITLE,
            "page": 3,
        },
    },
    {
        "id": "chk_reg_4",
        "chunk_index": 3,
        "title": "Chương IV: Xử lý học vụ, Cảnh báo học tập và Buộc thôi học (Điều 16 - Điều 18)",
        "content": (
            "Chương IV - XỬ LÝ HỌC VỤ, CẢNH BÁO HỌC TẬP VÀ BUỘC THÔI HỌC:\n"
            "Điều 16. Cảnh báo kết quả học tập (Cảnh báo học vụ):\n"
            "Cảnh báo học vụ được thực hiện theo từng học kỳ chính nhằm thông báo cho sinh viên biết kết quả học tập kém.\n"
            "Sinh viên bị cảnh báo học tập nếu rơi vào một trong các tiêu chí sau:\n"
            "1. Điểm trung bình chung học kỳ đạt dưới 0.80 đối với học kỳ đầu của khóa học, hoặc dưới 1.00 đối với các học kỳ tiếp theo.\n"
            "2. Điểm trung bình chung tích lũy đạt dưới 1.20 đối với sinh viên năm thứ nhất; dưới 1.40 đối với sinh viên năm thứ hai; "
            "dưới 1.60 đối với sinh viên năm thứ ba; hoặc dưới 1.80 đối với sinh viên các năm tiếp theo.\n"
            "3. Tổng số tín chỉ của các học phần bị điểm F tích lũy từ đầu khóa học vượt quá 24 tín chỉ.\n"
            "Điều 17. Xử lý Buộc thôi học:\n"
            "Sinh viên bị buộc thôi học nếu thuộc một trong các trường hợp sau:\n"
            "- Bị cảnh báo kết quả học tập 2 lần liên tiếp hoặc quá 3 lần trong toàn bộ khóa học.\n"
            "- Vượt quá thời gian tối đa được phép học tập tại trường theo quy định tại Điều 2 (vượt quá 8 năm).\n"
            "- Tự ý bỏ học không có lý do chính đáng quá thời hạn 1 học kỳ chính.\n"
            "Điều 18. Tạm dừng học tập và bảo lưu kết quả:\n"
            "- Sinh viên được xin tạm dừng học tập và bảo lưu kết quả trong các trường hợp: thi hành nghĩa vụ quân sự; "
            "bị ốm đau/tai nạn điều trị dài hạn có xác nhận của cơ quan y tế có thẩm quyền; hoặc vì hoàn cảnh cá nhân đặc biệt "
            "(đã học ít nhất 1 học kỳ và không thuộc diện bị buộc thôi học)."
        ),
        "metadata": {
            "chapter": "Chương IV",
            "articles": ["Điều 16", "Điều 17", "Điều 18"],
            "document_name": REGULATIONS_FILENAME,
            "title": REGULATIONS_TITLE,
            "page": 4,
        },
    },
    {
        "id": "chk_reg_5",
        "chunk_index": 4,
        "title": "Chương V: Chuẩn đầu ra Ngoại ngữ & Tin học (Điều 22 - Điều 23)",
        "content": (
            "Chương V - CHUẨN ĐẦU RA NGOẠI NGỮ VÀ TIN HỌC:\n"
            "Điều 22. Chuẩn đầu ra Ngoại ngữ (Tiếng Anh):\n"
            "Sinh viên phải đạt chuẩn đầu ra năng lực ngoại ngữ trước khi xét tốt nghiệp, cụ thể:\n"
            "- Nhóm ngành Sư phạm Ngoại ngữ (SP Tiếng Anh): Đạt Bậc 5 theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam (VSTEP C1) "
            "hoặc tương đương IELTS 6.5, TOEFL iBT 79.\n"
            "- Nhóm ngành Ngôn ngữ Anh: Đạt Bậc 5 (VSTEP C1).\n"
            "- Các ngành đào tạo khác (Sư phạm Toán, Tin, Vật lý, Ngữ văn, CNTT, Kỹ thuật, Quản trị kinh doanh, Kinh tế...): "
            "Đạt Bậc 3 theo Khung 6 bậc (VSTEP B1) hoặc các chứng chỉ quốc tế tương đương được công nhận:\n"
            "  * TOEIC 450 (Nghe-Đọc)\n"
            "  * IELTS 4.5\n"
            "  * TOEFL ITP 450, TOEFL iBT 45.\n"
            "- Chứng chỉ ngoại ngữ nộp về Phòng Đào tạo phải còn hiệu lực trong thời hạn 2 năm tính đến thời điểm xét tốt nghiệp.\n"
            "Điều 23. Chuẩn đầu ra Công nghệ thông tin (Tin học):\n"
            "- Sinh viên không chuyên ngành CNTT phải đạt Chứng chỉ Ứng dụng Công nghệ thông tin cơ bản "
            "theo quy định của Bộ Thông tin và Truyền thông tại Thông tư số 03/2014/TT-BTTTT.\n"
            "- Sinh viên các ngành CNTT, Kỹ thuật phần mềm, Sư phạm Tin học được miễn trừ nộp chứng chỉ này."
        ),
        "metadata": {
            "chapter": "Chương V",
            "articles": ["Điều 22", "Điều 23"],
            "document_name": REGULATIONS_FILENAME,
            "title": REGULATIONS_TITLE,
            "page": 5,
        },
    },
    {
        "id": "chk_reg_6",
        "chunk_index": 5,
        "title": "Chương VI: Xét công nhận tốt nghiệp & Xếp loại tốt nghiệp (Điều 25 - Điều 26)",
        "content": (
            "Chương VI - XÉT CÔNG NHẬN TỐT NGHIỆP VÀ CẤP BẰNG:\n"
            "Điều 25. Điều kiện công nhận tốt nghiệp đại học:\n"
            "Sinh viên được Hội đồng xét tốt nghiệp công nhận tốt nghiệp khi đáp ứng đầy đủ 5 điều kiện sau:\n"
            "1. Tích lũy đủ số học phần và khối lượng tín chỉ quy định trong chương trình đào tạo của ngành học (120 - 135 tín chỉ).\n"
            "2. Điểm trung bình chung tích lũy toàn khóa học đạt từ 2.00 trở lên (theo thang điểm 4).\n"
            "3. Đạt Chuẩn đầu ra Ngoại ngữ (Bậc 3 VSTEP / TOEIC 450) và Chuẩn đầu ra Tin học cơ bản theo quy định.\n"
            "4. Đạt Chứng chỉ Giáo dục Quốc phòng - An ninh (GDQP-AN) và hoàn thành đầy đủ các học phần Giáo dục Thể chất (GDTC).\n"
            "5. Không bị truy cứu trách nhiệm hình sự hoặc không đang trong thời gian bị kỷ luật từ mức đình chỉ học tập trở lên.\n"
            "Điều 26. Xếp hạng tốt nghiệp theo GPA thang điểm 4:\n"
            "- Loại Xuất sắc: Điểm trung bình tích lũy từ 3.60 đến 4.00.\n"
            "- Loại Giỏi: Điểm trung bình tích lũy từ 3.20 đến 3.59.\n"
            "- Loại Khá: Điểm trung bình tích lũy từ 2.50 đến 3.19.\n"
            "- Loại Trung bình: Điểm trung bình tích lũy từ 2.00 đến 2.49.\n"
            "- Quy định hạ bậc tốt nghiệp: Hạng tốt nghiệp của sinh viên có điểm GPA loại Giỏi hoặc Xuất sắc sẽ bị giảm đi 1 bậc nếu: "
            "Có tổng số tín chỉ của các học phần phải học lại (do điểm F) vượt quá 5% tổng số tín chỉ quy định của toàn khóa học; "
            "hoặc từng bị kỷ luật từ mức cảnh cáo cấp trường trở lên trong thời gian học."
        ),
        "metadata": {
            "chapter": "Chương VI",
            "articles": ["Điều 25", "Điều 26"],
            "document_name": REGULATIONS_FILENAME,
            "title": REGULATIONS_TITLE,
            "page": 6,
        },
    },
]

REGULATIONS_FACTS: list[dict[str, Any]] = [
    {
        "fact_key": "fact_thang_diem_quy_doi",
        "category": "academic_scale",
        "entity_name": "Thang điểm học phần ĐH Quy Nhơn",
        "attribute_name": "Quy đổi thang điểm 10 sang chữ và thang 4",
        "value": (
            "A (8.5-10.0 -> 4.0 Xuất sắc); B+ (7.8-8.4 -> 3.5 Khá giỏi); B (7.0-7.7 -> 3.0 Khá); "
            "C+ (6.2-6.9 -> 2.5 TB khá); C (5.5-6.1 -> 2.0 Trung bình); D+ (4.7-5.4 -> 1.5 TB yếu); "
            "D (4.0-4.6 -> 1.0 Yếu đạt); F (<4.0 -> 0.0 Kém học lại)."
        ),
        "fact_metadata": {
            "article": "Điều 13",
            "scale_type": "4.0",
            "pass_minimum": "4.0 (D)",
        },
    },
    {
        "fact_key": "fact_tin_chi_hoc_ky",
        "category": "academic_registration",
        "entity_name": "Số lượng tín chỉ đăng ký mỗi học kỳ",
        "attribute_name": "Giới hạn tín chỉ học kỳ chính và học kỳ hè",
        "value": (
            "Học kỳ chính sinh viên bình thường đăng ký tối thiểu 14 tín chỉ, tối đa 24 tín chỉ; "
            "sinh viên bị cảnh báo học vụ đăng ký tối thiểu 10 tín chỉ, tối đa 14 tín chỉ. "
            "Học kỳ hè đăng ký tối đa 8 tín chỉ."
        ),
        "fact_metadata": {
            "article": "Điều 5",
            "min_regular": 14,
            "max_regular": 24,
            "min_warning": 10,
            "max_warning": 14,
            "max_summer": 8,
        },
    },
    {
        "fact_key": "fact_moc_canh_bao_hoc_vu",
        "category": "academic_warning",
        "entity_name": "Mốc điểm GPA cảnh báo học tập ĐH Quy Nhơn",
        "attribute_name": "Điểm trung bình tích lũy tối thiểu để không bị cảnh báo",
        "value": (
            "Năm 1: GPA tích lũy < 1.20; Năm 2: GPA tích lũy < 1.40; Năm 3: GPA tích lũy < 1.60; "
            "Năm 4 trở đi: GPA tích lũy < 1.80. Hoặc điểm TB học kỳ < 0.80 (học kỳ đầu) hoặc < 1.00 (các kỳ sau). "
            "Bị cảnh báo 2 lần liên tiếp hoặc quá 3 lần toàn khóa sẽ bị Buộc thôi học."
        ),
        "fact_metadata": {
            "article": "Điều 16 & Điều 17",
            "threshold_year_1": 1.20,
            "threshold_year_2": 1.40,
            "threshold_year_3": 1.60,
            "threshold_year_4": 1.80,
            "max_warning_consecutive": 2,
            "max_warning_total": 3,
        },
    },
    {
        "fact_key": "fact_chuan_dau_ra_ngoai_ngu",
        "category": "graduation_requirements",
        "entity_name": "Chuẩn đầu ra Ngoại ngữ (Tiếng Anh) tốt nghiệp ĐH Quy Nhơn",
        "attribute_name": "Yêu cầu chứng chỉ ngoại ngữ theo khối ngành",
        "value": (
            "SP Tiếng Anh & Ngôn ngữ Anh: Bậc 5 (VSTEP C1, IELTS 6.5). "
            "Tất cả các ngành đào tạo còn lại: Bậc 3 (VSTEP B1) hoặc tương đương: TOEIC 450, IELTS 4.5, TOEFL ITP 450. "
            "Chứng chỉ có hiệu lực 2 năm đến thời điểm xét tốt nghiệp."
        ),
        "fact_metadata": {
            "article": "Điều 22",
            "general_vstep": "Bậc 3 (B1)",
            "general_toeic": 450,
            "general_ielts": 4.5,
            "english_major_vstep": "Bậc 5 (C1)",
            "english_major_ielts": 6.5,
        },
    },
    {
        "fact_key": "fact_chuan_dau_ra_tin_hoc",
        "category": "graduation_requirements",
        "entity_name": "Chuẩn đầu ra Tin học tốt nghiệp ĐH Quy Nhơn",
        "attribute_name": "Chứng chỉ Ứng dụng CNTT cơ bản",
        "value": (
            "Chứng chỉ Ứng dụng Công nghệ thông tin cơ bản theo Thông tư 03/2014/TT-BTTTT. "
            "Sinh viên chuyên ngành CNTT, Kỹ thuật phần mềm, SP Tin học được miễn trừ."
        ),
        "fact_metadata": {
            "article": "Điều 23",
            "standard": "TT 03/2014/TT-BTTTT",
        },
    },
    {
        "fact_key": "fact_dieu_kien_xet_tot_nghiep",
        "category": "graduation_requirements",
        "entity_name": "Checklist 5 điều kiện công nhận tốt nghiệp ĐH Quy Nhơn",
        "attribute_name": "Điều kiện cần và đủ để được cấp bằng tốt nghiệp",
        "value": (
            "1. Tích lũy đủ 120-135 tín chỉ theo ngành học; "
            "2. Điểm GPA tích lũy toàn khóa đạt từ 2.00/4.00 trở lên; "
            "3. Đạt Chuẩn đầu ra Ngoại ngữ (VSTEP B1 / TOEIC 450) và Tin học cơ bản; "
            "4. Đạt chứng chỉ GDQP-AN và hoàn thành các học phần GDTC; "
            "5. Không trong thời gian bị kỷ luật từ đình chỉ học tập trở lên."
        ),
        "fact_metadata": {
            "article": "Điều 25",
            "gpa_min": 2.00,
            "has_gdqp": True,
            "has_gdtc": True,
        },
    },
    {
        "fact_key": "fact_xep_hang_tot_nghiep",
        "category": "graduation_scale",
        "entity_name": "Xếp loại tốt nghiệp đại học ĐH Quy Nhơn theo thang 4",
        "attribute_name": "Khung điểm GPA xếp loại bằng tốt nghiệp",
        "value": (
            "Xuất sắc: GPA 3.60 - 4.00; Giỏi: GPA 3.20 - 3.59; "
            "Khá: GPA 2.50 - 3.19; Trung bình: GPA 2.00 - 2.49. "
            "Bị hạ 1 bậc nếu số tín chỉ học lại > 5% tổng số tín chỉ hoặc từng bị kỷ luật từ mức cảnh cáo."
        ),
        "fact_metadata": {
            "article": "Điều 26",
            "excellent_min": 3.60,
            "very_good_min": 3.20,
            "good_min": 2.50,
            "average_min": 2.00,
        },
    },
]
