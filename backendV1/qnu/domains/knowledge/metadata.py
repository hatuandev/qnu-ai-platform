"""Human-reviewed, source-bound annotations; unknown values never match a filter."""

import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from qnu.domains.knowledge.source_sections import source_sections
from qnu.platform.errors import AppException

MetadataScalar = (
    Annotated[str, Field(strict=True, min_length=1, max_length=500)]
    | StrictBool
    | StrictInt
    | Annotated[float, Field(strict=True, allow_inf_nan=False)]
)
MetadataAttributes = Annotated[
    dict[Annotated[str, Field(min_length=1, max_length=80)], MetadataScalar],
    Field(min_length=1, max_length=20),
]


def same_attribute(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    return left == right


def merge_scope(base: dict, extra: dict) -> dict:
    scope = {**base, **extra}
    if "attributes" in scope:
        scope["attributes"] = {**(base.get("attributes") or {}), **(extra.get("attributes") or {})}
    return scope


def scope_conflicts(fixed: dict, requested: dict) -> bool:
    pinned = fixed.get("attributes") or {}
    return any(
        key in fixed and fixed[key] != value
        for key, value in requested.items()
        if key != "attributes"
    ) or any(
        key in pinned and not same_attribute(pinned[key], value)
        for key, value in requested.get("attributes", {}).items()
    )


class MetadataValues(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    data_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    issued_year: int | None = Field(None, strict=True, ge=1000, le=9999)
    effective_from: date | None = None
    effective_until: date | None = None
    program: str | None = Field(None, min_length=1, max_length=160)
    intake: str | None = Field(None, min_length=1, max_length=160)
    attributes: MetadataAttributes | None = None

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

    attributes: MetadataAttributes | None = Field(None, exclude_if=lambda value: value is None)


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
        if self.target.startswith("section:") and not self.target[8:]:
            raise ValueError("Annotation cần dẫn chứng tiêu đề mục.")
        if self.target == "document" and any(
            (self.values.data_year, self.values.program, self.values.intake)
        ):
            raise ValueError("Năm dữ liệu/ngành/đợt phải gắn đoạn hoặc hàng/ô cụ thể.")
        return self


def _invalid(message: str) -> AppException:
    return AppException(message, code="retrieval_metadata_invalid", status_code=422)


def target_refs(content: dict, target: str, outline: dict | None = None) -> set[str]:
    if target == "document":
        return set(content["citations"])
    if target.startswith("section:"):
        ref = target.removeprefix("section:")
        section = (outline or {}).get(ref)
        if section is None or section.citation != ref:
            raise _invalid("Annotation cần trỏ đến tiêu đề mục trong nguồn đã ghim.")
        return {ref}
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
    raise _invalid(
        "Target phải là document, section:citation, paragraph:s:p hoặc table:citation:row:r[:column:c]."
    )


def attribute_in_quote(label: str, value: str | float | bool, quote: str) -> bool:
    folded = quote.casefold()
    if label.casefold() not in folded:
        return False
    literal = re.escape(str(value).casefold())
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return re.search(r"(?<![\w.,])" + literal + r"(?!\w|[.,]\d)", folded) is not None
    return re.search(r"(?<!\w)" + literal + r"(?!\w)", folded) is not None


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
    outline = (
        source_sections(documents)
        if any(a["target"].startswith("section:") for a in annotations)
        else {}
    )
    seen = set()
    global_values = next((a["values"] for a in annotations if a["target"] == "document"), {})
    for raw in annotations:
        item = RetrievalAnnotation.model_validate(raw)
        if item.target == "document" and len(documents) != 1:
            raise _invalid("Bản biên soạn nhiều nguồn cần metadata ở từng đoạn/hàng/ô.")
        if item.target in seen:
            raise _invalid("Target metadata bị trùng; gộp các trường vào một annotation.")
        seen.add(item.target)
        refs = target_refs(content, item.target, outline)
        # A proof in the same OCR run is not necessarily a proof for this unit.
        # For parsed table rows/cells the table-wide text is also too broad.
        local_texts = texts
        table = re.fullmatch(r"table:(.+):row:(\d+)(?::column:(\d+))?", item.target)
        if table:
            table_ref = table.group(1)
            local_texts = {
                **texts,
                table_ref: "\n".join(texts.get(r, "") for r in sorted(refs - {table_ref})),
            }
        for evidence in item.evidence:
            if (
                evidence.citation not in content["citations"]
                or evidence.citation not in refs
                or evidence.quote not in texts.get(evidence.citation, "")
                or evidence.quote not in local_texts.get(evidence.citation, "")
            ):
                raise _invalid("Trích đoạn metadata không thuộc nguồn đã ghim của target.")
        quotes = "\n".join(e.quote for e in item.evidence).casefold()
        for key, value in item.values.model_dump(mode="json", exclude_none=True).items():
            if key != "attributes" and key in global_values and global_values[key] != value:
                raise _invalid("Metadata của target mâu thuẫn với metadata toàn văn bản.")
            if key == "attributes":
                for label, entry in value.items():
                    global_attributes = global_values.get("attributes", {})
                    if label in global_attributes and (
                        type(global_attributes[label]) is not type(entry)
                        or global_attributes[label] != entry
                    ):
                        raise _invalid("Thuộc tính mâu thuẫn với metadata toàn văn bản.")
                    if not any(attribute_in_quote(label, entry, e.quote) for e in item.evidence):
                        raise _invalid("Nhãn và giá trị metadata cần có trong trích đoạn nguồn.")
                continue
            alternatives = [str(value)]
            if key.startswith("effective_"):
                day = date.fromisoformat(value)
                alternatives += [
                    f"{d}{sep}{m}{sep}{day.year}"
                    for d in {str(day.day), f"{day.day:02d}"}
                    for m in {str(day.month), f"{day.month:02d}"}
                    for sep in ("/", "-")
                ] + [
                    f"ngày {d} tháng {m} năm {day.year}"
                    for d in {str(day.day), f"{day.day:02d}"}
                    for m in {str(day.month), f"{day.month:02d}"}
                ]
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
    result = []
    for item in selected:
        values = {**global_values, **item["values"]}
        if "attributes" in values:
            values["attributes"] = {
                **global_values.get("attributes", {}),
                **item["values"].get("attributes", {}),
            }
        result.append(
            {
                "target": item["target"],
                "values": values,
                "evidence": [*global_evidence, *item["evidence"]],
            }
        )
    return result or (
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
            if key == "attributes":
                current = values.get("attributes") or {}
                matches &= all(same_attribute(current.get(k), v) for k, v in value.items())
            elif key == "effective_on":
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
