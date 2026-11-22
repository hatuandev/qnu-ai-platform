"""Admin and anonymous contracts for public chatbot releases.

Public DTOs carry presentation data only: no workspace, collection, assistant,
chunk or document identifiers cross the anonymous boundary.
"""

from datetime import date, datetime
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

SLUG_PATTERN = r"^[a-z0-9](?:[a-z0-9-]{1,58}[a-z0-9])$"


def normalize_origin(raw: str) -> str:
    text = raw.strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            f"Tên miền '{text}' không hợp lệ. Phải bắt đầu bằng http:// hoặc https:// (VD: https://qnu.edu.vn)."
        )
    return f"{parsed.scheme}://{parsed.netloc}".lower()


class PublicationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(min_length=3, max_length=60, pattern=SLUG_PATTERN)
    display_name: str = Field(min_length=1, max_length=160)
    welcome_message: str = Field("", max_length=2000)
    starter_prompts: list[str] = Field(default_factory=list, max_length=6)
    allowed_embed_origins: list[str] = Field(default_factory=list, max_length=50)
    max_turns_per_session: int = Field(15, strict=True, ge=1, le=100)
    daily_token_budget: int | None = Field(None, strict=True, ge=1000)
    enabled: bool = False

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("display_name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Tên hiển thị không được rỗng.")
        return value.strip()

    @field_validator("starter_prompts")
    @classmethod
    def clean_prompts(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            text = raw.strip()
            if not text:
                continue
            if len(text) > 160:
                raise ValueError("Câu hỏi gợi ý tối đa 160 ký tự.")
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(text)
        return cleaned

    @field_validator("allowed_embed_origins")
    @classmethod
    def clean_origins(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in values:
            origin = normalize_origin(raw)
            if not origin or origin in seen:
                continue
            seen.add(origin)
            cleaned.append(origin)
        return cleaned


class PublicationUpdate(PublicationConfig):
    expected_revision: int | None = Field(None, strict=True, ge=1)


class PublicationResponse(BaseModel):
    configured: bool
    enabled: bool
    slug: str | None
    display_name: str
    welcome_message: str
    starter_prompts: list[str]
    allowed_embed_origins: list[str] = Field(default_factory=list)
    max_turns_per_session: int
    daily_token_budget: int | None
    revision: int
    updated_by: str | None
    updated_at: datetime | None
    public_path: str | None
    system_enabled: bool
    readiness: str


class PublicChatbotInfo(BaseModel):
    display_name: str
    welcome_message: str
    starter_prompts: list[str]
    allowed_embed_origins: list[str] = Field(default_factory=list)
    max_turns_per_session: int
    available: bool
    unavailable_reason: str | None


class PublicChatbotSummary(BaseModel):
    slug: str
    display_name: str
    welcome_message: str
    available: bool
    unavailable_reason: str | None


class PublicChatbotListResponse(BaseModel):
    chatbots: list[PublicChatbotSummary]


class PublicSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    website: str | None = Field(default=None, max_length=200)


class PublicSessionResponse(BaseModel):
    session_id: str
    expires_in_seconds: int
    max_turns: int
    turns_remaining: int


class PublicTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=16, max_length=64)
    question: str = Field(min_length=1, max_length=1000)
    website: str | None = Field(default=None, max_length=200)

    @field_validator("question")
    @classmethod
    def nonblank_question(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Câu hỏi không được rỗng.")
        return text


class PublicCitation(BaseModel):
    index: int
    title: str
    page: int | None


class PublicTurnResponse(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    answer: str | None
    message: str | None
    citations: list[PublicCitation]
    turns_remaining: int


class PublicationStatDay(BaseModel):
    day: date
    sessions: int
    turns: int
    insufficient_turns: int
    error_turns: int
    tokens: int


class PublicationStatTotals(BaseModel):
    sessions: int
    turns: int
    insufficient_turns: int
    error_turns: int
    tokens: int


class PublicationUnansweredQuestion(BaseModel):
    question: str
    times_asked: int
    last_asked_at: datetime


class PublicationStatsResponse(BaseModel):
    configured: bool
    days: int
    totals: PublicationStatTotals
    daily: list[PublicationStatDay]
    budget_limit: int | None
    budget_used_today: int
    top_questions: list[PublicationUnansweredQuestion]
