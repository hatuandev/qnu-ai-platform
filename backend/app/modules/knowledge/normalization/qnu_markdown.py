"""QNU RAG Markdown Standard v1.0: models, deterministic renderer and validator.

The standard is defined in ``docs/quy_trinh/13_chuan_markdown_rag_v1.md``. This module
renders the standard from an already structured document model and validates the
result. It never reads source files, never calls a model and never guesses values.
"""

from __future__ import annotations

import json
import re
from collections.abc import Hashable
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row

QNU_MARKDOWN_SCHEMA = "qnu-rag-markdown/1.0"
QNU_BLOCK_TYPES = frozenset(
    {
        "section",
        "text",
        "list",
        "table",
        "table_row",
        "note",
        "code",
        "formula",
        "figure",
        "derived_index",
    }
)
QNU_REVIEW_STATUSES = frozenset({"unreviewed", "reviewed", "needs_review"})
QNU_CELL_STATES = frozenset(
    {"present", "blank", "not_stated", "not_applicable", "unreadable", "ambiguous"}
)
BODY_REQUIRED_TYPES = frozenset(
    {"section", "text", "list", "table_row", "note", "code", "formula"}
)

_OPEN_MARKER = "<!-- rag:block"
_CLOSE_MARKER = "<!-- /rag:block -->"
_FENCE_START = re.compile(r"^\s*(`{3,}|~{3,})")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PLACEHOLDER = re.compile(r"\{\{")


class QnuSourceLocation(BaseModel):
    """One real location in the source document; unknown parts stay null."""

    page: int | None = None
    page_label: str | None = None
    locator: str | None = None
    bbox: list[float] | None = None
    bbox_space: str | None = None


class QnuFieldValue(BaseModel):
    """Raw cell value with an explicit state; normalized stays null until verified."""

    raw: str = ""
    state: str = "present"
    normalized: Any | None = None


class QnuColumn(BaseModel):
    """Table column definition for the ``records`` representation."""

    id: str
    header_path: list[str] = Field(default_factory=list)


class QnuQualityFlag(BaseModel):
    """Structured warning attached to the affected block or cell."""

    code: str
    status: str = "unresolved"
    detail: str
    field_id: str | None = None
    related_block_ids: list[str] = Field(default_factory=list)


class QnuBlock(BaseModel):
    """One evidence block of the standard; ``body`` is Markdown content only."""

    id: str
    parent_id: str | None = None
    type: str
    source_locations: list[QnuSourceLocation] = Field(default_factory=list)
    source_label: str | None = None
    section_path: list[str] = Field(default_factory=list)
    context_refs: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    quality_flags: list[QnuQualityFlag] = Field(default_factory=list)
    body: str = ""
    # Machine-only fidelity data (for example exact Docling cells). Never rendered into
    # the Markdown block; kept in the JSON artifact so consumers can re-derive records.
    source_data: dict[str, Any] | None = None


class QnuSourceInfo(BaseModel):
    """Source file identity recorded in the frontmatter."""

    filename: str
    uri: str | None = None
    sha256: str | None = None
    page_count: int | None = None


class QnuStructuredDocument(BaseModel):
    """Structured document ready for rendering; no formatting decisions are stored here."""

    schema_version: str = QNU_MARKDOWN_SCHEMA
    title: str
    language: str = "vi"
    document_type: str | None = None
    source: QnuSourceInfo
    document_meta: dict[str, Any] = Field(default_factory=dict)
    blocks: list[QnuBlock] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class QnuIssue(BaseModel):
    """One validator finding with enough context to fix the file."""

    code: str
    detail: str
    block_id: str | None = None
    line: int | None = None


class ParsedQnuBlock(BaseModel):
    metadata: dict[str, Any]
    body: str
    line: int


class QnuParseResult(BaseModel):
    frontmatter: dict[str, Any] | None = None
    blocks: list[ParsedQnuBlock] = Field(default_factory=list)
    stray_lines: list[tuple[int, str]] = Field(default_factory=list)
    errors: list[QnuIssue] = Field(default_factory=list)
    warnings: list[QnuIssue] = Field(default_factory=list)


class QnuValidationReport(BaseModel):
    ok: bool = True
    errors: list[QnuIssue] = Field(default_factory=list)
    warnings: list[QnuIssue] = Field(default_factory=list)
    block_count: int = 0
    issues: list[QnuIssue] = Field(default_factory=list)

    def add_error(self, code: str, detail: str, block_id: str | None = None) -> None:
        self.errors.append(QnuIssue(code=code, detail=detail, block_id=block_id))
        self.ok = False

    def add_warning(self, code: str, detail: str, block_id: str | None = None) -> None:
        self.warnings.append(QnuIssue(code=code, detail=detail, block_id=block_id))


class _UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently keeping the last value."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        # Checked before the membership lookup so a complex key is a parse finding, not a TypeError.
        if not isinstance(key, Hashable):
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"unhashable key: {key!r}",
                key_node.start_mark,
            )
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key: {key}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


_PLAIN_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        # JSON strings are valid YAML double-quoted scalars and keep Unicode intact.
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    raise TypeError(f"Unsupported YAML scalar: {type(value).__name__}")


def _yaml_key(value: Any) -> str:
    text = str(value)
    return text if _PLAIN_KEY.match(text) else _yaml_scalar(text)


def _emit_mapping(mapping: dict[Any, Any], indent: int, lines: list[str]) -> None:
    for key, value in mapping.items():
        prefix = " " * indent + f"{_yaml_key(key)}:"
        if isinstance(value, dict):
            if value:
                lines.append(prefix)
                _emit_mapping(value, indent + 2, lines)
            else:
                lines.append(prefix + " {}")
        elif isinstance(value, list):
            if value:
                lines.append(prefix)
                _emit_sequence(value, indent + 2, lines)
            else:
                lines.append(prefix + " []")
        else:
            lines.append(prefix + " " + _yaml_scalar(value))


def _emit_sequence(sequence: list[Any], indent: int, lines: list[str]) -> None:
    for value in sequence:
        prefix = " " * indent + "-"
        if isinstance(value, dict) and value:
            sub: list[str] = []
            _emit_mapping(value, indent + 2, sub)
            sub[0] = prefix + " " + sub[0][indent + 2 :]
            lines.extend(sub)
        elif isinstance(value, list):
            if value:
                lines.append(prefix)
                _emit_sequence(value, indent + 2, lines)
            else:
                lines.append(prefix + " []")
        elif isinstance(value, dict):
            lines.append(prefix + " {}")
        else:
            lines.append(prefix + " " + _yaml_scalar(value))


def dump_qnu_yaml(data: dict[str, Any]) -> str:
    """Deterministic YAML for frontmatter and block metadata (plain keys, quoted strings)."""
    lines: list[str] = []
    _emit_mapping(data, 0, lines)
    text = "\n".join(lines) + "\n"
    # A comment cannot contain its own terminator; the YAML escapes decode to the original text.
    return text.replace("<!--", "<\\u0021--").replace("-->", "--\\u003e")


def _location_dict(location: QnuSourceLocation) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "page": location.page,
        "page_label": location.page_label,
        "locator": location.locator,
    }
    if location.bbox is not None:
        payload["bbox"] = list(location.bbox)
        payload["bbox_space"] = location.bbox_space
    return payload


def _flag_dict(flag: QnuQualityFlag) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": flag.code, "status": flag.status, "detail": flag.detail}
    if flag.field_id is not None:
        payload["field_id"] = flag.field_id
    if flag.related_block_ids:
        payload["related_block_ids"] = list(flag.related_block_ids)
    return payload


def _escape_metadata_strings(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        if "{{" in value:
            return value.replace("{{", "&#123;&#123;"), True
        return value, False
    if isinstance(value, dict):
        changed = False
        result: dict[Any, Any] = {}
        for key, item in value.items():
            new_item, item_changed = _escape_metadata_strings(item)
            result[key] = new_item
            changed = changed or item_changed
        return result, changed
    if isinstance(value, list):
        changed = False
        result_list: list[Any] = []
        for item in value:
            new_item, item_changed = _escape_metadata_strings(item)
            result_list.append(new_item)
            changed = changed or item_changed
        return result_list, changed
    return value, False


def escape_template_braces(text: str) -> tuple[str, bool]:
    """Escape source text that looks like a template placeholder outside fenced code."""
    if "{{" not in text:
        return text, False
    lines: list[str] = []
    fence: str | None = None
    changed = False
    for line in text.split("\n"):
        if fence is None:
            opened = _fence_open(line)
            if opened is not None:
                fence = opened
            elif "{{" in line:
                line = line.replace("{{", "&#123;&#123;")
                changed = True
        elif _fence_close(line, fence):
            fence = None
        lines.append(line)
    return "\n".join(lines), changed


def _outside_fence_text(body: str) -> str:
    lines: list[str] = []
    fence: str | None = None
    for line in body.split("\n"):
        if fence is None:
            opened = _fence_open(line)
            if opened is not None:
                fence = opened
                continue
            lines.append(line)
        elif _fence_close(line, fence):
            fence = None
    return "\n".join(lines)


def render_qnu_block(block: QnuBlock) -> str:
    metadata: dict[str, Any] = {"id": block.id, "parent_id": block.parent_id, "type": block.type}
    if block.source_label is not None:
        metadata["source_label"] = block.source_label
    metadata["source_locations"] = [_location_dict(loc) for loc in block.source_locations]
    metadata["section_path"] = list(block.section_path)
    metadata["context_refs"] = list(block.context_refs)
    metadata["attributes"] = dict(block.attributes)
    metadata, metadata_escaped = _escape_metadata_strings(metadata)
    body = escape_block_markers(block.body.strip("\n"))
    body, body_escaped = escape_template_braces(body)
    flags = list(block.quality_flags)
    if (metadata_escaped or body_escaped) and not any(
        flag.code == "template_placeholder" for flag in flags
    ):
        flags.append(
            QnuQualityFlag(
                code="template_placeholder",
                detail=(
                    "Nguồn chứa chuỗi giống placeholder mẫu (ngoặc nhọn kép); "
                    "bản Markdown dùng HTML entity, JSON giữ nguyên văn."
                ),
            )
        )
    metadata["quality_flags"] = [_flag_dict(flag) for flag in flags]
    metadata_text = dump_qnu_yaml(metadata).rstrip("\n")
    parts = [_OPEN_MARKER, metadata_text, "-->"]
    if body:
        parts.append(body)
    parts.append(_CLOSE_MARKER)
    return "\n".join(parts)


def _fence_open(line: str) -> str | None:
    match = _FENCE_START.match(line)
    return match.group(1) if match else None


def _fence_close(line: str, fence: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped[0] != fence[0]:
        return False
    return stripped == fence[0] * len(stripped) and len(stripped) >= len(fence) and len(stripped) >= 3


def escape_block_markers(body: str) -> str:
    """Escape literal block markers outside fenced code so the block structure stays valid."""
    if _OPEN_MARKER not in body and "<!-- /rag:block" not in body:
        return body
    lines: list[str] = []
    fence: str | None = None
    for line in body.split("\n"):
        if fence is None:
            opened = _fence_open(line)
            if opened is not None:
                fence = opened
            else:
                line = line.replace(_OPEN_MARKER, "&lt;!-- rag:block")
                line = line.replace("<!-- /rag:block", "&lt;!-- /rag:block")
        elif _fence_close(line, fence):
            fence = None
        lines.append(line)
    return "\n".join(lines)


def render_qnu_markdown(
    document: QnuStructuredDocument,
    *,
    document_id: str,
    revision_id: str,
    review_status: str = "unreviewed",
) -> str:
    """Render the standard file deterministically; identifiers come from the server."""
    if review_status not in QNU_REVIEW_STATUSES:
        raise ValueError(f"Unsupported review_status: {review_status}")
    frontmatter = {
        "schema_version": document.schema_version,
        "is_template": False,
        "document_id": document_id,
        "revision_id": revision_id,
        "title": document.title,
        "language": document.language,
        "document_type": document.document_type,
        "source": {
            "filename": document.source.filename,
            "uri": document.source.uri,
            "sha256": document.source.sha256,
            "page_count": document.source.page_count,
        },
        "metadata": document.document_meta,
        "review_status": review_status,
    }
    lines = ["---", dump_qnu_yaml(frontmatter).rstrip("\n"), "---", ""]
    title = " ".join(document.title.split())
    if title:
        lines.append(f"# {title}")
        lines.append("")
    for block in document.blocks:
        lines.append(render_qnu_block(block))
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def parse_qnu_markdown(markdown: str) -> QnuParseResult:
    """Fence-aware reader for frontmatter, blocks and stray content."""
    result = QnuParseResult()
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    index = 0
    if lines and lines[0].strip() == "---":
        end = None
        for candidate in range(1, len(lines)):
            if lines[candidate].strip() == "---":
                end = candidate
                break
        if end is None:
            result.errors.append(
                QnuIssue(code="frontmatter_unterminated", detail="Frontmatter không có dòng kết thúc '---'.")
            )
        else:
            try:
                loaded = yaml.load("\n".join(lines[1:end]), Loader=_UniqueKeyLoader)
                if loaded is not None and not isinstance(loaded, dict):
                    result.errors.append(
                        QnuIssue(code="frontmatter_not_mapping", detail="Frontmatter không phải YAML mapping.")
                    )
                else:
                    result.frontmatter = loaded or {}
            except yaml.YAMLError as exc:
                result.errors.append(QnuIssue(code="frontmatter_yaml_error", detail=str(exc)))
            index = end + 1
    while index < len(lines):
        line = lines[index]
        if line.strip() == _OPEN_MARKER:
            parsed = _parse_block(lines, index, result)
            if parsed is None:
                break
            result.blocks.append(parsed[0])
            index = parsed[1]
            continue
        if line.strip():
            result.stray_lines.append((index + 1, line))
        index += 1
    return result


def _parse_block(
    lines: list[str], start: int, result: QnuParseResult
) -> tuple[ParsedQnuBlock, int] | None:
    metadata_lines: list[str] = []
    index = start + 1
    while index < len(lines) and lines[index].strip() != "-->":
        metadata_lines.append(lines[index])
        index += 1
    if index >= len(lines):
        result.errors.append(
            QnuIssue(code="block_metadata_unterminated", detail="Khối thiếu dòng '-->' kết thúc metadata.", line=start + 1)
        )
        return None
    try:
        metadata = yaml.load("\n".join(metadata_lines), Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        result.errors.append(
            QnuIssue(code="block_metadata_yaml_error", detail=str(exc), line=start + 1)
        )
        metadata = None
    if metadata is not None and not isinstance(metadata, dict):
        result.errors.append(
            QnuIssue(code="block_metadata_not_mapping", detail="Metadata khối không phải YAML mapping.", line=start + 1)
        )
        metadata = None
    body_lines: list[str] = []
    index += 1
    fence: str | None = None
    closed = False
    while index < len(lines):
        line = lines[index]
        if fence is None and line.strip() == _CLOSE_MARKER:
            closed = True
            break
        if fence is None and line.strip() == _OPEN_MARKER:
            result.errors.append(
                QnuIssue(code="nested_block_marker", detail="Phát hiện khối lồng cặp; dùng parent_id.", line=index + 1)
            )
        if fence is None:
            opened = _fence_open(line)
            if opened is not None:
                fence = opened
        elif _fence_close(line, fence):
            fence = None
        body_lines.append(line)
        index += 1
    if not closed:
        result.errors.append(
            QnuIssue(code="block_body_unterminated", detail="Khối thiếu dòng '<!-- /rag:block -->'.", line=start + 1)
        )
        return None
    if fence is not None:
        result.errors.append(
            QnuIssue(code="unclosed_code_fence", detail="Code fence chưa đóng trong khối.", line=start + 1)
        )
    body_text = "\n".join(body_lines)
    if metadata is not None and (
        "&lt;!--" in body_text or "<!--" in _outside_fence_text(body_text)
    ):
        result.warnings.append(
            QnuIssue(code="escaped_block_marker", detail="Nội dung có marker comment/marker khối.", line=start + 1)
        )
    return (
        ParsedQnuBlock(metadata=metadata or {}, body="\n".join(body_lines).strip("\n"), line=start + 1),
        index + 1,
    )


def validate_qnu_markdown(markdown: str) -> QnuValidationReport:
    """Structural gate before saving the standard file; content uncertainty stays as flags."""
    report = QnuValidationReport()
    parsed = parse_qnu_markdown(markdown)
    for error in parsed.errors:
        report.add_error(error.code, error.detail, error.block_id)
    for warning in parsed.warnings:
        report.warnings.append(warning)
    _validate_frontmatter(parsed, report)
    _validate_blocks(parsed, report)
    stray_lines = [
        (line, text) for line, text in parsed.stray_lines if not text.lstrip().startswith("#")
    ]
    if stray_lines:
        stray = "; ".join(f"dòng {line}: {text[:60]}" for line, text in stray_lines[:5])
        report.add_warning("content_outside_blocks", f"Nội dung ngoài khối: {stray}")
    report.block_count = len(parsed.blocks)
    report.issues = [*report.errors, *report.warnings]
    return report


def _typed_in(value: Any, allowed: frozenset[str] | set[str]) -> bool:
    """Check the type before any set lookup: an unhashable value is invalid metadata, not a miss."""
    return isinstance(value, str) and value in allowed


def _validate_frontmatter(parsed: QnuParseResult, report: QnuValidationReport) -> None:
    frontmatter = parsed.frontmatter
    if frontmatter is None:
        report.add_error("frontmatter_missing", "Thiếu frontmatter của chuẩn QNU RAG Markdown.")
        return
    required = {
        "schema_version",
        "is_template",
        "document_id",
        "revision_id",
        "title",
        "language",
        "document_type",
        "source",
        "metadata",
        "review_status",
    }
    for key in sorted(required):
        if key not in frontmatter:
            report.add_error("frontmatter_missing_key", f"Thiếu khóa bắt buộc '{key}'.")
    for key in frontmatter:
        if key not in required:
            report.add_error("frontmatter_unknown_key", f"Khóa lõi không hỗ trợ: '{key}'.")
    version = frontmatter.get("schema_version")
    if version != QNU_MARKDOWN_SCHEMA:
        report.add_error("schema_version_unsupported", f"schema_version không hỗ trợ: {version!r}.")
    if frontmatter.get("is_template") is not False:
        report.add_error("template_not_allowed", "is_template phải là false trước khi nhập kiến thức.")
    if not _typed_in(frontmatter.get("review_status"), QNU_REVIEW_STATUSES):
        report.add_error("review_status_invalid", f"review_status không hợp lệ: {frontmatter.get('review_status')!r}.")
    for key in ("document_id", "revision_id", "title"):
        value = frontmatter.get(key)
        if not isinstance(value, str) or not value.strip():
            report.add_error("frontmatter_invalid_value", f"'{key}' phải là chuỗi không rỗng.")
    metadata = frontmatter.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        report.add_error("frontmatter_invalid_value", "'metadata' phải là mapping.")
    source = frontmatter.get("source")
    if not isinstance(source, dict):
        report.add_error("frontmatter_invalid_value", "'source' phải là mapping.")
        return
    for key in source:
        if key not in {"filename", "uri", "sha256", "page_count"}:
            report.add_error("frontmatter_unknown_key", f"'source.{key}' không hỗ trợ.")
    sha = source.get("sha256")
    if sha is not None and (not isinstance(sha, str) or not _SHA256.match(sha)):
        report.add_error("source_hash_invalid", "source.sha256 phải là 64 ký tự hex hoặc null.")
    page_count = source.get("page_count")
    if page_count is not None and (not isinstance(page_count, int) or page_count < 1):
        report.add_error("source_page_count_invalid", "source.page_count phải là số nguyên >= 1 hoặc null.")


def _mapping_value(value: Any, key: str, block_id: str, report: QnuValidationReport) -> dict[str, Any]:
    """A wrongly typed attribute is a structured finding, never an AttributeError."""
    raw = value.get(key)
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    report.add_error("table_field_invalid", f"'{key}' phải là mapping.", block_id=block_id)
    return {}


def _table_columns(metadata: dict[str, Any], block_id: str, report: QnuValidationReport) -> list[str]:
    attributes = metadata.get("attributes")
    if not isinstance(attributes, dict):
        return []
    raw = attributes.get("columns")
    if raw is None:
        return []
    if not isinstance(raw, list):
        report.add_error("table_column_invalid", "'columns' phải là danh sách.", block_id=block_id)
        return []
    ids: list[str] = []
    for column in raw:
        if not isinstance(column, dict) or not isinstance(column.get("id"), str) or not column["id"].strip():
            report.add_error("table_column_invalid", "Mỗi column cần 'id' là chuỗi không rỗng.", block_id=block_id)
            continue
        ids.append(column["id"])
        path = column.get("header_path")
        if not isinstance(path, list) or any(not isinstance(part, str) for part in path):
            report.add_error("table_column_invalid", "header_path phải là danh sách chuỗi.", block_id=block_id)
    if len(ids) != len(set(ids)):
        report.add_error("table_column_duplicate", "Bảng có column 'id' trùng nhau.", block_id=block_id)
    return ids


def parse_qnu_gfm_table(body: str) -> tuple[list[str], list[list[str]]]:
    """One shared GFM shape contract for the artifact gate and serving projection."""
    lines = [line for line in body.splitlines() if line.strip()]
    rows = [_split_gfm_row(line) for line in lines]
    if (len(rows) < 2 or not rows[0] or len(rows[1]) != len(rows[0])
            or not all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in rows[1])
            or any(len(row) != len(rows[0]) for row in rows[2:])):
        raise ValueError("GFM requires a header, separator and rows of equal width")
    return rows[0], rows[2:]


def _validate_gfm(body: str, columns: Any, block_id: str, report: QnuValidationReport) -> None:
    try:
        headers, _ = parse_qnu_gfm_table(body)
    except ValueError:
        report.add_error("table_gfm_invalid", "Bảng GFM phải có header, separator và các dòng cùng số cột.", block_id=block_id)
        return
    if not isinstance(columns, list) or not columns:
        return
    paths = [column.get("header_path") if isinstance(column, dict) else None for column in columns]
    if any(not isinstance(path, list) or any(not isinstance(part, str) for part in path) for path in paths):
        return  # The column schema validator reports the malformed path.
    if headers not in ([" / ".join(path) for path in paths], [path[-1] if path else "" for path in paths]):
        report.add_error("table_gfm_invalid", "Header GFM không khớp columns đã khai báo.", block_id=block_id)


def _validate_quality_flags(metadata: dict[str, Any], block_id: str, report: QnuValidationReport) -> bool:
    """Validate warnings before allowing them to explain an unknown source location."""
    flags = metadata.get("quality_flags")
    has_location_warning = False
    for flag in flags if isinstance(flags, list) else []:
        if (not isinstance(flag, dict) or not isinstance(flag.get("code"), str) or not flag["code"].strip()
                or not _typed_in(flag.get("status"), {"unresolved", "confirmed", "resolved", "rejected"})
                or not isinstance(flag.get("detail"), str) or not flag["detail"].strip()
                or not isinstance(flag.get("related_block_ids", []), list)
                or any(not isinstance(ref, str) for ref in flag.get("related_block_ids", []))):
            report.add_error("block_quality_flag_invalid", "Cờ chất lượng cần code/status/detail hợp lệ.", block_id=block_id)
            continue
        has_location_warning |= flag["code"] == "source_location_unverified" and flag["status"] in {"unresolved", "confirmed"}
    return has_location_warning


def _validate_table_relations(
    parsed: QnuParseResult,
    report: QnuValidationReport,
    index: dict[str, dict[str, Any]],
    columns_by_table: dict[str, list[str]],
) -> None:
    """Fields and origins are only meaningful against the parent table, not the row itself."""
    for block in parsed.blocks:
        metadata = block.metadata
        block_id = metadata.get("id")
        if metadata.get("type") != "table_row" or not isinstance(block_id, str):
            continue
        parent_id = metadata.get("parent_id")
        parent = index.get(parent_id) if isinstance(parent_id, str) else None
        if parent is None or parent.get("type") != "table":
            report.add_error(
                "table_row_parent_invalid",
                "table_row phải có parent_id trỏ tới một khối table.",
                block_id=block_id,
            )
            continue
        parent_attributes = parent.get("attributes")
        parent_attributes = parent_attributes if isinstance(parent_attributes, dict) else {}
        if parent_attributes.get("representation") != "records":
            report.add_error(
                "table_row_parent_invalid",
                "Khối table cha không dùng biểu diễn records; dòng không thuộc bảng này.",
                block_id=block_id,
            )
            continue
        column_ids = set(columns_by_table.get(parent_id) or [])
        attributes = metadata.get("attributes")
        attributes = attributes if isinstance(attributes, dict) else {}
        # A wrong "fields" type is already reported as table_field_invalid by the main pass.
        raw_fields = attributes.get("fields")
        fields = raw_fields if isinstance(raw_fields, dict) else {}
        for field_id in fields:
            if column_ids and field_id not in column_ids:
                report.add_error(
                    "table_field_unknown_column",
                    f"Trường '{field_id}' không thuộc columns của bảng cha.",
                    block_id=block_id,
                )
        origins = _mapping_value(attributes, "field_origins", block_id, report)
        for field_id, origin in origins.items():
            if field_id not in fields:
                report.add_error(
                    "table_field_origin_invalid",
                    f"'field_origins.{field_id}' không tham chiếu field nào của dòng.",
                    block_id=block_id,
                )
                continue
            if not isinstance(origin, dict):
                report.add_error("table_field_origin_invalid", "Mỗi origin phải là mapping.", block_id=block_id)
                continue
            if not _typed_in(origin.get("basis"), {"merged_cell", "explicit_reference"}):
                report.add_error(
                    "table_field_origin_invalid",
                    f"'{field_id}' thiếu basis hợp lệ (merged_cell/explicit_reference).",
                    block_id=block_id,
                )
            origin_block = origin.get("block_id")
            origin_column = origin.get("column_id")
            if not isinstance(origin_block, str) or origin_block not in index:
                report.add_error(
                    "table_field_origin_invalid",
                    f"'{field_id}' trỏ tới block_id không tồn tại.",
                    block_id=block_id,
                )
            else:
                referenced = index[origin_block]
                same_table = origin_block == parent_id or (
                    _typed_in(referenced.get("type"), {"table_row", "note"}) and referenced.get("parent_id") == parent_id
                )
                if not same_table:
                    report.add_error(
                        "table_field_origin_invalid",
                        f"'{field_id}' trỏ tới block ngoài phạm vi bảng cha.",
                        block_id=block_id,
                    )
            if not isinstance(origin_column, str) or origin_column not in column_ids:
                report.add_error(
                    "table_field_origin_invalid",
                    f"'{field_id}' trỏ tới column_id không thuộc bảng cha.",
                    block_id=block_id,
                )


def _validate_blocks(parsed: QnuParseResult, report: QnuValidationReport) -> None:
    seen: set[str] = set()
    parents: dict[str, str | None] = {}
    index: dict[str, dict[str, Any]] = {}
    columns_by_table: dict[str, list[str]] = {}
    for block in parsed.blocks:
        metadata = block.metadata
        block_id = metadata.get("id")
        if not isinstance(block_id, str) or not block_id.strip():
            report.add_error("block_id_missing", "Khối thiếu 'id'.", block_id=None)
            continue
        if block_id in seen:
            report.add_error("block_id_duplicate", f"ID khối trùng: '{block_id}'.", block_id=block_id)
        seen.add(block_id)
        block_type = metadata.get("type")
        if not _typed_in(block_type, QNU_BLOCK_TYPES):
            report.add_error("block_type_invalid", f"Loại khối không hỗ trợ: {block_type!r}.", block_id=block_id)
        locations = metadata.get("source_locations")
        if not isinstance(locations, list):
            report.add_error("block_locations_invalid", "source_locations phải là danh sách.", block_id=block_id)
        else:
            for location in locations:
                if not isinstance(location, dict):
                    report.add_error("block_locations_invalid", "Mỗi source_location phải là mapping.", block_id=block_id)
                    continue
                page = location.get("page")
                if page is not None and (isinstance(page, bool) or not isinstance(page, int) or page < 1):
                    report.add_error("block_location_page_invalid", f"page không hợp lệ: {page!r}.", block_id=block_id)
        parent_id = metadata.get("parent_id")
        parents[block_id] = parent_id if isinstance(parent_id, str) and parent_id else None
        for key in ("attributes",):
            value = metadata.get(key)
            if value is not None and not isinstance(value, dict):
                report.add_error("block_attribute_invalid", f"'{key}' phải là mapping.", block_id=block_id)
        for key in ("context_refs", "section_path", "quality_flags"):
            value = metadata.get(key)
            if value is not None and not isinstance(value, list):
                report.add_error("block_attribute_invalid", f"'{key}' phải là danh sách.", block_id=block_id)
        has_location_warning = _validate_quality_flags(metadata, block_id, report)
        has_source_location = isinstance(locations, list) and any(
            isinstance(loc, dict) and (
                (isinstance(loc.get("page"), int) and not isinstance(loc["page"], bool) and loc["page"] >= 1)
                or (isinstance(loc.get("locator"), str) and bool(loc["locator"].strip()))) for loc in locations)
        if isinstance(locations, list) and not has_source_location and block_type != "derived_index" and not has_location_warning:
            report.add_error("block_location_unverified", "Khối thiếu vị trí nguồn cần cờ source_location_unverified.", block_id=block_id)
        index[block_id] = metadata
        attributes = metadata.get("attributes")
        attributes = attributes if isinstance(attributes, dict) else {}
        if block_type == "table":
            columns_by_table[block_id] = _table_columns(metadata, block_id, report)
        fields = attributes.get("fields")
        if fields is not None and not isinstance(fields, dict):
            report.add_error("table_field_invalid", "'fields' phải là mapping.", block_id=block_id)
            fields = None
        for field_id, field in (fields or {}).items():
            if not isinstance(field, dict) or "raw" not in field or "state" not in field:
                report.add_error("table_field_invalid", f"Trường '{field_id}' thiếu raw/state.", block_id=block_id)
                continue
            if not _typed_in(field.get("state"), QNU_CELL_STATES):
                report.add_error("table_field_state_invalid", f"state không hợp lệ: {field.get('state')!r}.", block_id=block_id)
            if not isinstance(field.get("raw"), str):
                report.add_error("table_field_invalid", f"raw của '{field_id}' phải là chuỗi.", block_id=block_id)
        if _typed_in(block_type, BODY_REQUIRED_TYPES) and not block.body.strip():
            report.add_error("block_body_empty", "Khối chứng cứ thiếu nội dung.", block_id=block_id)
        if block_type == "figure" and not block.body.strip() and not metadata.get("quality_flags"):
            report.add_error("block_body_empty", "Khối figure rỗng cần cờ chất lượng.", block_id=block_id)
        if block_type == "table":
            representation = attributes.get("representation")
            if not _typed_in(representation, {"gfm", "records"}):
                report.add_error("table_representation_invalid", "Biểu diễn bảng chỉ hỗ trợ gfm hoặc records.", block_id=block_id)
            elif representation == "gfm" and block.body.strip():
                _validate_gfm(block.body, attributes.get("columns"), block_id, report)
            if representation == "records" and not columns_by_table.get(block_id):
                report.add_error(
                    "table_column_invalid",
                    "Bảng records phải khai báo columns để kiểm tra field và origin.",
                    block_id=block_id,
                )
            child_rows = [
                other
                for other in parsed.blocks
                if other.metadata.get("parent_id") == block_id
                and _typed_in(other.metadata.get("type"), {"table_row", "note"})
            ]
            if representation == "records" and not child_rows:
                report.add_error(
                    "table_records_missing", "Bảng records không có khối table_row/note con.", block_id=block_id
                )
            if representation != "records" and not block.body.strip() and not metadata.get("quality_flags"):
                report.add_error(
                    "block_body_empty", "Khối table GFM rỗng cần nội dung hoặc cờ chất lượng.", block_id=block_id
                )
        # str() over json.dumps: wrongly typed metadata must not turn a finding into a serialization crash.
        placeholder_scope = _outside_fence_text(block.body) + str(metadata)
        if _PLACEHOLDER.search(placeholder_scope):
            report.add_error("template_placeholder", "Còn placeholder dạng ngoặc nhọn kép trong khối.", block_id=block_id)
    _validate_table_relations(parsed, report, index, columns_by_table)
    for block_id, parent_id in parents.items():
        if parent_id is not None and parent_id not in parents:
            report.add_error("block_parent_missing", f"parent_id '{parent_id}' không tồn tại.", block_id=block_id)
    for block in parsed.blocks:
        metadata = block.metadata
        block_id = metadata.get("id")
        if not isinstance(block_id, str):
            continue
        # A wrong "context_refs" type is already reported as block_attribute_invalid by the main pass.
        raw_refs = metadata.get("context_refs")
        for ref in raw_refs if isinstance(raw_refs, list) else []:
            if not isinstance(ref, str) or ref not in parents:
                report.add_error("block_context_ref_missing", f"context_ref '{ref}' không tồn tại.", block_id=block_id)
    for block_id in parents:
        # Follow parent links; a cycle would revisit the same node.
        cursor: str | None = block_id
        hops = 0
        while cursor is not None and hops <= len(parents):
            cursor = parents.get(cursor)
            hops += 1
            if cursor == block_id:
                report.add_error("block_parent_cycle", f"Quan hệ cha–con có chu trình tại '{block_id}'.", block_id=block_id)
                break
