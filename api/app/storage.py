from __future__ import annotations

import io
import uuid
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig

from .config import settings


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        use_ssl=settings.s3_use_ssl,
        config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket_exists(client=None, bucket: Optional[str] = None):
    client = client or get_s3_client()
    bucket = bucket or settings.s3_bucket
    try:
        client.head_bucket(Bucket=bucket)
    except Exception:
        # Create bucket (MinIO ignores LocationConstraint for us-east-1)
        params = {"Bucket": bucket}
        if settings.s3_region and settings.s3_region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": settings.s3_region}
        client.create_bucket(**params)


def upload_bytes(key: str, data: bytes, content_type: str | None = None, client=None, bucket: Optional[str] = None):
    client = client or get_s3_client()
    bucket = bucket or settings.s3_bucket
    ensure_bucket_exists(client, bucket)
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type or "application/octet-stream")


def presigned_get(key: str, expires: Optional[int] = None, client=None, bucket: Optional[str] = None) -> str:
    client = client or get_s3_client()
    bucket = bucket or settings.s3_bucket
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires or settings.download_url_expire_seconds,
    )


def presigned_put(key: str, content_type: str | None = None, expires: Optional[int] = None, client=None, bucket: Optional[str] = None) -> str:
    client = client or get_s3_client()
    bucket = bucket or settings.s3_bucket
    params = {"Bucket": bucket, "Key": key}
    if content_type:
        params["ContentType"] = content_type
    return client.generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=expires or settings.download_url_expire_seconds,
    )


def new_object_key(project_id: int, filename: str) -> str:
    ext = ""
    if "." in filename:
        ext = filename.rsplit(".", 1)[1].lower()
    return f"projects/{project_id}/artifacts/{uuid.uuid4().hex}{('.' + ext) if ext else ''}"

