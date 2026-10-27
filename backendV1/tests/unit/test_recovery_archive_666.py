"""Recovery authenticates all data and never interprets archive contents as SQL/code."""

import subprocess
import sys

import pytest

from qnu.domains.operations.recovery import archive
from qnu.platform.errors import Conflict


def test_recovery_cli_registers_every_owned_table_in_a_fresh_process():
    program = "import runpy; runpy.run_path('scripts/recovery_bundle.py', run_name='schema_probe'); from qnu.platform.ownership import V1_TABLES; from qnu.platform.database import Base; assert not V1_TABLES-set(Base.metadata.tables), sorted(V1_TABLES-set(Base.metadata.tables))"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", program], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_bundle_is_encrypted_authenticated_and_preserves_exact_bytes():
    key = "test-recovery-key-" + "a" * 32
    payload = archive.pack(
        {"tables": {"provider_keys": [{"secret_encrypted": "enc:v1:ciphertext"}]}},
        {"v1/source.pdf": b"original\x00bytes"},
        key,
    )
    assert b"ciphertext" not in payload and b"original" not in payload
    snapshot, objects = archive.unpack(payload, key)
    assert snapshot["tables"]["provider_keys"][0]["secret_encrypted"] == "enc:v1:ciphertext"
    assert objects == {"v1/source.pdf": b"original\x00bytes"}
    with pytest.raises(Conflict, match="Recovery bundle"):
        archive.unpack(payload, "wrong-key-" + "b" * 32)
    with pytest.raises(Conflict):
        archive.unpack(payload[:-5] + b"wrong", key)


def test_bundle_refuses_weak_key_and_oversized_objects(monkeypatch):
    with pytest.raises(Conflict):
        archive.pack({}, {}, "short")
    monkeypatch.setattr(archive, "MAX_BYTES", 10)
    with pytest.raises(Exception, match="vượt giới hạn"):
        archive.pack({}, {"a": b"01234567890"}, "test-key-" + "z" * 32)
