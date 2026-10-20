"""Atomic, source-bound fact evidence through packing and claim projection."""
import json
from copy import deepcopy

import pytest

from app.core.exceptions import AppException
from app.modules.rag.evidence_blocks import pack_context
from app.modules.rag.evidence_context import model_block
from app.modules.rag.evidence_dependencies import dependency_groups
from app.modules.rag.evidence_passages import source_grounded_claims
from app.modules.rag.evidence_schemas import EvidenceBlock, QuoteReference
from app.modules.rag.evidence_validation import bind_quote


def canonical(unit, text, start, refs=()):
    return EvidenceBlock(id='canonical:' + unit, unit_id=unit, text=text, start=start,
        end=start + len(text), title='Fixture', binding_id='binding', index_revision_id='index',
        source_revision_id='revision', canonical_hash='a' * 64,
        fact_context={'context_unit_ids': list(refs)})


def evidence():
    header = canonical('header', '# Annual places', 0)
    note = canonical('note', 'Counts refer to students, except group B.', 100)
    row = canonical('row', 'Alpha | 00127 | 2026 | 20.', 200, ['header', 'note'])
    fact = row.model_copy(update={'id': 'fact:alpha', 'unit_id': None, 'origin': 'reviewed_fact',
        'start': -1, 'end': -1, 'fact_id': 'fact-alpha',
        'fact_context': {'verified_dependencies': True, 'source_unit_id': 'row',
                         'context_unit_ids': ['header'], 'entity_name': 'Alpha'}})
    return [header, note, row], fact


def claim(fact, blocks):
    reference = bind_quote(QuoteReference(block_id=fact.id, quote=fact.text), {b.id: b for b in blocks})
    return [{'id': 'claim', 'text': fact.text, 'references': [reference]}]


def test_fact_group_keeps_exact_source_row_and_its_own_dependencies():
    blocks, fact = evidence()
    before = deepcopy([b.model_dump() for b in [*blocks, fact]])
    group = dependency_groups([*blocks, fact])[fact.id]
    assert [b.id for b in group] == [fact.id, blocks[2].id, blocks[0].id, blocks[1].id]
    assert next(b for b in group if b.unit_id == 'row') is blocks[2]
    assert [b.model_dump() for b in [*blocks, fact]] == before


def test_fact_selection_pack_and_claim_projection_retains_source_proof():
    blocks, fact = evidence()
    packed = pack_context([*blocks, fact], [fact], [2026], 5, 36000, atomic_lists=False)
    assert {fact.id, *(b.id for b in blocks)} <= {b.id for b in packed}
    dependency_groups(packed)
    projected = source_grounded_claims(claim(fact, packed), packed)
    assert projected and projected[0]['references'][0]['quote'] == fact.text
    assert projected[0]['references'][0]['canonical_hash'] == fact.canonical_hash


@pytest.mark.parametrize('target', ['row', 'note', 'header'])
def test_missing_required_source_unit_stays_blocked(target):
    blocks, fact = evidence()
    with pytest.raises(AppException) as error:
        dependency_groups([b for b in blocks if b.unit_id != target] + [fact])
    assert error.value.code == 'EVIDENCE_CONTEXT_MISSING'


@pytest.mark.parametrize('field,value', [('source_revision_id', 'other'), ('canonical_hash', 'b' * 64),
    ('binding_id', 'other-binding'), ('index_revision_id', 'stale-index')])
def test_wrong_source_identity_is_not_replaced_by_similar_text(field, value):
    blocks, fact = evidence()
    wrong = blocks[2].model_copy(update={field: value})
    with pytest.raises(AppException) as error:
        dependency_groups([*blocks[:2], wrong, fact])
    assert error.value.code == 'EVIDENCE_CONTEXT_MISSING'


def test_duplicate_canonical_unit_is_rejected():
    blocks, fact = evidence()
    duplicate = blocks[2].model_copy(update={'id': 'canonical:duplicate'})
    with pytest.raises(AppException) as error:
        dependency_groups([*blocks, duplicate, fact])
    assert error.value.code == 'EVIDENCE_CONTEXT_MISSING'


def test_source_row_transitive_dependencies_and_cycles_are_closed_once():
    blocks, fact = evidence()
    condition = canonical('condition', 'Only full time students.', 80, ['note'])
    blocks[1].fact_context['context_unit_ids'] = ['condition', 'row']
    packed = pack_context([*blocks, condition, fact], [fact], [], 10, 36000, atomic_lists=False)
    assert {b.unit_id for b in packed if b.origin == 'canonical'} == {'row', 'header', 'note', 'condition'}
    assert len({b.id for b in packed}) == len(packed)
    dependency_groups(packed)
    assert source_grounded_claims(claim(fact, packed), packed)


@pytest.mark.parametrize('limit,budget,reason', [(2, 36000, 'block_limit'), (10, 100, 'character_budget')])
def test_insufficient_budget_rejects_whole_fact_group(limit, budget, reason):
    blocks, fact = evidence()
    trace = {}
    packed = pack_context([*blocks, fact], [fact], [], limit, budget, diagnostics=trace)
    assert packed == []
    assert trace['dropped'][0]['reason'] == reason
    assert source_grounded_claims([], packed) == []


def test_shared_source_and_note_deduplicate_with_stable_order_and_serialization():
    blocks, fact = evidence()
    second = fact.model_copy(update={'id': 'fact:second', 'fact_id': 'fact-second'})
    source = [*blocks, fact, second]
    first = pack_context(source, [fact, second], [], 5, 36000, atomic_lists=False)
    again = pack_context(list(reversed(source)), [fact, second], [], 5, 36000, atomic_lists=False)
    assert [b.id for b in first] == [b.id for b in again]
    assert len(first) == len({b.id for b in first}) == 5
    assert sum(b.unit_id == 'row' for b in first) == 1
    assert sum(b.unit_id == 'note' for b in first) == 1
    dependency_groups(first)
    assert json.loads(json.dumps([model_block(b) for b in first], ensure_ascii=False))[0]['text']
    assert source_grounded_claims(claim(fact, first) + claim(second, first), first)


def test_source_row_can_be_shared_but_note_does_not_expand_other_fact_rows():
    blocks, fact = evidence()
    row2 = canonical('row2', 'Beta | 00459 | 2026 | 30.', 300, ['note'])
    other = fact.model_copy(update={'id': 'fact:beta', 'fact_context': {
        'verified_dependencies': True, 'source_unit_id': 'row2', 'context_unit_ids': ['note']}})
    groups = dependency_groups([*blocks, row2, fact, other])
    assert row2.id not in {b.id for b in groups[fact.id]}
    assert fact.id not in {b.id for b in groups.get(blocks[1].id, [])}


def test_canonical_text_without_reviewed_facts_keeps_existing_behavior():
    paragraph = canonical('paragraph', 'Applications open in March.', 0)
    packed = pack_context([paragraph], [paragraph], [], 5, 36000)
    assert packed == [paragraph]
    projected = source_grounded_claims(claim(paragraph, packed), packed)
    assert projected[0]['text'] == paragraph.text


@pytest.mark.parametrize('refs', [None, 'note', ['note', 4]])
def test_invalid_dependency_metadata_is_not_accepted(refs):
    blocks, fact = evidence()
    fact.fact_context['context_unit_ids'] = refs
    with pytest.raises(AppException) as error:
        dependency_groups([*blocks, fact])
    assert error.value.code == 'EVIDENCE_CONTEXT_MISSING'


@pytest.mark.asyncio
async def test_published_fact_selection_through_projection_does_not_mutate_snapshot():
    from test_review536_findings import (
        build_state,
        db_for,
        fact_objects,
        published,
        request,
        snapshot,
    )

    from app.modules.rag.evidence_blocks import load_published_blocks
    from app.modules.rag.evidence_facts import reviewed_fact_blocks
    from app.modules.rag.evidence_schemas import QueryPlan

    state = build_state()
    before = deepcopy(vars(state.source))
    snap = snapshot()
    snapshot_before = snap.model_copy(deep=True)
    blocks = await load_published_blocks(published([(state.source, state.index, state.binding)]), snap)
    facts = await reviewed_fact_blocks(db_for(fact_objects(state.approved)), request(), snap,
        QueryPlan(query=request().question, years=[2026]), blocks, exhaustive=True)
    assert facts
    fact = facts[0]
    packed = pack_context([*blocks, *facts], [fact], [2026], 10, 36000)
    assert fact.id in {b.id for b in packed}
    assert fact.fact_context['source_unit_id'] in {b.unit_id for b in packed}
    assert source_grounded_claims(claim(fact, packed), packed)
    assert vars(state.source) == before
    assert snap == snapshot_before
