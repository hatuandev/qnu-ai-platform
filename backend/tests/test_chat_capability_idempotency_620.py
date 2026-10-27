"""Observing an unchanged capability must not mutate the compiler configuration."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.modelops.services.chat_capabilities import save_chat_capabilities


def database(capabilities,*,endpoint='https://provider.example/v1'):
    record={'endpoint':endpoint,'capabilities':capabilities,'observed_at':'2026-10-01T00:00:00+00:00'}
    provider=SimpleNamespace(api_base_url=endpoint,extra_config={'chat_request_contracts':{'alias':record},'other':{'preserve':True}})
    db=AsyncMock();result=MagicMock();result.scalar_one_or_none.return_value=provider;db.execute.return_value=result
    return db,provider


@pytest.mark.asyncio
async def test_identical_observation_does_not_commit_change_timestamp_or_provider_configuration():
    db,provider=database({'token_parameter':'max_completion_tokens','temperature_supported':False})
    before=deepcopy(provider.extra_config)
    await save_chat_capabilities(db,'p','alias',provider.api_base_url,{'temperature_supported':False,'token_parameter':'max_completion_tokens'})
    db.commit.assert_not_awaited()
    assert provider.extra_config==before


@pytest.mark.asyncio
async def test_actual_capability_change_is_still_persisted_and_keeps_other_config():
    db,provider=database({'token_parameter':'max_tokens'})
    await save_chat_capabilities(db,'p','alias',provider.api_base_url,{'token_parameter':'max_completion_tokens'})
    db.commit.assert_awaited_once()
    record=provider.extra_config['chat_request_contracts']['alias']
    assert record['capabilities']=={'token_parameter':'max_completion_tokens'}
    assert record['observed_at']!='2026-10-01T00:00:00+00:00' and provider.extra_config['other']=={'preserve':True}


@pytest.mark.asyncio
async def test_old_endpoint_observation_cannot_be_mistaken_for_current_endpoint():
    db,provider=database({'token_parameter':'max_tokens'})
    before=deepcopy(provider.extra_config)
    await save_chat_capabilities(db,'p','alias','https://previous.example/v1',{'token_parameter':'max_completion_tokens'})
    db.commit.assert_not_awaited()
    assert provider.extra_config==before


@pytest.mark.asyncio
async def test_same_capabilities_under_old_recorded_endpoint_require_fresh_binding():
    db,provider=database({'token_parameter':'max_tokens'})
    provider.extra_config['chat_request_contracts']['alias']['endpoint']='https://previous.example/v1'
    await save_chat_capabilities(db,'p','alias',provider.api_base_url,{'token_parameter':'max_tokens'})
    db.commit.assert_awaited_once()
    assert provider.extra_config['chat_request_contracts']['alias']['endpoint']==provider.api_base_url


@pytest.mark.asyncio
async def test_real_compiler_route_fingerprint_is_stable_after_repeated_model_success(monkeypatch):
    from app.modules.knowledge.services.compilation_modelops import (
        configuration_hash,
        resolve_route,
    )
    from app.modules.modelops.models import ModelProviderConfig
    from app.modules.modelops.services.model_catalog_service import model_catalog_service

    endpoint='https://provider.example/v1'
    caps={'token_parameter':'max_completion_tokens'}
    cfg=ModelProviderConfig(id='p',name='Fixture',provider_type='custom',api_base_url=endpoint,is_active=True,
        extra_config={'chat_request_contracts':{'alias':{'endpoint':endpoint,'capabilities':caps,'observed_at':'original'}},
            'model_capabilities':{'alias':{'token_limits':{'endpoint':endpoint,'context_window_tokens':200000,'max_output_tokens':128000}}}})
    db=AsyncMock();row=MagicMock();row.scalar_one_or_none.return_value=cfg;db.execute.return_value=row
    db.scalars.return_value=SimpleNamespace(all=lambda:[cfg])
    defaults=SimpleNamespace(default_chat_provider_id='p',default_chat_model='alias',default_chat_mode='single')
    monkeypatch.setattr(model_catalog_service,'get_system_model_defaults',AsyncMock(return_value=SimpleNamespace(defaults=defaults)))
    before=configuration_hash(await resolve_route(db),{})
    for _ in range(3):
        await save_chat_capabilities(db,'p','alias',endpoint,caps)
    assert configuration_hash(await resolve_route(db),{})==before
    db.commit.assert_not_awaited()
