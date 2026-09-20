"""Golden Evaluation Benchmark Suite & Ragas TM-08 Quality Metrics Verification."""

from __future__ import annotations

from app.modules.evaluation.dataset_seeder import QNU_BENCHMARK_DATASETS
from app.modules.evaluation.evaluator import HeuristicTM08Evaluator
from app.modules.rag.citation_guard import citation_guard
from app.modules.rag.schemas import Citation


class TestGoldenBenchmarkDatasets:
    """Test suite verifying golden dataset schema integrity and coverage."""

    def test_implementation_plan_benchmark_exists_and_valid(self):
        dataset = next(
            (d for d in QNU_BENCHMARK_DATASETS if d["id"] == "qnu_implementation_plan_benchmark"),
            None,
        )
        assert dataset is not None
        assert len(dataset["test_cases"]) >= 15

        task_codes = ["1.1", "1.3", "6.8", "11.5"]
        found_tasks = set()
        for tc in dataset["test_cases"]:
            assert "id" in tc
            assert "question" in tc
            assert "ground_truth" in tc
            assert "keywords" in tc
            assert len(tc["keywords"]) > 0
            for code in task_codes:
                if code in tc["question"] or code in tc["ground_truth"]:
                    found_tasks.add(code)

        assert found_tasks == set(task_codes), f"Missing task codes: {set(task_codes) - found_tasks}"

    def test_admissions_2026_benchmark_coverage(self):
        plan_dataset = next(
            (d for d in QNU_BENCHMARK_DATASETS if d["id"] == "qnu_implementation_plan_benchmark"),
            None,
        )
        assert plan_dataset is not None

        # Verify admissions 2026 key records (IELTS/VSTEP, AI 7480107, Automotive 7510205)
        all_text = " ".join(
            tc["question"] + " " + tc["ground_truth"] for tc in plan_dataset["test_cases"]
        ).lower()
        assert "7480107" in all_text, "Mã ngành Trí tuệ nhân tạo 7480107 must be in golden benchmark"
        assert "ielts" in all_text, "Chứng chỉ IELTS must be in golden benchmark"
        assert "vstep" in all_text, "Chứng chỉ VSTEP must be in golden benchmark"
        assert "7510205" in all_text, "Mã ngành Công nghệ kỹ thuật ô tô 7510205 must be in golden benchmark"


class TestRagasTM08EvaluationMetrics:
    """Test suite executing TM-08 heuristic evaluation on official benchmark questions."""

    def setup_method(self):
        self.evaluator = HeuristicTM08Evaluator()

    def test_exact_fact_task_6_8_evaluation_scores(self):
        query = "Nhiệm vụ 6.8 trong Kế hoạch triển khai năm học 2025-2026 có nội dung gì, ai chủ trì và hạn hoàn thành khi nào?"
        ground_truth = (
            "Nhiệm vụ 6.8: Nâng cấp hạ tầng công nghệ thông tin và chuyển đổi số phục vụ quản trị đại học; "
            "đơn vị chủ trì là Trung tâm CNTT, hạn hoàn thành tháng 12/2025."
        )
        contexts = [
            (
                "### Nhiệm vụ 6.8\n"
                "- Nhóm công tác: Công tác chuyển đổi số và công nghệ thông tin\n"
                "- Nội dung: Nâng cấp hạ tầng công nghệ thông tin và chuyển đổi số phục vụ quản trị đại học\n"
                "- Đơn vị chủ trì: Trung tâm CNTT\n"
                "- Đơn vị phối hợp: Các khoa, phòng ban liên quan\n"
                "- Thời gian hoàn thành: Tháng 12/2025\n"
                "- Sản phẩm kết quả: Hệ thống hạ tầng CNTT nâng cấp hoàn thành\n"
                "- Nguồn: Trang 16"
            )
        ]
        answer = (
            "Dựa trên Kế hoạch triển khai nhiệm vụ năm học 2025-2026 của Trường ĐH Quy Nhơn:\n\n"
            "- **Nội dung nhiệm vụ**: Nâng cấp hạ tầng công nghệ thông tin và chuyển đổi số phục vụ quản trị đại học.\n"
            "- **Đơn vị chủ trì**: Trung tâm CNTT.\n"
            "- **Thời gian hoàn thành**: Tháng 12/2025.\n\n"
            "Thông tin được trích dẫn chính xác từ Phụ lục Kế hoạch nhiệm vụ, Trang 16."
        )
        keywords = ["nhiệm vụ 6.8", "trung tâm cntt", "chuyển đổi số", "tháng 12/2025"]

        res = self.evaluator.evaluate_item(
            query=query,
            ground_truth=ground_truth,
            answer=answer,
            contexts=contexts,
            keywords=keywords,
        )

        assert res["faithfulness"] >= 0.90, f"Faithfulness {res['faithfulness']} must be >= 0.90"
        assert res["answer_relevance"] >= 0.85, f"Answer Relevance {res['answer_relevance']} must be >= 0.85"
        assert res["context_precision"] >= 0.80, f"Context Precision {res['context_precision']} must be >= 0.80"
        assert res["passed"] is True

    def test_exact_fact_ielts_conversion_evaluation_scores(self):
        query = "Chứng chỉ IELTS 6.0 được quy đổi thành bao nhiêu điểm trong xét tuyển năm 2026 của QNU?"
        ground_truth = "Theo Bảng quy đổi chứng chỉ tiếng Anh quốc tế của Trường ĐH Quy Nhơn, chứng chỉ IELTS 6.0 được quy đổi thành 8.5 điểm trên thang điểm 10."
        contexts = [
            "Bảng quy đổi chứng chỉ ngoại ngữ tiếng Anh quốc tế sang thang điểm 10: IELTS 5.0 -> 7.0 điểm, IELTS 5.5 -> 7.5 điểm, IELTS 6.0 -> 8.5 điểm, IELTS 6.5 -> 9.0 điểm, IELTS 7.0 trở lên -> 10.0 điểm. Nguồn: Trang 9."
        ]
        answer = "Chào bạn! Theo Bảng quy đổi chứng chỉ tiếng Anh của Trường ĐH Quy Nhơn (Trang 9), chứng chỉ IELTS 6.0 được quy đổi thành 8.5 điểm trên thang điểm 10."
        keywords = ["ielts 6.0", "8.5 điểm", "thang điểm 10"]

        res = self.evaluator.evaluate_item(
            query=query,
            ground_truth=ground_truth,
            answer=answer,
            contexts=contexts,
            keywords=keywords,
        )

        assert res["faithfulness"] >= 0.90
        assert res["answer_relevance"] >= 0.85
        assert res["context_precision"] >= 0.80
        assert res["passed"] is True

    def test_no_answer_policy_evaluation_compliance(self):
        """When query asks for out-of-scope / missing fact, safe refusal must score 100% faithfulness."""
        query = "Trường Đại học Quy Nhơn có kế hoạch xây dựng cơ sở 2 tại địa điểm nào trong năm 2026?"
        ground_truth = "Thông tin này hiện chưa có trong văn bản Kế hoạch triển khai nhiệm vụ chính thức của trường. Vui lòng liên hệ bộ phận chức năng để được giải đáp."
        contexts: list[str] = []
        answer = (
            "Chào bạn! Thông tin về kế hoạch xây dựng cơ sở 2 hiện chưa có trong tài liệu chính thức "
            "của Trường Đại học Quy Nhơn. Vui lòng liên hệ ban tư vấn hoặc hotline 0256.3846.156 để được giải đáp."
        )

        assert self.evaluator.is_refusal_answer(answer) is True
        res = self.evaluator.evaluate_item(
            query=query,
            ground_truth=ground_truth,
            answer=answer,
            contexts=contexts,
        )
        assert res["faithfulness"] == 1.0, "Refusal answer complying with No-Answer policy must yield 100% faithfulness"
        assert res["passed"] is True


class TestCitationGroundingAudit:
    """Test suite verifying claim-level citation audit and evidence grounding."""

    def test_audit_claim_citations_with_valid_citations(self):
        answer = "Ngành Trí tuệ nhân tạo (mã ngành 7480107) có chỉ tiêu dự kiến là 60 sinh viên."
        citations = [
            Citation(
                source_id="doc_ts_2026",
                title="Danh mục ngành tuyển sinh 2026",
                section="Trí tuệ nhân tạo",
                page_number=6,
                source_pages=[6],
                entity_key="program:7480107",
                quote="Mã ngành 7480107, Trí tuệ nhân tạo, Chỉ tiêu: 60 sinh viên",
            )
        ]
        facts_used = [{"entity": "Trí tuệ nhân tạo", "attr": "expected_quota", "val": "60"}]

        audit = citation_guard.audit_claim_citations(answer, citations, facts_used)
        assert audit["is_grounded"] is True
        assert audit["citation_coverage"] == 1.0
        assert audit["has_citations"] is True
        assert audit["facts_count"] == 1
        assert len(audit["issues"]) == 0

    def test_audit_claim_citations_detects_ungrounded_answer(self):
        answer = "Học phí của ngành Trí tuệ nhân tạo là 25 triệu đồng mỗi kỳ học."
        citations = []
        facts_used = []

        audit = citation_guard.audit_claim_citations(answer, citations, facts_used)
        assert audit["is_grounded"] is False
        assert len(audit["issues"]) > 0
        assert "không có bất kỳ trích dẫn" in audit["issues"][0]
