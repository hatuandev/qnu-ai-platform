"""Mixed repairs preserve independently proved values without relaxing source review."""
from copy import deepcopy

import pytest

from app.core.exceptions import AppException
from app.modules.knowledge.compilation_runtime_schemas import (
    PacketCheck,
    PacketCoverage,
    PacketDraft,
    SynthesisDraft,
)
from app.modules.knowledge.services.compilation_engine import compile_topic
from app.modules.knowledge.services.compilation_grounding import (
    materialize_packet,
    materialize_synthesis,
)
from app.modules.knowledge.services.compilation_validation import validate_result
from app.modules.knowledge.services.wiki_compiler import digest
from tests.test_compilation_engine_603 import ACTOR, Model
from tests.test_compilation_grounding_616 import selected
from tests.test_compilation_metrics_615 import no_network  # noqa: F401
from tests.test_foundation_602 import source


class MixedRepair(Model):
    def __init__(self, amount, year, *, missing=False, mapping=True, missed=False, repeated=False):
        super().__init__()
        self.amount, self.year, self.missing, self.mapping = amount, year, missing, mapping
        self.missed = missed
        self.repeated = repeated

    async def __call__(self, contract, instruction, payload):
        if contract is PacketDraft:
            pid = payload['primary_evidence_ids'][0]
            evidence = payload['evidence']
            subject = selected(evidence, pid, 'Học viện Alpha')
            metric = selected(evidence, pid, 'Tổng chỉ tiêu')
            restriction = selected(evidence, pid, 'Không áp dụng cho mùa khác.')
            absent = selected(evidence, pid, 'Chưa công bố giá trị.') if self.missing else restriction
            unknown = {'id': 'missing', 'subject': subject, 'metric': metric,
                'value_state': 'source_unspecified', 'limitation': absent,
                'temporal': [{'role': 'data', 'years': [self.year], 'evidence_ids': [pid]}]}
            claims = [unknown]
            if payload.get('candidate_correction') and not self.missing:
                value = {**unknown, 'id': 'value', 'value_state': 'present', 'limitation': None,
                    'scalar': selected(evidence, pid, self.amount),
                    'scope': [{'dimension': 'applicability', 'anchor': restriction}]}
                claims = [value, unknown if self.repeated else {**unknown, 'temporal': []}]
            return contract.model_validate(materialize_packet({'claims': claims}, payload))
        if contract is PacketCheck:
            assert 'topic' not in payload and 'candidate_correction' not in payload
            items = []
            for a in payload['draft']['assertions']:
                valid = a['value_state'] == 'present' or self.missing
                items.append({'id': a['id'], 'verdict': 'supported' if valid else 'contradicted',
                    'entity_scope': True, 'temporal_roles': True, 'conditions_complete': True,
                    'evidence_ids': a['evidence_ids'],
                    'reason': 'Scope restriction is not proof that the scoped value is absent.'})
            return contract(items=items)
        if contract is PacketCoverage:
            return contract(missed_evidence_ids=[], reason='The independently offered primary content is represented.')
        if contract.__name__ == 'RepairSelectionCheck':
            assert len(payload['draft']['assertions']) == 1
            assert all(a['value_state'] == 'present' for a in payload['draft']['assertions'])
            return contract(items=[{'id': a['id'],
                'assertion_ids': [payload['draft']['assertions'][0]['id']] if self.mapping else [],
                'verdict': 'supported' if self.mapping else 'unresolved',
                'reason': 'The replacement preserves the exact population, metric, data year and restriction.'}
                for a in payload['repair_targets']],
                missed_evidence_ids=payload['primary_evidence_ids'] if self.missed else [],
                reason='No source content or real unknown was discarded.')
        if contract is SynthesisDraft:
            pid = next(iter(payload['evidence']))
            plan = {'relations': [], 'sections': [{'heading': selected(payload['evidence'], pid, 'Học viện Alpha'),
                'assertion_ids': [a['id'] for a in payload['draft']['assertions']]}]}
            return contract.model_validate(materialize_synthesis(plan, payload))
        return await super().__call__(contract, instruction, payload)


async def build(amount='5.173', year=2026, *, missing=False, mapping=True, missed=False, repeated=False):
    raw = f'Học viện Alpha: Tổng chỉ tiêu {year}: {amount}. Không áp dụng cho mùa khác.'
    if missing:
        raw = f'Học viện Alpha: Tổng chỉ tiêu {year}. Chưa công bố giá trị. Không áp dụng cho mùa khác.'
    item = source(raw)
    item.id, item.binding_id, item.collection_id = 'revision622', 'binding622', 'c603'
    result = await compile_topic([item], 'c603', 'Tổng chỉ tiêu theo năm', ACTOR,
        MixedRepair(amount, year, missing=missing, mapping=mapping, missed=missed, repeated=repeated), 'repair622')
    return item, result


@pytest.mark.asyncio
@pytest.mark.parametrize('amount,year', [('5.173', 2026), ('2,480', 2029), ('0007', 2031)])
async def test_mixed_repair_accepts_proved_value_after_independent_replacement_and_coverage_audit(amount, year):
    item, result = await build(amount, year)
    assert result['machine_complete']
    assertions = result['binding']['proposal']['assertions']
    assert len(assertions) == 1 and assertions[0]['value'] == amount
    assert assertions[0]['temporal'][0]['years'] == [year]
    assert any(s['value'] == 'Không áp dụng cho mùa khác.' for s in assertions[0]['scope'])
    assert result['publication'] == 'unpublished'
    validate_result(result, [item], 'c603')


@pytest.mark.asyncio
async def test_a_real_source_absence_remains_unknown_without_a_repair():
    item, result = await build(missing=True)
    assert result['machine_complete']
    assertion = result['binding']['proposal']['assertions'][0]
    assert assertion['value_state'] == 'unknown' and assertion['value'] is None
    assert 'semantic_repair' not in result['packet_results'][0]
    validate_result(result, [item], 'c603')


@pytest.mark.asyncio
async def test_a_repeated_failed_extra_is_quarantined_without_overriding_its_verdict():
    item, result = await build(repeated=True)
    assert result['machine_complete']
    packet = result['packet_results'][0]
    ledger = packet['semantic_repair']
    assert ledger['candidate']['review']['items'][1]['verdict'] == 'contradicted'
    assert len(ledger['selection']['quarantined_assertion_ids']) == 1
    assert all(a['value_state'] == 'present' for a in packet['draft']['assertions'])
    validate_result(result, [item], 'c603')


@pytest.mark.asyncio
async def test_unresolved_replacement_never_activates_a_supported_but_unmapped_fact():
    item, result = await build(mapping=False)
    assert not result['machine_complete']
    assert result['binding']['proposal']['assertions'][0]['value_state'] == 'unknown'
    validate_result(result, [item], 'c603')


@pytest.mark.asyncio
async def test_missing_source_coverage_blocks_even_a_supported_replacement_mapping():
    item, result = await build(missed=True)
    assert not result['machine_complete']
    packet = result['packet_results'][0]
    assert packet['semantic_repair']['selection']['review']['missed_evidence_ids']
    assert packet['draft']['assertions'][0]['value_state'] == 'unknown'
    validate_result(result, [item], 'c603')


@pytest.mark.asyncio
async def test_selection_that_cannot_fit_is_not_run_and_does_not_activate_candidates(monkeypatch):
    from app.modules.knowledge.services import compilation_candidate_repair as repair
    from app.modules.knowledge.services.compilation_repair_selection import RepairSelectionCheck

    original = repair.planned_request_budget
    monkeypatch.setattr(repair, 'planned_request_budget', lambda contract, *a, **k:
        {'fits': False} if contract is RepairSelectionCheck else original(contract, *a, **k))
    item, result = await build()
    assert not result['machine_complete']
    packet = result['packet_results'][0]
    assert packet['semantic_repair']['selection']['capacity']['status'] == 'NOT_RUN'
    assert packet['draft']['assertions'][0]['value_state'] == 'unknown'
    validate_result(result, [item], 'c603')


@pytest.mark.asyncio
async def test_replacement_transport_uses_only_offered_target_assertion_and_proof_handles():
    from pydantic import ValidationError

    from app.modules.knowledge.services.compilation_repair_selection import RepairSelectionCheck
    from app.modules.knowledge.services.compilation_transport import prepare, restore

    _, result = await build()
    packet = result['packet_results'][0]
    ledger = packet['semantic_repair']
    payload = {'draft': packet['draft'], 'repair_targets': ledger['initial']['draft']['assertions'],
        'repair_target_entities': ledger['initial']['draft']['entities'], 'evidence': result['binding']['evidence']}
    contract, wire, reverse = prepare(RepairSelectionCheck, payload)
    data = {'items': [{'id': wire['repair_targets'][0]['id'],
        'assertion_ids': [wire['draft']['assertions'][0]['id']], 'verdict': 'supported', 'reason': 'Exact source.'}],
        'missed_evidence_ids': [], 'reason': 'No lost source context.'}
    restored = restore(contract.model_validate(data).model_dump(), reverse)
    assert restored['items'][0]['id'] == payload['repair_targets'][0]['id']
    for key in ('id', 'assertion_ids'):
        bad = deepcopy(data)
        bad['items'][0][key] = 'fabricated' if key == 'id' else ['fabricated']
        with pytest.raises(ValidationError):
            contract.model_validate(bad)


def test_prose_year_is_temporal_evidence_and_cannot_become_a_table_column():
    from pydantic import ValidationError

    from app.modules.knowledge.services.compilation_grounding import PROTOCOL
    from app.modules.knowledge.services.compilation_transport import prepare

    evidence = {'p': {'source_revision_id': 's', 'quote': 'Học viện Alpha: Tổng chỉ tiêu 2029: 2.480.',
        'structural_evidence': {'role': 'paragraph'}}}
    payload = {'evidence': evidence, 'primary_evidence_ids': ['p'], 'source_grounding_protocol': PROTOCOL}
    claim = {'id': 'a', 'subject': selected(evidence, 'p', 'Học viện Alpha'),
        'metric': selected(evidence, 'p', 'Tổng chỉ tiêu'), 'scalar': selected(evidence, 'p', '2.480'),
        'column': selected(evidence, 'p', '2029'), 'value_state': 'present'}
    with pytest.raises(AppException) as error:
        materialize_packet({'claims': [claim]}, payload)
    assert error.value.details['reason'] == 'prose_cannot_assert_table_column'
    shape, wire, _ = prepare(PacketDraft, payload)
    assert not any('column' in span['allowed_roles'] for span in wire['source_spans'].values())
    with pytest.raises(ValidationError):
        shape.model_validate({'claims': [claim]})


@pytest.mark.asyncio
@pytest.mark.parametrize('mutation', ['bad_mapping', 'keep_bad_fact', 'remove_quarantine', 'missing_coverage'])
async def test_persisted_mixed_repair_is_revalidated_against_original_candidate(mutation):
    item, result = await build()
    assert result['machine_complete']
    changed = deepcopy(result)
    packet = changed['packet_results'][0]
    selection = packet['semantic_repair']['selection']
    if mutation == 'bad_mapping':
        selection['review']['items'][0]['assertion_ids'] = ['unoffered']
    elif mutation == 'keep_bad_fact':
        packet['draft'] = deepcopy(packet['semantic_repair']['candidate']['draft'])
    elif mutation == 'remove_quarantine':
        selection['quarantined_assertion_ids'] = []
    else:
        packet.pop('coverage_review')
    changed['sha256'] = digest({k: v for k, v in changed.items() if k != 'sha256'})
    with pytest.raises(AppException):
        validate_result(changed, [item], 'c603')
