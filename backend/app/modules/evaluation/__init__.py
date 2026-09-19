"""Evaluation Module for QNU AI Platform."""

from app.modules.evaluation.evaluator import (
    BaseTM08Evaluator,
    HeuristicTM08Evaluator,
    LLMJudgeTM08Evaluator,
    RagasTM08Evaluator,
    get_evaluator,
    tm08_evaluator,
)
from app.modules.evaluation.models import (
    EvaluationDataset,
    EvaluationResultItem,
    EvaluationRun,
    EvaluationTestCase,
)
from app.modules.evaluation.router import router
from app.modules.evaluation.schemas import (
    DatasetResponse,
    EvaluationResultItemResponse,
    EvaluationRunDetailResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
    TestCaseResponse,
)
from app.modules.evaluation.service import EvaluationService

evaluation_router = router

__all__ = [
    "BaseTM08Evaluator",
    "DatasetResponse",
    "EvaluationDataset",
    "EvaluationResultItem",
    "EvaluationResultItemResponse",
    "EvaluationRun",
    "EvaluationRunDetailResponse",
    "EvaluationRunRequest",
    "EvaluationRunResponse",
    "EvaluationService",
    "EvaluationTestCase",
    "HeuristicTM08Evaluator",
    "LLMJudgeTM08Evaluator",
    "RagasTM08Evaluator",
    "TestCaseResponse",
    "evaluation_router",
    "get_evaluator",
    "router",
    "tm08_evaluator",
]
