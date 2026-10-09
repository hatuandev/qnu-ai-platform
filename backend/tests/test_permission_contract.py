"""Automated contract test verifying backend permissions match qnu-ai-permissions.json."""

from __future__ import annotations

import ast
import json
from pathlib import Path


def _find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for _ in range(5):
        if (current / "qnu-ai-permissions.json").exists():
            return current
        current = current.parent
    raise FileNotFoundError("Could not find qnu-ai-permissions.json in repository hierarchy.")


def _collect_backend_required_permissions() -> set[str]:
    """Inspect all backend Python files using AST to extract string literals passed to require_permission(...)."""
    repo_root = _find_repo_root()
    modules_dir = repo_root / "backend" / "app" / "modules"
    required_permissions: set[str] = set()

    for py_file in modules_dir.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr

                if func_name == "require_permission" and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        required_permissions.add(arg.value)

    return required_permissions


def test_permission_contract_all_backend_permissions_exist_in_manifest():
    """Verify that every permission required in backend endpoints exists in the canonical manifest."""
    repo_root = _find_repo_root()
    manifest_path = repo_root / "qnu-ai-permissions.json"
    assert manifest_path.exists(), "qnu-ai-permissions.json must exist at repo root."

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    canonical_permissions = {p["name"] for p in manifest_data.get("permissions", [])}
    assert len(canonical_permissions) == 27, f"Manifest should contain exactly 27 permissions, found {len(canonical_permissions)}"

    backend_permissions = _collect_backend_required_permissions()
    assert len(backend_permissions) > 0, "Backend must have endpoints guarded by require_permission."

    # Must be a subset
    missing_in_catalog = backend_permissions - canonical_permissions
    assert not missing_in_catalog, (
        f"Backend routes require permissions that are NOT declared in canonical catalog: {missing_in_catalog}"
    )

    # Specific check: Ensure no legacy .edit permissions are required
    edit_permissions = {p for p in backend_permissions if p.endswith(".edit")}
    assert not edit_permissions, f"Found legacy .edit permissions in backend routes: {edit_permissions}"
