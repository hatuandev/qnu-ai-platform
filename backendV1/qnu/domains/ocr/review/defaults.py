"""Persist and apply the system policy for automatic spelling checks."""

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from qnu.domains.ocr.review.text import leaf_units
from qnu.platform.database import Base


class SpellingDefaults(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", from_attributes=True)
    ocr: bool = True
    pdf_text: bool = False
    word_text: bool = False


class SpellingDefaultsRow(Base):
    __tablename__ = "ocr_spelling_defaults"
    __table_args__ = (CheckConstraint("id = 1", name="ck_ocr_spelling_defaults_singleton"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ocr: Mapped[bool] = mapped_column(Boolean)
    pdf_text: Mapped[bool] = mapped_column(Boolean)
    word_text: Mapped[bool] = mapped_column(Boolean)


async def read(db: AsyncSession) -> SpellingDefaults:
    row = await db.get(SpellingDefaultsRow, 1)
    return SpellingDefaults.model_validate(row) if row else SpellingDefaults()


async def save(db: AsyncSession, policy: SpellingDefaults) -> SpellingDefaults:
    values = policy.model_dump()
    statement = insert(SpellingDefaultsRow).values(id=1, **values)
    await db.execute(statement.on_conflict_do_update(index_elements=["id"], set_=values))
    await db.commit()
    return policy


def eligible_ids(document: dict, extension: str, policy: SpellingDefaults) -> set[str]:
    native_enabled = {".pdf": policy.pdf_text, ".docx": policy.word_text}.get(extension, False)
    pages = [
        {
            **page,
            "blocks": [
                block
                for block in page["blocks"]
                if (native_enabled if block.get("origin") == "native" else policy.ocr)
            ],
        }
        for page in document["pages"]
    ]
    return {unit.evidence_id for unit, _ in leaf_units({"pages": pages})}
