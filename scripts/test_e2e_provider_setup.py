"""Offline provider bootstrap regressions; no server, credential or browser required."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import e2e_provider_setup as setup
import httpx
from v1_e2e_session import read, save


class ProviderSetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
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


if __name__ == "__main__":
    unittest.main()
