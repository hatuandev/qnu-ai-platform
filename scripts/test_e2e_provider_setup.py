"""Offline provider bootstrap regressions; no server, credential or browser required."""

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import e2e_provider_setup as setup
import httpx
from v1_e2e_session import read, save


class ProviderSetupTests(unittest.TestCase):
    def test_mineru_bootstrap_uses_task_protocol_and_qnu_key_source(self):
        self.assertEqual(setup.KEY_ENV_NAMES["ocrProviderSetup"], "E2E_QNU_API_KEY")
        seen = []
        def handle(incoming):
            if incoming.url.path.endswith("/connections"):
                if incoming.method == "GET":
                    return httpx.Response(200,json=[])
                body=json.loads(incoming.content);seen.append(body)
                return httpx.Response(201,json={"id":"ocr-conn","is_active":True,"api_type":body["api_type"]})
            return httpx.Response(200,json=[{"id":"ocr-key","status":"active"}])
        with httpx.Client(base_url="http://example.test/",transport=httpx.MockTransport(handle)) as client:
            state={"runId":"test-ocr"}
            setup.prepare_connection(client,self.directory,state,
                {"base_url":"https://upstream.test/mineru","api_type":"mineru","timeout_seconds":300},
                "ocrProviderSetup","OCR","qnu")
        self.assertEqual(seen[0]["api_type"],"mineru")
        self.assertEqual(seen[0]["timeout_seconds"],300)
        self.assertEqual(state["ocrProviderSetup"]["keyId"],"ocr-key")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        env_patch = patch.object(
            setup, "KEY_ENV_FILE", self.directory / ".env", create=True
        )
        env_patch.start()
        self.addCleanup(env_patch.stop)
        self.profile = self.directory / "profile.json"
        save(self.profile, {"base_url": "http://example.test/v1"})
        save(
            self.directory / "manifest.json",
            {
                "run_id": "e00000000000",
                "mode": "live",
                "cleaned": False,
                "ports": {"api": 1234},
            },
        )
        save(self.directory / "checkpoint.json", {"results": {}})
        self.key_added = False
        self.secret = "synthetic-test-only-secret"
        self.calls = []

    def handler(self, request):
        suffix = request.url.path.removeprefix("/platform/v1alpha1/")
        self.calls.append((request.method, suffix))
        if suffix == "auth/login":
            return httpx.Response(200, json={"access_token": "synthetic-admin-token"})
        if suffix == "modelops/connections" and request.method == "GET":
            return httpx.Response(200, json=[])
        if suffix == "modelops/connections":
            return httpx.Response(201, json={"id": "conn_test", "is_active": True})
        if request.method == "POST":
            self.assertEqual(json.loads(request.content)["secret"], self.secret)
            self.key_added = True
            return httpx.Response(201, json={"id": "key_test", "status": "active"})
        return httpx.Response(
            200, json=[{"id": "key_test", "status": "active"}] if self.key_added else []
        )

    def test_hidden_key_is_sent_to_local_modelops_but_not_saved_in_checkpoint(self):
        client = httpx.Client(
            base_url="http://127.0.0.1:1234/platform/v1alpha1/",
            transport=httpx.MockTransport(self.handler),
        )
        with (
            patch.object(setup.httpx, "Client", return_value=client),
            patch.object(setup.sys.stdin, "isatty", return_value=True),
            patch.object(setup.getpass, "getpass", return_value=self.secret),
        ):
            setup.prepare_provider(
                self.directory,
                {"DEV_ACCESS_PASSWORD": "fixture-dev-password"},
                self.profile,
            )
        state = read(self.directory / "checkpoint.json")
        self.assertEqual(state["providerSetup"]["connectionId"], "conn_test")
        self.assertEqual(state["providerSetup"]["keyId"], "key_test")
        for file in self.directory.iterdir():
            self.assertNotIn(self.secret, file.read_text())
        self.assertTrue(self.key_added)

    def test_noninteractive_terminal_does_not_fall_back_to_echoed_input(self):
        client = httpx.Client(
            base_url="http://127.0.0.1:1234/platform/v1alpha1/",
            transport=httpx.MockTransport(self.handler),
        )
        with (
            patch.object(setup.httpx, "Client", return_value=client),
            patch.object(setup.sys.stdin, "isatty", return_value=False),
            patch.object(setup.getpass, "getpass") as prompt,
            self.assertRaisesRegex(RuntimeError, "PowerShell"),
        ):
            setup.prepare_provider(
                self.directory,
                {"DEV_ACCESS_PASSWORD": "fixture-dev-password"},
                self.profile,
            )
        prompt.assert_not_called()
        self.assertFalse(self.key_added)

    def test_error_never_includes_upstream_or_request_secret(self):
        response = httpx.Response(403, json={"detail": self.secret})
        client = unittest.mock.Mock()
        client.request.return_value = response
        with self.assertRaises(RuntimeError) as error:
            setup.request(client, "POST", "keys", {"secret": self.secret})
        self.assertNotIn(self.secret, str(error.exception))

    def test_provider_toggle_setup_is_blocked_after_upload(self):
        save(self.directory / "checkpoint.json", {"sources": [{"id": "src_test"}]})
        with (
            patch.object(setup.httpx, "Client") as client,
            self.assertRaisesRegex(RuntimeError, "upload"),
        ):
            setup.prepare_provider(
                self.directory,
                {"DEV_ACCESS_PASSWORD": "fixture-dev-password"},
                self.profile,
            )
        client.assert_not_called()

    def run_two_providers(self, *, limits, answers, from_env=False):
        profile = read(self.profile)
        profile.update(
            models={"chat": "qwen-test"},
            additional_chat_provider={
                "base_url": "https://router.test/v1",
                "models": {"chat": "ollama/gpt-oss:120b"},
            },
        )
        save(self.profile, profile)
        providers, keys, sent = [], {}, []
        secrets = {
            "conn_qnu": "synthetic-qnu-secret",
            "conn_router": "synthetic-router-secret",
        }

        def handle(incoming):
            suffix = incoming.url.path.removeprefix("/platform/v1alpha1/")
            body = json.loads(incoming.content) if incoming.content else {}
            if suffix == "auth/login":
                return httpx.Response(200, json={"access_token": "test-admin"})
            if suffix == "modelops/connections":
                if incoming.method == "GET":
                    return httpx.Response(200, json=providers)
                row = {
                    **body,
                    "id": "conn_qnu" if body["family"] == "qnu" else "conn_router",
                    "is_active": True,
                }
                providers.append(row)
                return httpx.Response(201, json=row)
            if suffix.endswith("/keys"):
                identifier = suffix.split("/")[2]
                if incoming.method == "POST":
                    self.assertEqual(body["secret"], secrets[identifier])
                    sent.append(identifier)
                    keys[identifier] = [{"id": "key_" + identifier, "status": "active"}]
                    return httpx.Response(201, json=keys[identifier][0])
                return httpx.Response(200, json=keys.get(identifier, []))
            if suffix.endswith("/test"):
                return httpx.Response(
                    200,
                    json={
                        "ok": True,
                        "check_id": "diag_router",
                        "models": ["ollama/gpt-oss:120b"],
                    },
                )
            if suffix.endswith("/sync-capacity"):
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": "model_router",
                            "model_name": "ollama/gpt-oss:120b",
                            "token_limits": limits,
                        }
                    ],
                )
            if suffix.endswith("/models"):
                return httpx.Response(
                    200, json=[] if incoming.method == "GET" else {"id": "model_router"}
                )
            if (
                suffix == "modelops/providers/model_router"
                and incoming.method == "PATCH"
            ):
                sent.append(body)
                return httpx.Response(200, json={"id": "model_router"})
            raise AssertionError(suffix)

        client = httpx.Client(
            base_url="http://127.0.0.1:1234/platform/v1alpha1/",
            transport=httpx.MockTransport(handle),
        )
        output = io.StringIO()
        if from_env:
            (self.directory / ".env").write_text(
                "E2E_QNU_API_KEY=synthetic-qnu-secret\n"
                "E2E_9ROUTER_API_KEY='synthetic-router-secret'\n",
                encoding="utf-8",
            )
        with (
            patch.object(setup.httpx, "Client", return_value=client),
            patch.object(setup.sys.stdin, "isatty", return_value=True),
            patch.object(
                setup.getpass, "getpass", side_effect=secrets.values()
            ) as prompt,
            patch("builtins.input", side_effect=answers) as choice,
            patch("sys.stdout", output),
        ):
            setup.prepare_provider(
                self.directory, {"DEV_ACCESS_PASSWORD": "test-password"}, self.profile
            )
        if from_env:
            prompt.assert_not_called()
        else:
            self.assertIn("server QNU", prompt.call_args_list[0].args[0])
            self.assertIn("9router", prompt.call_args_list[1].args[0])
        for value in secrets.values():
            self.assertNotIn(value, output.getvalue())
            for file in self.directory.iterdir():
                if file.name == ".env":
                    continue
                self.assertNotIn(value, file.read_text())
        return read(self.directory / "checkpoint.json"), sent, choice

    def test_dotenv_bootstraps_both_keys_via_modelops_without_key_prompts(self):
        state, sent, _ = self.run_two_providers(
            limits={"context_window_tokens": 65536, "max_output_tokens": 4096},
            answers=["1"],
            from_env=True,
        )
        self.assertEqual(sent, ["conn_qnu", "conn_router"])
        self.assertEqual(state["chatSelection"], "qnu")

    def test_dotenv_keys_are_literal_and_missing_keys_fall_back(self):
        (self.directory / ".env").write_text(
            'UNRELATED=synthetic-other-secret\nE2E_QNU_API_KEY="literal-${UNRELATED}-secret"\n',
            encoding="utf-8",
        )
        self.assertEqual(
            setup.key_from_env("providerSetup"), "literal-${UNRELATED}-secret"
        )
        self.assertEqual(setup.key_from_env("routerProviderSetup"), "")

    def test_dotenv_parse_errors_are_safe(self):
        (self.directory / ".env").write_text(
            "E2E_QNU_API_KEY='synthetic-broken-secret\n", encoding="utf-8"
        )
        with self.assertRaises(RuntimeError) as raised:
            setup.key_from_env("providerSetup")
        self.assertNotIn("synthetic-broken-secret", str(raised.exception))

    def test_dotenv_missing_file_returns_empty_without_prompt(self):
        self.assertEqual(setup.key_from_env("providerSetup"), "")

    def test_dotenv_rejects_duplicate_or_multiline_keys_without_echoing_values(self):
        for contents in (
            "E2E_QNU_API_KEY=synthetic-first-secret\nE2E_QNU_API_KEY=synthetic-second-secret\n",
            'E2E_QNU_API_KEY="synthetic-first-secret\\nsynthetic-second-secret"\n',
        ):
            with self.subTest(contents_type="invalid key"):
                (self.directory / ".env").write_text(contents, encoding="utf-8")
                with self.assertRaises(RuntimeError) as raised:
                    setup.key_from_env("providerSetup")
                self.assertNotIn("synthetic-first-secret", str(raised.exception))
                self.assertNotIn("synthetic-second-secret", str(raised.exception))

    def test_existing_modelops_key_never_reads_dotenv_or_rotates(self):
        self.key_added = True
        client = httpx.Client(
            base_url="http://127.0.0.1:1234/platform/v1alpha1/",
            transport=httpx.MockTransport(self.handler),
        )
        with patch.object(
            setup,
            "key_from_env",
            create=True,
            side_effect=AssertionError("must not read"),
        ):
            setup.prepare_connection(
                client,
                self.directory,
                {"runId": "e00000000000"},
                read(self.profile),
                "providerSetup",
                "server QNU",
                "qnu",
            )
        self.assertFalse(
            any(
                method == "POST" and suffix.endswith("/keys")
                for method, suffix in self.calls
            )
        )

    def test_two_hidden_keys_and_selected_router_use_distinct_modelops_connections(
        self,
    ):
        state, sent, choice = self.run_two_providers(
            limits={"context_window_tokens": 65536, "max_output_tokens": 4096},
            answers=["2"],
        )
        self.assertEqual(sent, ["conn_qnu", "conn_router"])
        self.assertEqual(state["providerSetup"]["keyId"], "key_conn_qnu")
        self.assertEqual(state["routerProviderSetup"]["keyId"], "key_conn_router")
        self.assertEqual(state["chatSelection"], "router")
        self.assertEqual(choice.call_count, 1)

    def test_undeclared_router_capacity_uses_only_operator_values(self):
        state, sent, choice = self.run_two_providers(
            limits={}, answers=["2", "65536", "4096"]
        )
        self.assertEqual(state["chatSelection"], "router")
        self.assertEqual(
            sent[-1],
            {
                "token_limits": {
                    "context_window_tokens": 65536,
                    "max_output_tokens": 4096,
                }
            },
        )
        self.assertEqual(choice.call_count, 3)

    def test_qnu_selection_does_not_require_or_invent_router_capacity(self):
        state, sent, choice = self.run_two_providers(limits={}, answers=["1"])
        self.assertEqual(state["chatSelection"], "qnu")
        self.assertEqual(sent, ["conn_qnu", "conn_router"])
        self.assertEqual(choice.call_count, 1)

    def test_unverified_capacity_cannot_be_bypassed_by_empty_input(self):
        with self.assertRaisesRegex(RuntimeError, "giới hạn token thực tế"):
            self.run_two_providers(limits={}, answers=["2", ""])

    def test_invalid_choice_is_not_saved_as_a_default(self):
        with self.assertRaisesRegex(RuntimeError, "Chọn 1 hoặc 2"):
            self.run_two_providers(limits={}, answers=["3"])
        self.assertNotIn("chatSelection", read(self.directory / "checkpoint.json"))

    def test_router_discovery_error_distinguishes_contract_failure_from_missing_model(
        self,
    ):
        state = {"routerProviderSetup": {"connectionId": "conn_router", "keyId": "key"}}
        profile = {"models": {"chat": "ollama/gpt-oss:120b"}}
        with (
            patch.object(
                setup,
                "request",
                return_value={
                    "ok": False,
                    "code": "provider_catalog_too_large",
                    "http_status": 200,
                    "detail": self.secret,
                },
            ) as request,
            self.assertRaisesRegex(
                RuntimeError, "provider_catalog_too_large, HTTP 200"
            ) as error,
        ):
            setup.prepare_router_capacity(None, state, profile)
        request.assert_called_once()
        self.assertNotIn(self.secret, str(error.exception))
        with (
            patch.object(
                setup, "request", return_value={"ok": True, "models": ["other"]}
            ),
            self.assertRaisesRegex(RuntimeError, "kết nối thành công"),
        ):
            setup.prepare_router_capacity(None, state, profile)

    def test_router_discovery_error_does_not_echo_arbitrary_diagnostic_values(self):
        with (
            patch.object(
                setup,
                "request",
                return_value={
                    "ok": False,
                    "code": self.secret,
                    "http_status": self.secret,
                },
            ),
            self.assertRaisesRegex(RuntimeError, "diagnostic_failed") as error,
        ):
            setup.prepare_router_capacity(
                None,
                {
                    "routerProviderSetup": {
                        "connectionId": "conn_router",
                        "keyId": "key",
                    }
                },
                {"models": {"chat": "ollama/gpt-oss:120b"}},
            )
        self.assertNotIn(self.secret, str(error.exception))


if __name__ == "__main__":
    unittest.main()
