"""Seed data for official QNU Question Bank & Bloom Exam Matrix Knowledge (Quy định Ngân hàng câu hỏi thi ĐH Quy Nhơn)."""

from __future__ import annotations

from typing import Any

QUESTION_BANK_DOCUMENT_ID = "doc_qnu_quy_dinh_ngan_hang_cau_hoi"
QUESTION_BANK_COLLECTION_ID = "col_question_bank"
QUESTION_BANK_TITLE = (
    "Quy định Xây dựng Ngân hàng câu hỏi thi và Ma trận đề thi kết thúc học phần "
    "theo thang đo Bloom Trường Đại học Quy Nhơn"
)
QUESTION_BANK_FILENAME = "Quy_dinh_xay_dung_ngan_hang_cau_hoi_va_de_thi_QNU.pdf"

QUESTION_BANK_CHUNKS: list[dict[str, Any]] = [
    {
        "id": "chk_qb_1",
        "chunk_index": 0,
        "title": "Chương I: Nguyên tắc chung và Thang đo tư duy Bloom áp dụng tại QNU",
        "content": (
            "TRƯỜNG ĐẠI HỌC QUY NHƠN\n"
            "QUY ĐỊNH XÂY DỰNG NGÂN HÀNG CÂU HỎI THI VÀ MA TRẬN ĐỀ THI\n"
            "Chương I - QUY ĐỊNH CHUNG VÀ THANG ĐO NHẬN THỨC BLOOM:\n"
            "1. Mục đích: Chuẩn hóa ngân hàng câu hỏi thi, đề thi kết thúc học phần gắn liền với chuẩn đầu ra học phần (CLO) và chuẩn đầu ra chương trình đào tạo (PLO).\n"
            "2. Thang đo nhận thức Bloom cải tiến (Revised Bloom's Taxonomy) áp dụng tại QNU gồm 4 mức độ chuẩn hóa:\n"
            "   - Mức 1: Nhận biết (Remembering) - Nhắc lại, nhận diện định nghĩa, công thức, thuật ngữ, sự kiện đã học.\n"
            "   - Mức 2: Thông hiểu (Understanding) - Giải thích, diễn giải, phân loại, tóm tắt ý nghĩa, so sánh khái niệm.\n"
            "   - Mức 3: Vận dụng (Applying) - Vận dụng kiến thức, quy tắc, thuật toán để giải quyết bài toán/tình huống quen thuộc.\n"
            "   - Mức 4: Vận dụng cao (Analyzing / Evaluating / Creating) - Phân tích cấu trúc hệ thống, đánh giá phản biện dựa trên tiêu chí, hoặc sáng tạo giải pháp/thiết kế mới trong bối cảnh mới."
        ),
        "metadata": {
            "section": "Chương I",
            "topic": "Thang đo nhận thức Bloom 4 mức độ",
            "document_name": QUESTION_BANK_FILENAME,
            "title": QUESTION_BANK_TITLE,
            "page": 1,
        },
    },
    {
        "id": "chk_qb_2",
        "chunk_index": 1,
        "title": "Chương II: Tiêu chuẩn kỹ thuật câu hỏi trắc nghiệm khách quan nhiều lựa chọn (MCQ)",
        "content": (
            "Chương II - TIÊU CHUẨN XÂY DỰNG CÂU HỎI THI TRẮC NGHIỆM (MCQ):\n"
            "1. Cấu trúc câu hỏi trắc nghiệm 4 lựa chọn chuẩn:\n"
            "   - Phần dẫn (Stem): Nêu rõ vấn đề cần giải quyết, câu văn ngắn gọn, rõ nghĩa, không chứa từ ngữ đánh đố hoặc phủ định hai lần. Nếu có từ phủ định (KHÔNG, SAI), bắt buộc phải in hoa và bôi đậm.\n"
            "   - 01 Phương án đúng duy nhất (Key): Chính xác tuyệt đối, được chứng minh bởi tài liệu giảng dạy chính thức.\n"
            "   - 03 Phương án nhiễu (Distractors): Hợp lý, có tính logic, phản ánh các lỗi sai phổ biến của sinh viên; độ dài và cấu trúc ngữ pháp tương đồng với phương án đúng.\n"
            "2. Các điều cấm tuyệt đối khi ra câu hỏi trắc nghiệm:\n"
            "   - Tuyệt đối cấm dùng các phương án: 'Tất cả các câu trên đều đúng', 'Tất cả các phương án đều sai', 'Cả A và B đều đúng'.\n"
            "   - Không để lộ đáp án đúng qua manh mối ngữ pháp, độ dài vượt trội hoặc sự lặp từ với phần dẫn."
        ),
        "metadata": {
            "section": "Chương II",
            "topic": "Tiêu chuẩn kỹ thuật câu hỏi MCQ",
            "document_name": QUESTION_BANK_FILENAME,
            "title": QUESTION_BANK_TITLE,
            "page": 2,
        },
    },
    {
        "id": "chk_qb_3",
        "chunk_index": 2,
        "title": "Chương III: Ma trận đề thi chuẩn và Tỷ trọng phân bổ mức độ nhận thức",
        "content": (
            "Chương III - THIẾT KẾ MA TRẬN ĐỀ THI KẾT THÚC HỌC PHẦN:\n"
            "1. Ma trận đề thi kết thúc học phần bắt buộc phân bổ theo tỷ lệ trọng số nhận thức chuẩn tại QNU:\n"
            "   - Mức độ Nhận biết: 30% - 40% tổng điểm.\n"
            "   - Mức độ Thông hiểu: 30% - 40% tổng điểm.\n"
            "   - Mức độ Vận dụng: 15% - 25% tổng điểm.\n"
            "   - Mức độ Vận dụng cao: 10% - 15% tổng điểm.\n"
            "   - Tỷ lệ chuẩn mực tham chiếu khuyến nghị cho kỳ thi chính thức: 40% Nhận biết - 30% Thông hiểu - 20% Vận dụng - 10% Vận dụng cao.\n"
            "2. Hình thức thi:\n"
            "   - Đề trắc nghiệm thuần túy: Thời lượng 45 - 60 phút (tối thiểu 40 - 50 câu hỏi).\n"
            "   - Đề kết hợp trắc nghiệm (50%) và tự luận (50%): Thời lượng 60 - 90 phút.\n"
            "   - Đề tự luận thuần túy: Thời lượng 75 - 90 phút (thường gồm 3 - 5 câu hỏi lớn có các ý nhỏ phân hóa theo 4 mức độ Bloom)."
        ),
        "metadata": {
            "section": "Chương III",
            "topic": "Ma trận đề thi và tỷ lệ trọng số Bloom",
            "document_name": QUESTION_BANK_FILENAME,
            "title": QUESTION_BANK_TITLE,
            "page": 3,
        },
    },
    {
        "id": "chk_qb_4",
        "chunk_index": 3,
        "title": "Chương IV: Chỉ số Thống kê Đo lường Chất lượng Câu hỏi Thi (P và D)",
        "content": (
            "Chương IV - PHÂN TÍCH THỐNG KÊ CHẤT LƯỢNG CÂU HỎI THI SAU THỰC NGHIỆM:\n"
            "1. Độ khó của câu hỏi thi (Difficulty Index - P):\n"
            "   - Công thức: P = R / T (R là số thí sinh trả lời đúng, T là tổng số thí sinh làm bài).\n"
            "   - Dải độ khó chuẩn chấp nhận đưa vào ngân hàng: 0.25 <= P <= 0.75.\n"
            "   - Câu hỏi có P tối ưu đạt chất lượng cao: 0.50 <= P <= 0.60.\n"
            "   - Câu hỏi có P > 0.85 bị coi là quá dễ; P < 0.20 bị coi là quá khó, phải loại bỏ hoặc chỉnh sửa.\n"
            "2. Độ phân cách của câu hỏi thi (Discrimination Index - D):\n"
            "   - Công thức: D = (H - L) / N_nhóm (so sánh nhóm 27% điểm cao nhất H và 27% điểm thấp nhất L).\n"
            "   - D >= 0.40: Câu hỏi rất tốt, khả năng phân hóa năng lực xuất sắc.\n"
            "   - 0.30 <= D < 0.40: Câu hỏi chuẩn mực tốt, đủ điều kiện lưu kho ngân hàng chính thức.\n"
            "   - 0.20 <= D < 0.30: Câu hỏi tạm chấp nhận, cần rà soát sửa đổi phương án nhiễu.\n"
            "   - D < 0.20: Câu hỏi kém hoặc có sai sót kỹ thuật, loại bỏ ngay khỏi ngân hàng đề thi."
        ),
        "metadata": {
            "section": "Chương IV",
            "topic": "Chỉ số độ khó P và độ phân cách D",
            "document_name": QUESTION_BANK_FILENAME,
            "title": QUESTION_BANK_TITLE,
            "page": 4,
        },
    },
    {
        "id": "chk_qb_5",
        "chunk_index": 4,
        "title": "Chương V: Quy chuẩn Thiết kế Rubric và Thang điểm chấm thi Tự luận",
        "content": (
            "Chương V - QUY CHUẨN ĐÁP ÁN, BIỂU ĐIỂM VÀ RUBRIC CHẤM THI TỰ LUẬN:\n"
            "1. Yêu cầu bắt buộc đối với đáp án chấm thi tự luận:\n"
            "   - Đáp án phải đi kèm Rubric hoặc barem điểm chi tiết đến từng bước giải/luận điểm.\n"
            "   - Bước nhảy điểm tối đa là 0.25 điểm cho mỗi ý chấm; không cho điểm gộp 1.0 hay 2.0 điểm mà không có căn cứ chia nhỏ.\n"
            "   - Barem điểm phải ghi rõ tiêu chí chấp nhận các cách giải khác hợp lý của sinh viên mà vẫn đạt trọn vẹn điểm số.\n"
            "2. Tiêu chí phân loại trong Rubric chấm:\n"
            "   - Mức Xuất sắc/Giỏi: Nắm vững lý thuyết, lập luận chặt chẽ, dẫn chứng xác đáng, có tư duy sáng tạo/phản biện.\n"
            "   - Mức Khá: Đạt đủ nội dung cốt lõi, lập luận đúng, cách trình bày rõ ràng.\n"
            "   - Mức Trung bình: Đạt các ý nhận biết cơ bản, còn thiếu sót ở phần phân tích vận dụng sâu.\n"
            "   - Mức Yếu/Kém: Sai lệch bản chất khái niệm hoặc bỏ sót nội dung lớn."
        ),
        "metadata": {
            "section": "Chương V",
            "topic": "Rubric chấm thi và barem điểm 0.25",
            "document_name": QUESTION_BANK_FILENAME,
            "title": QUESTION_BANK_TITLE,
            "page": 5,
        },
    },
    {
        "id": "chk_qb_6",
        "chunk_index": 5,
        "title": "Chương VI: Quy trình Thẩm định, Nghiệm thu và Bảo mật Ngân hàng Đề thi",
        "content": (
            "Chương VI - QUY TRÌNH QUẢN LÝ VÀ BẢO MẬT NGÂN HÀNG ĐỀ THI:\n"
            "1. Quy trình nghiệm thu 3 cấp:\n"
            "   - Cấp 1 (Bộ môn): Giảng viên biên soạn nộp câu hỏi kèm ma trận đề; Bộ môn tổ chức phản biện chéo (ít nhất 02 giảng viên cùng chuyên môn).\n"
            "   - Cấp 2 (Khoa/Bộ môn trực thuộc): Hội đồng nghiệm thu Khoa rà soát sự tương thích với Chuẩn đầu ra (CLO/PLO).\n"
            "   - Cấp 3 (Phòng Khảo thí & Bảo đảm chất lượng): Kiểm định kỹ thuật, mã hóa và nạp vào phần mềm quản trị khảo thí trung tâm.\n"
            "2. Chế độ bảo mật:\n"
            "   - Toàn bộ ngân hàng câu hỏi và đề thi kết thúc học phần được quản lý theo chế độ bảo mật tài liệu mật cấp cơ sở.\n"
            "   - Máy tính lưu trữ dữ liệu ngân hàng đề thi được cách ly mạng nội bộ, quản trị bằng mật khẩu 2 lớp và phân quyền cán bộ phụ trách."
        ),
        "metadata": {
            "section": "Chương VI",
            "topic": "Quy trình nghiệm thu 3 cấp & Bảo mật",
            "document_name": QUESTION_BANK_FILENAME,
            "title": QUESTION_BANK_TITLE,
            "page": 6,
        },
    },
]

QUESTION_BANK_FACTS: list[dict[str, Any]] = [
    {
        "fact_key": "fact_qb_bloom_levels",
        "category": "bloom_taxonomy",
        "entity_name": "4 mức độ nhận thức thang đo Bloom áp dụng trong đề thi QNU",
        "attribute_name": "Danh mục 4 mức độ nhận thức và đặc trưng kỹ năng",
        "value": (
            "Thang đo Bloom tại QNU phân thành 4 mức độ nhận thức: "
            "1. Nhận biết (Remembering - tái hiện thông tin, công thức); "
            "2. Thông hiểu (Understanding - diễn giải, so sánh, phân loại khái niệm); "
            "3. Vận dụng (Applying - giải quyết bài toán, tình huống quen thuộc); "
            "4. Vận dụng cao (Analyzing / Evaluating / Creating - phân tích, đánh giá, thiết kế giải pháp mới)."
        ),
        "fact_metadata": {
            "levels": ["Nhận biết", "Thông hiểu", "Vận dụng", "Vận dụng cao"],
            "level_count": 4,
            "system": "Revised Bloom Taxonomy",
        },
    },
    {
        "fact_key": "fact_qb_mcq_structure",
        "category": "question_structure",
        "entity_name": "Cấu trúc chuẩn và quy tắc cấm đối với câu hỏi trắc nghiệm MCQ",
        "attribute_name": "Quy cách phần dẫn, phương án đúng, phương án nhiễu và các cụm từ cấm",
        "value": (
            "Cấu trúc MCQ gồm: 01 phần dẫn rõ nghĩa + 01 phương án đúng duy nhất + 03 phương án nhiễu logic. "
            "Tuyệt đối cấm sử dụng các phương án: 'Tất cả các câu trên đều đúng/sai', 'Cả A và B đều đúng'. "
            "Từ phủ định (KHÔNG, SAI) bắt buộc in hoa và bôi đậm."
        ),
        "fact_metadata": {
            "options_count": 4,
            "keys_count": 1,
            "distractors_count": 3,
            "prohibited_phrases": [
                "Tất cả các câu trên đều đúng",
                "Tất cả các phương án đều sai",
                "Cả A và B đều đúng",
            ],
        },
    },
    {
        "fact_key": "fact_qb_matrix_weights",
        "category": "exam_matrix",
        "entity_name": "Tỷ lệ trọng số phân bổ mức độ nhận thức trong ma trận đề thi chuẩn QNU",
        "attribute_name": "Tỷ lệ điểm số chuẩn theo 4 mức độ Bloom",
        "value": (
            "Tỷ lệ phân bổ chuẩn trong ma trận đề thi QNU: "
            "Nhận biết: 40% (dao động 30-40%); "
            "Thông hiểu: 30% (dao động 30-40%); "
            "Vận dụng: 20% (dao động 15-25%); "
            "Vận dụng cao: 10% (dao động 10-15%). Tổng điểm: 100%."
        ),
        "fact_metadata": {
            "remembering_pct": 40,
            "understanding_pct": 30,
            "applying_pct": 20,
            "higher_order_pct": 10,
            "total_pct": 100,
        },
    },
    {
        "fact_key": "fact_qb_difficulty_index",
        "category": "psychometrics",
        "entity_name": "Chỉ số độ khó P của câu hỏi thi trắc nghiệm",
        "attribute_name": "Công thức tính, dải chấp nhận chuẩn và dải tối ưu",
        "value": (
            "Chỉ số độ khó P = R / T. Dải chuẩn chấp nhận vào ngân hàng đề: 0.25 <= P <= 0.75. "
            "Dải độ khó tối ưu chất lượng cao: 0.50 <= P <= 0.60. Câu hỏi có P > 0.85 (quá dễ) hoặc P < 0.20 (quá khó) phải loại bỏ."
        ),
        "fact_metadata": {
            "formula": "P = R / T",
            "min_acceptable_p": 0.25,
            "max_acceptable_p": 0.75,
            "optimal_p_range": [0.50, 0.60],
        },
    },
    {
        "fact_key": "fact_qb_discrimination_index",
        "category": "psychometrics",
        "entity_name": "Chỉ số độ phân cách D của câu hỏi thi trắc nghiệm",
        "attribute_name": "Công thức tính và ngưỡng phân loại chất lượng câu hỏi",
        "value": (
            "Chỉ số độ phân cách D = (H - L) / N_nhóm. "
            "D >= 0.40: Rất tốt; 0.30 <= D < 0.40: Tốt (chuẩn mực lưu kho); "
            "0.20 <= D < 0.30: Tạm chấp nhận cần chỉnh sửa; D < 0.20: Kém, loại bỏ ngay khỏi ngân hàng."
        ),
        "fact_metadata": {
            "formula": "D = (H - L) / N_group_27pct",
            "excellent_threshold": 0.40,
            "good_threshold": 0.30,
            "marginal_threshold": 0.20,
        },
    },
    {
        "fact_key": "fact_qb_rubric_standards",
        "category": "scoring_rubric",
        "entity_name": "Tiêu chuẩn thiết kế Rubric và barem điểm bài thi tự luận",
        "attribute_name": "Bước nhảy chia nhỏ điểm số và nguyên tắc linh hoạt",
        "value": (
            "Đáp án tự luận bắt buộc có Rubric chi tiết với bước nhảy điểm tối đa 0.25 điểm cho mỗi ý. "
            "Không cho điểm gộp; bắt buộc có tiêu chí chấp nhận các phương pháp giải sáng tạo khác của sinh viên."
        ),
        "fact_metadata": {
            "max_score_step": 0.25,
            "requires_alternative_solution_criteria": True,
            "scoring_levels": ["Xuất sắc/Giỏi", "Khá", "Trung bình", "Yếu/Kém"],
        },
    },
    {
        "fact_key": "fact_qb_workflow_approval",
        "category": "governance",
        "entity_name": "Quy trình nghiệm thu 3 cấp và chế độ bảo mật ngân hàng đề thi QNU",
        "attribute_name": "Các cấp phê duyệt và yêu cầu bảo mật thông tin",
        "value": (
            "Quy trình nghiệm thu 3 cấp: Cấp 1 (Bộ môn phản biện chéo 2 giảng viên); Cấp 2 (Khoa nghiệm thu chuẩn CLO/PLO); "
            "Cấp 3 (Phòng Khảo thí kiểm định kỹ thuật và mã hóa). Quản lý theo chế độ tài liệu mật cấp cơ sở."
        ),
        "fact_metadata": {
            "levels_count": 3,
            "cross_reviewers_count": 2,
            "security_tier": "Bảo mật cấp cơ sở",
            "managed_by": "Phòng Khảo thí & Bảo đảm chất lượng",
        },
    },
]
