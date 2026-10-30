"""Word fixtures need a valid package, not merely XML the test parser tolerates."""

import io
import posixpath
import zipfile
from xml.etree import ElementTree

from qnu.domains.ocr.artifacts.docx_html import convert_docx_to_html
from qnu.domains.ocr.native_docx import _Tables
from tests.docx_fixture import W, docx_with_table


def test_docx_fixture_registers_and_links_all_word_parts():
    with zipfile.ZipFile(io.BytesIO(docx_with_table())) as archive:
        assert archive.testzip() is None
        types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
        overrides = {n.attrib.get("PartName"): n.attrib.get("ContentType") for n in types}
        for part, kind in (
            ("document", "document.main"),
            ("styles", "styles"),
            ("footnotes", "footnotes"),
        ):
            assert overrides["/word/" + part + ".xml"] == (
                "application/vnd.openxmlformats-officedocument.wordprocessingml." + kind + "+xml"
            )
        root = ElementTree.fromstring(archive.read("_rels/.rels"))
        assert any(
            n.attrib["Type"].endswith("/officeDocument")
            and n.attrib["Target"] == "word/document.xml"
            for n in root
        )
        linked = ElementTree.fromstring(archive.read("word/_rels/document.xml.rels"))
        for relation in linked:
            target = posixpath.normpath("word/" + relation.attrib["Target"])
            ElementTree.fromstring(archive.read(target))
        document = ElementTree.fromstring(archive.read("word/document.xml"))
        notes = ElementTree.fromstring(archive.read("word/footnotes.xml"))
        note_ids = {n.get(f"{{{W}}}id") for n in notes}
        assert all(
            n.get(f"{{{W}}}id") in note_ids for n in document.iter(f"{{{W}}}footnoteReference")
        )


def test_docx_fixture_keeps_multilevel_headers_merges_literals_and_footnote():
    converted = convert_docx_to_html(docx_with_table())
    parser = _Tables()
    parser.feed(converted.html)
    assert len(parser.tables) == 1
    table = parser.tables[0]
    cells = [c for row in table.rows for c in row]
    assert all(c.header for c in table.rows[0])
    assert any(c.header and c.col_span == 2 and c.text == "Năm" for c in cells)
    assert any(c.row_span == 2 and c.text == "Ghi chú" for c in cells)
    assert {"0", "-", "", "2023", "2024", "150"} <= {c.text for c in cells}
    assert converted.footnotes == 1 and "Ghi chú: số liệu năm 2023." in converted.html
