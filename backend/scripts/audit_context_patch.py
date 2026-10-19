"""Read-only endpoint audit. Never prints credentials or changes service config."""
import argparse
import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def main():
    db = make_url(settings.DATABASE_URL)
    def endpoint(value):
        url = urlsplit(value)
        return {'scheme': url.scheme,'host': url.hostname,'port': url.port}
    report = {'environment': settings.ENVIRONMENT,
        'database': {'host': db.host,'port': db.port,'database': db.database,'driver': db.drivername},
        'storage': {'driver': settings.STORAGE_DRIVER,'local_root': str(Path(settings.LOCAL_STORAGE_PATH).resolve()),'minio': endpoint(settings.S3_ENDPOINT)},
        'qdrant': endpoint(settings.QDRANT_URL),'auto_migrate': settings.DEV_AUTO_MIGRATE,'auto_seed': settings.DEV_AUTO_SEED,
        'previous_preflight': {'log_exists': (Path(__file__).resolve().parents[2]/'backend/storage/context548-preflight.log').exists(),'results_available': False}}
    if settings.ENVIRONMENT not in {'development','dev','local','test','testing'} or db.host not in {'localhost','127.0.0.1','::1'}:
        report['decision']='BLOCKED: database is not verified local; no connection attempted'
    else:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as connection:
            await connection.execute(text('SET TRANSACTION READ ONLY'))
            row = (await connection.execute(text('SELECT current_database() AS database, inet_server_addr()::text AS server_address, inet_server_port() AS server_port, current_setting(\'transaction_read_only\') AS read_only'))).mappings().one()
            report['observed_database']=dict(row)
        await engine.dispose()
        report['decision']='LOCAL_CONFIG_VERIFIED; tests NOT authorized on shared application database without isolation'
    path=args.output.resolve()
    assert path.is_relative_to(Path(__file__).resolve().parents[2]/'backend/storage')
    path.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,ensure_ascii=True))

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[2]/'backend/storage/context548-safety.json')
args = parser.parse_args()
asyncio.run(main())
