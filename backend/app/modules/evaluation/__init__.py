"""Evaluation Module for QNU AI Platform."""

from app.modules.evaluation.evaluator import RagasTM08Evaluator, tm08_evaluator
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
    EvaluationRunRequest,
    EvaluationRunResponse,
    TestCaseResponse,
)
from app.modules.evaluation.service import EvaluationService

evaluation_router = router

__all__ = [
    "DatasetResponse",
    "EvaluationDataset",
    "EvaluationResultItem",
    "EvaluationResultItemResponse",
    "EvaluationRun",
    "EvaluationRunRequest",
    "EvaluationRunResponse",
    "EvaluationService",
    "EvaluationTestCase",
    "RagasTM08Evaluator",
    "TestCaseResponse",
    "evaluation_router",
    "router",
    "tm08_evaluator",
]
