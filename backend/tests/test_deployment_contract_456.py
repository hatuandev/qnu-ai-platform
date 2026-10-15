"""Deployment contracts checked against the real Compose CLI, without services."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ComposeLoader = Callable[[dict[str, str] | None], subprocess.CompletedProcess[str]]
REQUIRED_ENV = {
    "DATABASE_URL": "postgresql+asyncpg://demo:demo@test-postgres:5432/demo",
    "REDIS_URL": "redis://test-redis:6379/0",
    "QDRANT_URL": "http://test-qdrant:6333",
    "S3_ENDPOINT": "http://test-minio:9000",
    "S3_ACCESS_KEY": "test-access",
    "S3_SECRET_KEY": "test-secret",
    "GOTENBERG_URL": "http://test-gotenberg:3000",
    "SECRET_KEY": "test-signing-key-not-used-for-real-auth",
    "PROVIDER_ENCRYPTION_KEY": "test-encryption-key-not-used-for-real-data",
    "INTERNAL_API_KEY": "test-internal-key-not-used-for-real-requests",
    "ALLOWED_ORIGINS": '["https://demo.example.test"]',
}


@pytest.fixture
def compose_config(tmp_path: Path) -> ComposeLoader:
    if not shutil.which("docker"):
        pytest.skip("Real Docker Compose CLI is required; no mock configuration is used")
    version = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
        timeout=15,
        check=False,
    )
    if version.returncode != 0:
        pytest.skip("Docker Compose plugin is unavailable; no mock configuration is used")
    env_path = tmp_path / "compose.env"
    env_path.write_text("# No project or operator secrets in this test\n", encoding="utf-8")

    def load(overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        environment = {
            name: value
            for name, value in os.environ.items()
            if name.upper()
            in {
                "PATH",
                "SYSTEMROOT",
                "SYSTEMDRIVE",
                "TEMP",
                "TMP",
                "USERPROFILE",
                "HOME",
                "APPDATA",
                "LOCALAPPDATA",
                "PROGRAMFILES",
                "PROGRAMFILES(X86)",
                "PROGRAMDATA",
            }
        }
        environment.update(REQUIRED_ENV)
        environment["DEV_ACCESS_PASSWORD"] = "test-unused-dev-password"
        environment.update(overrides or {})
        return subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(env_path),
                "-f",
                str(REPO_ROOT / "docker-compose.yml"),
                "config",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )

    return load


def test_compose_production_defaults_and_shared_security(compose_config: ComposeLoader) -> None:
    result = compose_config()
    assert result.returncode == 0, result.stderr
    services = json.loads(result.stdout)["services"]
    for service in ("bootstrap", "backend", "worker"):
        environment = services[service]["environment"]
        assert environment["ENVIRONMENT"] == "production"
        assert environment["DEV_AUTH_ENABLED"] == "false"
        assert environment["DEV_AUTH_ALLOW_IN_PRODUCTION"] == "false"
        assert environment["SSO_ENABLED"] == "true"
        assert environment["SSO_AUTHORITY"].startswith("https://")
        assert environment["PROVIDER_ENCRYPTION_KEY"] == REQUIRED_ENV["PROVIDER_ENCRYPTION_KEY"]


def test_compose_forwards_explicit_production_password_gate(compose_config: ComposeLoader) -> None:
    result = compose_config({"DEV_AUTH_ENABLED": "true", "DEV_AUTH_ALLOW_IN_PRODUCTION": "true", "SSO_ENABLED": "false"})
    assert result.returncode == 0, result.stderr
    for service in ("bootstrap", "backend", "worker"):
        environment = json.loads(result.stdout)["services"][service]["environment"]
        assert environment["DEV_AUTH_ENABLED"] == "true"
        assert environment["DEV_AUTH_ALLOW_IN_PRODUCTION"] == "true"
        assert environment["SSO_ENABLED"] == "false"


def test_compose_forwards_sso_to_api_worker_and_frontend_build(
    compose_config: ComposeLoader,
) -> None:
    result = compose_config(
        {
            "SSO_AUTHORITY": "https://identity.example.test",
            "SSO_CLIENT_ID": "demo-client",
            "SSO_AUDIENCE": "demo-api",
            "VITE_SSO_REDIRECT_URI": "/signin-oidc",
        }
    )
    assert result.returncode == 0, result.stderr
    services = json.loads(result.stdout)["services"]
    for service in ("bootstrap", "backend", "worker"):
        assert services[service]["environment"]["SSO_AUTHORITY"] == "https://identity.example.test"
        assert services[service]["environment"]["SSO_AUDIENCE"] == "demo-api"
    assert (
        services["frontend"]["build"]["args"]["VITE_SSO_AUTHORITY"]
        == "https://identity.example.test"
    )
    assert services["frontend"]["build"]["args"]["VITE_SSO_CLIENT_ID"] == "demo-client"


def test_compose_does_not_inject_legacy_llm_configuration(compose_config: ComposeLoader) -> None:
    result = compose_config(
        {"OPENAI_API_KEY": "test-stale-key", "DEFAULT_LLM_MODEL": "stale-model"}
    )
    assert result.returncode == 0, result.stderr
    for service in ("bootstrap", "backend", "worker"):
        environment = json.loads(result.stdout)["services"][service]["environment"]
        assert "OPENAI_API_KEY" not in environment
        assert "GEMINI_API_KEY" not in environment
        assert "DEFAULT_LLM_MODEL" not in environment


@pytest.mark.parametrize("name", list(REQUIRED_ENV))
def test_compose_rejects_missing_required_infrastructure_or_secret(
    compose_config: ComposeLoader, name: str
) -> None:
    result = compose_config({name: ""})
    assert result.returncode != 0
    assert name in result.stderr


def test_compose_preserves_volume_and_bootstrap_order(compose_config: ComposeLoader) -> None:
    result = compose_config()
    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    assert config["volumes"]["qnu_storage"]["name"] == "qnu_platform_storage"
    for service in ("backend", "worker"):
        assert (
            config["services"][service]["depends_on"]["bootstrap"]["condition"]
            == "service_completed_successfully"
        )
        assert not config["services"][service].get("ports")
    assert config["services"]["bootstrap"]["command"] == ["db", "bootstrap"]


def test_image_builds_require_lockfiles_and_do_not_install_retired_local_models() -> None:
    backend = (REPO_ROOT / "backend/Dockerfile").read_text(encoding="utf-8")
    frontend = (REPO_ROOT / "frontend/Dockerfile").read_text(encoding="utf-8")
    assert "uv sync --locked --no-dev" in backend
    assert "--no-editable" in backend
    assert "uv pip install" not in backend
    assert "torch torchvision" not in backend
    assert "|| true" not in backend
    assert "COPY package.json package-lock.json ./" in frontend
    assert "RUN npm ci\n" in frontend
    assert "npm ci ||" not in frontend
    lock = tomllib.loads((REPO_ROOT / "backend/uv.lock").read_text(encoding="utf-8"))
    assert not {"torch", "torchvision"} & {package["name"] for package in lock["package"]}


def test_build_context_excludes_runtime_data_and_environment_files() -> None:
    root_rules = (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    frontend_rules = (REPO_ROOT / "frontend/.dockerignore").read_text(encoding="utf-8").splitlines()
    assert "backend/storage" in root_rules
    assert "tmp" in root_rules
    assert "**/.env*" in root_rules
    assert ".env*" in frontend_rules
