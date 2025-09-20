import pytest
from app.celery_app import celery_app
from app.db import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    # Ensure models are imported to populate metadata
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

    # Celery eager
    celery_app.conf.task_always_eager = True

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def setup_entities(client):
    # Org
    from app import models

    org = models.Org(name="orgE")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    org_id = org.id
    # User
    email = "e@example.com"
    password = "secret123"
    client.post(
        "/auth/register", json={"email": email, "password": password, "org_id": org_id}
    )
    # Elevate role to allow rulepack creation
    user = db_session.query(models.User).filter(models.User.email == email).first()
    user.roles = ["researcher"]
    db_session.add(user)
    db_session.commit()
    tok = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    # Project
    proj = client.post(
        "/api/v1/projects", json={"name": "projE"}, headers=headers
    ).json()
    # Scenario
    # create via DB directly is simpler, but we don't have endpoint; use DB fixture indirectly not available here; hack: add through /alembic not present.
    # Instead, create artifact to associate; scenario creation missing endpoint: We'll simulate by inserting via direct model import using dependency override? Keep simple: create scenario via default in DB session through app.dependency_overrides in test, but we don't have access here.
    return headers, proj


def test_evaluation_happy_path(client, db_session):
    # Prepare entities: create org directly in DB
    from app import models

    org = models.Org(name="orgE")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    org_id = org.id
    email = "e@example.com"
    password = "secret123"
    client.post(
        "/auth/register", json={"email": email, "password": password, "org_id": org_id}
    )
    tok = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    proj = client.post(
        "/api/v1/projects", json={"name": "projE"}, headers=headers
    ).json()

    # Insert scenario directly via DB
    sc = models.SimulationScenario(
        project_id=proj["id"],
        name="s1",
        config={
            "distance_to_control_cm": 50,
            "fg_rgb": [255, 255, 255],
            "bg_rgb": [0, 0, 0],
            "required_force_N": 15,
            "capability_N": 20,
        },
    )
    db_session.add(sc)
    db_session.commit()
    db_session.refresh(sc)

    # Create artifact directly
    art = models.DesignArtifact(project_id=proj["id"], name="a1", type="gltf")
    db_session.add(art)
    db_session.commit()
    db_session.refresh(art)

    # Create rulepack
    rp_payload = {
        "name": "pack1",
        "version": "1.0.0",
        "rules": {
            "rules": [
                {
                    "id": "contrast",
                    "variables": ["contrast_ratio"],
                    "thresholds": {"min_ratio": 4.5},
                    "condition": "contrast_ratio >= min_ratio",
                    "severity": "high",
                }
            ]
        },
    }
    rp = client.post("/api/v1/rulepacks", json=rp_payload, headers=headers).json()

    # Enqueue evaluation
    enq = client.post(
        "/api/v1/evaluations",
        json={"artifact_id": art.id, "scenario_id": sc.id, "rulepack_id": rp["id"]},
        headers=headers,
    )
    assert enq.status_code == 202, enq.text
    eid = enq.json()["id"]

    # Since eager, task already ran
    res = client.get(f"/api/v1/evaluations/{eid}", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "done"
    assert body["results"]["visual"]["ok"] is True
    assert body["inclusivity_index"]["score"] >= 0.0
