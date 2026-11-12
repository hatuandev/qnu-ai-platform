"""Read-only startup diagnostics; fixtures never connect to application services."""

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import OperationalError

SPEC = importlib.util.spec_from_file_location(
    "check_v1_runtime", Path(__file__).parents[1] / "check_v1_runtime.py"
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class CheckTests(unittest.IsolatedAsyncioTestCase):
    def database_engine(self, results):
        connection = Mock(scalar=AsyncMock(side_effect=results))
        engine = Mock(dispose=AsyncMock())
        engine.connect.return_value.__aenter__ = AsyncMock(return_value=connection)
        engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)
        return engine, connection

    async def test_missing_version_table_is_schema_problem_not_connection_problem(self):
        engine, connection = self.database_engine([False])
        with patch.object(checker, "create_async_engine", return_value=engine):
            ok, detail = await checker.check_database("test-url", "head")
        self.assertFalse(ok)
        self.assertIn("not initialized", detail)
        self.assertIn("v1-migrate", detail)
        self.assertEqual(connection.scalar.await_count, 1)
        engine.dispose.assert_awaited_once()

    async def test_current_schema_is_ready(self):
        engine, _ = self.database_engine([True, "head"])
        with patch.object(checker, "create_async_engine", return_value=engine):
            self.assertTrue((await checker.check_database("test-url", "head"))[0])

    async def test_old_schema_does_not_auto_migrate(self):
        engine, _ = self.database_engine([True, "old"])
        with patch.object(checker, "create_async_engine", return_value=engine):
            ok, detail = await checker.check_database("test-url", "head")
        self.assertFalse(ok)
        self.assertIn("v1-db-check", detail)

    async def test_schema_mismatch_reports_both_revisions(self):
        engine, _ = self.database_engine([True, "0022_new"])
        with patch.object(checker, "create_async_engine", return_value=engine):
            ok, detail = await checker.check_database("test-url", "0021_old")
        self.assertFalse(ok)
        self.assertIn("0022_new", detail)
        self.assertIn("0021_old", detail)
        self.assertIn("SCHEMA_HEAD", detail)

    async def test_connection_error_is_sanitized(self):
        engine, _ = self.database_engine([])
        engine.connect.return_value.__aenter__ = AsyncMock(
            side_effect=OperationalError(
                "private-db", {}, RuntimeError("private-password")
            )
        )
        with patch.object(checker, "create_async_engine", return_value=engine):
            ok, detail = await checker.check_database("private-url", "head")
        self.assertFalse(ok)
        self.assertNotIn("private", detail)
        engine.dispose.assert_awaited_once()

    async def test_redis_timeout_closes_client_without_exposing_url(self):
        client = Mock(
            ping=AsyncMock(side_effect=RedisConnectionError("private-url")),
            aclose=AsyncMock(),
        )
        with patch.object(checker.Redis, "from_url", return_value=client):
            ok, detail = await checker.check_redis("private-url")
        self.assertFalse(ok)
        self.assertNotIn("private-url", detail)
        client.aclose.assert_awaited_once()

    async def test_redis_ping_success(self):
        client = Mock(ping=AsyncMock(return_value=True), aclose=AsyncMock())
        with patch.object(checker.Redis, "from_url", return_value=client):
            self.assertTrue((await checker.check_redis("private-url"))[0])

    async def test_qdrant_reads_collections_only(self):
        client = Mock(get=AsyncMock(return_value=Mock(status_code=200)))
        manager = Mock()
        manager.__aenter__ = AsyncMock(return_value=client)
        manager.__aexit__ = AsyncMock(return_value=False)
        with patch.object(checker.httpx, "AsyncClient", return_value=manager):
            self.assertTrue((await checker.check_qdrant("http://test-vector/"))[0])
        client.get.assert_awaited_once_with("http://test-vector/collections")

    async def test_frontend_missing_reports_install_step(self):
        settings = SimpleNamespace(REDIS_URL="r", DATABASE_URL="d", QDRANT_URL="v")
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(
                checker, "check_redis", new=AsyncMock(return_value=(True, "ok"))
            ),
            patch.object(
                checker, "check_database", new=AsyncMock(return_value=(True, "ok"))
            ),
            patch.object(
                checker, "check_qdrant", new=AsyncMock(return_value=(True, "ok"))
            ),
            patch.object(
                checker,
                "check_storage",
                new=AsyncMock(return_value=(False, "storage offline")),
                create=True,
            ),
        ):
            root = Path(directory)
            result = await checker.inspect(settings, root, "head")
            vite_v1 = root / "frontendV1/node_modules/vite/bin/vite.js"
            vite_v1.parent.mkdir(parents=True)
            vite_v1.touch()
            v2_missing = await checker.inspect(settings, root, "head", "frontendV2")
            vite_v2 = root / "frontendV2/node_modules/vite/bin/vite.js"
            vite_v2.parent.mkdir(parents=True)
            vite_v2.touch()
            v2_ready = await checker.inspect(settings, root, "head", "frontendV2")
        self.assertFalse(result["frontend"][0])
        self.assertIn("v1-install-fe", result["frontend"][1])
        self.assertFalse(result["storage"][0])
        self.assertEqual(v2_missing["frontend"], (False, "Run npm ci in frontendV2 first"))
        self.assertEqual(v2_ready["frontend"], (True, "Vite installed in frontendV2"))


class CheckOutputTests(unittest.TestCase):
    def test_schema_failure_does_not_instruct_restarting_healthy_docker(self):
        results = {
            "redis": (True, "ready"),
            "postgresql": (False, "schema not initialized; run v1-migrate"),
            "qdrant": (True, "ready"),
            "frontend": (True, "ready"),
        }
        with (
            patch.object(checker, "inspect", new=AsyncMock(return_value=results)),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(checker.main(), 1)
        self.assertIn("v1-migrate", output.getvalue())
        self.assertNotIn("open Docker Desktop", output.getvalue())

    def test_all_dependencies_pass_returns_zero(self):
        results = {
            name: (True, "ready")
            for name in ("redis", "postgresql", "qdrant", "frontend")
        }
        with (
            patch.object(checker, "inspect", new=AsyncMock(return_value=results)),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(checker.main(), 0)
        self.assertNotIn("[FAIL]", output.getvalue())
