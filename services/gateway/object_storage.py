"""#118 (OPS-05): shared S3/MinIO client construction.

One small module so the export writer, and any future lifecycle/backfill
work (OPS-07/OPS-14), reuse the same client/bucket config instead of each
constructing their own. Reads endpoint/credentials from env, matching the
compose MinIO vars (`infra/compose/docker-compose.yml`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config as BotoConfig

type S3Client = Any

DEFAULT_EXPORTS_BUCKET = "omc-exports"


@dataclass(frozen=True, slots=True)
class ObjectStorageConfig:
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket: str
    region: str = "auto"


def object_storage_config_from_env() -> ObjectStorageConfig:
    return ObjectStorageConfig(
        endpoint_url=os.getenv("OMC_S3_ENDPOINT_URL", "http://localhost:9090"),
        access_key=os.getenv("OMC_S3_ACCESS_KEY", os.getenv("MINIO_ROOT_USER", "minio")),
        secret_key=os.getenv("OMC_S3_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD", "minio_secret")),
        bucket=os.getenv("OMC_S3_EXPORTS_BUCKET", DEFAULT_EXPORTS_BUCKET),
    )


def build_s3_client(config: ObjectStorageConfig) -> S3Client:
    return boto3.client(
        "s3",
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
        region_name=config.region,
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket_exists(client: S3Client, bucket: str) -> None:
    """Idempotent bucket creation -- safe to call on every startup."""
    from botocore.exceptions import ClientError

    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)


def presigned_export_url(
    client: S3Client,
    *,
    bucket: str,
    key: str,
    expires_in_seconds: int = 300,
) -> str:
    """Time-bounded signed URL for one object -- never proxy export bytes
    through the API. Short default TTL, tunable per call."""
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in_seconds,
    )


# #120 (OPS-07): expire `exports/<run_id>/...` objects on the same clock as
# the DB `artifacts`/`snapshots` retention (180d default -- RetentionConfig
# in `retention.py`) so a signed URL never resolves to an object that
# outlived its DB key, or vice versa.
#
# S3/MinIO lifecycle expiration is a blind object-age TTL -- it cannot see a
# run's ADR-026 revision-window/pending/escalated state the way
# `prune_policy.is_prunable` can for DB rows. This is a deliberate,
# documented approximation, not a full join of "is this object's run
# provably prunable": at 180 days of age, no run is plausibly still inside
# its (900-second) fast-lane revert window, so a conservative age-only TTL
# is safe in practice, but it is not a deterministic per-object safety proof
# the way the DB-side predicate is. If exports ever need that same
# provable guarantee, expiry needs to become app-driven (delete-on-prune)
# rather than a bucket-level lifecycle rule.
EXPORTS_LIFECYCLE_RULE_ID = "omc-exports-retention"


def export_lifecycle_configuration(*, expiration_days: int) -> dict[str, list[dict[str, object]]]:
    """The lifecycle rule body applied to the exports bucket -- a pure
    builder so it's trivially unit-testable without a live S3/MinIO."""
    return {
        "Rules": [
            {
                "ID": EXPORTS_LIFECYCLE_RULE_ID,
                "Status": "Enabled",
                "Filter": {"Prefix": "exports/"},
                "Expiration": {"Days": expiration_days},
            },
        ],
    }


def apply_export_lifecycle_rules(client: S3Client, bucket: str, *, expiration_days: int) -> None:
    """Idempotent -- safe to call on every startup, like `ensure_bucket_exists`."""
    client.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration=export_lifecycle_configuration(expiration_days=expiration_days),
    )
