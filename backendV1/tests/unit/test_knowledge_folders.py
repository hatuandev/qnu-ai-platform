"""Unit tests for knowledge folders domain (validation, cycle prevention, schemas)."""

import pytest

from qnu.domains.knowledge.folders.schemas import (
    FolderCreateRequest,
    FolderImpactResponse,
    FolderMoveRequest,
    FolderUpdateRequest,
)
from qnu.domains.knowledge.folders.service import _validate_folder_name
from qnu.platform.errors import AppException


def test_validate_folder_name_valid():
    assert _validate_folder_name("Quy chế đào tạo") == "Quy chế đào tạo"
    assert _validate_folder_name("  Tài liệu 2026  ") == "Tài liệu 2026"
    assert _validate_folder_name("Học bổng - Học phí (kỳ 1)") == "Học bổng - Học phí (kỳ 1)"


def test_validate_folder_name_empty():
    with pytest.raises(AppException) as exc_info:
        _validate_folder_name("   ")
    assert exc_info.value.code == "invalid_folder_name"
    assert exc_info.value.status_code == 422


def test_validate_folder_name_too_long():
    with pytest.raises(AppException) as exc_info:
        _validate_folder_name("a" * 256)
    assert exc_info.value.code == "folder_name_too_long"
    assert exc_info.value.status_code == 422


def test_validate_folder_name_path_traversal():
    for name in [".", "..", "folder/subfolder", "folder\\subfolder", "name*wild", "quote\"name"]:
        with pytest.raises(AppException):
            _validate_folder_name(name)


def test_folder_schemas_roundtrip():
    create_req = FolderCreateRequest(name="Khoa CNTT", parent_id="fld_root")
    assert create_req.name == "Khoa CNTT"
    assert create_req.parent_id == "fld_root"

    update_req = FolderUpdateRequest(name="Khoa Công nghệ thông tin")
    assert update_req.name == "Khoa Công nghệ thông tin"

    move_req = FolderMoveRequest(target_parent_id=None)
    assert move_req.target_parent_id is None

    impact = FolderImpactResponse(
        folder_id="fld_1",
        folder_name="Học vụ",
        subfolder_count=3,
        source_count=12,
        descendant_folder_ids=["fld_2", "fld_3", "fld_4"],
    )
    assert impact.subfolder_count == 3
    assert impact.source_count == 12
