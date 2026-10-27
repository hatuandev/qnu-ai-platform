"""Durable candidate stages; a completed inference is never an approval."""
from app.modules.knowledge.services.compilation_catalog import invalid, load_sources
from app.modules.knowledge.services.compilation_store import (
    append_event,
    assign,
    read_object,
    registry,
    save_object,
)
from app.modules.knowledge.services.wiki_compiler import digest


def known_prefix(record: dict) -> bool:
    entries = record.get('checkpoints')
    if not record.get('execution_policy') or not isinstance(entries, dict) or record.get('model_calls_count') != len(entries):
        return False
    return all(isinstance(entry, dict) and isinstance(entry.get('identity'), dict)
        and entry.get('status') in {'completed', 'rejected'}
        and digest(entry.get('identity')) == key and entry['identity'].get('config') == record['configuration_hash']
        and (entry['status'] != 'rejected' or isinstance(entry.get('error'), dict)
             and entry['error'].get('code') == 'KNOWLEDGE_WIKI_INVALID')
        for key, entry in entries.items())


class StageCheckpoints:
    def __init__(self, db, collection_id, record, actor, verify_config, policy):
        self.db, self.collection_id, self.record, self.actor = db, collection_id, record, actor
        self.verify_config, self.policy = verify_config, policy
        self.total_calls = record.get('model_calls_count', 0)

    async def audit(self, current, event):
        # Keep the existing decision audit API stable; candidate stages have their own chain.
        target = {'id': current['id'], 'events': current.setdefault('checkpoint_events', [])}
        await append_event(self.collection_id, target, {**event, 'actor_id': self.actor.actor_id})

    async def locked(self):
        collection, _, _, fingerprint = await load_sources(self.db, self.collection_id,
            self.record['source_revision_ids'], self.actor, lock=True)
        state = registry(collection)
        current = state['jobs'][self.record['id']]
        if (current['status'] != 'running' or current['version'] != self.record['version']
                or fingerprint != current['source_set_hash']):
            raise invalid('checkpoint_ownership_or_source_changed')
        await self.verify_config()
        return collection, state, current

    async def lookup(self, key):
        _, _, current = await self.locked()
        entry = current.get('checkpoints', {}).get(key)
        if not entry:
            await self.db.rollback()  # Never hold a collection lock across inference.
            return None
        if digest(entry.get('identity')) != key or entry['identity'].get('config') != current['configuration_hash']:
            raise invalid('checkpoint_identity')
        if entry['status'] == 'completed':
            value = await read_object(self.collection_id, entry['reference'])
            if value.get('key') != key or value.get('identity') != entry['identity']:
                raise invalid('checkpoint_binding')
            result = {'status': 'completed', 'value': value['value']}
        else:
            result = {k: entry[k] for k in ('status', 'error') if k in entry}
        await self.db.rollback()
        return result

    async def start(self, key, identity):
        collection, state, current = await self.locked()
        if digest(identity) != key or identity.get('config') != current['configuration_hash']:
            raise invalid('checkpoint_identity')
        entries = current.setdefault('checkpoints', {})
        if key in entries:
            raise invalid('checkpoint_already_started')
        if current.get('model_calls_count', 0) >= self.policy.max_total_calls:
            raise invalid('total_model_call_budget', 422)
        entries[key] = {'status': 'started', 'identity': identity}
        current['model_calls_count'] = current.get('model_calls_count', 0) + 1
        await self.audit(current, {'type': 'inference_stage_started', 'stage_key': key,
                                                       'ordinal': identity['ordinal'], 'contract': identity['contract']})
        assign(collection, state)
        await self.db.commit()
        self.total_calls = current['model_calls_count']

    async def complete(self, key, value):
        collection, state, current = await self.locked()
        entry = current['checkpoints'][key]
        if entry['status'] != 'started':
            raise invalid('checkpoint_not_owned')
        reference = await save_object(self.collection_id, {'key': key, 'identity': entry['identity'], 'value': value})
        entry.update(status='completed', reference=reference)
        await self.audit(current, {'type': 'inference_stage_completed', 'stage_key': key,
                                                       'candidate_sha256': reference['sha256'], 'approved': False})
        assign(collection, state)
        await self.db.commit()

    async def reject(self, key, error):
        collection, state, current = await self.locked()
        entry = current['checkpoints'][key]
        if entry['status'] != 'started':
            raise invalid('checkpoint_not_owned')
        known = error.code == 'KNOWLEDGE_WIKI_INVALID'
        entry.update(status='rejected' if known else 'uncertain',
                     error={'code': error.code, 'details': error.details if known else None})
        await self.audit(current, {'type': 'inference_stage_rejected' if known else 'inference_stage_uncertain',
                                                       'stage_key': key, 'code': error.code, 'automatic_retry': False})
        assign(collection, state)
        await self.db.commit()
