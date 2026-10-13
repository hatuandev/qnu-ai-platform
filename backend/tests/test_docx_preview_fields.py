"""Preview copies preserve source formula results rather than recalculate them."""

from io import BytesIO
from zipfile import ZipFile

import pytest
from lxml import etree

from app.core.exceptions import AppException
from app.modules.knowledge.services.docx_preview_fields import preserve_table_formula_results

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def package(body: str) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{NS}"><w:body>{body}</w:body></w:document>')
        archive.writestr("word/styles.xml", b"unchanged-styles")
    return stream.getvalue()


def field(instruction: str, result: str) -> str:
    return (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText>{instruction}</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r><w:rPr><w:b/></w:rPr><w:t>{result}</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )


def root(content: bytes) -> etree._Element:
    with ZipFile(BytesIO(content)) as archive:
        assert archive.read("word/styles.xml") == b"unchanged-styles"
        return etree.fromstring(archive.read("word/document.xml"))


def test_formula_in_merged_table_is_materialized_but_page_field_survives() -> None:
    original = package(
        '<w:tbl><w:tr><w:tc><w:tcPr><w:gridSpan w:val="3"/></w:tcPr>'
        f'<w:p>{field(" =SUM(ABOVE) ", "1070")}</w:p></w:tc></w:tr></w:tbl>'
        f'<w:p>{field(" PAGE ", "7")}</w:p>'
    )
    transformed = root(preserve_table_formula_results(original))
    instructions = transformed.findall(f".//{{{NS}}}instrText")
    assert [node.text for node in instructions] == [" PAGE "]
    assert transformed.find(f".//{{{NS}}}gridSpan").get(f"{{{NS}}}val") == "3"
    assert transformed.find(f".//{{{NS}}}b") is not None
    assert [node.text for node in transformed.findall(f".//{{{NS}}}t")] == ["1070", "7"]
    assert "SUM" in "".join(root(original).itertext())


def test_simple_formula_and_split_instruction() -> None:
    content = package('<w:tbl><w:tr><w:tc><w:p><w:fldSimple w:instr=" = A1 + A2 ">'
                      '<w:r><w:t>451</w:t></w:r></w:fldSimple></w:p></w:tc></w:tr></w:tbl>')
    result = root(preserve_table_formula_results(content))
    assert result.find(f".//{{{NS}}}fldSimple") is None
    assert result.find(f".//{{{NS}}}t").text == "451"


def test_missing_cached_formula_result_fails_closed() -> None:
    content = package(f'<w:tbl><w:tr><w:tc><w:p>{field("=SUM(ABOVE)", "")}</w:p></w:tc></w:tr></w:tbl>')
    with pytest.raises(AppException) as error:
        preserve_table_formula_results(content)
    assert error.value.code == "DOCX_FORMULA_RESULT_MISSING"


def test_non_formula_document_is_byte_identical() -> None:
    content = package(f'<w:p>{field("NUMPAGES", "7")}</w:p>')
    assert preserve_table_formula_results(content) == content


def test_invalid_docx_is_rejected_without_calling_converter() -> None:
    with pytest.raises(AppException) as error:
        preserve_table_formula_results(b"not a zip archive")
    assert error.value.code == "DOCX_PREVIEW_INVALID"


def test_page_field_inside_table_is_unchanged() -> None:
    content = package(f'<w:tbl><w:tr><w:tc><w:p>{field("PAGE", "7")}</w:p></w:tc></w:tr></w:tbl>')
    assert preserve_table_formula_results(content) == content


def test_unclosed_formula_is_rejected() -> None:
    formula = field("=SUM(ABOVE)", "1070").replace('<w:r><w:fldChar w:fldCharType="end"/></w:r>', "")
    content = package(f'<w:tbl><w:tr><w:tc><w:p>{formula}</w:p></w:tc></w:tr></w:tbl>')
    with pytest.raises(AppException) as error:
        preserve_table_formula_results(content)
    assert error.value.code == "DOCX_FORMULA_MALFORMED"


def test_split_instruction_and_shared_run_preserve_visible_formatting() -> None:
    formula = field("=SUM(ABOVE)", "402").replace(
        "<w:instrText>=SUM(ABOVE)</w:instrText>",
        "<w:instrText>=SUM(</w:instrText></w:r><w:r><w:instrText>ABOVE)</w:instrText>",
    )
    content = package(f'<w:tbl><w:tr><w:tc><w:p>{formula}</w:p></w:tc></w:tr></w:tbl>')
    result = root(preserve_table_formula_results(content))
    assert result.find(f".//{{{NS}}}instrText") is None
    assert result.find(f".//{{{NS}}}t").text == "402"


def test_nested_formula_does_not_silently_flatten_page_fields() -> None:
    formula = field("=SUM(ABOVE)", "351").replace(
        '<w:t>351</w:t>', f'<w:t>351</w:t></w:r>{field("PAGE", "7")}<w:r>',
    )
    content = package(f'<w:tbl><w:tr><w:tc><w:p>{formula}</w:p></w:tc></w:tr></w:tbl>')
    with pytest.raises(AppException) as error:
        preserve_table_formula_results(content)
    assert error.value.code == "DOCX_FORMULA_NESTED_UNSUPPORTED"


@pytest.mark.asyncio
async def test_gotenberg_receives_only_the_preview_copy() -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.modules.knowledge.services.ingestion_service import IngestionService

    content = package(f'<w:tbl><w:tr><w:tc><w:p>{field("=SUM(ABOVE)", "1070")}</w:p></w:tc></w:tr></w:tbl>')
    client = AsyncMock()
    client.post.return_value = MagicMock(status_code=200, content=b"%PDF-preview")
    factory = MagicMock()
    factory.return_value.__aenter__.return_value = client
    with patch("httpx.AsyncClient", factory):
        assert await IngestionService()._convert_office_to_pdf(content, "input.docx") == b"%PDF-preview"
    uploaded = client.post.call_args.kwargs["files"]["files"][1]
    assert root(uploaded).find(f".//{{{NS}}}instrText") is None
    assert root(content).find(f".//{{{NS}}}instrText") is not None
