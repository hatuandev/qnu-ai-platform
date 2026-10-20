"""Source structure and human projection regressions; no network or published writes."""
from copy import deepcopy

import pytest

from app.modules.knowledge.normalization.qnu_markdown import (
    QnuBlock,
    QnuSourceInfo,
    QnuStructuredDocument,
)
from app.modules.knowledge.parsers.pdf_structure import build_pdf_document


def pdf_page(number=1):
    return {'page': number, 'native': {'page': number, 'width': 600, 'height': 800,
        'bbox_space': 'pymupdf_unrotated_points', 'layout': {'blocks': []}, 'tables': [], 'images': []}}


def text(value, y, *, bold=False, x=40, width=500):
    return {'bbox': [x, y, x + width, y + 14], 'lines': [{'spans': [
        {'text': value, 'size': 12, 'flags': 16 if bold else 0, 'font': 'Times-Bold' if bold else 'Times'}]}]}


def test_same_size_pdf_sections_keep_source_parent_across_pages():
    first, second = pdf_page(), pdf_page(2)
    first['native']['layout']['blocks'] = [text('1. Schedule', 70, bold=True), text('The process starts after verification.', 100),
        text('1.1. Exceptions', 150, bold=True), text('Only the stated exceptions apply.', 180)]
    second['native']['layout']['blocks'] = [text('Continuation of the same exception.', 40), text('2. Location', 100, bold=True), text('Read the original location.', 130)]
    source = {'pages': [first, second]}
    frozen = deepcopy(source)
    document = build_pdf_document(source, filename='independent.pdf', sha256='a' * 64)
    headings = [b for b in document.blocks if b.type == 'section']
    assert [b.source_label for b in headings] == ['1.', '1.1.', '2.']
    assert headings[1].parent_id == headings[0].id and headings[2].parent_id is None
    continued = next(b for b in document.blocks if 'Continuation' in b.body)
    assert continued.parent_id == headings[1].id and len(continued.section_path) == 2
    assert source == frozen


def test_numbered_body_and_isolated_number_are_not_pdf_headings():
    page = pdf_page()
    page['native']['layout']['blocks'] = [text('1. Submit the completed form.', 70), text('2. Keep the original receipt.', 95), text('3', 120, bold=True)]
    document = build_pdf_document({'pages': [page]}, filename='body.pdf', sha256='b' * 64)
    assert not any(b.type == 'section' for b in document.blocks)


def test_reader_notes_are_derived_linked_and_do_not_change_raw_body():
    from app.modules.knowledge.normalization.qnu_reader import reader_document

    note = QnuBlock(id='n', type='note', body='\tFirst paragraph.\n\n\tSecond paragraph.',
        attributes={'role': 'footnote', 'source_anchors': [{'block_id': 'p', 'locator': 'xml#p1'}, {'block_id': 'p2', 'locator': 'xml#p2'}]})
    document = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='fixture.docx'), blocks=[
        QnuBlock(id='p', type='text', body='A source paragraph.', context_refs=['n']),
        QnuBlock(id='p2', type='text', body='Another source paragraph.', context_refs=['n']), note])
    frozen = document.model_dump()
    result = reader_document(document)
    assert '[^' in result['markdown'] and '\tFirst' not in result['markdown']
    assert len(result['notes']) == 1 and len(result['notes'][0]['anchors']) == 2
    assert document.model_dump() == frozen
    assert result == reader_document(document)


def test_reader_keeps_duplicate_note_text_as_separate_source_notes():
    from app.modules.knowledge.normalization.qnu_reader import reader_document

    document = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='f.docx'), blocks=[
        QnuBlock(id='n1', type='note', body='\tIdentical.', attributes={'role': 'footnote'}),
        QnuBlock(id='n2', type='note', body='\tIdentical.', attributes={'role': 'endnote'})])
    assert len(reader_document(document)['notes']) == 2


@pytest.mark.parametrize('value', ['0', '00028', '–', '/', ''])
def test_reader_table_values_remain_source_literals(value):
    from app.modules.knowledge.normalization.qnu_reader import reader_document

    document = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='f.docx'), blocks=[
        QnuBlock(id='t', type='table', attributes={'representation': 'records', 'columns': [{'id': 'c1', 'header_path': ['2034', 'Count (SV)']}]}),
        QnuBlock(id='r', type='table_row', parent_id='t', attributes={'fields': {'c1': {'raw': value, 'state': 'blank' if value == '' else 'present'}}})])
    table = next(b['table'] for b in reader_document(document)['blocks'] if b.get('table'))
    assert table['rows'][0][0] == value
    assert table['headers'] == ['2034 / Count (SV)']


def test_pdf_columns_and_repeated_margin_do_not_create_false_sections():
    first, second = pdf_page(), pdf_page(2)
    for page in (first, second):
        page['native']['layout']['blocks'] = [text('1. Repeated margin', 5, bold=True),
            text('1. Left section', 90, bold=True, width=200), text('Left column body.', 120, width=200),
            text('2. Right section', 90, bold=True, x=340, width=200), text('Right column body.', 120, x=340, width=200)]
    document = build_pdf_document({'pages': [first, second]}, filename='columns.pdf', sha256='a' * 64)
    assert not any('Repeated' in b.body and b.type == 'section' for b in document.blocks)
    assert sum(b.type == 'section' for b in document.blocks) == 4


def _numbered_docx():
    from io import BytesIO

    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    document = Document()
    root = document.part.numbering_part.element
    abstract = OxmlElement('w:abstractNum'); abstract.set(qn('w:abstractNumId'), '501')
    for index, fmt, pattern in [(0, 'decimal', '%1.'), (1, 'lowerLetter', '%2)'), (2, 'bullet', '•')]:
        level = OxmlElement('w:lvl'); level.set(qn('w:ilvl'), str(index))
        for name, val in [('start', '1'), ('numFmt', fmt), ('lvlText', pattern)]:
            child = OxmlElement('w:' + name); child.set(qn('w:val'), val); level.append(child)
        abstract.append(level)
    root.append(abstract)
    for num_id, start in [('501', 7), ('502', 3)]:
        number = OxmlElement('w:num'); number.set(qn('w:numId'), num_id)
        parent = OxmlElement('w:abstractNumId'); parent.set(qn('w:val'), '501'); number.append(parent)
        override = OxmlElement('w:lvlOverride'); override.set(qn('w:ilvl'), '0')
        beginning = OxmlElement('w:startOverride'); beginning.set(qn('w:val'), str(start)); override.append(beginning); number.append(override)
        root.append(number)

    def add(value, level, num='501'):
        p = document.add_paragraph(value)
        props = p._p.get_or_add_pPr(); numbering = OxmlElement('w:numPr')
        for tag, val in [('ilvl', str(level)), ('numId', num)]:
            element = OxmlElement('w:' + tag); element.set(qn('w:val'), val); numbering.append(element)
        props.append(numbering)
    add('Parent source item', 0)
    add('Child source item', 1)
    add('Condition one\nContinuation within the same item', 2)
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = 'Code'; table.cell(0, 1).text = 'Count'
    table.cell(1, 0).text = '00028'; table.cell(1, 1).text = '0'
    add('Child following the table', 1)
    document.add_page_break()
    add('Next parent on another page', 0)
    add('Restarted sequence', 0, '502')
    output = BytesIO(); document.save(output)
    return output.getvalue()


@pytest.mark.asyncio
async def test_docx_native_numbering_and_item_relations_survive_tables_and_restart():
    from app.modules.knowledge.parsers.docling_office_parser import DoclingOfficeParser
    from app.modules.knowledge.parsers.docling_structure import build_qnu_structured_document

    content = _numbered_docx()
    parsed = await DoclingOfficeParser('docx').parse(content, 'independent.docx')
    document = build_qnu_structured_document(parsed.docling_document, filename='independent.docx', sha256='a' * 64,
        source_evidence=parsed.docx_source_evidence, header_evidence=parsed.docx_header_evidence)
    items = [i for block in document.blocks for i in block.attributes.get('list_items', [])]
    assert [i['marker'] for i in items] == ['7.', 'a)', '•', 'b)', '8.', '3.']
    assert items[3]['parent_id'] == items[0]['id']
    assert all(i['source_locator'] and i['numbering']['num_id'] for i in items)
    assert 'Continuation within the same item' in items[2]['text']
    assert any(b.type == 'table' for b in document.blocks)
    assert '<!-- source-list-restart -->' in '\n'.join(b.body for b in document.blocks)


def test_reader_rejects_inconsistent_span_layout_without_changing_cell_values():
    from app.modules.knowledge.normalization.qnu_reader import reader_document

    table = QnuBlock(id='t', type='table', attributes={'representation': 'records', 'columns': [{'id': 'c', 'header_path': ['Count']}]},
        source_data={'num_rows': 2, 'num_cols': 1, 'header_rows': 1, 'cells': [
            {'text': 'Count', 'row_start': 0, 'row_end': 1, 'col_start': 0, 'col_end': 1},
            {'text': '999', 'row_start': 1, 'row_end': 2, 'col_start': 0, 'col_end': 1}]})
    row = QnuBlock(id='r', parent_id='t', type='table_row', attributes={'fields': {'c': {'raw': '0', 'state': 'present'}}})
    doc = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='f.docx'), blocks=[table, row])
    result = reader_document(doc)['blocks'][0]['table']
    assert result['layout'] is None and result['rows'] == [['0']]


def test_pdf_heading_at_page_end_uses_following_page_without_inventing_a_page():
    first, second = pdf_page(), pdf_page(2)
    first['native']['layout']['blocks'] = [text('1. Late section', 760, bold=True)]
    second['native']['layout']['blocks'] = [text('Body of the same section.', 40)]
    document = build_pdf_document({'pages': [first, second]}, filename='page-end.pdf', sha256='a' * 64)
    assert document.blocks[0].type == 'section'
    assert document.blocks[1].parent_id == document.blocks[0].id
    assert document.blocks[0].source_locations[0].page == 1


def test_large_isolated_pdf_number_is_not_a_heading():
    page = pdf_page()
    number = text('2034', 70, bold=True); number['lines'][0]['spans'][0]['size'] = 18
    page['native']['layout']['blocks'] = [number, text('A sufficiently long ordinary source paragraph about the current task.', 110)]
    document = build_pdf_document({'pages': [page]}, filename='number.pdf', sha256='a' * 64)
    assert not any(b.type == 'section' for b in document.blocks)


def test_native_heading_leading_blank_line_does_not_break_markdown_heading():
    page = pdf_page()
    raw = text(' \n1. Source section ', 70, bold=True)
    page['native']['layout']['blocks'] = [raw, text('Following source body.', 110)]
    document = build_pdf_document({'pages': [page]}, filename='blank.pdf', sha256='a' * 64)
    assert document.blocks[0].body == '## 1. Source section'
    assert document.blocks[0].source_data['raw'] == raw


def test_repeated_references_and_complex_note_keep_identity_and_raw_tabs():
    from app.modules.knowledge.normalization.qnu_reader import reader_document
    from app.modules.knowledge.parsers.docx_evidence import apply_docx_evidence

    doc = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='f.docx'), blocks=[QnuBlock(id='p', type='text', body='Reference paragraph.')])
    ref = {'part': 'footnote', 'id': '7'}
    evidence = {'paragraphs': [{'locator': 'xml#p1', 'style': [], 'table': None, 'text': 'Reference paragraph.', 'notes': [ref, ref]}],
                'notes': [{'part': 'footnote', 'id': '7', 'text': '\tLiteral note.', 'locator': 'notes#7', 'complex_structure': True}]}
    apply_docx_evidence(doc, evidence)
    note = doc.blocks[-1]
    assert note.body == '\tLiteral note.' and len(note.attributes['source_anchors']) == 2
    view = reader_document(doc)
    assert len(view['notes'][0]['anchors']) == 2
    assert len({a['id'] for a in view['notes'][0]['anchors']}) == 2
    assert view['limitations'][0]['code'] == 'source_note_structure_unresolved'


def test_missing_note_target_is_reported_without_fabricating_a_note():
    from app.modules.knowledge.normalization.qnu_reader import reader_document
    from app.modules.knowledge.parsers.docx_evidence import apply_docx_evidence

    doc = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='f.docx'), blocks=[QnuBlock(id='p', type='text', body='Reference.')])
    evidence = {'paragraphs': [{'locator': 'xml#p1', 'style': [], 'table': None, 'text': 'Reference.', 'notes': [{'part': 'endnote', 'id': '7'}]}], 'notes': []}
    apply_docx_evidence(doc, evidence)
    view = reader_document(doc)
    assert not view['notes'] and view['limitations'][0]['code'] == 'source_note_missing'


def test_note_in_child_item_stays_at_that_item_in_the_reader():
    from app.modules.knowledge.normalization.qnu_reader import reader_document

    items = [{'id': 'i1', 'level': 0, 'marker': '7.', 'text': 'Parent.'},
             {'id': 'i2', 'level': 1, 'marker': 'a)', 'text': 'Child.'}]
    doc = QnuStructuredDocument(title='Fixture', source=QnuSourceInfo(filename='f.docx'), blocks=[
        QnuBlock(id='l', type='list', attributes={'list_items': items}),
        QnuBlock(id='n', type='note', body='\tNote.', attributes={'role': 'footnote', 'source_anchors': [
            {'block_id': 'l', 'item_id': 'i2', 'locator': 'xml#p2', 'table': None}]})])
    view = reader_document(doc)
    assert 'Child.[1](#qnu-' in view['blocks'][0]['markdown']
    assert not view['blocks'][0]['references']
    assert len(view['blocks'][0]['embedded_references']) == 1
    assert 'Child.[^qnu-' in view['markdown'] and 'Parent.[^' not in view['markdown']
