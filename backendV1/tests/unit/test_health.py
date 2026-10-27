"""Liveness contract and route registration."""

from __future__ import annotations

from fastapi.testclient import TestClient

from qnu.main import app


def test_health_live_returns_service_identity() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_exposes_identity_routes() -> None:
    paths = app.openapi()["paths"]
    assert "/platform/v1alpha1/auth/me" in paths
    assert "/platform/v1alpha1/auth/login" in paths
