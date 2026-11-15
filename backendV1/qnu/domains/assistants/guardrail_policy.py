"""Assistant behavior policy; stored with the assistant config and off by default."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

GuardrailCategory = Literal["privacy", "other_school", "out_of_scope"]
GUARDRAIL_CATEGORIES: tuple[str, ...] = ("privacy", "other_school", "out_of_scope")


class GuardrailPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    categories: list[GuardrailCategory] = Field(default_factory=list)

    @field_validator("categories")
    @classmethod
    def unique_categories(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def category_when_enabled(self) -> "GuardrailPolicy":
        if self.enabled and not self.categories:
            raise ValueError("Bật guardrail cần chọn ít nhất một nhóm.")
        return self
