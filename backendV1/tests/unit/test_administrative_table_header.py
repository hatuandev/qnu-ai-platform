from qnu.domains.knowledge.index.facts import project_table
from qnu.domains.knowledge.index.table_dependencies import administrative_header


def test_administrative_header_detected_for_task_table():
    # Administrative table matching KH 130 / standard administrative tasks
    table = {
        "rows": [
            [
                {"text": "TT", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Nội dung", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Thời gian thực hiện", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Đơn vị chủ trì", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Đơn vị phối hợp", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Ghi chú", "header": False, "row_span": 1, "col_span": 1},
            ],
            [
                {"text": "1", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Nhiệm vụ chuẩn bị phòng phỏng vấn", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Trước 01/06/2026", "header": False, "row_span": 1, "col_span": 1},
                {"text": "P.KT&BĐCL", "header": False, "row_span": 1, "col_span": 1},
                {"text": "BTK, NCT", "header": False, "row_span": 1, "col_span": 1},
                {"text": "", "header": False, "row_span": 1, "col_span": 1},
            ],
            [
                {"text": "2", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Bảo đảm đường truyền mạng Internet", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Trong quá trình ĐGN", "header": False, "row_span": 1, "col_span": 1},
                {"text": "TT. S&HL", "header": False, "row_span": 1, "col_span": 1},
                {"text": "Các đơn vị", "header": False, "row_span": 1, "col_span": 1},
                {"text": "", "header": False, "row_span": 1, "col_span": 1},
            ],
        ],
        "column_count": 6,
    }

    assert administrative_header(table) is True

    # Verify project_table projects into UniversalFact instead of raw_rows
    proj = project_table(table, table_id="test_tbl", source_table_citation="cit:tbl1")
    assert proj.has_header is True
    assert proj.storage_mode == "facts"
    assert len(proj.facts) == 2
    assert len(proj.raw_rows) == 0
    assert "Đơn vị chủ trì" in proj.facts[0].attributes
    assert proj.facts[0].attributes["Đơn vị chủ trì"].raw == "P.KT&BĐCL"


def test_administrative_header_rejects_headerless_data_table():
    # Headerless table matching Table 4 of 07/KH-AM
    table = {
        "rows": [
            [
                {"text": "Alpha", "header": False, "row_span": 1, "col_span": 1},
                {"text": "North", "header": False, "row_span": 1, "col_span": 1},
            ],
            [
                {"text": "Beta", "header": False, "row_span": 1, "col_span": 1},
                {"text": "South", "header": False, "row_span": 1, "col_span": 1},
            ],
            [
                {"text": "Gamma", "header": False, "row_span": 1, "col_span": 1},
                {"text": "East", "header": False, "row_span": 1, "col_span": 1},
            ],
        ],
        "column_count": 2,
    }

    assert administrative_header(table) is False

    # Verify project_table keeps as raw_rows
    proj = project_table(table, table_id="test_headerless", source_table_citation="cit:tbl4")
    assert proj.has_header is False
    assert proj.storage_mode == "raw_rows"
    assert len(proj.facts) == 0
    assert len(proj.raw_rows) == 3
