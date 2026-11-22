"""Unit tests for direct Markdown (.md) extraction pipeline."""

import pytest

from qnu.domains.knowledge.compilation.schemas import DRAFT_PARAGRAPH_TEXT_LIMIT
from qnu.domains.ocr.direct_md import MD_PARAGRAPH_TEXT_LIMIT, extract_md
from qnu.platform.errors import AppException


def test_extract_md_empty_payload_raises():
    with pytest.raises(AppException) as exc_info:
        extract_md(b"")
    assert exc_info.value.code == "md_empty"


def test_extract_md_whitespace_only_raises():
    with pytest.raises(AppException) as exc_info:
        extract_md(b"   \n\n  \t  \n")
    assert exc_info.value.code == "md_empty_content"


def test_extract_md_headings_and_paragraphs():
    md = b"""# Tieu de 1
Noi dung doan 1.

## Tieu de 2
Noi dung doan 2 dong 1.
Noi dung doan 2 dong 2.

### Tieu de 3
- Muc danh sach 1
- Muc danh sach 2
"""
    rendered, plan = extract_md(md)
    assert rendered.extension == ".md"
    assert rendered.renderer["name"] == "native_md"
    assert len(plan.pages) == 1

    blocks = plan.pages[0].layout.blocks
    # 3 headings + 3 paragraphs = 6 blocks
    assert len(blocks) == 6

    # Block 0: Heading 1
    assert blocks[0].kind == "title"
    assert blocks[0].label == "Heading 1"
    assert blocks[0].text == "# Tieu de 1"

    # Block 1: Paragraph 1
    assert blocks[1].kind == "text"
    assert blocks[1].text == "Noi dung doan 1."

    # Block 2: Heading 2
    assert blocks[2].kind == "title"
    assert blocks[2].label == "Heading 2"
    assert blocks[2].text == "## Tieu de 2"

    # Block 3: Paragraph 2
    assert blocks[3].kind == "text"
    assert "Noi dung doan 2 dong 1." in blocks[3].text
    assert "Noi dung doan 2 dong 2." in blocks[3].text

    # Block 4: Heading 3
    assert blocks[4].kind == "title"
    assert blocks[4].label == "Heading 3"

    # Block 5: List
    assert blocks[5].kind == "text"
    assert "- Muc danh sach 1" in blocks[5].text


def test_extract_md_table_parsed():
    md = b"""# Bang diem

| Diem he 10 | Diem chu | Diem he 4 | Xep loai |
| :--- | :---: | :---: | --- |
| 8.5 - 10.0 | A | 4.0 | Gioi |
| 7.0 - 8.4 | B | 3.0 | Kha |
| 5.5 - 6.9 | C | 2.0 | Trung binh |

Doan van ket thuc.
"""
    _rendered, plan = extract_md(md)
    blocks = plan.pages[0].layout.blocks

    assert len(blocks) == 3
    assert blocks[0].kind == "title"

    table_block = blocks[1]
    assert table_block.kind == "table"
    assert table_block.table is not None
    assert table_block.table.status == "parsed"
    assert table_block.table.column_count == 4
    # 1 header + 3 data rows = 4 rows
    assert len(table_block.table.rows) == 4

    # Header check
    header_row = table_block.table.rows[0]
    assert [c.text for c in header_row] == ["Diem he 10", "Diem chu", "Diem he 4", "Xep loai"]
    assert all(c.header for c in header_row)

    # Data row check
    data_row_1 = table_block.table.rows[1]
    assert [c.text for c in data_row_1] == ["8.5 - 10.0", "A", "4.0", "Gioi"]
    assert all(not c.header for c in data_row_1)

    # Ending paragraph
    assert blocks[2].kind == "text"
    assert blocks[2].text == "Doan van ket thuc."


def test_extract_md_fenced_code_block_preserves_characters():
    md = b"""# Huong dan

```python
# Day la code comment, khong phai heading
| col1 | col2 |
| --- | --- |
| val1 | val2 |
```

Doan van sau code.
"""
    _rendered, plan = extract_md(md)
    blocks = plan.pages[0].layout.blocks

    # 1 heading + 1 code block + 1 text block = 3 blocks
    assert len(blocks) == 3
    assert blocks[0].kind == "title"

    code_block = blocks[1]
    assert code_block.label == "Code"
    assert code_block.table is None
    assert "# Day la code comment" in code_block.text
    assert "| col1 | col2 |" in code_block.text

    assert blocks[2].text == "Doan van sau code."


def test_extract_md_frontmatter_ignored():
    md = b"""---
title: Tai lieu quy che
author: QNU
date: 2026-01-01
---

# Noi dung chinh

Day la doan mo dau.
"""
    _rendered, plan = extract_md(md)
    blocks = plan.pages[0].layout.blocks

    assert len(blocks) == 2
    assert blocks[0].text == "# Noi dung chinh"
    assert blocks[1].text == "Day la doan mo dau."


def test_extract_md_long_paragraph_splits_within_limit():
    long_text = "TuKhoa " * 700  # ~4900 chars > 4000
    md = f"# Tieu de\n\n{long_text}".encode()

    _rendered, plan = extract_md(md)
    blocks = plan.pages[0].layout.blocks

    # Should split into at least 2 text blocks
    text_blocks = [b for b in blocks if b.kind == "text"]
    assert len(text_blocks) >= 2
    for b in text_blocks:
        assert len(b.text) <= MD_PARAGRAPH_TEXT_LIMIT
        assert len(b.text) <= DRAFT_PARAGRAPH_TEXT_LIMIT
