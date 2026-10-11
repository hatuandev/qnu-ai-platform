import asyncio
import sys
from pathlib import Path

import httpx

from app.core.config import settings

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8001"
API_PREFIX = settings.API_PREFIX


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120) as client:
        # 1. Login
        login_resp = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"access_key": settings.DEV_ACCESS_PASSWORD},
        )
        login_resp.raise_for_status()
        token = login_resp.cookies.get("qnu_session", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        print(f"Logged in successfully. Session cookie: {bool(token)}")

        # 2. Ensure collection
        cols_resp = await client.get(f"{API_PREFIX}/knowledge/collections", headers=headers)
        cols_resp.raise_for_status()
        cols = cols_resp.json()
        if cols:
            col_id = cols[0]["id"]
            print(f"Using existing collection: {col_id} ({cols[0]['name']})")
        else:
            create_col = await client.post(
                f"{API_PREFIX}/knowledge/collections",
                headers=headers,
                json={
                    "name": "Bộ sưu tập Kiểm thử E2E Document Studio",
                    "module_code": "admissions",
                    "description": "Kiểm thử chức năng bóc tách, đối soát khung OCR và hiệu đính 2 chiều",
                },
            )
            create_col.raise_for_status()
            col_id = create_col.json()["id"]
            print(f"Created collection: {col_id}")

        # 3. Check or Upload fixture to documents repository
        fixture_path = Path(__file__).resolve().parents[1] / "storage" / "e2e_fixtures" / "341" / "e2e341_scan_2pages.pdf"
        assert fixture_path.exists(), f"Fixture not found at {fixture_path}"

        file_bytes = await asyncio.to_thread(fixture_path.read_bytes)

        upload_resp = await client.post(
            f"{API_PREFIX}/documents",
            headers=headers,
            files={"file": ("e2e341_scan_2pages.pdf", file_bytes, "application/pdf")},
            data={"title": "Tài liệu scan kiểm thử E2E Document Studio #341"},
        )
        if upload_resp.status_code in (200, 201):
            doc_id = upload_resp.json()["id"]
            print(f"Uploaded new document: {doc_id}")
        else:
            # Document might already exist by hash, query existing
            list_docs = await client.get(f"{API_PREFIX}/documents?search=e2e341_scan_2pages", headers=headers)
            list_docs.raise_for_status()
            items = list_docs.json().get("items", [])
            assert items, "Failed to find or upload document"
            doc_id = items[0]["id"]
            print(f"Found existing document: {doc_id}")

        # 4. Import snapshot into knowledge collection with vision_ocr
        import_batch_resp = await client.post(
            f"{API_PREFIX}/knowledge/collections/{col_id}/imports",
            headers=headers,
            json={
                "document_ids": [doc_id],
                "parser_profile": "vision_ocr",
                "ocr_engine": "paddleocr",
                "chunk_strategy": "ClauseBasedChunker",
            },
        )
        import_batch_resp.raise_for_status()
        batch_data = import_batch_resp.json()
        batch_id = batch_data["id"]
        print(f"Created snapshot import batch: {batch_id}, status: {batch_data['status']}")

        # 5. Poll for completion
        for _ in range(60):
            poll_resp = await client.get(
                f"{API_PREFIX}/knowledge/collections/{col_id}/imports/{batch_id}",
                headers=headers,
            )
            poll_resp.raise_for_status()
            current_batch = poll_resp.json()
            status = current_batch["status"]
            print(f"Batch status: {status} (succeeded={current_batch.get('succeeded_count')}, review={current_batch.get('review_required_count')}, failed={current_batch.get('failed_count')})")
            if status in ("completed", "partial_failed", "review_required"):
                break
            await asyncio.sleep(2)

        # 6. Retrieve knowledge source
        sources_resp = await client.get(f"{API_PREFIX}/knowledge/collections/{col_id}/bindings", headers=headers)
        sources_resp.raise_for_status()
        bindings = sources_resp.json()
        assert bindings, "No bindings created in collection"
        target_binding = next((b for b in bindings if b.get("repository_document_id") == doc_id), bindings[0])
        source_id = target_binding["id"]
        print(f"Target knowledge source binding: {source_id}")

        # 7. Check Studio API
        studio_resp = await client.get(
            f"{API_PREFIX}/knowledge/collections/{col_id}/sources/{source_id}/studio",
            headers=headers,
        )
        studio_resp.raise_for_status()
        studio_data = studio_resp.json()
        print(f"Studio API verification: total_pages={studio_data['total_pages']}, engine={studio_data['engine']}")
        for p in studio_data["pages"]:
            print(f"  Page {p['page_number']}: word_count={p['word_count']}, boxes={len(p['bounding_boxes'])}, regions={len(p['regions'])}, dimensions={p.get('dimensions')}")
            for b in p["bounding_boxes"][:3]:
                print(f"    Box: label={b['label']}, layout_conf={b.get('layout_confidence')}, text_conf={b.get('text_confidence')}, coords={b['coordinates']}")

        frontend_url = f"http://127.0.0.1:3000/knowledge/{col_id}/sources/{source_id}"
        print(f"\nSUCCESS! Target Frontend URL for Playwright testing: {frontend_url}\n")
        return {"col_id": col_id, "source_id": source_id, "token": token, "url": frontend_url}


if __name__ == "__main__":
    asyncio.run(main())
