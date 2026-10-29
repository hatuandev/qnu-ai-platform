"""Storage setup boundary tests; no live endpoint or existing object is touched."""

import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError, EndpointConnectionError

sys.path.insert(0, str(Path(__file__).parents[1]))
SPEC = importlib.util.spec_from_file_location(
    "v1_storage", Path(__file__).parents[1] / "v1_storage.py"
)
storage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(storage)


def settings(**overrides):
    return SimpleNamespace(
        **{
            "STORAGE_DRIVER": "s3",
            "S3_ENDPOINT": "http://127.0.0.1:9000",
            "S3_ACCESS_KEY": "test-access",
            "S3_SECRET_KEY": "test-secret",
            "S3_BUCKET": "test-bucket",
            "S3_SECURE": False,
            **overrides,
        }
    )


def client_error(code):
    return ClientError(
        {"Error": {"Code": code, "Message": "private-secret"}}, "HeadBucket"
    )


class StorageTests(unittest.TestCase):
    def test_invalid_endpoint_fails_without_constructing_client(self):
        for endpoint in (
            "http://[broken",
            "http://localhost:invalid",
            "http://user:secret@host",
        ):
            with patch.object(storage, "s3_client") as client:
                ok, detail = storage.check_storage_sync(settings(S3_ENDPOINT=endpoint))
            self.assertFalse(ok)
            self.assertNotIn("secret", detail)
            client.assert_not_called()

    def test_readiness_is_read_only_and_closes_client(self):
        client = Mock()
        with patch.object(storage, "s3_client", return_value=client):
            self.assertTrue(storage.check_storage_sync(settings())[0])
        client.head_bucket.assert_called_once_with(Bucket="test-bucket")
        for name in ("create_bucket", "put_object", "delete_object"):
            getattr(client, name).assert_not_called()
        client.close.assert_called_once()

    def test_missing_bucket_and_auth_error_are_distinct_and_do_not_write(self):
        for code, message in (
            ("404", "bucket missing"),
            ("403", "authentication/permission"),
        ):
            client = Mock(head_bucket=Mock(side_effect=client_error(code)))
            with patch.object(storage, "s3_client", return_value=client):
                ok, detail = storage.check_storage_sync(settings())
            self.assertFalse(ok)
            self.assertIn(message, detail)
            self.assertNotIn("private-secret", detail)
            client.create_bucket.assert_not_called()

    def test_unreachable_service_is_sanitized(self):
        client = Mock(
            head_bucket=Mock(
                side_effect=EndpointConnectionError(endpoint_url="private")
            )
        )
        with patch.object(storage, "s3_client", return_value=client):
            ok, detail = storage.check_storage_sync(settings())
        self.assertFalse(ok)
        self.assertNotIn("private", detail)
        client.close.assert_called_once()

    def test_create_missing_local_bucket_and_roundtrip_cleanup(self):
        body = io.BytesIO(b"qnu-v1-storage-check")
        client = Mock(
            head_bucket=Mock(side_effect=client_error("404")),
            put_object=Mock(return_value={}),
            get_object=Mock(return_value={"Body": body}),
        )
        with patch.object(storage, "s3_client", return_value=client):
            self.assertTrue(storage.prepare_local_storage(settings())[0])
        client.create_bucket.assert_called_once_with(Bucket="test-bucket")
        key = client.put_object.call_args.kwargs["Key"]
        self.assertTrue(key.startswith(".qnu/v1-infra-check/"))
        client.delete_object.assert_called_once_with(Bucket="test-bucket", Key=key)
        self.assertTrue(body.closed)
        client.close.assert_called_once()

    def test_existing_bucket_is_not_recreated_and_versioned_probe_is_removed(self):
        client = Mock(
            put_object=Mock(return_value={"VersionId": "probe-version"}),
            get_object=Mock(return_value={"Body": io.BytesIO(b"qnu-v1-storage-check")}),
        )
        with patch.object(storage, "s3_client", return_value=client):
            self.assertTrue(storage.prepare_local_storage(settings())[0])
        client.create_bucket.assert_not_called()
        self.assertEqual(
            client.delete_object.call_args.kwargs["VersionId"], "probe-version"
        )

    def test_read_failure_still_cleans_probe_and_reports_failure(self):
        client = Mock(
            put_object=Mock(return_value={}),
            get_object=Mock(side_effect=client_error("403")),
        )
        with patch.object(storage, "s3_client", return_value=client):
            self.assertFalse(storage.prepare_local_storage(settings())[0])
        client.delete_object.assert_called_once()
        client.close.assert_called_once()

    def test_delete_failure_is_not_reported_as_success(self):
        client = Mock(
            put_object=Mock(return_value={}),
            get_object=Mock(return_value={"Body": io.BytesIO(b"qnu-v1-storage-check")}),
            delete_object=Mock(side_effect=client_error("403")),
        )
        with patch.object(storage, "s3_client", return_value=client):
            self.assertFalse(storage.prepare_local_storage(settings())[0])

    def test_denied_bucket_is_never_created_or_written(self):
        client = Mock(head_bucket=Mock(side_effect=client_error("403")))
        with patch.object(storage, "s3_client", return_value=client):
            self.assertFalse(storage.prepare_local_storage(settings())[0])
        client.create_bucket.assert_not_called()
        client.put_object.assert_not_called()

    def test_remote_or_custom_local_endpoint_is_never_mutated(self):
        for endpoint in ("https://storage.example.test", "http://127.0.0.1:9900"):
            client = Mock()
            with patch.object(storage, "s3_client", return_value=client):
                ok, detail = storage.prepare_local_storage(
                    settings(S3_ENDPOINT=endpoint)
                )
            self.assertTrue(ok)
            self.assertIn("unchanged", detail)
            client.create_bucket.assert_not_called()
            client.put_object.assert_not_called()
            client.delete_object.assert_not_called()

    def test_missing_credentials_fail_before_network(self):
        with patch.object(storage, "s3_client") as client:
            self.assertFalse(
                storage.prepare_local_storage(settings(S3_SECRET_KEY=""))[0]
            )
        client.assert_not_called()

    def test_local_setup_preserves_files_and_check_creates_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "blobs"
            config = settings(STORAGE_DRIVER="local", LOCAL_STORAGE_PATH=str(root))
            self.assertTrue(storage.check_storage_sync(config)[0])
            self.assertFalse(root.exists())
            self.assertTrue(storage.prepare_local_storage(config)[0])
            original = root / "original.txt"
            original.write_bytes(b"keep")
            self.assertTrue(storage.prepare_local_storage(config)[0])
            self.assertEqual(list(root.iterdir()), [original])
            self.assertEqual(original.read_bytes(), b"keep")

    def test_local_file_instead_of_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "file"
            path.touch()
            self.assertFalse(
                storage.check_storage_sync(
                    settings(
                        STORAGE_DRIVER="local",
                        LOCAL_STORAGE_PATH=str(path),
                    )
                )[0]
            )

    def test_minio_image_is_pinned_to_requested_release(self):
        compose = (Path(__file__).parents[2] / "docker-compose.infra.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("image: pgsty/minio:RELEASE.2026-06-18T00-00-00Z", compose)


if __name__ == "__main__":
    unittest.main()
