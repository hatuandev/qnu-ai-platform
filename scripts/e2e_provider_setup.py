"""Bootstrap isolated E2E credentials into ModelOps from local .env or hidden input."""

from __future__ import annotations

import getpass
import json
import re
import sys
import warnings

import httpx
from dotenv.parser import parse_stream
from v1_e2e_session import ROOT, read, save

KEY_ENV_FILE = ROOT / ".env"
KEY_ENV_NAMES = {
    "providerSetup": "E2E_QNU_API_KEY",
    "routerProviderSetup": "E2E_9ROUTER_API_KEY",
    "ocrProviderSetup": "E2E_QNU_API_KEY",
}


def key_from_env(field):
    """Operator-authorized E2E bootstrap only; never export keys to child environments."""
    name = KEY_ENV_NAMES[field]
    try:
        with KEY_ENV_FILE.open(encoding="utf-8-sig") as source:
            secret = ""
            found = False
            for binding in parse_stream(source):
                if binding.error:
                    raise RuntimeError(
                        "Không đọc được .env E2E; kiểm tra cú pháp, không gửi nội dung khóa."
                    )
                if binding.key == name:
                    if found:
                        raise RuntimeError(
                            f".env có biến {name} trùng; giữ một khai báo."
                        )
                    found = True
                    secret = (binding.value or "").strip()
            if secret and (len(secret) < 8 or any(ord(c) < 32 for c in secret)):
                raise RuntimeError(
                    f"Biến {name} không hợp lệ; cần khóa một dòng ít nhất 8 ký tự."
                )
            return secret
    except FileNotFoundError:
        return ""
    except (OSError, UnicodeError):
        raise RuntimeError(
            "Không đọc được .env E2E; kiểm tra quyền truy cập và UTF-8."
        ) from None


def request(client, method, suffix, body=None):
    response = client.request(method, suffix, json=body)
    if not response.is_success:
        # Never include a request body or server error text in exceptions.
        raise RuntimeError(
            f"Provider setup: {method} {suffix}, HTTP {response.status_code}."
        )
    return response.json() if response.status_code != 204 else None


def require_terminal():
    if not sys.stdin.isatty():
        raise RuntimeError(
            "Chạy provider-setup trong PowerShell tương tác để nhập khóa ẩn/chọn model; "
            "hoặc điền E2E_QNU_API_KEY/E2E_9ROUTER_API_KEY trong .env ở root để nạp khóa."
        )


def prepare_connection(client, directory, state, profile, field, label, family):
    endpoint = profile["base_url"].rstrip("/")
    connections = request(client, "GET", "modelops/connections")
    matches = [row for row in connections if row["base_url"].rstrip("/") == endpoint]
    if len(matches) > 1:
        raise RuntimeError(
            "Có nhiều nhà cung cấp cùng endpoint; xử lý cấu hình trùng trước."
        )
    connection = (
        matches[0]
        if matches
        else request(
            client,
            "POST",
            "modelops/connections",
            {
                "name": f"{label} E2E {state['runId']}",
                "family": family,
                "base_url": endpoint,
                "timeout_seconds": profile.get("timeout_seconds", 60),
                **({"api_type": profile["api_type"]} if profile.get("api_type") else {}),
            },
        )
    )
    if not connection["is_active"]:
        raise RuntimeError(
            f"Nhà cung cấp {label} hiện đang tắt; bật lại trước khi test."
        )
    if profile.get("api_type") and connection.get("api_type") != profile["api_type"]:
        raise RuntimeError(f"Giao thức {label} không khớp profile; sửa trong ModelOps trước.")
    setup = state.setdefault(field, {})
    setup.update(
        connectionId=connection["id"],
        createdConnection=not matches or setup.get("createdConnection", False),
    )
    save(directory / "checkpoint.json", state)
    keys_path = f"modelops/providers/{connection['id']}/keys"
    active = [
        key for key in request(client, "GET", keys_path) if key["status"] == "active"
    ]
    if active:
        setup["keyId"] = active[0]["id"]
    else:
        secret = key_from_env(field)
        if not secret:
            require_terminal()
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                secret = getpass.getpass(
                    f"API key {label} (nhập ẩn, chỉ lưu qua ModelOps): "
                ).strip()
        if len(secret) < 8:
            raise RuntimeError("Khóa trống/quá ngắn; chưa thêm vào ModelOps.")
        try:
            key = request(
                client,
                "POST",
                keys_path,
                {"name": f"{label} E2E upstream", "secret": secret},
            )
            metadata = request(client, "GET", keys_path)
            if secret in json.dumps(key) or secret in json.dumps(metadata):
                raise RuntimeError("API metadata phản chiếu secret; dừng test.")
            setup.update(keyId=key["id"], createdKey=True)
        finally:
            secret = ""
    save(directory / "checkpoint.json", state)


def choose_chat(directory, state, profile):
    previous = state.get("chatSelection")
    if not sys.stdin.isatty() and previous in {"qnu", "router"}:
        return previous
    require_terminal()
    default = "2" if previous == "router" else "1"
    print(f"1. Server QNU — {profile['models']['chat']}")
    print(f"2. 9router — {profile['additional_chat_provider']['models']['chat']}")
    choice = input(f"Model chat/biên soạn mặc định [{default}]: ").strip() or default
    if choice not in {"1", "2"}:
        raise RuntimeError("Chọn 1 hoặc 2; chưa thay model mặc định.")
    state["chatSelection"] = "qnu" if choice == "1" else "router"
    save(directory / "checkpoint.json", state)
    return state["chatSelection"]


def prepare_router_capacity(client, state, profile):
    """Only the selected chat model needs capacity before diagnostics/pipeline."""
    setup = state["routerProviderSetup"]
    base = f"modelops/connections/{setup['connectionId']}"
    checked = request(client, "POST", base + "/test", {"key_id": setup["keyId"]})
    name = profile["models"]["chat"]
    if not checked.get("ok"):
        code = checked.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[a-z_]{1,64}", code):
            code = "diagnostic_failed"
        status = checked.get("http_status")
        http = (
            f", HTTP {status}" if type(status) is int and 100 <= status <= 599 else ""
        )
        raise RuntimeError(
            f"9router: kiểm tra danh sách model thất bại ({code}{http}). "
            "Xem chẩn đoán nhà cung cấp trong ModelOps; giữ phiên và key đã lưu."
        )
    if name not in checked.get("models", []):
        raise RuntimeError(
            "9router kết nối thành công nhưng chưa liệt kê model đã chọn; "
            "đối chiếu tên model trong profile với danh sách ModelOps."
        )
    models = request(client, "GET", base + "/models")
    selected = [model for model in models if model["model_name"] == name]
    if len(selected) > 1:
        raise RuntimeError("Model 9router bị trùng; kiểm tra trong ModelOps.")
    if not selected:
        request(
            client,
            "POST",
            base + "/models",
            {
                "model_name": name,
                "capabilities": ["chat"],
                "discovery_check_id": checked["check_id"],
            },
        )
    rows = request(
        client,
        "POST",
        base + "/sync-capacity",
        {
            "check_id": checked["check_id"],
            "model_names": [name],
        },
    )
    model = next(row for row in rows if row["model_name"] == name)
    limits = model.get("token_limits") or {}
    patch = {}
    for field, label in (
        ("context_window_tokens", "context"),
        ("max_output_tokens", "output tối đa"),
    ):
        if limits.get(field) is not None:
            continue
        require_terminal()
        value = input(
            f"9router không công bố {label}; nhập số token Ollama thực tế (trống để dừng): "
        ).strip()
        if not value.isascii() or not value.isdecimal() or int(value) <= 0:
            raise RuntimeError(
                "Cần giới hạn token thực tế; có thể cấu hình trong ModelOps rồi chạy lại."
            )
        patch[field] = int(value)
    if patch:
        limits = {**limits, **patch}
        if limits["max_output_tokens"] >= limits["context_window_tokens"]:
            raise RuntimeError("Output phải nhỏ hơn context để còn chỗ cho input.")
        request(
            client,
            "PATCH",
            f"modelops/providers/{model['id']}",
            {"token_limits": limits},
        )


def prepare_provider(directory, env, profile_file):
    manifest, state, profile = map(
        read,
        (
            directory / "manifest.json",
            directory / "checkpoint.json",
            profile_file,
        ),
    )
    if manifest["mode"] != "live" or manifest["cleaned"]:
        raise RuntimeError("Provider setup cần phiên E2E live đang hoạt động.")
    if state.get("sources") or state.get("admissions", {}).get("source"):
        raise RuntimeError(
            "Phiên đã upload tài liệu; tạo phiên mới để test bật/tắt nhà cung cấp an toàn."
        )
    state.setdefault("runId", manifest["run_id"])
    api = f"http://127.0.0.1:{manifest['ports']['api']}/platform/v1alpha1/"
    try:
        with httpx.Client(
            base_url=api, timeout=90, trust_env=False, follow_redirects=False
        ) as client:
            token = request(
                client, "POST", "auth/login", {"access_key": env["DEV_ACCESS_PASSWORD"]}
            )["access_token"]
            client.headers["Authorization"] = "Bearer " + token
            prepare_connection(
                client, directory, state, profile, "providerSetup", "server QNU", "qnu"
            )
            ocr = profile.get("additional_ocr_provider")
            if ocr:
                prepare_connection(
                    client, directory, state, ocr, "ocrProviderSetup", "MinerU OCR", "qnu"
                )
            router = profile.get("additional_chat_provider")
            if router:
                prepare_connection(
                    client,
                    directory,
                    state,
                    router,
                    "routerProviderSetup",
                    "9router",
                    "custom",
                )
                if choose_chat(directory, state, profile) == "router":
                    prepare_router_capacity(client, state, router)
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
