"""A1: source-mined abbreviation catalog and query-time lexical alias expansion."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from qnu.domains.knowledge.index import abbreviations, contextual, hybrid
from qnu.domains.knowledge.index import search as search_module
from qnu.domains.knowledge.index.schemas import SearchRequest
from qnu.domains.knowledge.metadata import MetadataFilter


def _cell(text: str, evidence_id: str, *, header: bool = False) -> dict:
    return {
        "text": text,
        "evidence_id": evidence_id,
        "header": header,
        "row_span": 1,
        "col_span": 1,
    }


def _source(rows=(), *, status="parsed", extra_tables=()):
    run = "ocr"
    table = {
        "status": status,
        "row_count": len(rows),
        "column_count": 3,
        "rows": [list(row) for row in rows],
    }
    citations = {run + ":ev-block": {"page": 1}, run + ":ev-table": {"page": 1}}
    for row in rows:
        for cell in row:
            citations[run + ":" + cell["evidence_id"]] = {"page": 1}
    documents = [
        {
            "ocr_run_id": run,
            "pages": [
                {
                    "page_number": 1,
                    "blocks": [
                        {"evidence_id": "ev-block", "text": "Quy chế ban hành.", "label": "Text"},
                        {"evidence_id": "ev-table", "text": "Bảng viết tắt.", "label": "Table"},
                    ],
                }
            ],
        }
    ]
    content = {
        "title": "Quy chế đào tạo",
        "citations": citations,
        "sections": [],
        "source_tables": [
            {"citation": run + ":ev-table", "page_number": 1, "table": table},
            *extra_tables,
        ],
    }
    return content, documents


HEADER = [
    _cell("STT", "h0", header=True),
    _cell("Viết tắt", "h1", header=True),
    _cell("Diễn giải", "h2", header=True),
]


def test_table_rows_define_aliases_only_when_initials_and_evidence_agree():
    content, documents = _source(
        [
            HEADER,
            [_cell("1", "c00"), _cell("CĐR", "c01"), _cell("Chuẩn đầu ra", "c02")],
            [_cell("2", "c10"), _cell("hdh", "c11"), _cell("Hải dương học", "c12")],
            [_cell("3", "c20"), _cell("NXB", "c21"), _cell("Nhà xuất bản sách", "c22")],
            [_cell("4", "c30"), _cell("ĐBCL", "c31"), _cell("Đảm bảo chất lượng", "c32")],
            [_cell("5", "c40"), _cell("XYZ", "c41"), _cell("", "c42")],
            [_cell("6", "c50"), _cell("", "c51"), _cell("Xe yên zé", "c52")],
            [_cell("7", "c60"), _cell("KQ", "c61"), _cell("Kết quả", "c62")],
        ]
    )
    del content["citations"]["ocr:c61"]
    catalog = abbreviations.mine(content, documents)
    aliases = {entry["alias"]: entry for entry in catalog["definitions"]}
    assert catalog["version"] == abbreviations.VERSION
    assert catalog["truncated"] is False
    assert set(aliases) == {"CĐR", "ĐBCL"}
    assert aliases["CĐR"]["expansion"] == "Chuẩn đầu ra"
    assert aliases["CĐR"]["citation"] == "ocr:c02"
    assert aliases["CĐR"]["quote"] == "Chuẩn đầu ra"


def test_unparsed_tables_are_not_mined():
    run = "ocr"
    rows = [[_cell("1", "c00"), _cell("ZZ", "c01"), _cell("Zê zê", "c02")]]
    unparsed = {
        "status": "review_required",
        "row_count": 1,
        "column_count": 3,
        "rows": rows,
    }
    content, documents = _source([])
    content["source_tables"] = [
        {"citation": run + ":ev-table", "page_number": 1, "table": unparsed}
    ]
    for cell in rows[0]:
        content["citations"][run + ":" + cell["evidence_id"]] = {"page": 1}
    assert abbreviations.mine(content, documents)["definitions"] == []


def test_parenthetical_definitions_are_shared_with_search_context():
    content, documents = _source([])
    documents[0]["pages"][0]["blocks"].append(
        {"evidence_id": "ev-def", "text": "Chuẩn đầu ra (CĐR) được quy định.", "label": "Text"}
    )
    content["citations"]["ocr:ev-def"] = {"page": 1}
    catalog = abbreviations.mine(content, documents)
    assert [entry["alias"] for entry in catalog["definitions"]] == ["CĐR"]
    assert catalog["definitions"] == contextual.glossary(content, documents)


CATALOG = {
    "version": abbreviations.VERSION,
    "definitions": [
        {
            "alias": "CĐR",
            "expansion": "Chuẩn đầu ra",
            "citation": "ocr:e1",
            "quote": "Chuẩn đầu ra",
        },
        {
            "alias": "HDH",
            "expansion": "Hải dương học",
            "citation": "ocr:e2",
            "quote": "Hải dương học",
        },
    ],
}


def test_expand_matches_whole_alias_words_and_keeps_the_original_query():
    text, trace = abbreviations.expand("CĐR của ngành K46 là gì?", CATALOG)
    assert trace["applied"] == [{"alias": "CĐR", "expansion": "Chuẩn đầu ra"}]
    assert text.startswith("CĐR của ngành K46 là gì?\n")
    assert "Chuẩn đầu ra" in text and "Hải dương học" not in text

    text, trace = abbreviations.expand("cđr và CĐRX", CATALOG)
    assert trace["applied"] == [{"alias": "CĐR", "expansion": "Chuẩn đầu ra"}]

    text, trace = abbreviations.expand("Quy chế hiện hành?", CATALOG)
    assert text == "Quy chế hiện hành?" and trace["applied"] == []

    text, trace = abbreviations.expand("CĐR của Chuẩn đầu ra", CATALOG)
    assert text == "CĐR của Chuẩn đầu ra" and trace["applied"] == []

    assert abbreviations.expand("CĐR", None) == ("CĐR", {})
    assert abbreviations.expand("CĐR", {"version": "qnu.index-abbreviations/v0"})[0] == "CĐR"


def test_ambiguous_aliases_are_never_guessed():
    catalog = {
        "version": abbreviations.VERSION,
        "definitions": [
            *CATALOG["definitions"],
            {
                "alias": "CĐR",
                "expansion": "Chuẩn đầu ra khác",
                "citation": "ocr:e3",
                "quote": "Chuẩn đầu ra khác",
            },
        ],
    }
    text, trace = abbreviations.expand("CĐR là gì?", catalog)
    assert text == "CĐR là gì?"
    assert trace["applied"] == [] and trace["ambiguous"] == ["CĐR"]


def test_expansion_is_bounded_and_deterministic():
    catalog = {
        "version": abbreviations.VERSION,
        "definitions": [
            {
                "alias": f"A{index}",
                "expansion": f"An {index}",
                "citation": "ocr:e",
                "quote": "",
            }
            for index in range(12)
        ],
    }
    query = " ".join(f"A{index}" for index in range(12))
    text, trace = abbreviations.expand(query, catalog)
    assert text.startswith(query + "\n")
    assert len(trace["applied"]) == abbreviations.MAX_QUERY_EXPANSIONS
    assert trace["truncated"] is True
    assert [entry["alias"] for entry in trace["applied"]] == sorted(
        f"A{index}" for index in range(12)
    )[: abbreviations.MAX_QUERY_EXPANSIONS]


def test_catalog_merge_is_order_independent_and_bounded():
    entries = [
        {
            "alias": f"A{index}",
            "expansion": f"An {index}",
            "citation": "ocr:e",
            "quote": "",
        }
        for index in range(abbreviations.MAX_ENTRIES + 5)
    ]
    catalog = abbreviations.merge([{"version": abbreviations.VERSION, "definitions": entries}])
    assert catalog["version"] == abbreviations.VERSION
    assert len(catalog["definitions"]) == abbreviations.MAX_ENTRIES
    assert catalog["truncated"] is True
    reversed_catalog = abbreviations.merge(
        [{"version": abbreviations.VERSION, "definitions": list(reversed(entries))}]
    )
    assert catalog == reversed_catalog


def _wire(monkeypatch, catalog):
    run = SimpleNamespace(
        id="run",
        generation=3,
        workspace_id="ws",
        collection_id="col",
        provider_id="prov",
        manifest_sha256="sha",
        vector_collection="vectors",
        config={
            "vector_target_hash": "target",
            "provider": {"configuration_hash": "embed-hash"},
            **({"abbreviations": catalog} if catalog else {}),
        },
    )
    calls, embedded = [], []

    async def lexical(db, run, allowed, text, count, chunk_ids=None, *, phrases=False):
        calls.append({"text": text, "phrases": phrases})
        return []

    async def query_vector(db, actor, run, text, model):
        embedded.append(text)
        return [0.5]

    monkeypatch.setattr(hybrid, "lexical", lexical)
    monkeypatch.setattr(search_module, "resolve_workspace_access", AsyncMock())
    monkeypatch.setattr(search_module, "authorize", AsyncMock())
    monkeypatch.setattr(
        search_module, "manifest", AsyncMock(return_value={"chunks": [], "config": run.config})
    )
    monkeypatch.setattr(
        search_module,
        "_eligible",
        AsyncMock(
            return_value=(
                [
                    SimpleNamespace(
                        id="input",
                        version_id="ver",
                        document_id="doc",
                        publication_decision_id="pub",
                    )
                ],
                [],
            )
        ),
    )
    monkeypatch.setattr(search_module, "metadata_chunk_ids", AsyncMock(return_value=None))
    monkeypatch.setattr(
        search_module, "published_versions", AsyncMock(return_value=[SimpleNamespace(id="ver")])
    )
    monkeypatch.setattr(search_module, "_query_vector", query_vector)
    monkeypatch.setattr(
        search_module,
        "resolve_embedding_runtime",
        AsyncMock(return_value=SimpleNamespace(configuration_hash="embed-hash")),
    )
    monkeypatch.setattr(search_module, "_hits", AsyncMock(return_value=[]))
    db = SimpleNamespace(
        scalar=AsyncMock(return_value=run),
        execute=AsyncMock(
            return_value=SimpleNamespace(one_or_none=lambda: (run.id, run.manifest_sha256))
        ),
        commit=AsyncMock(),
    )
    vectors = SimpleNamespace(target_hash="target", search=AsyncMock(return_value=[]))
    return db, vectors, calls, embedded


@pytest.mark.asyncio
async def test_search_adds_one_expanded_lexical_branch_only(monkeypatch):
    db, vectors, calls, embedded = _wire(monkeypatch, CATALOG)
    request = SearchRequest(
        query="Điều kiện CĐR của ngành là gì?",
        top_k=5,
        candidate_k=30,
        mode="hybrid",
        metadata_filter=MetadataFilter(data_year=2031),
    )
    result = await search_module.search(db, None, None, vectors, None, "ws", "col", request)
    assert [call["text"] for call in calls[:2]] == [request.query, request.query]
    assert calls[2]["phrases"] is False and "Chuẩn đầu ra" in calls[2]["text"]
    assert len(calls) == 3
    assert embedded == [request.query]
    assert result.trace["glossary_expansions"] == [{"alias": "CĐR", "expansion": "Chuẩn đầu ra"}]
    assert result.trace["fusion_branches"] == [
        "dense",
        "lexical",
        "lexical_phrases",
        "lexical_expanded",
    ]
    assert result.trace["score_kinds"]["lexical_expanded"] == "postgres_ts_rank_cd_alias"
    assert search_module.metadata_chunk_ids.await_count == 2
    assert all(
        call.args[3] == MetadataFilter(data_year=2031)
        for call in search_module.metadata_chunk_ids.await_args_list
    )


@pytest.mark.asyncio
async def test_search_without_a_catalog_keeps_the_existing_branches(monkeypatch):
    db, vectors, calls, embedded = _wire(monkeypatch, None)
    request = SearchRequest(
        query="Điều kiện CĐR của ngành là gì?", top_k=5, candidate_k=30, mode="hybrid"
    )
    result = await search_module.search(db, None, None, vectors, None, "ws", "col", request)
    assert len(calls) == 2
    assert result.trace["glossary_expansions"] == []
    assert result.trace["fusion_branches"] == ["dense", "lexical", "lexical_phrases"]
    assert embedded == [request.query]
