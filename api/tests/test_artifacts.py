import json
import types
from io import BytesIO

import pytest
from app import models
from app import storage as storage_mod
from app.db import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.objects[(Bucket, Key)] = {
            "Body": Body if isinstance(Body, (bytes, bytearray)) else Body.read(),
            "ContentType": ContentType,
        }

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f"https://example.com/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    # DB override
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    import app.db as app_db

    app_db.SessionLocal = lambda: db_session

    # Storage overrides
    fake = FakeS3()
    monkeypatch.setattr(storage_mod, "get_s3_client", lambda: fake)
    monkeypatch.setattr(
        storage_mod, "ensure_bucket_exists", lambda client=None, bucket=None: None
    )
    # Settings
    from app.config import settings

    settings.s3_bucket = "test-bucket"

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client, db_session):
    from app import models

    org = models.Org(name="orgX")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    # Register user
    email = "u@example.com"
    password = "secret123"
    r = client.post(
        "/auth/register",
        json={"email": email, "password": password, "org_id": org["id"]},
    )
    assert r.status_code == 201
    # Login
    r = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, org


def test_upload_artifact_flow(client, db_session):
    headers, org = auth_headers(client, db_session)

    # Create project
    r = client.post("/api/v1/projects", json={"name": "projA"}, headers=headers)
    assert r.status_code == 201
    project = r.json()

    # Upload artifact (multipart)
    files = {
        "file": ("model.glb", b"abcdefg", "model/gltf-binary"),
        "params": (
            "params.json",
            json.dumps({"a": 1}).encode("utf-8"),
            "application/json",
        ),
    }
    data = {"name": "My Model", "type": "gltf"}
    r = client.post(
        f"/api/v1/projects/{project['id']}/artifacts",
        files=files,
        data=data,
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] > 0
    assert body["object_key"]
    assert body["presigned_url"].startswith("https://example.com/")
