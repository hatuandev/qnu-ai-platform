"""Human-reviewed, source-bound annotations; unknown values never match a filter."""

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qnu.platform.errors import AppException


class MetadataValues(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    data_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    issued_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    effective_from: date | None = None
    effective_until: date | None = None
    program: str | None = Field(None, min_length=1, max_length=160)
    intake: str | None = Field(None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def interval(self):
        if (
            self.effective_from
            and self.effective_until
            and self.effective_from > self.effective_until
        ):
            raise ValueError("Khoảng hiệu lực không hợp lệ.")
        return self


class MetadataFilter(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    data_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    issued_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    effective_on: date | None = None
    program: str | None = Field(None, min_length=1, max_length=160)
    intake: str | None = Field(None, min_length=1, max_length=160)


class MetadataEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    citation: str = Field(min_length=3, max_length=200)
    quote: str = Field(min_length=1, max_length=2000)


class RetrievalAnnotation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str = Field(min_length=1, max_length=260)
    values: MetadataValues
    evidence: list[MetadataEvidence] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.values.model_dump(exclude_none=True):
            raise ValueError("Annotation cần ít nhất một giá trị có căn cứ.")
        if self.target == "document" and any(
            (self.values.data_year, self.values.program, self.values.intake)
        ):
            raise ValueError("Năm dữ liệu/ngành/đợt phải gắn đoạn hoặc hàng/ô cụ thể.")
        return self


def _invalid(message: str) -> AppException:
    return AppException(message, code="retrieval_metadata_invalid", status_code=422)


def target_refs(content: dict, target: str) -> set[str]:
    if target == "document":
        return set(content["citations"])
    paragraph = re.fullmatch(r"paragraph:(\d+):(\d+)", target)
    if paragraph:
        try:
            section, index = map(int, paragraph.groups())
            return set(content["sections"][section]["paragraphs"][index]["citations"])
        except IndexError:
            raise _invalid("Annotation trỏ đến đoạn không tồn tại.") from None
    table = re.fullmatch(r"table:(.+):row:(\d+)(?::column:(\d+))?", target)
    if table:
        citation, row, column = table.groups()
        entry = next((t for t in content["source_tables"] if t["citation"] == citation), None)
        try:
            cells = entry["table"]["rows"][int(row)] if entry else []
            if column is not None:
                cells = [cells[int(column)]]
            if not cells:
                raise IndexError
        except IndexError:
            raise _invalid("Annotation trỏ đến hàng/ô không tồn tại.") from None
        return {citation, *[citation.split(":", 1)[0] + ":" + c["evidence_id"] for c in cells]}
    raise _invalid("Target phải là document, paragraph:s:p hoặc table:citation:row:r[:column:c].")


def validate_annotations(annotations: list[dict], content: dict, documents: list[dict]) -> None:
    texts = {}
    for document in documents:
        prefix = document["ocr_run_id"] + ":"
        for page in document["pages"]:
            for block in page["blocks"]:
                texts[prefix + block["evidence_id"]] = block["text"]
                for row in (block.get("table") or {}).get("rows", []):
                    for cell in row:
                        texts[prefix + cell["evidence_id"]] = cell["text"]
    seen = set()
    global_values = next((a["values"] for a in annotations if a["target"] == "document"), {})
    for raw in annotations:
        item = RetrievalAnnotation.model_validate(raw)
        if item.target == "document" and len(documents) != 1:
            raise _invalid("Bản biên soạn nhiều nguồn cần metadata ở từng đoạn/hàng/ô.")
        if item.target in seen:
            raise _invalid("Target metadata bị trùng; gộp các trường vào một annotation.")
        seen.add(item.target)
        refs = target_refs(content, item.target)
        runs = {r.split(":", 1)[0] for r in refs}
        for evidence in item.evidence:
            if (
                evidence.citation not in content["citations"]
                or evidence.citation.split(":", 1)[0] not in runs
                or evidence.quote not in texts.get(evidence.citation, "")
            ):
                raise _invalid("Trích đoạn metadata không thuộc nguồn đã ghim của target.")
        quotes = "\n".join(e.quote for e in item.evidence).casefold()
        for key, value in item.values.model_dump(mode="json", exclude_none=True).items():
            if key in global_values and global_values[key] != value:
                raise _invalid("Metadata của target mâu thuẫn với metadata toàn văn bản.")
            alternatives = [str(value)]
            if key.startswith("effective_"):
                day = date.fromisoformat(value)
                alternatives += [day.strftime("%d/%m/%Y"), f"{day.day}/{day.month}/{day.year}"]
            found = any(v.casefold() in quotes for v in alternatives)
            if key.endswith("_year"):
                found = re.search(r"(?<!\d)" + str(value) + r"(?!\d)", quotes) is not None
            if not found:
                raise _invalid("Giá trị metadata cần xuất hiện trong trích đoạn nguồn.")


def chunk_metadata(annotations: list[dict], targets: set[str]) -> list[dict]:
    global_item = next((a for a in annotations if a["target"] == "document"), {})
    global_values = global_item.get("values", {})
    global_evidence = global_item.get("evidence", [])
    selected = [a for a in annotations if a["target"] in targets]
    return [
        {
            "target": a["target"],
            "values": {**global_values, **a["values"]},
            "evidence": [*global_evidence, *a["evidence"]],
        }
        for a in selected
    ] or (
        [{"target": "document", "values": global_values, "evidence": global_evidence}]
        if global_values
        else []
    )


def matches_metadata(structure: dict | None, scope: MetadataFilter) -> bool:
    wanted = scope.model_dump(mode="json", exclude_none=True)
    if not wanted:
        return True
    for annotation in (structure or {}).get("retrieval_metadata", []):
        values = annotation["values"]
        matches = True
        for key, value in wanted.items():
            if key == "effective_on":
                matches &= bool(
                    values.get("effective_from")
                    and values.get("effective_until")
                    and values["effective_from"] <= value <= values["effective_until"]
                )
            else:
                matches &= str(values.get(key, "")).casefold() == str(value).casefold()
        if matches:
            return True
    return False
