"""Task-owned LOCAL test DB and temporary storage; no shared DB schema/data writes."""
import argparse
import asyncio
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

STATE = ROOT / 'backend/storage/context548-isolation.json'
EVIDENCE = ROOT / 'backend/storage/context548-evidence'

def checked():
    configured = make_url(settings.DATABASE_URL)
    assert settings.ENVIRONMENT in {'development','dev','local','test','testing'}
    assert configured.host in {'127.0.0.1','localhost','::1'}
    assert json.loads((ROOT/'backend/storage/context548-safety.json').read_text(encoding='utf-8'))['observed_database']['read_only'] == 'on'
    return configured

async def setup():
    configured = checked()
    if STATE.exists():
        await initialize(configured,json.loads(STATE.read_text(encoding='utf-8')))
        return
    nonce = uuid4().hex
    name = 'qnu_test_context548_' + nonce[:12]
    runtime = ROOT / ('backend/storage/context548-runtime-' + nonce[:12])
    runtime.mkdir(parents=True,exist_ok=False)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    admin = create_async_engine(configured.set(database='postgres'),isolation_level='AUTOCOMMIT')
    async with admin.connect() as conn:
        assert not (await conn.execute(text('SELECT 1 FROM pg_database WHERE datname=:name'),{'name': name})).scalar()
        await conn.execute(text(f'CREATE DATABASE "{name}"'))
        await conn.execute(text(f"COMMENT ON DATABASE \"{name}\" IS 'context548:{nonce}'"))
    await admin.dispose()
    state = {'name': name,'nonce': nonce,'runtime': str(runtime),'shared_database': configured.database,'status': 'created'}
    STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8',newline='\n')
    await initialize(configured,state)

async def initialize(configured,state):
    assert state['status']=='created' and re.fullmatch(r'qnu_test_context548_[a-f0-9]{12}',state['name'])
    # All DDL below is confined to the newly created empty test database.
    from app.core.database import Base
    for path in sorted((ROOT/'backend/app/modules').glob('*/models.py')):
        importlib.import_module('app.modules.' + path.parent.name + '.models')
    # Existing ORM declares some identical indexes twice. Deduplicate identical
    # names/expressions in this temporary metadata only; never edit app models.
    deduplicated=[]
    for table in Base.metadata.tables.values():
        indexes={}
        for index in list(table.indexes):
            signature=tuple(str(expr) for expr in index.expressions)
            if index.name in indexes:
                assert indexes[index.name]==signature, 'Conflicting indexes need operator review'
                table.indexes.remove(index)
                deduplicated.append(index.name)
            else:
                indexes[index.name]=signature
    test_engine = create_async_engine(configured.set(database=state['name']))
    async with test_engine.begin() as conn:
        assert (await conn.execute(text('SELECT current_database()'))).scalar() == state['name']
        assert (await conn.execute(text("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=current_database()"))).scalar()=='context548:'+state['nonce']
        await conn.run_sync(Base.metadata.create_all)
    await test_engine.dispose()
    state['status']='ready'
    state['tables']=len(Base.metadata.tables)
    state['temporary_metadata_duplicate_indexes']=deduplicated
    STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(state))

def test_environment():
    configured = checked()
    state = json.loads(STATE.read_text(encoding='utf-8'))
    assert state['status']=='ready' and re.fullmatch(r'qnu_test_context548_[a-f0-9]{12}',state['name'])
    env = os.environ.copy()
    env.update(DATABASE_URL=configured.set(database=state['name']).render_as_string(hide_password=False),
        ENVIRONMENT='test',STORAGE_DRIVER='local',LOCAL_STORAGE_PATH=str(Path(state['runtime'])/'objects'),
        S3_ENDPOINT='http://127.0.0.1:1',QDRANT_URL='http://127.0.0.1:1',REDIS_URL='redis://127.0.0.1:1/15',
        DEV_AUTO_MIGRATE='false',DEV_AUTO_SEED='false')
    return state,env

def run(args):
    state,env=test_environment()
    label=args.label
    assert re.fullmatch('[a-z0-9-]+',label)
    prefix=[sys.executable,'-m','pytest']
    if label == 'baseline':
        snapshot=Path(state['runtime'])/'baseline-code'
        assert not snapshot.exists(), 'Baseline snapshot already exists; do not overwrite'
        shutil.copytree(ROOT/'backend/app',snapshot/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        bootstrap=snapshot/'run.py'
        bootstrap.write_text("import sys\nfrom pathlib import Path\nsys.path.insert(0,str(Path(__file__).parent))\nimport app\nimport pytest\nraise SystemExit(pytest.main(sys.argv[1:]))\n",encoding='utf-8',newline='\n')
        prefix=[sys.executable,str(bootstrap)]
        hashes={str(p.relative_to(snapshot)):__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in (snapshot/'app').rglob('*.py')}
        (EVIDENCE/'baseline-code-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8',newline='\n')
    command=[*prefix,'-q',*args.tests,'--basetemp='+str(Path(state['runtime'])/label),
        '--junitxml='+str(EVIDENCE/(label+'.xml'))]
    with (EVIDENCE/(label+'.log')).open('w',encoding='utf-8',newline='\n') as stream:
        result=subprocess.run(command,cwd=ROOT/'backend',env=env,stdout=stream,stderr=subprocess.STDOUT,check=False)
    report={'command': [part.replace(str(ROOT),'<repo>') for part in command],'cwd': str(ROOT/'backend'),
        'database': state['name'],'storage': env['LOCAL_STORAGE_PATH'],'minio': env['S3_ENDPOINT'],'qdrant': env['QDRANT_URL'],
        'redis': env['REDIS_URL'],'auto_migrate': False,'auto_seed': False,'exit_code': result.returncode}
    (EVIDENCE/(label+'-run.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))
    return result.returncode

def script(args):
    state,env=test_environment()
    arguments=json.loads(Path(args.args_json).read_text(encoding='utf-8'))
    path=(ROOT/arguments[0]).resolve()
    assert path.is_relative_to(ROOT) and path.name in {'verify_semantic_modelops.py'}
    command=[sys.executable,str(path),*arguments[1:]]
    with (EVIDENCE/(args.label+'.log')).open('w',encoding='utf-8',newline='\n') as stream:
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,check=False)
    report={'command': arguments,'cwd': str(ROOT),'database': state['name'],'exit_code': result.returncode}
    (EVIDENCE/(args.label+'-run.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))
    return result.returncode

async def seed_modelops():
    configured=checked()
    state=json.loads(STATE.read_text(encoding='utf-8'))
    assert state['status']=='ready' and state['name'].startswith('qnu_test_context548_')
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.modelops.models import ModelProviderConfig, ProviderApiKey
    source=create_async_engine(configured,hide_parameters=True)
    destination=create_async_engine(configured.set(database=state['name']),hide_parameters=True)
    async with AsyncSession(source) as db:
        await db.execute(text('SET TRANSACTION READ ONLY'))
        defaults=await db.get(ModelProviderConfig,'system_model_defaults')
        data=defaults.extra_config['defaults']
        ids={data['default_chat_provider_id'],*(item['provider_id'] for item in data['chat_combo_chain'] if item.get('is_active',True))}
        providers=(await db.scalars(select(ModelProviderConfig).where(ModelProviderConfig.id.in_({'system_model_defaults',*ids})))).all()
        keys=(await db.scalars(select(ProviderApiKey).where(ProviderApiKey.provider_id.in_(ids)))).all()
        records=[(type(row),{column.name:getattr(row,column.name) for column in row.__table__.columns}) for row in [*providers,*keys]]
    async with AsyncSession(destination) as db:
        assert (await db.execute(text('SELECT current_database()'))).scalar()==state['name']
        for model,payload in records:
            db.add(model(**payload))
        await db.commit()
    await source.dispose(); await destination.dispose()
    state['modelops_copy']={'providers':len(providers),'credential_rows':len(keys),'scope':'existing configured chat only; encrypted secrets remain in temporary DB, never logged; source read-only'}
    STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(state['modelops_copy']))

async def cleanup():
    configured=checked()
    state=json.loads(STATE.read_text(encoding='utf-8'))
    name=state['name']
    assert re.fullmatch(r'qnu_test_context548_[a-f0-9]{12}',name) and name != configured.database
    admin=create_async_engine(configured.set(database='postgres'),isolation_level='AUTOCOMMIT')
    async with admin.connect() as conn:
        observed=(await conn.execute(text("SELECT shobj_description(oid,'pg_database') FROM pg_database WHERE datname=:name"),{'name': name})).scalar()
        assert observed=='context548:'+state['nonce'], 'Test DB ownership mismatch; STOP'
        await conn.execute(text('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=:name AND pid<>pg_backend_pid()'),{'name': name})
        await conn.execute(text(f'DROP DATABASE "{name}"'))
        assert not (await conn.execute(text('SELECT 1 FROM pg_database WHERE datname=:name'),{'name': name})).scalar()
    await admin.dispose()
    state['status']='database_removed_storage_pending'
    STATE.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(state))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['setup','seed-modelops','run','script','cleanup'])
    parser.add_argument('--args-json')
    parser.add_argument('--state-file',type=Path,default=STATE)
    parser.add_argument('--evidence-dir',type=Path,default=EVIDENCE)
    parser.add_argument('--label',default='focused-baseline')
    parser.add_argument('tests',nargs='*')
    args=parser.parse_args()
    STATE=args.state_file.resolve()
    EVIDENCE=args.evidence_dir.resolve()
    assert STATE.is_relative_to(ROOT/'backend/storage') and EVIDENCE.is_relative_to(ROOT/'backend/storage'), 'Test state/evidence must stay in workspace Storage'
    if args.action=='setup': asyncio.run(setup())
    elif args.action=='seed-modelops': asyncio.run(seed_modelops())
    elif args.action=='cleanup': asyncio.run(cleanup())
    elif args.action=='script': raise SystemExit(script(args))
    else: raise SystemExit(run(args))
