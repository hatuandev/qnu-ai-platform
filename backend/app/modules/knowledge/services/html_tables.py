"""Flatten explicit HTML table spans without inferring missing cell values."""

import re
from html.parser import HTMLParser


class _TableGrid(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.spanned: dict[tuple[int, int], str] = {}
        self.cell: list[str] | None = None
        self.row = -1
        self.column = 0
        self.span = (1, 1)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row += 1
            self.column = 0
            self.rows.append([])
        elif tag in {"th", "td"}:
            self.cell = []
            attributes = dict(attrs)
            self.span = tuple(max(1, min(64, int(attributes.get(key) or "1"))) for key in ("rowspan", "colspan"))
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag not in {"td", "th"} or self.cell is None or self.row < 0:
            return
        while (self.row, self.column) in self.spanned:
            self.column += 1
        value = "".join(self.cell).strip().replace("|", r"\|").replace("\n", " ")
        for offset_row in range(self.span[0]):
            for offset_col in range(self.span[1]):
                self.spanned[self.row + offset_row, self.column + offset_col] = "" if tag == "th" and offset_row else value
        self.column += self.span[1]
        self.cell = None

    def markdown(self) -> str:
        width = max((column + 1 for _, column in self.spanned), default=0)
        if width < 2 or not self.rows:
            return "\n".join(dict.fromkeys(self.spanned.values()))
        rows = [[self.spanned.get((row, col), "") for col in range(width)] for row in range(len(self.rows))]
        output = ["| " + " | ".join(row) + " |" for row in rows]
        output.insert(1, "| " + " | ".join(["---"] * width) + " |")
        return "\n\n" + "\n".join(output) + "\n\n"


def normalize_html_tables(markdown: str) -> str:
    def convert(match: re.Match[str]) -> str:
        parser = _TableGrid()
        try:
            parser.feed(match.group())
        except ValueError:
            # Keep malformed evidence intact; the structural gate will request review.
            return match.group()
        return parser.markdown()

    return re.sub(r"<table\b[^>]*>.*?</table\s*>", convert, markdown, flags=re.IGNORECASE | re.DOTALL)
