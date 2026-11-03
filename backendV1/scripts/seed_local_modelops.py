"""Install the QNU ModelOps defaults for a local V1 development database."""

import asyncio
import getpass
import sys
import warnings
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from qnu.domains.identity.dev_gate import dev_admin_actor
from qnu.domains.modelops.catalog.service import catalog_service
from qnu.domains.modelops.connections import service
from qnu.domains.modelops.connections.schemas import ConnectionCreate, ConnectionModelCreate
from qnu.domains.modelops.diagnostics.router import get_diagnostic_client
from qnu.domains.modelops.keys.service import key_service
from qnu.domains.modelops.providers.service import provider_service
from qnu.domains.modelops.reasoning import EXTRA_CONFIG_KEY, REASONING_TASKS, ReasoningPolicy
from qnu.domains.modelops.schemas import DefaultsUpdateRequest, KeyCreateRequest
from qnu.platform.config import get_settings
from qnu.platform.database import AsyncSessionFactory, engine
from qnu.platform.errors import AppException

QNU_GATEWAY = "http://100.105.13.53:8000"
ROUTER_URL = "https://qnu-9router.duckdns.org/v1"
ROUTER_KEY = "E2E_9ROUTER_API_KEY"
QWEN_MODEL = "qwen3.8-27b-q4"
# This QNU endpoint/model contract was exercised in sessions 778 and 802.
QWEN_REASONING = ReasoningPolicy(
    mode="chat_template_kwarg",
    parameter="enable_thinking",
    off_value=False,
    tasks={"off": list(REASONING_TASKS)},
    verified=True,
)
PROFILE = (
    (
        "QNU AI Server",
        QNU_GATEWAY + "/v1",
        "openai_compatible",
        {
            "chat": QWEN_MODEL,
            "embedding": "bge-m3",
            "rerank": "bge-reranker-v2-m3",
        },
    ),
    ("QNU MinerU GPU", QNU_GATEWAY + "/mineru", "mineru", {"ocr": "mineru"}),
    ("9router Luna", ROUTER_URL, "openai_compatible", {"chat": "cx/gpt-6-luna"}),
)


async def seed():
    actor = dev_admin_actor()
    client = get_diagnostic_client()
    async with AsyncSessionFactory() as db:
        connections = await service.list_connections(db)
        defaults = {}
        credential = None
        for name, url, api_type, models in PROFILE:
            matching = [
                row
                for row in connections
                if row.base_url.rstrip("/") == url and row.api_type == api_type
            ]
            if len(matching) > 1 or (matching and not matching[0].is_active):
                raise ValueError(f"Kiểm tra kết nối trùng hoặc đang tắt trong ModelOps: {name}")
            connection = matching[0] if matching else None
            keys = await key_service.list_keys(db, connection.id) if connection else []
            if not any(key.status == "active" and key.model_ids is None for key in keys):
                if url == ROUTER_URL:
                    env_file = Path(__file__).resolve().parents[2] / ".env"
                    secret = (
                        dotenv_values(env_file, interpolate=False).get(ROUTER_KEY) or ""
                    ).strip()
                    if not 8 <= len(secret) <= 4096:
                        raise AppException(
                            "Thiếu API key 9router trong .env gốc.",
                            code="seed_9router_key_missing",
                        )
                    connection_key = KeyCreateRequest(name="9router local", secret=secret)
                elif credential is None:
                    credential = KeyCreateRequest(
                        name="QNU local",
                        secret=getpass.getpass("API key QNU dùng chung với MinerU: "),
                    )
                    connection_key = credential
                else:
                    connection_key = credential
                if connection is None:
                    connection = await service.save_connection(
                        db,
                        actor,
                        ConnectionCreate(
                            name=name,
                            base_url=url,
                            family="qnu",
                            api_type=api_type,
                            timeout_seconds=300,
                        ),
                    )
                parent = await service.get_connection(db, connection.id)
                await key_service.add_key(db, parent, connection_key, actor)
            registered = {
                row.model_name: row for row in await service.list_models(db, connection.id)
            }
            for capability, model_name in models.items():
                model = registered.get(model_name)
                if model is None:
                    model = await service.add_model(
                        db,
                        actor,
                        connection.id,
                        ConnectionModelCreate(model_name=model_name, capabilities=[capability]),
                        client=client,
                    )
                if (
                    url == QNU_GATEWAY + "/v1"
                    and model_name == QWEN_MODEL
                    and (model.extra_config or {}).get(EXTRA_CONFIG_KEY)
                    != QWEN_REASONING.model_dump(mode="json")
                ):
                    await provider_service.set_reasoning(db, model.id, QWEN_REASONING, actor)
                if url != ROUTER_URL:
                    defaults[f"{capability}_provider_id"] = model.id
        current = await catalog_service.get_defaults(db)
        if current is None or any(getattr(current, k) != v for k, v in defaults.items()):
            await catalog_service.update_defaults(db, DefaultsUpdateRequest(**defaults), actor)
        for _, _, _, models in PROFILE:
            for capability, model_name in models.items():
                print(f"{capability}: {model_name}")


async def main():
    settings = get_settings()
    if (
        settings.ENVIRONMENT.lower() != "development"
        or not settings.DEV_AUTH_ENABLED
        or make_url(settings.DATABASE_URL).host not in {"localhost", "127.0.0.1", "::1"}
    ):
        print("Seed chỉ dành cho DB development trên máy local.", file=sys.stderr)
        return 2
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            await seed()
    except AppException as exc:
        print(f"Seed dừng: {exc.code}. Sửa cấu hình rồi chạy lại.", file=sys.stderr)
        return 1
    except (ValueError, EOFError, getpass.GetPassWarning):
        print(
            "Seed dừng. Kiểm tra kết nối ModelOps hoặc nhập khóa ẩn trong terminal.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"Seed dừng ({type(exc).__name__}). Kiểm tra DB và migration.", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
