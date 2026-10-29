"""Read-only physical purge checks, restricted to a generated E2E session."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from v1_e2e_session import BE, environment, load_session, read, save


async def inspect(directory: Path, mode: str):
    # Set the verified private environment before importing any QNU settings/models.
    env = environment(directory)
    manifest = read(directory / "manifest.json")
    expected = f"127.0.0.1:{manifest['ports']['postgres']}/qnu_v1_test_e2e_{manifest['run_id']}"
    if (
        expected not in env["DATABASE_URL"]
        or env["S3_BUCKET"] != "qnu-e2e-" + manifest["run_id"]
    ):
        raise RuntimeError("Probe refuses a database/bucket outside the E2E session.")
    os.environ.update(env)
    sys.path.insert(0, str(BE))
    import boto3
    import httpx
    import qnu.main  # noqa: F401 — registers all models without starting lifespan
    from qnu.domains.knowledge.index.models import IndexRun
    from qnu.domains.lifecycle.purge_graph import graph_for_source, graph_plan
    from qnu.platform.database import Base
    from sqlalchemy import select, text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    state = read(directory / "checkpoint.json")
    source = state["sources"][0]
    engine = create_async_engine(env["DATABASE_URL"])
    try:
        if mode == "capture":
            async with async_sessionmaker(engine)() as db, db.begin():
                await db.execute(text("SET TRANSACTION READ ONLY"))
                graph = await graph_for_source(db, state["workspace"], source["id"])
                plan = graph_plan(graph)
                vectors = {}
                for chunk in graph.get("kb_index_chunks", {}).values():
                    run = await db.get(IndexRun, chunk["run_id"])
                    if not run:
                        raise RuntimeError("Missing indexing run in purge graph.")
                    vectors.setdefault(run.vector_collection, []).append(
                        chunk["point_id"]
                    )
                save(
                    directory / "purge-proof.json",
                    {
                        "source": source["id"],
                        "objects": list(plan["objects"]),
                        "vectors": vectors,
                    },
                )
        else:
            proof = read(directory / "purge-proof.json")
            if proof["source"] != source["id"] or not proof["objects"]:
                raise RuntimeError("Missing source-bound object proof.")
            s3 = boto3.client(
                "s3",
                endpoint_url=env["S3_ENDPOINT"],
                aws_access_key_id=env["S3_ACCESS_KEY"],
                aws_secret_access_key=env["S3_SECRET_KEY"],
            )
            for key in proof["objects"]:
                paginator = s3.get_paginator("list_object_versions")
                for page in paginator.paginate(Bucket=env["S3_BUCKET"], Prefix=key):
                    if any(
                        row["Key"] == key
                        for field in ("Versions", "DeleteMarkers")
                        for row in page.get(field, [])
                    ):
                        raise RuntimeError(
                            "Purge left an S3 object version/delete marker."
                        )
            async with httpx.AsyncClient(
                base_url=env["QDRANT_URL"], timeout=30
            ) as client:
                for collection, ids in proof["vectors"].items():
                    for offset in range(0, len(ids), 256):
                        response = await client.post(
                            f"/collections/{collection}/points",
                            json={
                                "ids": ids[offset : offset + 256],
                                "with_payload": False,
                                "with_vector": False,
                            },
                        )
                        if response.status_code != 404:
                            response.raise_for_status()
                            if response.json()["result"]:
                                raise RuntimeError("Purge left Qdrant points.")
            async with async_sessionmaker(engine)() as db, db.begin():
                await db.execute(text("SET TRANSACTION READ ONLY"))
                table = Base.metadata.tables["kb_sources"]
                if await db.scalar(
                    select(table.c.id).where(table.c.id == source["id"])
                ):
                    raise RuntimeError("Purge left the source row in PostgreSQL.")
            save(
                directory / "purge-verification.json",
                {
                    "source_row_absent": True,
                    "all_s3_versions_absent": True,
                    "vector_points_absent": True,
                },
            )
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True)
    parser.add_argument("mode", choices=("capture", "verify"))
    args = parser.parse_args()
    try:
        directory, manifest = load_session(args.session)
        if manifest["cleaned"]:
            raise RuntimeError("Session was cleaned.")
        asyncio.run(inspect(directory, args.mode))
        print(json.dumps({"probe": args.mode, "status": "PASS"}))
    except Exception as exc:  # noqa: BLE001 — sanitize credential-bearing SDK exceptions
        print(f"Probe FAIL: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
