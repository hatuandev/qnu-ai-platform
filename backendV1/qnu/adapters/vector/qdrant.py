"""Qdrant dense generations; only backendV1-owned names may be written."""

from __future__ import annotations

import hashlib
import math
import re

import httpx

from qnu.platform.config import get_settings
from qnu.platform.errors import AppException, DependencyUnavailable
from qnu.platform.network_policy import assert_allowed_endpoint
from qnu.ports.vector_store import VectorHit

PAYLOAD_INDEX_FIELDS = ("run_id", "workspace_id", "collection_id", "version_id", "chunk_id")


class QdrantVectorStore:
    async def delete_points(self, collection: str, point_ids: list[str]) -> None:
        import uuid

        self._name(collection)
        for value in point_ids:
            uuid.UUID(value)
        if not point_ids:
            return
        response = await self._request(
            "POST",
            f"/collections/{collection}/points/delete?wait=true",
            body={"points": point_ids},
        )
        if (
            response.status_code != 404
            and response.json().get("result", {}).get("status") != "completed"
        ):
            raise DependencyUnavailable(
                "Qdrant chưa hoàn tất xóa vector.", code="purge_vector_pending"
            )

    def __init__(
        self, base_url: str | None = None, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._base = (base_url or get_settings().QDRANT_URL).rstrip("/")
        self._transport = transport

    @property
    def target_hash(self) -> str:
        return hashlib.sha256(self._base.encode()).hexdigest()

    def _name(self, name: str) -> None:
        if not re.fullmatch(r"qnu_v1_idx_[a-f0-9]{32}", name):
            raise AppException(
                "Vector collection không thuộc namespace v1.",
                code="vector_collection_forbidden",
                status_code=403,
            )

    async def _request(self, method: str, path: str, *, body: dict | None = None) -> httpx.Response:
        # Infrastructure address comes only from server settings, never request/model input.
        assert_allowed_endpoint(self._base, allow_private=True)
        headers = {}
        api_key = get_settings().QDRANT_API_KEY
        if api_key:
            headers["api-key"] = api_key
        try:
            async with httpx.AsyncClient(
                timeout=get_settings().HTTP_TIMEOUT_SECONDS,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
                headers=headers,
            ) as client:
                result = await client.request(method, self._base + path, json=body)
        except httpx.RequestError as exc:
            raise DependencyUnavailable(
                "Không kết nối được Qdrant.", code="vector_unavailable"
            ) from exc
        if result.status_code not in (200, 201, 404):
            raise DependencyUnavailable(
                "Qdrant từ chối hoặc không xử lý được yêu cầu.", code="vector_unavailable"
            )
        return result

    async def collection_exists(self, collection: str) -> bool:
        self._name(collection)
        response = await self._request("GET", f"/collections/{collection}")
        return response.status_code == 200

    async def count(self, collection: str) -> int:
        self._name(collection)
        response = await self._request(
            "POST", f"/collections/{collection}/points/count", body={"exact": True}
        )
        if response.status_code != 200:
            raise DependencyUnavailable("Không kiểm được số vector.", code="vector_unavailable")
        return int(response.json()["result"]["count"])

    async def health(self) -> dict:
        response = await self._request("GET", "/collections")
        return {"ok": response.status_code == 200}

    async def ensure_collection(self, collection: str, size: int, distance: str = "Cosine") -> None:
        self._name(collection)
        response = await self._request("GET", f"/collections/{collection}")
        if response.status_code == 404:
            response = await self._request(
                "PUT",
                f"/collections/{collection}",
                body={"vectors": {"size": size, "distance": distance}},
            )
            if response.status_code not in (200, 201):
                raise DependencyUnavailable(
                    "Không tạo được vector collection.", code="vector_unavailable"
                )
        else:
            try:
                vectors = response.json()["result"]["config"]["params"]["vectors"]
                if vectors["size"] != size or vectors["distance"] != distance:
                    raise ValueError()
            except (ValueError, KeyError, TypeError) as exc:
                raise DependencyUnavailable(
                    "Vector collection không khớp dimension/distance.",
                    code="vector_configuration_mismatch",
                ) from exc
        await self._ensure_payload_indexes(collection)

    async def _ensure_payload_indexes(self, collection: str) -> None:
        # Idempotent in Qdrant; creating an existing keyword index is a no-op.
        for field in PAYLOAD_INDEX_FIELDS:
            response = await self._request(
                "PUT",
                f"/collections/{collection}/index?wait=true",
                body={"field_name": field, "field_schema": "keyword"},
            )
            if response.status_code != 200:
                raise DependencyUnavailable(
                    "Không tạo được payload index cho vector collection.",
                    code="vector_unavailable",
                )
            try:
                if response.json()["result"]["status"] != "completed":
                    raise ValueError()
            except (ValueError, KeyError, TypeError) as exc:
                raise DependencyUnavailable(
                    "Qdrant chưa xác nhận payload index.", code="vector_unavailable"
                ) from exc

    async def upsert(self, collection: str, points: list[dict]) -> None:
        self._name(collection)
        result = await self._request(
            "PUT", f"/collections/{collection}/points?wait=true", body={"points": points}
        )
        if result.status_code != 200:
            raise DependencyUnavailable("Không ghi được vector.", code="vector_unavailable")
        try:
            if result.json()["result"]["status"] != "completed":
                raise ValueError()
        except (ValueError, KeyError, TypeError) as exc:
            raise DependencyUnavailable(
                "Qdrant chưa xác nhận ghi xong vector.", code="vector_unavailable"
            ) from exc

    async def search(
        self, collection: str, vector: list[float], limit: int, scope: dict
    ) -> list[VectorHit]:
        self._name(collection)
        filters = {
            "must": [
                {
                    "key": key,
                    "match": {"any": value} if isinstance(value, list) else {"value": value},
                }
                for key, value in scope.items()
            ]
        }
        response = await self._request(
            "POST",
            f"/collections/{collection}/points/search",
            body={
                "vector": vector,
                "limit": limit,
                "with_payload": True,
                "filter": filters,
            },
        )
        if response.status_code == 404:
            raise DependencyUnavailable(
                "Vector collection đã mất.", code="vector_collection_missing"
            )
        try:
            rows = response.json()["result"]
            if not isinstance(rows, list) or len(rows) > limit:
                raise ValueError()
            hits = []
            for row in rows:
                score = row["score"]
                if (
                    type(score) not in (int, float)
                    or not math.isfinite(score)
                    or not isinstance(row["payload"], dict)
                ):
                    raise ValueError()
                hits.append(VectorHit(str(row["id"]), float(score), row["payload"]))
            return hits
        except (ValueError, KeyError, TypeError) as exc:
            raise DependencyUnavailable(
                "Phản hồi vector sai cấu trúc.", code="vector_response_invalid"
            ) from exc

    async def delete_collection(self, collection: str) -> None:
        self._name(collection)
        await self._request("DELETE", f"/collections/{collection}")
