"""Secure, interactive key bootstrap for the isolated provider E2E stage."""

from __future__ import annotations

import getpass
import json
import sys
import warnings

import httpx
from v1_e2e_session import read, save


def request(client, method, suffix, body=None):
    response = client.request(method, suffix, json=body)
    if not response.is_success:
        # Do not include request body or server error text in exceptions.
        raise RuntimeError(
            f"Provider setup: {method} {suffix}, HTTP {response.status_code}."
        )
    return response.json() if response.status_code != 204 else None


def prepare_provider(directory, env, profile_file):
    manifest, state, profile = map(
        read, (directory / "manifest.json", directory / "checkpoint.json", profile_file)
    )
    if manifest["mode"] != "live" or manifest["cleaned"]:
        raise RuntimeError("Provider setup cần phiên E2E live đang hoạt động.")
    if state.get("sources"):
        raise RuntimeError(
            "Phiên đã upload tài liệu; tạo phiên mới để test bật/tắt nhà cung cấp an toàn."
        )
    endpoint = profile["base_url"].rstrip("/")
    api = f"http://127.0.0.1:{manifest['ports']['api']}/platform/v1alpha1/"
    try:
        with httpx.Client(
            base_url=api, timeout=30, trust_env=False, follow_redirects=False
        ) as client:
            token = request(
                client, "POST", "auth/login", {"access_key": env["DEV_ACCESS_PASSWORD"]}
            )["access_token"]
            client.headers["Authorization"] = "Bearer " + token
            connections = request(client, "GET", "modelops/connections")
            matches = [
                row for row in connections if row["base_url"].rstrip("/") == endpoint
            ]
            if len(matches) > 1:
                raise RuntimeError(
                    "Có nhiều nhà cung cấp cùng endpoint trong phiên thử; xử lý cấu hình trùng trước."
                )
            created = not matches
            connection = (
                matches[0]
                if matches
                else request(
                    client,
                    "POST",
                    "modelops/connections",
                    {
                        "name": f"QNU AI Server E2E {manifest['run_id']}",
                        "family": "qnu",
                        "base_url": endpoint,
                        "timeout_seconds": 60,
                    },
                )
            )
            if not connection["is_active"]:
                raise RuntimeError(
                    "Nhà cung cấp hiện đang tắt; bật lại trước khi test."
                )
            setup = state.setdefault("providerSetup", {})
            setup.update(
                {
                    "connectionId": connection["id"],
                    "createdConnection": created
                    or setup.get("createdConnection", False),
                }
            )
            save(directory / "checkpoint.json", state)
            keys_path = f"modelops/providers/{connection['id']}/keys"
            keys = request(client, "GET", keys_path)
            active = [key for key in keys if key["status"] == "active"]
            if not active:
                if not sys.stdin.isatty():
                    raise RuntimeError(
                        "Chạy provider-setup trong PowerShell tương tác để nhập khóa ẩn; không truyền key qua lệnh hoặc .env."
                    )
                with warnings.catch_warnings():
                    warnings.simplefilter("error", getpass.GetPassWarning)
                    secret = getpass.getpass(
                        "API key server QNU (nhập ẩn, chỉ lưu qua ModelOps): "
                    ).strip()
                if len(secret) < 8:
                    raise RuntimeError("Khóa trống/quá ngắn; chưa thêm vào ModelOps.")
                try:
                    key = request(
                        client,
                        "POST",
                        keys_path,
                        {"name": "QNU E2E upstream", "secret": secret},
                    )
                    metadata = request(client, "GET", keys_path)
                    if secret in json.dumps(key) or secret in json.dumps(metadata):
                        raise RuntimeError("API metadata phản chiếu secret; dừng test.")
                    setup["keyId"] = key["id"]
                    setup["createdKey"] = True
                finally:
                    secret = ""
            else:
                setup["keyId"] = active[0]["id"]
            save(directory / "checkpoint.json", state)
    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        getpass.GetPassWarning,
        EOFError,
    ) as exc:
        raise RuntimeError(
            "Không chuẩn bị được provider/key; kiểm tra phiên local hoặc nhập key qua terminal tương tác."
        ) from exc
