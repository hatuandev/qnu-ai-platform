from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from qnu.domains.knowledge.index.schemas import SearchRequest
from qnu.domains.knowledge.metadata import MetadataFilter
from qnu.domains.rag.answer.schemas import AnswerResponse


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assistant_id: str = Field(min_length=1, max_length=64)
    title: str = Field("Hội thoại mới", min_length=1, max_length=160)
    document_ids: list[str] | None = Field(None, min_length=1, max_length=100)

    @field_validator("document_ids")
    @classmethod
    def validate_documents(cls, value: list[str] | None) -> list[str] | None:
        return SearchRequest.unique_documents(value)


class ConversationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    status: str = Field(pattern="^(active|archived)$")


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    collection_id: str
    assistant_id: str
    assistant_revision: int
    owner_ref: str
    title: str
    status: str
    document_ids: list[str] | None
    last_turn_no: int
    created_at: datetime
    updated_at: datetime


class TurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1, max_length=8000)
    expected_turn_no: int = Field(strict=True, ge=0)
    metadata_filter: MetadataFilter | None = None

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class TurnFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rating: Literal["like", "dislike"] | None = None
    reason: str | None = Field(default=None, max_length=500)


class DirectReply(BaseModel):
    id: str
    status: Literal["direct_reply"] = "direct_reply"
    route: Literal["greeting", "courtesy", "identity", "protected_request", "guardrail", "direct_chat"]
    answer: str


class TurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    conversation_id: str
    turn_no: int
    question: str
    resolved_question: str | None
    metadata_filter: MetadataFilter = Field(default_factory=MetadataFilter)
    history_turn_ids: list[str]
    status: str
    error_code: str | None
    result: AnswerResponse | DirectReply | None
    feedback: dict | None = None
    rewrite_trace: dict | None
    source_status: str = "current"
    source_status_reason: str | None = None
    created_at: datetime
    finished_at: datetime | None


class PromoteToBenchmarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_points: list[str] | None = None
    expected_behavior: str | None = None
    notes: str | None = Field(default=None, max_length=500)


class PromoteToBenchmarkResponse(BaseModel):
    turn_id: str
    question_id: str
    question: str
    already_exists: bool
    benchmark_file: str
    total_questions: int

