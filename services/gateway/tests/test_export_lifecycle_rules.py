"""OPS-07: object-storage lifecycle rules for the exports bucket, verified
against a real MinIO instance (no mocks) -- same reachability convention as
`object_storage.py`'s env defaults (`OMC_S3_ENDPOINT_URL`, default
``http://localhost:9090``).
"""

from __future__ import annotations

import contextlib

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from services.gateway.object_storage import (
    EXPORTS_LIFECYCLE_RULE_ID,
    apply_export_lifecycle_rules,
    build_s3_client,
    ensure_bucket_exists,
    export_lifecycle_configuration,
    object_storage_config_from_env,
)

_TEST_BUCKET = "omc-exports-test"


@pytest.fixture
def client():
    config = object_storage_config_from_env()
    client = build_s3_client(config)
    try:
        ensure_bucket_exists(client, _TEST_BUCKET)
    except (ClientError, EndpointConnectionError) as exc:
        pytest.skip(f"MinIO not available: {exc}")
    yield client
    with contextlib.suppress(ClientError):
        client.delete_bucket_lifecycle(Bucket=_TEST_BUCKET)


def test_export_lifecycle_configuration_targets_exports_prefix_only() -> None:
    """Pure builder -- no I/O -- so the rule shape is testable without MinIO."""
    config = export_lifecycle_configuration(expiration_days=180)
    rule = config["Rules"][0]
    assert rule["ID"] == EXPORTS_LIFECYCLE_RULE_ID
    assert rule["Status"] == "Enabled"
    assert rule["Filter"] == {"Prefix": "exports/"}
    assert rule["Expiration"] == {"Days": 180}


class TestAppliedAgainstRealMinIO:
    def test_apply_is_idempotent_and_readable_back(self, client) -> None:
        apply_export_lifecycle_rules(client, _TEST_BUCKET, expiration_days=180)
        # idempotent re-apply
        apply_export_lifecycle_rules(client, _TEST_BUCKET, expiration_days=180)

        response = client.get_bucket_lifecycle_configuration(Bucket=_TEST_BUCKET)
        rule_ids = {rule["ID"] for rule in response["Rules"]}
        assert EXPORTS_LIFECYCLE_RULE_ID in rule_ids

    def test_rule_expiration_matches_configured_days(self, client) -> None:
        apply_export_lifecycle_rules(client, _TEST_BUCKET, expiration_days=45)
        response = client.get_bucket_lifecycle_configuration(Bucket=_TEST_BUCKET)
        rule = next(r for r in response["Rules"] if r["ID"] == EXPORTS_LIFECYCLE_RULE_ID)
        assert rule["Expiration"]["Days"] == 45


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
