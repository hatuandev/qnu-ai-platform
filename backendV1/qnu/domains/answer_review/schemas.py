"""Contracts for assistant answer tests and their human review labels."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from qnu.domains.rag.answer.schemas import AnswerResponse

AnswerLabel = Literal["correct", "missing", "wrong_source", "wrong_year"]


class AnswerReviewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    questions: list[str] = Field(min_length=1, max_length=3)

    @field_validator("questions")
    @classmethod
    def valid_questions(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            question = value.strip()
            if not question:
                raise ValueError("Câu hỏi không được rỗng.")
            if len(question) > 8000:
                raise ValueError("Câu hỏi vượt quá 8000 ký tự.")
            if question in cleaned:
                raise ValueError("Câu hỏi bị lặp trong cùng bộ kiểm thử.")
            cleaned.append(question)
        return cleaned


class AnswerReviewLabelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: AnswerLabel | None = None
    note: str = Field("", max_length=2000)

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str) -> str:
        return value.strip()


class AnswerReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    review_id: str
    ordinal: int
    question: str
    status: Literal["answered", "insufficient_evidence", "failed", "uncertain"]
    error_code: str | None
    result: AnswerResponse | None
    index_run_id: str | None
    generation: int | None
    label: AnswerLabel | None
    label_note: str | None
    labelled_by: str | None
    labelled_at: datetime | None
    created_at: datetime
    finished_at: datetime | None


class AnswerReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    collection_id: str
    assistant_id: str
    assistant_revision: int
    requested_by: str
    question_count: int
    status: Literal["running", "completed", "failed", "uncertain"]
    error_code: str | None
    created_at: datetime
    finished_at: datetime | None
    items: list[AnswerReviewItemResponse] = Field(default_factory=list)
