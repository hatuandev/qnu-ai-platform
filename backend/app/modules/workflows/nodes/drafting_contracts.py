"""Typed contracts shared by the adaptive administrative drafting nodes."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

DocumentBlockType = Literal[
    "paragraph",
    "section",
    "bullet_list",
    "numbered_list",
    "attachment_note",
    "table",
]
SemanticRole = Literal[
    "basis",
    "rationale",
    "proposal",
    "objective",
    "requirements",
    "schedule",
    "responsibilities",
    "closing",
    "announcement",
    "decision",
    "implementation",
    "resources",
    "effectiveness",
    "attachments",
    "other",
]

_PLACEHOLDER_RE = re.compile(r"\[\s*(?:BỔ SUNG|CHƯA CẤP)[^\]]*\]", re.IGNORECASE)


def normalize_text(value: Any) -> str:
    """Return clean NFC text without inventing a value for non-text inputs."""
    if not isinstance(value, str):
        return ""
    return unicodedata.normalize("NFC", value).strip()


class DraftBlock(BaseModel):
    """One semantic block in a document body, independent from DOCX layout."""

    type: DocumentBlockType
    role: SemanticRole
    heading: str | None = Field(default=None, max_length=200)
    content: str | None = Field(default=None, max_length=12000)
    items: list[str] = Field(default_factory=list, max_length=40)
    columns: list[str] = Field(default_factory=list, max_length=12)
    rows: list[list[str]] = Field(default_factory=list, max_length=100)
    source_refs: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def validate_payload(self) -> DraftBlock:
        self.heading = normalize_text(self.heading) or None
        self.content = normalize_text(self.content) or None
        self.items = [text for item in self.items if (text := normalize_text(item))]
        self.columns = [text for item in self.columns if (text := normalize_text(item))]
        self.rows = [
            [normalize_text(cell) for cell in row]
            for row in self.rows
            if isinstance(row, list)
        ]
        self.source_refs = [
            text for item in self.source_refs if (text := normalize_text(item))
        ]
        if not self.content and not self.items and not self.rows:
            raise ValueError("Mỗi block phải có content hoặc items.")
        if self.type in {"bullet_list", "numbered_list"} and not self.items:
            raise ValueError("Block danh sách phải có ít nhất một item.")
        if self.type == "table":
            if not self.columns or not self.rows:
                raise ValueError("Block bảng phải có columns và rows.")
            if any(len(row) != len(self.columns) for row in self.rows):
                raise ValueError("Mỗi hàng bảng phải có cùng số ô với columns.")
        return self

    def plain_text(self) -> str:
        cells = [cell for row in self.rows for cell in row]
        parts = [
            self.heading or "",
            self.content or "",
            *self.items,
            *self.columns,
            *cells,
        ]
        return " ".join(part for part in parts if part).strip()


class DocumentAst(BaseModel):
    """LLM output contract consumed by quality, validation, and render nodes."""

    version: Literal["document_ast.v1"] = "document_ast.v1"
    title: str = Field(min_length=3, max_length=300)
    structure_profile: Literal[
        "adaptive",
        "reference_led",
        "compact_narrative",
        "detailed_plan",
    ] = "adaptive"
    blocks: list[DraftBlock] = Field(min_length=1, max_length=24)
    missing_fields: list[str] = Field(default_factory=list, max_length=40)

    @model_validator(mode="after")
    def normalize_values(self) -> DocumentAst:
        self.title = normalize_text(self.title)
        self.missing_fields = [
            text for item in self.missing_fields if (text := normalize_text(item))
        ]
        return self


def block_is_substantive(block: DraftBlock) -> bool:
    """Check semantic substance after removing visible placeholder tokens."""
    text = _PLACEHOLDER_RE.sub(" ", block.plain_text())
    tokens = re.findall(r"\w+", text, flags=re.UNICODE)
    return len(tokens) >= 4


def semantic_quality_issues(
    ast: DocumentAst,
    required_roles: list[str],
) -> list[dict[str, str]]:
    """Validate semantic obligations without rewarding artificial document length."""
    covered_roles = {
        block.role for block in ast.blocks if block_is_substantive(block)
    }
    issues = [
        {
            "code": "missing_semantic_role",
            "role": role,
            "message": f"Phần nội dung chưa đáp ứng nghĩa bắt buộc: {role}.",
        }
        for role in required_roles
        if role not in covered_roles
    ]
    if not any(block_is_substantive(block) for block in ast.blocks):
        issues.append(
            {
                "code": "empty_document_body",
                "role": "body",
                "message": "Phần thân chưa có nội dung nghiệp vụ đủ nghĩa.",
            }
        )
    return issues


def render_document_blocks(blocks: list[DraftBlock]) -> str:
    """Render the semantic AST into the plain-text body expected by DOCX templates."""
    rendered: list[str] = []
    for block in blocks:
        if block.heading:
            rendered.append(block.heading)
        if block.content:
            rendered.append(block.content)
        if block.items:
            if block.type == "numbered_list":
                rendered.append(
                    "\n".join(f"{index}. {item}" for index, item in enumerate(block.items, 1))
                )
            else:
                rendered.append("\n".join(f"- {item}" for item in block.items))
        if block.type == "table" and block.columns and block.rows:
            rendered.append(" | ".join(block.columns))
            rendered.extend(" | ".join(row) for row in block.rows)
    return "\n\n".join(part for part in rendered if part).strip()
