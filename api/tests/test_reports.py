import pytest
from app import models
from app import storage as storage_mod
from app.db import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType=None):
        self.objects[(Bucket, Key)] = (
            Body if isinstance(Body, (bytes, bytearray)) else Body.read()
        )

    def generate_presigned_url(self, op, Params, ExpiresIn):
        return f"https://example.com/{Params['Bucket']}/{Params['Key']}"


@pytest.fixture(scope="function")
def db_session():
    # Ensure models are imported so metadata is populated
    from app import models as _models  # noqa: F401

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    import app.db as app_db

    app_db.SessionLocal = lambda: db_session
    # Ensure audit middleware uses the same session
    import app.middleware as app_mw

    app_mw.SessionLocal = lambda: db_session

    fake = FakeS3()
    monkeypatch.setattr(storage_mod, "get_s3_client", lambda: fake)
    monkeypatch.setattr(
        storage_mod, "ensure_bucket_exists", lambda client=None, bucket=None: None
    )
    from app.config import settings

    settings.s3_bucket = "test-bkt"

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client, db_session):
    from app import models

    org = models.Org(name="orgR")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    org_id = org.id
    email = "r@example.com"
    pw = "secret123"
    client.post(
        "/auth/register", json={"email": email, "password": pw, "org_id": org_id}
    )
    # Elevate role to allow rulepack creation during test
    u = db_session.query(models.User).filter(models.User.email == email).first()
    u.roles = ["researcher", "designer"]
    db_session.add(u)
    db_session.commit()
    tok = client.post(
        "/auth/token",
        data={"username": email, "password": pw},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def ready_evaluation(client, db_session):
    headers = auth_headers(client, db_session)
    proj = client.post("/api/v1/projects", json={"name": "P"}, headers=headers).json()
    sc = models.SimulationScenario(project_id=proj["id"], name="S", config={})
    db_session.add(sc)
    db_session.commit()
    db_session.refresh(sc)
    art = models.DesignArtifact(project_id=proj["id"], name="A", type="gltf")
    db_session.add(art)
    db_session.commit()
    db_session.refresh(art)
    art_id = art.id
    # minimal rulepack
    rp = client.post(
        "/api/v1/rulepacks",
        json={"name": "RP", "version": "1.0.0", "rules": {"rules": []}},
        headers=headers,
    ).json()
    # enqueue and force eager
    from app.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    enq = client.post(
        "/api/v1/evaluations",
        json={"artifact_id": art_id, "scenario_id": sc.id, "rulepack_id": rp["id"]},
        headers=headers,
    )
    eid = enq.json()["id"]
    # Now run is done
    return headers, eid


def test_report_checksum_stable(client, db_session):
    headers, eid = ready_evaluation(client, db_session)
    r1 = client.post(f"/api/v1/evaluations/{eid}/report", headers=headers)
    assert r1.status_code == 200, r1.text
    rep1 = r1.json()
    r2 = client.post(f"/api/v1/evaluations/{eid}/report", headers=headers)
    rep2 = r2.json()
    assert rep1["checksum_sha256"] == rep2["checksum_sha256"]
    assert rep1["presigned_pdf_url"].startswith("https://example.com/")
    assert rep1["presigned_html_url"].startswith("https://example.com/")
