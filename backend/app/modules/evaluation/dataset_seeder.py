"""Default Benchmark Datasets for Continuous Quality Evaluation."""

from __future__ import annotations

from typing import Any

QNU_BENCHMARK_DATASETS: list[dict[str, Any]] = [
    {
        "id": "qnu_admissions_benchmark",
        "name": "Bộ Kiểm thử RAG Tuyển sinh QNU (Chuẩn TM-08)",
        "description": "Bộ 100 câu hỏi tuyển sinh đại học chính quy ĐH Quy Nhơn đo lường độ trung thực và chống bịa đặt.",
        "assistant_code": "admissions_assistant",
        "test_cases": [
            {
                "id": "tc_001",
                "question": "Mã cơ sở đào tạo của Trường Đại học Quy Nhơn trong tuyển sinh là gì?",
                "ground_truth": "Mã cơ sở đào tạo của Trường Đại học Quy Nhơn trong tuyển sinh là DQN.",
                "expected_source": "Thông báo 1906/TB-ĐHQN",
                "keywords": ["mã cơ sở", "dqn", "quy nhơn"],
            },
            {
                "id": "tc_002",
                "question": "Địa chỉ chính thức của Trường Đại học Quy Nhơn trong thông tin tuyển sinh là ở đâu?",
                "ground_truth": "Địa chỉ ghi trong thông báo tuyển sinh là 170 An Dương Vương, Quy Nhơn, Bình Định.",
                "expected_source": "Thông báo 1906/TB-ĐHQN",
                "keywords": ["170 an dương vương", "quy nhơn"],
            },
            {
                "id": "tc_003",
                "question": "Số điện thoại hotline tư vấn tuyển sinh chính thức của Trường ĐH Quy Nhơn là số nào?",
                "ground_truth": "Hotline tư vấn tuyển sinh chính thức của Trường là 0256.3846.156 hoặc 1800.55.88.49.",
                "expected_source": "Thông báo 1906/TB-ĐHQN",
                "keywords": ["0256.3846.156", "hotline", "tuyển sinh"],
            },
            {
                "id": "tc_004",
                "question": "Trang thông tin điện tử (website) chính thức của Trường Đại học Quy Nhơn là gì?",
                "ground_truth": "Trang thông tin điện tử của Trường Đại học Quy Nhơn là https://qnu.edu.vn.",
                "expected_source": "Thông báo 1906/TB-ĐHQN",
                "keywords": ["qnu.edu.vn", "website"],
            },
            {
                "id": "tc_005",
                "question": "Ngành Công nghệ thông tin (mã ngành 7480201) xét tuyển những tổ hợp môn nào?",
                "ground_truth": "Ngành Công nghệ thông tin xét tuyển các tổ hợp: A00 (Toán, Lý, Hóa), A01 (Toán, Lý, Anh), D01 (Toán, Văn, Anh), D07 (Toán, Hóa, Anh).",
                "expected_source": "Thông báo 1906/TB-ĐHQN",
                "keywords": ["7480201", "a00", "a01", "d01", "công nghệ thông tin"],
            },
        ],
    },
    {
        "id": "qnu_regulations_benchmark",
        "name": "Bộ Kiểm thử Quy chế Học vụ & Khảo thí QNU",
        "description": "Tập câu hỏi thẩm định tính tuân thủ quy chế đào tạo tín chỉ, chuẩn đầu ra và kỷ luật sinh viên.",
        "assistant_code": "regulations_assistant",
        "test_cases": [
            {
                "id": "tc_reg_001",
                "question": "Điều kiện để sinh viên được xét cấp học bổng khuyến khích học tập là gì?",
                "ground_truth": "Sinh viên phải có điểm trung bình chung học kỳ từ loại Khá trở lên và điểm rèn luyện đạt loại Tốt trở lên, không bị kỷ luật từ mức khiển trách.",
                "expected_source": "Quy chế Đào tạo Tín chỉ ĐHQN",
                "keywords": ["học bổng", "điểm trung bình", "rèn luyện tốt"],
            },
            {
                "id": "tc_reg_002",
                "question": "Sinh viên được cảnh báo học tập khi rơi vào các trường hợp nào?",
                "ground_truth": "Bị cảnh báo học tập nếu điểm trung bình học kỳ dưới 1.0 đối với học kỳ đầu, hoặc dưới 1.2 đối với các học kỳ tiếp theo.",
                "expected_source": "Quy chế Đào tạo Tín chỉ ĐHQN",
                "keywords": ["cảnh báo học tập", "điểm trung bình"],
            },
        ],
    },
]
