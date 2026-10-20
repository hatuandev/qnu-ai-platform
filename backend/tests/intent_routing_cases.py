"""Independent utterance labels; no runtime import of this test vocabulary."""
SOCIAL = [
    'Xin chào', 'xin chào!', '  Xin   Chào  ', 'chào bạn', 'chao ban',
    'Xin chào bạn nhé.', 'Chào anh', 'chào chị ạ', 'chào thầy', 'chào cô',
    'Hello', 'HELLO!', 'hi', 'Hi bạn', 'hey', 'Good morning!', 'good afternoon',
    'Good evening', 'chào buổi sáng', 'Chào buổi tối', 'Cảm ơn', 'cam on',
    'Cảm ơn bạn nhiều nhé', 'Xin cảm ơn!', 'Cảm ơn rất nhiều', 'Cảm ơn anh ạ',
    'Thank you', 'Thanks', 'Thanks a lot', 'Tạm biệt', 'tam biet nhe', 'bye',
    'Bye bye!', 'Goodbye', 'Hẹn gặp lại', 'See you', 'xin cha\u0300o',
]
META = ['Bạn là ai?', 'ban la ai', 'Bạn tên gì?', 'Bạn tên là gì', 'Bạn giúp được gì?',
        'Bạn có thể làm gì?', 'Bạn hỗ trợ những gì?', 'Who are you?',
        'What can you do?', 'Bạn có thể tư vấn tuyển sinh không?',
        'Xin chào, bạn là ai?', 'Chào bạn, bạn là ai?']
KNOWLEDGE = [
    'Học phí CNTT năm 2026?', 'Điểm chuẩn Sư phạm Toán?', 'Điều kiện xét tuyển học bạ là gì?',
    'Danh sách ngành tuyển sinh?', 'Trường nhận hồ sơ từ ngày nào?', 'Mã chương trình 00127?',
    'Học bổng dành cho đối tượng nào?', 'Chương trình Alpha học mấy năm?',
    'Ngành Beta có những môn học nào?', 'Điều kiện miễn học phí?', 'Tra cứu học phí năm 2025.',
    'Đối chiếu dữ liệu 2025 và 2026.', 'Năm học 2026–2027 có bao nhiêu tín chỉ?',
    'Học phần bắt buộc của chương trình Gamma?', 'Các phương thức tuyển sinh được công bố?',
    'Trường Đại học Delta có ngành tiếng Nhật không?', 'Thời gian nhận hồ sơ hệ sau đại học?',
    'Đăng ký thi ở địa chỉ nào?', 'Số hiệu quyết định mới được công bố?',
    'Hạn đăng ký ký túc xá?', 'Yêu cầu đầu vào ngoại ngữ?', 'Học phí có bao gồm lệ phí thi không?',
    'Môn học mang tên Hello có bao nhiêu tín chỉ?', 'Từ “cảm ơn” xuất hiện ở trang nào?',
    'Hiến pháp quy định thế nào về giáo dục?', 'Danh sách tổ hợp xét tuyển của mã 0123456?',
    'Mức phí áp dụng cho nhóm B, không áp dụng cho nhóm A?', 'Phạm vi của phụ lục IV?',
    'Điều kiện chuyển ngành được quy định ở đâu?', 'So sánh chương trình Alpha và Beta năm 2026.',
    'Chương trình chất lượng cao yêu cầu những gì?', 'Có bao nhiêu phương thức tuyển sinh năm 2027?',
]
MIXED = [
    'Xin chào, học phí CNTT năm 2026 bao nhiêu?', 'Cảm ơn, cho tôi hỏi điểm chuẩn năm 2026.',
    'Hi, cho mình biết phương thức xét tuyển.', 'Hello, trường có bao nhiêu ngành?',
    'Chào bạn, cho tôi danh sách ngành tuyển sinh.', 'Cam on, hoc phi CNTT 2026?',
    'Xin chào! Tôi muốn tra cứu mã ngành 00123.', 'Cảm ơn anh, ngành Alpha học mấy năm?',
    'Chào chị, điều kiện miễn học phí là gì?', 'Thanks, what are the admission requirements?',
    'Thank you, học phí ngành Beta bao nhiêu?', 'Chào cô, trường có học bổng không?',
    'Tạm biệt, nhưng cho tôi hỏi hạn nộp hồ sơ.', 'Hi, năm học 2026–2027 có mấy học kỳ?',
    'Chào buổi sáng, các môn bắt buộc là gì?', 'Xin chào, không tính nhóm A thì có bao nhiêu?',
    'Chào bạn, ngành X và ngành Y khác nhau thế nào?', 'Cảm ơn nhé, giúp tôi so sánh hai phương thức.',
    'Xin chào, thông tin liên hệ trong tài liệu là gì?', 'Hello, chương trình 00007 có yêu cầu gì?',
]
CLARIFY = ['Tư vấn giúp tôi', 'tư vấn giúp mình', 'Ngành nào tốt?', 'giúp tôi',
           'help', 'Help me', 'Còn môn tự chọn?', 'Ngành đó học mấy năm?',
           'Còn năm 2025?', 'Cảm ơn, còn học phí?', 'Có', 'Không', 'Ok',
           'Không, tôi hỏi năm 2026', 'Cho tôi danh sách môn học gì đó']

CASES = ([(q, 'SOCIAL', False) for q in SOCIAL] + [(q, 'ASSISTANT_META', False) for q in META]
         + [(q, 'KNOWLEDGE', True) for q in KNOWLEDGE] + [(q, 'MIXED', True) for q in MIXED]
         + [(q, 'CLARIFICATION', False) for q in CLARIFY])
