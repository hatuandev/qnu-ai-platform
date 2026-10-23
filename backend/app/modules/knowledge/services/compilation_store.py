"""Immutable StorageDriver objects and collection-locked registry, without schema changes."""
import json
from copy import deepcopy
from datetime import UTC, datetime

from app.core.exceptions import AppException
from app.core.storage import storage_service
from app.modules.knowledge.compilation_runtime_schemas import REGISTRY
from app.modules.knowledge.services.compilation_catalog import invalid
from app.modules.knowledge.services.wiki_compiler import digest


def now() -> str:
    return datetime.now(UTC).isoformat()


def registry(collection) -> dict:
    value = deepcopy((collection.collection_metadata or {}).get(REGISTRY,
        {'version': 1, 'jobs': {}, 'requests': {}, 'packets': {}}))
    if value.get('version') != 1 or any(not isinstance(value.get(key), dict) for key in ('jobs', 'requests', 'packets')):
        raise invalid('registry_contract')
    return value


def assign(collection, state: dict) -> None:
    collection.collection_metadata = {**(collection.collection_metadata or {}), REGISTRY: deepcopy(state)}


def object_path(collection_id: str, checksum: str) -> str:
    return f'knowledge-compilations/{digest(collection_id)}/{checksum}.json'


async def save_object(collection_id: str, value: dict) -> dict:
    checksum = digest(value)
    path = object_path(collection_id, checksum)
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    if len(data) > 16_000_000:
        raise invalid('artifact_size_budget', 422)
    await storage_service.save(path, data)
    reference = {'path': path, 'sha256': checksum}
    if await read_object(collection_id, reference) != value:
        raise invalid('storage_roundtrip')
    return reference


async def read_object(collection_id: str, reference: dict) -> dict:
    checksum = reference.get('sha256', '')
    if len(checksum) != 64 or any(c not in '0123456789abcdef' for c in checksum):
        raise invalid('storage_reference')
    if reference.get('path') != object_path(collection_id, checksum):
        raise invalid('storage_scope')
    data = await storage_service.get(reference['path'])
    if data is None:
        raise invalid('storage_object_unavailable', 503)
    try:
        value = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise invalid('storage_json') from exc
    if not isinstance(value, dict) or digest(value) != checksum:
        raise invalid('storage_checksum')
    return value


async def available_packets(collection_id: str, state: dict) -> dict:
    packets = {}
    for key, entry in state['packets'].items():
        owner = state['jobs'].get(entry['job_id'], {})
        if owner.get('status') not in {'ready_for_review', 'needs_attention', 'reviewed'}:
            continue
        try:
            check_lineage(state, owner.get('reused_job_ids', []))
        except AppException:
            continue  # Explicitly revoked lineage is not a reusable inference result.
        # Load only a matching packet on demand, not every historical source artifact.
        packets[key] = entry['reference']
    return packets


def check_lineage(state: dict, job_ids: list[str]) -> None:
    pending, visited = [(jid, set()) for jid in job_ids], set()
    while pending:
        job_id, ancestors = pending.pop()
        if job_id in ancestors:
            raise invalid('derivative_dependency_cycle')
        if job_id in visited:
            continue
        visited.add(job_id)
        record = state['jobs'].get(job_id)
        if not record or record['status'] in {'rejected', 'revoked', 'uncertain', 'running'}:
            raise invalid('revoked_derivative_dependency')
        pending.extend((parent, ancestors | {job_id}) for parent in record.get('reused_job_ids', []))


async def append_event(collection_id: str, record: dict, event: dict) -> None:
    history = record.setdefault('events', [])
    body = {**event, 'job_id': record['id'], 'sequence': len(history) + 1,
            'previous': history[-1]['sha256'] if history else None, 'at': now()}
    history.append(await save_object(collection_id, body))


async def audit_events(collection_id: str, record: dict) -> list[dict]:
    previous, events = None, []
    for index, reference in enumerate(record['events'], 1):
        event = await read_object(collection_id, reference)
        if event['sequence'] != index or event['previous'] != previous or event['job_id'] != record['id']:
            raise invalid('audit_chain')
        previous = reference['sha256']
        events.append(event)
    return events
