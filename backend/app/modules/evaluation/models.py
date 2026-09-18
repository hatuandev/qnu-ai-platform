"""SQLAlchemy Models for Continuous Evaluation (Ragas TM-08 Standard)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class EvaluationDataset(Base):
    """Benchmark evaluation dataset containing ground truth Q&A pairs."""

    __tablename__ = "evaluation_datasets"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    assistant_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    total_test_cases: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvaluationTestCase(Base):
    """Single benchmark question with reference answer and verification criteria."""

    __tablename__ = "evaluation_test_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    ground_truth: Mapped[str] = mapped_column(Text, nullable=False)
    expected_source: Mapped[str] = mapped_column(String(255), default="")
    keywords: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EvaluationRun(Base):
    """Evaluation execution session recording aggregate TM-08 metrics."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    dataset_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    assistant_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="running")  # running, completed, failed
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    passed_cases: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0)

    # Core Ragas TM-08 Metrics (thresholds: faith>=0.90, rel>=0.85, prec>=0.80)
    faithfulness_avg: Mapped[float] = mapped_column(Float, default=0.0)
    answer_relevance_avg: Mapped[float] = mapped_column(Float, default=0.0)
    context_precision_avg: Mapped[float] = mapped_column(Float, default=0.0)
    meets_tm08_standard: Mapped[bool] = mapped_column(Boolean, default=False)

    metadata_info: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_eval_run_assistant_created", "assistant_code", "created_at"),
    )


class EvaluationResultItem(Base):
    """Granular metric scores for a single question evaluation."""

    __tablename__ = "evaluation_result_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    test_case_id: Mapped[str] = mapped_column(String(36), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    generated_answer: Mapped[str] = mapped_column(Text, nullable=False)
    contexts: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # TM-08 Item Scores
    faithfulness_score: Mapped[float] = mapped_column(Float, default=0.0)
    answer_relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    context_precision_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_hallucinated: Mapped[bool] = mapped_column(Boolean, default=False)
    passed_all_criteria: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class KnowledgeGapRecord(Base):
    """Unanswered question triggering No-Answer Policy (knowledge deficiency)."""

    __tablename__ = "knowledge_gaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assistant_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    collection_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)  # pending, resolved, dismissed
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_gap_assistant_status", "assistant_code", "status"),
    )
