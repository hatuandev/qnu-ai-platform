"""Read-only coordinates for legacy facts whose identity/metric labels are incomplete."""

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.knowledge.entity_codes import code_candidates, normalize_code
from app.modules.knowledge.facts import detect_column_role
from app.modules.knowledge.models import KnowledgeIndexRevision, KnowledgeSourceRevision
from app.modules.knowledge.parsers.markdown_parser import _split_gfm_row
from app.modules.knowledge.services.source_artifact import cell_context, get_source_artifact
from app.modules.knowledge.services.table_context import clean_cell, row_identities
from app.modules.rag.evidence_blocks import load_published_blocks
from app.modules.rag.evidence_schemas import EvidenceBlock
from app.modules.rag.query_constraints import source_name_in_question
from app.modules.rag.schemas import AskRequest, RetrievalSnapshot

POLICY = 'source-literal-coordinates-v2'


def _invalid() -> AppException:
    return AppException('Dữ kiện không khớp tọa độ và bản nguồn đã xuất bản.', code='FACT_SOURCE_INVALID', status_code=409)


def _cell(value: str) -> str:
    return value.replace('\r\n', '\n').replace('\n', '<br>').strip()


@dataclass
class FactScope:
    candidates: list[str]
    blocks: list[EvidenceBlock] = field(default_factory=list)
    rows: dict[tuple[str, str, str], dict] = field(default_factory=dict)
    trace: dict = field(default_factory=dict)
    question: str = ''

    @property
    def resolved_codes(self) -> list[str]:
        return list(dict.fromkeys(row['code'] for row in self.rows.values()))

    @property
    def ambiguous_identity(self) -> bool:
        names = {}
        for row in self.rows.values():
            block = row['block']
            identity = (block.binding_id, block.index_revision_id, row['code'] or block.unit_id)
            names.setdefault(row['name'].casefold(), set()).add(identity)
        return any(len(identities) > 1 for identities in names.values())

    def eligible_columns(self, row: dict, attributes: list[str] | None) -> list[str]:
        columns = []
        for column in row['table']['columns']:
            expected = row['expected'].get((row['block'].unit_id, column['id']))
            if not expected:
                continue
            raw = expected['raw_data']
            metric = (raw.get('attribute_code') if (raw.get('context_review') or {}).get('status') == 'verified'
                      else cell_context(' / '.join(column['header_path']))['attribute_code'])
            if not attributes or metric in attributes:
                columns.append(column['id'])
        return columns

    def add_source(self, artifact: dict, index_id: str, source_id: str) -> None:
        units = {b.unit_id: b for b in self.blocks if b.index_revision_id == index_id}
        expected = {(f['raw_data'].get('source_unit_id'), f['raw_data'].get('column_id')): f
                    for f in artifact.get('facts', [])}
        for table in artifact.get('tables', []):
            paths = table['header_paths']
            code_cols = [i for i, path in enumerate(paths) if detect_column_role(' / '.join(path))[0] == 'code']
            if not code_cols and self.candidates:
                continue
            for position, cells in enumerate(table['rows']):
                identities = row_identities(cells, table)
                if self.candidates and not any(normalize_code(clean_cell(cells[i])) in self.candidates for i in code_cols):
                    continue
                if not self.candidates:
                    identities = [item for item in identities if source_name_in_question(item[2], self.question)]
                    # A merged identity label may carry a parenthetic row-count,
                    # which describes the label rather than changing its identity.
                    if not identities and code_cols and len({clean_cell(cells[i]) for i in code_cols}) == 1:
                        label = clean_cell(cells[code_cols[0]])
                        base = re.sub(r'\s*\([^)]*\)\s*$', '', label)
                        if len(base.split()) >= 2 and source_name_in_question(base, self.question):
                            identities = [(code_cols[0], len(cells), label, None)]
                    if len(identities) != 1:
                        continue
                row_ids = table.get('row_unit_ids', [])
                if position >= len(row_ids) or row_ids[position] not in units:
                    continue  # No invented mapping for a legacy source lacking an exact row locator.
                block = units[row_ids[position]]
                parsed = _split_gfm_row(block.text)
                header = next((line for line in block.header_context.splitlines() if line.strip().startswith('|')), '')
                headers = _split_gfm_row(header)
                if (block.source_revision_id != source_id or len(cells) != len(parsed)
                        or [_cell(v) for v in cells] != [_cell(v) for v in parsed]
                        or [_cell(' / '.join(p)) for p in paths] != [_cell(v) for v in headers]):
                    raise _invalid()
                if self.candidates:
                    identities = [item for item in identities if item[3] and normalize_code(item[3]) in self.candidates]
                if len(identities) != 1:
                    continue
                _, _, name, code = identities[0]
                key = (block.binding_id, index_id, block.unit_id)
                self.rows[key] = {'block': block, 'code': normalize_code(code or ''), 'name': name,
                    'table': table, 'position': position, 'expected': expected}

    def bind(self, fact) -> dict:
        record = (deepcopy(fact) if isinstance(fact, dict) else {key: deepcopy(getattr(fact, key, None)) for key in
            ('id', 'entity_name', 'entity_code', 'attribute_name', 'attribute_value', 'raw_data', 'binding_id', 'index_revision_id')})
        raw = record.get('raw_data') or {}
        key = (record.get('binding_id'), record.get('index_revision_id'), raw.get('source_unit_id'))
        row = self.rows.get(key)
        if row is None:
            raise _invalid()
        block, table = row['block'], row['table']
        expected = row['expected'].get((block.unit_id, raw.get('column_id')))
        original_raw = {k: v for k, v in raw.items() if k not in {'source_revision_id', 'fact_set_hash'}}
        if (not expected or original_raw != expected['raw_data']
                or any(record.get(k) != expected.get(k) for k in ('entity_name', 'attribute_name', 'attribute_value'))
                or raw.get('source_revision_id') != block.source_revision_id
                or raw.get('content_hash') != block.canonical_hash):
            raise _invalid()
        column = raw.get('column_index')
        if (not isinstance(column, int) or column < 0 or column >= len(table['headers'])
                or raw.get('row_index') != row['position'] or raw.get('table_id') != table['id']
                or raw.get('header_segments') != table['header_paths'][column]
                or raw.get('column_id') != table['columns'][column]['id']
                or _cell(raw.get('raw_value', '')) != _cell(table['rows'][row['position']][column])
                or _cell(record['attribute_value']) != _cell(raw.get('raw_value', ''))):
            raise _invalid()
        # A reviewed override remains authoritative. Never recompute its metric/year.
        reviewed = (raw.get('context_review') or {}).get('status') == 'verified'
        if not reviewed:
            context = cell_context(' / '.join(table['header_paths'][column]))
            raw.update(attribute_code=context['attribute_code'], unit=context.get('unit'))
            record['entity_name'] = row['name']
        record['entity_code'] = row['code']
        raw['source_resolution'] = {'policy': POLICY, 'entity_code': row['code'],
            'column_id': raw['column_id'], 'original_attribute_code': expected['raw_data'].get('attribute_code'),
            'review_status_preserved': (raw.get('context_review') or {}).get('status')}
        record['raw_data'] = raw
        record['canonical_quote'] = block.text
        record['canonical_hash'] = block.canonical_hash
        record['source_title'] = block.title
        record['span_start'], record['span_end'] = block.start, block.end
        return record


async def resolve_fact_scope(db: AsyncSession, snapshot: RetrievalSnapshot, question: str, *,
                             candidate_mode: bool = False) -> FactScope | None:
    candidates = code_candidates(question)
    scope = FactScope(candidates=candidates, question=question)
    scope.blocks = await load_published_blocks(db, snapshot, candidate_mode=candidate_mode)
    source_ids = {b.source_revision_id for b in scope.blocks}
    if not source_ids:
        return scope if candidates else None
    sources = list((await db.scalars(select(KnowledgeSourceRevision).where(KnowledgeSourceRevision.id.in_(source_ids)))).all())
    indexes = list((await db.scalars(select(KnowledgeIndexRevision).where(KnowledgeIndexRevision.id.in_(snapshot.binding_revisions.values())))).all())
    for source in sources:
        artifact = get_source_artifact(source)
        digest = hashlib.sha256(json.dumps(artifact['facts'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        index = next((i for i in indexes if i.source_revision_v2_id == source.id
                      and snapshot.binding_revisions.get(i.binding_id) == i.id), None)
        if index is None or artifact.get('fact_set_hash') != digest:
            raise _invalid()
        pinned = (index.parity_report or {}).get('fact_set_hash')
        if pinned and pinned != digest:
            raise _invalid()
        scope.add_source(artifact, index.id, source.id)
    if not candidates and not scope.rows:
        return None
    scope.trace.update(policy=POLICY, entity_code_candidates=candidates,
        resolved_entity_codes=scope.resolved_codes, identity_row_count=len(scope.rows))
    return scope


async def verify_fact_proof(db: AsyncSession, req: AskRequest, snapshot: RetrievalSnapshot, scope: FactScope, decision: dict,
                          *, limit: int, max_chars: int) -> bool:
    """Reuse published fact guards and atomic packing, without model inference or approval."""
    from app.modules.rag.evidence_blocks import pack_context
    from app.modules.rag.evidence_facts import reviewed_fact_blocks
    from app.modules.rag.evidence_passages import source_grounded_claims
    from app.modules.rag.evidence_schemas import QueryPlan, QuoteReference
    from app.modules.rag.evidence_validation import bind_quote

    ids = set(decision.get('matched_fact_ids') or [])
    groups = await reviewed_fact_blocks(db, req, snapshot,
        QueryPlan(query=req.question, years=decision['requested']['years']), scope.blocks,
        exhaustive=True, selected_fact_ids=ids)
    members = {cell['fact_id'] for group in groups for cell in group.fact_context.get('cells', [])}
    if not ids.issubset(members):
        raise _invalid()
    diagnostics = {}
    packed = pack_context([*scope.blocks, *groups], groups, decision['requested']['years'],
                          limit, max_chars, atomic_lists=False, diagnostics=diagnostics)
    packed_ids = {block.id for block in packed}
    if any(group.id not in packed_ids for group in groups):
        scope.trace.update(evidence_packing=diagnostics, evidence_closure='BUDGET_EXCLUDED')
        return False
    claims = [{'id': group.id, 'text': group.text,
        'references': [bind_quote(QuoteReference(block_id=group.id, quote=group.text),
                                  {block.id: block for block in packed})]} for group in groups]
    projected = source_grounded_claims(claims, packed)
    if not projected:
        raise _invalid()
    scope.trace.update(evidence_packing=diagnostics, evidence_closure='PASS', claim_projection='PASS',
        selected_fact_block_ids=[group.id for group in groups], proof_origin='published_materialized_fact',
        semantic_approval_changed=False)
    row_units = {group.fact_context['source_unit_id'] for group in groups}
    notes = [block for block in packed if block.origin == 'canonical' and not block.is_container
             and block.unit_id not in row_units and block.fact_context.get('source_kind') != 'table'
             and not block.text.lstrip().startswith('#')]
    if notes:
        decision['answer'] += '\n\nChú thích đi kèm bằng chứng, giữ nguyên phạm vi trong nguồn:\n\n' + '\n\n'.join(block.text for block in notes)
        decision['proof_context_references'] = [bind_quote(QuoteReference(block_id=block.id, quote=block.text),
            {item.id: item for item in packed}) for block in notes]
    return True
