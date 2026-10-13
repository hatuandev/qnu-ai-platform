"""Materialize cached table formula results in a DOCX preview copy only."""

from dataclasses import dataclass, field
from io import BytesIO
from zipfile import BadZipFile, ZipFile

from lxml import etree

from app.core.exceptions import AppException

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass
class _Field:
    instruction: list[str] = field(default_factory=list)
    controls: list[etree._Element] = field(default_factory=list)
    cached_text: list[str] = field(default_factory=list)
    separated: bool = False
    nested: bool = False
    in_table: bool = False


def _is_formula(instruction: str) -> bool:
    return instruction.lstrip().startswith("=")


def _require_cache(value: str) -> None:
    if not value.strip():
        raise AppException(
            "Ô công thức trong DOCX chưa có kết quả đã lưu; cần kiểm tra trong Word.",
            code="DOCX_FORMULA_RESULT_MISSING", status_code=422,
        )


def _reject_nested() -> None:
    raise AppException(
        "Công thức DOCX có trường lồng nhau; cần kiểm tra trước khi tạo bản xem.",
        code="DOCX_FORMULA_NESTED_UNSUPPORTED", status_code=422,
    )


def _materialize_complex(root: etree._Element) -> int:
    stack: list[_Field] = []
    count = 0
    for node in list(root.iter()):
        if node.tag == W + "fldChar":
            kind = node.get(W + "fldCharType")
            if kind == "begin":
                for parent in stack:
                    parent.nested = True
                stack.append(_Field(in_table=any(p.tag == W + "tc" for p in node.iterancestors())))
            if not stack:
                continue
            current = stack[-1]
            current.controls.append(node)
            if kind == "separate":
                current.separated = True
            if kind == "end":
                current = stack.pop()
                if current.in_table and _is_formula("".join(current.instruction)):
                    if current.nested:
                        _reject_nested()
                    _require_cache("".join(current.cached_text))
                    for control in current.controls:
                        control.getparent().remove(control)
                    count += 1
        elif stack and node.tag == W + "instrText" and not stack[-1].separated:
            stack[-1].instruction.append(node.text or "")
            stack[-1].controls.append(node)
        elif stack and node.tag == W + "t" and stack[-1].separated:
            stack[-1].cached_text.append(node.text or "")
        elif stack and node.tag == W + "fldSimple":
            stack[-1].nested = True
    if any(f.in_table and _is_formula("".join(f.instruction)) for f in stack):
        raise AppException("Cấu trúc công thức DOCX chưa hoàn chỉnh.", code="DOCX_FORMULA_MALFORMED", status_code=422)
    return count


def _materialize_simple(root: etree._Element) -> int:
    count = 0
    for node in list(root.iter(W + "fldSimple")):
        if not _is_formula(node.get(W + "instr", "")) or not any(p.tag == W + "tc" for p in node.iterancestors()):
            continue
        if node.find(".//" + W + "fldChar") is not None or node.find(".//" + W + "fldSimple") is not None:
            _reject_nested()
        _require_cache("".join(node.itertext(W + "t")))
        parent = node.getparent()
        index = parent.index(node)
        for child in list(node):
            parent.insert(index, child)
            index += 1
        parent.remove(node)
        count += 1
    return count


def _transform_package(content: bytes) -> bytes:
    """Preserve archive parts and formatting; never modify original bytes on disk."""
    with ZipFile(BytesIO(content)) as source:
        replacements: dict[str, bytes] = {}
        for name in source.namelist():
            if not name.startswith("word/") or not name.endswith(".xml"):
                continue
            xml = source.read(name)
            if b"fldChar" not in xml and b"fldSimple" not in xml:
                continue
            root = etree.fromstring(xml, etree.XMLParser(resolve_entities=False, no_network=True))
            count = _materialize_complex(root) + _materialize_simple(root)
            if count:
                replacements[name] = etree.tostring(root, encoding="UTF-8", xml_declaration=True)
        if not replacements:
            return content
        stream = BytesIO()
        with ZipFile(stream, "w") as preview:
            preview.comment = source.comment
            for info in source.infolist():
                preview.writestr(info, replacements.get(info.filename, source.read(info.filename)))
        return stream.getvalue()


def preserve_table_formula_results(content: bytes) -> bytes:
    """Reject invalid containers/XML without bypassing formula safety."""
    try:
        return _transform_package(content)
    except (BadZipFile, etree.XMLSyntaxError) as exc:
        raise AppException(
            "DOCX không hợp lệ; không thể tạo bản xem trước an toàn.",
            code="DOCX_PREVIEW_INVALID", status_code=422,
        ) from exc
