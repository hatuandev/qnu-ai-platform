"""Tampered archives must fail even if their outer checksum has been recomputed."""

import io
import json
import zipfile

import pytest

from qnu.domains.operations.backups.archive import pack, verify
from qnu.platform.errors import Conflict


@pytest.mark.parametrize(
    "change", ["object", "source_hash", "tables", "extra_entry", "credentials"]
)
def test_archive_rejects_inconsistent_contents(change):
    data, _ = pack(
        {"workspace_id": "ws", "tables": {"items": [{"id": 1}]}}, [("source", b"original", None)]
    )
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    manifest = json.loads(files["manifest.json"])
    if change == "object":
        files[manifest["objects"][0]["entry"]] = b"changed"
    elif change == "source_hash":
        manifest["objects"][0]["expected_sha256"] = "0" * 64
    elif change == "tables":
        manifest["snapshot_tables"]["items"] = 20
    elif change == "credentials":
        manifest["credentials_included"] = True
    else:
        files["../unexpected"] = b"extra"
    files["manifest.json"] = json.dumps(manifest).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for key, payload in files.items():
            archive.writestr(key, payload)
    with pytest.raises(Conflict, match="hỏng|an toàn"):
        verify(stream.getvalue())


def test_archive_source_hash_mismatch_fails_before_publish():
    with pytest.raises(Conflict) as error:
        pack({"workspace_id": "ws", "tables": {}}, [("source", b"original", "0" * 64)])
    assert error.value.code == "backup_source_integrity_failed"
