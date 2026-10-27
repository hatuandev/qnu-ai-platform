"""Capacity declarations are optional; unknown never means unlimited or verified."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PositiveTokens = Annotated[int, Field(strict=True, gt=0)]


class OcrPageInputBudget(BaseModel):
    """Operator-declared conservative bound for images within an explicit envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    max_image_width: PositiveTokens
    max_image_height: PositiveTokens
    input_tokens_upper_bound: PositiveTokens
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ModelTokenLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # Set shared context only when the endpoint declares a shared envelope.
    # Independent input/output APIs can leave it unknown and specify both limits.
    context_window_tokens: PositiveTokens | None = None
    max_input_tokens: PositiveTokens | None = None
    max_output_tokens: PositiveTokens | None = None
    ocr_page_input: OcrPageInputBudget | None = None

    @model_validator(mode="after")
    def consistent_limits(self) -> ModelTokenLimits:
        if all(
            value is None
            for value in (self.context_window_tokens, self.max_input_tokens, self.max_output_tokens)
        ):
            raise ValueError("Cần khai báo ít nhất một giới hạn token đã biết.")
        if self.context_window_tokens is not None:
            for value in (self.max_input_tokens, self.max_output_tokens):
                if value is not None and value > self.context_window_tokens:
                    raise ValueError("Giới hạn riêng không được vượt context dùng chung.")
        return self


class ModelCapacity(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: Literal["unknown", "configured", "stale"]
    token_limits: ModelTokenLimits | None = None
    basis: Literal["operator_configured"] | None = None


class CapacitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    provider_id: str
    model_name: str
    token_limits: ModelTokenLimits
    basis: Literal["operator_configured"]
    configuration_hash: str


class RequestTokenBudget(BaseModel):
    model_config = ConfigDict(frozen=True)
    input_tokens: int
    reserve_tokens: int
    max_output_tokens: int
    total_reserved_tokens: int
