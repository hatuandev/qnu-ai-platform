"""Bounded MinerU archive reader and lossless projection of its explicit layout."""

import io
import json
import math
import stat
import zipfile
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import PurePosixPath

from qnu.domains.ocr.layout import Block, Cell, PageLayout, Table, _place_rows
from qnu.platform.errors import AppException

VERSION = "mineru-layout/v1"
MAX_FILES = 1000
MAX_UNCOMPRESSED_BYTES = 150 * 1024 * 1024


def invalid() -> AppException:
    return AppException(
        "Kết quả MinerU không khớp hợp đồng tài liệu.",
        code="mineru_layout_invalid",
        status_code=502,
    )


def archive_pages(payload: bytes, expected_pages: int) -> dict[int, dict]:
    """Never extract files on disk; reject traversal, links, duplicate names and bombs."""
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            entries = archive.infolist()
            if (
                len(entries) > MAX_FILES
                or sum(e.file_size for e in entries) > MAX_UNCOMPRESSED_BYTES
            ):
                raise invalid()
            names = set()
            for item in entries:
                path = PurePosixPath(item.filename.replace("\\", "/"))
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or ":" in str(path)
                    or str(path) in names
                    or stat.S_ISLNK(item.external_attr >> 16)
                ):
                    raise invalid()
                names.add(str(path))
            selected = [e for e in entries if PurePosixPath(e.filename).name == "middle_json.json"]
            if len(selected) != 1 or selected[0].file_size > 20 * 1024 * 1024:
                raise invalid()
            document = json.loads(archive.read(selected[0]))
            if not isinstance(document, dict) or document.get("is_full_document") is not True:
                raise invalid()
            pages = document.get("pages")
            if not isinstance(pages, list) or len(pages) != expected_pages:
                raise invalid()
            result = {}
            for page in pages:
                index = page.get("page_idx")
                if type(index) is not int or index + 1 in result or not 0 <= index < expected_pages:
                    raise invalid()
                result[index + 1] = {"format": VERSION, "page": page}
            return result
    except (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        zipfile.BadZipFile,
        RuntimeError,
        EOFError,
        RecursionError,
    ) as exc:
        raise invalid() from exc


class TableReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows, self.row, self.cell = [], None, None
        self.parts, self.spans, self.header = [], (1, 1), False
        self.tables = 0

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables += 1
            if self.tables != 1:
                raise ValueError("nested table")
        if tag == "tr":
            if self.row is not None or len(self.rows) >= 2048:
                raise ValueError("invalid row")
            self.row = []
        if tag in {"td", "th"}:
            if self.row is None or self.cell is not None or len(self.row) >= 64:
                raise ValueError("invalid cell")
            values = dict(attrs)
            self.spans = (int(values.get("rowspan", "1")), int(values.get("colspan", "1")))
            if not 1 <= self.spans[0] <= 2048 or not 1 <= self.spans[1] <= 64:
                raise ValueError("invalid span")
            self.cell, self.header, self.parts = tag, tag == "th", []
        if tag == "br" and self.cell:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.cell:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"}:
            if self.cell != tag:
                raise ValueError("unbalanced cell")
            self.row.append(Cell("".join(self.parts), *self.spans, self.header))
            self.cell = None
        if tag == "tr":
            if self.cell is not None or self.row is None:
                raise ValueError("unbalanced row")
            self.rows.append(self.row)
            self.row = None


def parse_table(html: str) -> Table:
    try:
        reader = TableReader()
        reader.feed(html)
        reader.close()
        if (
            reader.tables != 1
            or not reader.rows
            or reader.row is not None
            or reader.cell is not None
        ):
            raise ValueError
        # HTML omits cells covered by rowspan. Validate before the shared LaTeX
        # projector, which also accepts legacy empty merge placeholders.
        columns = sum(c.col_span for c in reader.rows[0])
        if not 0 < columns <= 64:
            raise ValueError
        occupied = set()
        for y, row in enumerate(reader.rows):
            x = 0
            for cell in row:
                while (y, x) in occupied:
                    x += 1
                if x + cell.col_span > columns or y + cell.row_span > len(reader.rows):
                    raise ValueError
                for yy in range(y, y + cell.row_span):
                    for xx in range(x, x + cell.col_span):
                        if (yy, xx) in occupied:
                            raise ValueError
                        occupied.add((yy, xx))
                x += cell.col_span
            if any((y, xx) not in occupied for xx in range(columns)):
                raise ValueError
        placed = _place_rows(reader.rows, columns)
        if placed is not None:
            return Table("parsed", tuple(tuple(row) for row in placed), columns)
    except (ValueError, TypeError):
        pass
    return Table("unsupported", reason="mineru_html_grid_invalid")


def content_text(content, depth=0) -> str:
    if depth > 12:
        raise invalid()
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(content_text(item, depth + 1) for item in content)
    if isinstance(content, dict):
        return content_text(content.get("content", ""), depth + 1)
    raise invalid()


def _page_items(source: list):
    """Keep explicit table caption/footnote children as separately citable blocks.

    Parsed tables render their cells rather than raw HTML in Markdown, so retaining
    a caption only inside the parent raw text would hide it from that export.
    """
    for item in source:
        if not isinstance(item, dict):
            raise invalid()
        content = item.get("content")
        if item.get("type") != "table" or not isinstance(content, list):
            yield item
            continue
        if any(not isinstance(part, dict) for part in content):
            raise invalid()
        annotations = [part for part in content if part.get("type") != "table_body"]
        bodies = [part for part in content if part.get("type") == "table_body"]
        for part in annotations:
            if part.get("type") == "table_caption":
                yield {**part, "bbox": part.get("bbox", item.get("bbox")), "type": "caption"}
        yield {**item, "content": bodies}
        for part in annotations:
            if part.get("type") != "table_caption":
                yield {**part, "bbox": part.get("bbox", item.get("bbox"))}


def parse_mineru_page(raw: dict) -> PageLayout:
    if raw.get("format") != VERSION:
        raise invalid()
    source = raw.get("page", {}).get("blocks")
    if not isinstance(source, list) or len(source) > 10000:
        raise invalid()
    blocks = []
    for item in _page_items(source):
        bbox = item.get("bbox")
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(type(v) in (int, float) and math.isfinite(v) for v in bbox)
            or not 0 <= bbox[0] < bbox[2] <= 1
            or not 0 <= bbox[1] < bbox[3] <= 1
        ):
            raise invalid()
        label = item.get("type")
        if not isinstance(label, str):
            raise invalid()
        text = content_text(item.get("content", ""))
        table = None
        if label == "table":
            bodies = [
                part
                for part in item.get("content", [])
                if isinstance(part, dict) and part.get("type") == "table_body"
            ]
            table = (
                parse_table(bodies[0]["content"])
                if len(bodies) == 1
                else Table("unsupported", reason="mineru_table_body_missing")
            )
        kind = {
            "table": "table",
            "title": "title",
            "header": "header",
            "footer": "footer",
            "page_number": "footer",
            "image": "figure",
            "equation": "formula",
            "caption": "caption",
            "table_footnote": "footnote",
        }.get(label, "text")
        blocks.append(
            Block(
                len(blocks) + 1,
                label,
                kind,
                text,
                tuple(bbox),
                requires_review=bool(table and table.status != "parsed"),
                table=table,
            )
        )
    warnings = []
    regions = raw.get("image_ocr", [])
    if not isinstance(regions, list) or len(regions) > 2048:
        raise invalid()
    assets = set()
    for region in regions:
        if not isinstance(region, dict) or not isinstance(region.get("result"), dict):
            raise invalid()
        asset, bbox = region.get("image_asset_no"), region.get("bbox")
        number = region.get("image_region", 1)
        if (
            type(asset) is not int
            or asset <= 0
            or type(number) is not int
            or not 1 <= number <= 65
            or (asset, number) in assets
            or not isinstance(bbox, list)
            or len(bbox) != 4
            or not all(type(v) in (int, float) and math.isfinite(v) for v in bbox)
            or not 0 <= bbox[0] < bbox[2] <= 1
            or not 0 <= bbox[1] < bbox[3] <= 1
            or region.get("result", {}).get("image_ocr")
        ):
            raise invalid()
        assets.add((asset, number))
        image_layout = parse_mineru_page(region["result"])
        text_blocks = [b for b in image_layout.blocks if b.text.strip()]
        if not text_blocks:
            warnings.append(f"image_text_unresolved:{asset}")
        for block in text_blocks:
            x0, y0, x1, y1 = block.bbox
            blocks.append(
                replace(
                    block,
                    order=len(blocks) + 1,
                    bbox=(
                        bbox[0] + x0 * (bbox[2] - bbox[0]),
                        bbox[1] + y0 * (bbox[3] - bbox[1]),
                        bbox[0] + x1 * (bbox[2] - bbox[0]),
                        bbox[1] + y1 * (bbox[3] - bbox[1]),
                    ),
                    requires_review=True,
                    source_image_asset_no=asset,
                )
            )
    return PageLayout(tuple(blocks), tuple(warnings))
