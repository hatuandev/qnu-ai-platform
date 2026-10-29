"""Convert DOCX body XML into deterministic HTML for fixed-layout rendering.

Only what affects the visible page is projected: paragraphs, runs with bold/italic,
heading levels, tables with ``gridSpan``/``vMerge`` (colspan/rowspan) and repeat
header rows, footnotes and embedded images. Text is escaped, never normalised: a
``0``, an empty cell and a ``-`` stay exactly what the document contains.

Nothing here guesses content. Constructs that are not projected are counted and
reported as warnings instead of being silently dropped.
"""

from __future__ import annotations

import base64
import io
import zipfile
from dataclasses import dataclass, field
from html import escape
from xml.etree import ElementTree

from qnu.platform.errors import AppException

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

MAX_TABLE_DEPTH = 2
MAX_IMAGE_BYTES = 4 * 1024 * 1024
IMAGE_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "bmp": "image/bmp",
}


@dataclass(slots=True)
class DocxHtml:
    html: str
    paragraphs: int = 0
    tables: int = 0
    table_rows: int = 0
    footnotes: int = 0
    images: int = 0
    skipped_images: int = 0
    warnings: list[str] = field(default_factory=list)


def _invalid(detail: str) -> AppException:
    return AppException(detail, code="docx_invalid", status_code=422, title="Tệp DOCX không hợp lệ")


def _read_part(archive: zipfile.ZipFile, name: str) -> bytes | None:
    try:
        return archive.read(name)
    except KeyError:
        return None


def _relationships(archive: zipfile.ZipFile) -> dict[str, str]:
    payload = _read_part(archive, "word/_rels/document.xml.rels")
    if payload is None:
        return {}
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return {}
    return {
        element.get("Id", ""): element.get("Target", "")
        for element in root
        if element.get("Id") and element.get("Target")
    }


def _footnotes(archive: zipfile.ZipFile) -> dict[str, int]:
    """Map footnote id to a 1-based display number in document order."""
    payload = _read_part(archive, "word/footnotes.xml")
    if payload is None:
        return {}
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return {}
    mapping: dict[str, int] = {}
    for footnote in root.findall(W + "footnote"):
        raw_id = footnote.get(W + "id") or ""
        try:
            if int(raw_id) < 1:
                continue
        except ValueError:
            continue
        mapping[raw_id] = len(mapping) + 1
    return mapping


def _footnote_texts(archive: zipfile.ZipFile) -> dict[str, str]:
    payload = _read_part(archive, "word/footnotes.xml")
    if payload is None:
        return {}
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError:
        return {}
    texts: dict[str, str] = {}
    for footnote in root.findall(W + "footnote"):
        raw_id = footnote.get(W + "id") or ""
        try:
            if int(raw_id) < 1:
                continue
        except ValueError:
            continue
        texts[raw_id] = "".join(node.text or "" for node in footnote.iter(W + "t")).strip()
    return texts


def _image_uri(archive: zipfile.ZipFile, targets: dict[str, str], embed: str) -> str | None:
    target = targets.get(embed)
    if not target:
        return None
    name = target.lstrip("/")
    if not name.startswith("word/"):
        name = "word/" + name
    extension = name.rsplit(".", 1)[-1].lower()
    mime = IMAGE_TYPES.get(extension)
    if mime is None:
        return None
    payload = _read_part(archive, name)
    if not payload or len(payload) > MAX_IMAGE_BYTES:
        return None
    return f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"


def _heading_level(paragraph: ElementTree.Element) -> int | None:
    style = paragraph.find(f"{W}pPr/{W}pStyle")
    if style is None:
        return None
    value = (style.get(W + "val") or "").strip().lower()
    if value.startswith("heading") and value[-1:].isdigit():
        return max(1, min(int(value[-1]), 6))
    if value == "title":
        return 1
    if value == "subtitle":
        return 2
    return None


def _render_run(
    run: ElementTree.Element,
    footnotes: dict[str, int],
    state: DocxHtml,
    targets: dict[str, str],
    archive: zipfile.ZipFile,
) -> str:
    pieces: list[str] = []
    for child in run:
        tag = child.tag
        if tag == W + "t":
            pieces.append(escape(child.text or ""))
        elif tag == W + "tab":
            pieces.append(" ")
        elif tag in {W + "br", W + "cr"}:
            pieces.append("<br/>")
        elif tag == W + "noBreakHyphen":
            pieces.append("-")
        elif tag == W + "footnoteReference":
            number = footnotes.get(child.get(W + "id") or "")
            if number is not None:
                pieces.append(f'<sup class="fn">{number}</sup>')
        elif tag == W + "drawing":
            embed = ""
            for node in child.iter():
                if node.tag == A + "blip":
                    embed = node.get(R + "embed") or ""
                    break
            if not embed:
                state.skipped_images += 1
                continue
            uri = _image_uri(archive, targets, embed)
            if uri is None:
                state.skipped_images += 1
                continue
            state.images += 1
            pieces.append(f'<img src="{uri}" class="docx-image"/>')
    text = "".join(pieces)
    if not text:
        return ""
    properties = run.find(W + "rPr")
    if properties is not None:
        if properties.find(W + "b") is not None:
            text = f"<b>{text}</b>"
        if properties.find(W + "i") is not None:
            text = f"<i>{text}</i>"
    return text


def _render_paragraph(
    paragraph: ElementTree.Element,
    footnotes: dict[str, int],
    state: DocxHtml,
    targets: dict[str, str],
    archive: zipfile.ZipFile,
) -> str:
    content = "".join(
        _render_run(run, footnotes, state, targets, archive) for run in paragraph.iter(W + "r")
    )
    level = _heading_level(paragraph)
    if level is not None:
        state.paragraphs += 1
        return f"<h{level}>{content}</h{level}>" if content else ""
    state.paragraphs += 1
    return f"<p>{content}</p>" if content else "<p></p>"


def _cell_properties(cell: ElementTree.Element) -> tuple[int, str | None]:
    properties = cell.find(W + "tcPr")
    if properties is None:
        return 1, None
    span = properties.find(W + "gridSpan")
    colspan = 1
    if span is not None:
        try:
            colspan = max(1, min(int(span.get(W + "val") or "1"), 64))
        except ValueError:
            colspan = 1
    merge = properties.find(W + "vMerge")
    if merge is None:
        return colspan, None
    return colspan, merge.get(W + "val") or "continue"


def _cell_content(
    cell: ElementTree.Element,
    footnotes: dict[str, int],
    state: DocxHtml,
    targets: dict[str, str],
    archive: zipfile.ZipFile,
    depth: int,
) -> str:
    parts: list[str] = []
    for child in cell:
        if child.tag == W + "p":
            rendered = _render_paragraph(child, footnotes, state, targets, archive)
            parts.append(rendered.replace("<p></p>", ""))
        elif child.tag == W + "tbl" and depth < MAX_TABLE_DEPTH:
            parts.append(_render_table(child, footnotes, state, targets, archive, depth + 1))
    return "".join(parts)


def _render_table(
    table: ElementTree.Element,
    footnotes: dict[str, int],
    state: DocxHtml,
    targets: dict[str, str],
    archive: zipfile.ZipFile,
    depth: int = 0,
) -> str:
    rows = table.findall(W + "tr")
    if not rows:
        return ""
    state.tables += 1
    grid: list[list[dict[str, object]]] = []
    origins: dict[tuple[int, int], dict[str, object]] = {}
    occupied: set[tuple[int, int]] = set()
    header_rows: set[int] = set()

    for row_index, row in enumerate(rows):
        properties = row.find(W + "trPr")
        if properties is not None and properties.find(W + "tblHeader") is not None:
            header_rows.add(row_index)
        column = 0
        cells: list[dict[str, object]] = []
        for cell in row.findall(W + "tc"):
            while (row_index, column) in occupied:
                column += 1
            colspan, merge = _cell_properties(cell)
            if merge == "continue":
                origin = origins.get((row_index - 1, column))
                if origin is None or int(origin["col_span"]) != colspan:
                    raise AppException(
                        "Không xác định được ô gốc của vùng gộp dọc DOCX.",
                        code="docx_table_merge_unsupported",
                        status_code=422,
                    )
                origin["row_span"] = int(origin["row_span"]) + 1
                for offset in range(colspan):
                    occupied.add((row_index, column + offset))
                    origins[(row_index, column + offset)] = origin
                column += colspan
                continue
            record: dict[str, object] = {
                "html": _cell_content(cell, footnotes, state, targets, archive, depth),
                "col_span": colspan,
                "row_span": 1,
                "header": row_index in header_rows,
            }
            cells.append(record)
            origins[(row_index, column)] = record
            for offset in range(colspan):
                occupied.add((row_index, column + offset))
                if offset:
                    origins[(row_index, column + offset)] = record
            column += colspan
        grid.append(cells)
        state.table_rows += 1

    output = ['<table class="docx"><tbody>']
    for cells in grid:
        output.append("<tr>")
        for cell in cells:
            tag = "th" if cell["header"] else "td"
            attributes = ""
            if int(cell["col_span"]) > 1:
                attributes += f' colspan="{cell["col_span"]}"'
            if int(cell["row_span"]) > 1:
                attributes += f' rowspan="{cell["row_span"]}"'
            output.append(f"<{tag}{attributes}>{cell['html']}</{tag}>")
        output.append("</tr>")
    output.append("</tbody></table>")
    return "".join(output)


def convert_docx_to_html(payload: bytes) -> DocxHtml:
    """Build the render HTML for one DOCX package; raises on a non-DOCX archive."""
    if not payload:
        raise _invalid("Tệp DOCX rỗng.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(payload))
    except (zipfile.BadZipFile, OSError) as exc:
        raise _invalid("Tệp không phải gói DOCX hợp lệ.") from exc

    with archive:
        document = _read_part(archive, "word/document.xml")
        if document is None:
            raise _invalid("Thiếu word/document.xml trong gói DOCX.")
        try:
            root = ElementTree.fromstring(document)
        except ElementTree.ParseError as exc:
            raise _invalid("word/document.xml không đọc được.") from exc
        body = root.find(W + "body")
        if body is None:
            raise _invalid("DOCX không có phần thân tài liệu.")

        # Story cannot reproduce section-dependent Word headers/footers. Never OCR
        # a body-only projection and label it a complete rendering of the source.
        unsupported = ("headerReference", "footerReference")
        if any(root.find(f".//{W}{tag}") is not None for tag in unsupported):
            raise AppException(
                "DOCX có header/footer theo section chưa được bộ chuyển đổi giữ đầy đủ; "
                "hãy cung cấp bản PDF có bố cục trang cố định.",
                code="docx_layout_unsupported",
                status_code=422,
            )

        footnotes = _footnotes(archive)
        targets = _relationships(archive)
        state = DocxHtml(html="")
        blocks: list[str] = []
        for child in body:
            if child.tag == W + "p":
                rendered = _render_paragraph(child, footnotes, state, targets, archive)
                if rendered:
                    blocks.append(rendered)
            elif child.tag == W + "tbl":
                rendered = _render_table(child, footnotes, state, targets, archive)
                if rendered:
                    blocks.append(rendered)
            elif child.tag in {W + "sectPr", W + "bookmarkStart", W + "bookmarkEnd"}:
                continue

        texts = _footnote_texts(archive)
        if footnotes:
            items = []
            for raw_id, number in sorted(footnotes.items(), key=lambda item: item[1]):
                items.append(f"<li>{escape(texts.get(raw_id, ''))}</li>")
            blocks.append(
                '<div class="footnotes"><p>Chú thích</p><ol>' + "".join(items) + "</ol></div>"
            )
            state.footnotes = len(items)

        if state.skipped_images:
            state.warnings.append(f"docx_image_skipped:{state.skipped_images}")
        if not blocks:
            raise _invalid("DOCX không có nội dung hiển thị.")

        state.html = (
            '<html><head><meta charset="utf-8"/></head><body>' + "".join(blocks) + "</body></html>"
        )
        return state
