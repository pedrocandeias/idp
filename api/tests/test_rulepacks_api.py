import pytest
from app.db import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    # Import models to register tables
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
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client, db_session):
    from app import models

    org = models.Org(name="orgRules")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    org_id = org.id
    # Register user
    email = "rules@example.com"
    password = "secret123"
    r = client.post(
        "/auth/register", json={"email": email, "password": password, "org_id": org_id}
    )
    assert r.status_code == 201
    # Elevate role for creating rulepacks
    user = db_session.query(models.User).filter(models.User.email == email).first()
    user.roles = ["researcher"]
    db_session.add(user)
    db_session.commit()
    # Login
    r = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_rulepack_store_and_retrieve(client, db_session):
    headers = auth_headers(client, db_session)
    payload = {
        "name": "General EU v1",
        "version": "1.0.0",
        "rules": {
            "rules": [
                {
                    "id": "button_size_min",
                    "condition": "w >= 9 and h >= 9",
                    "thresholds": {},
                    "variables": ["w", "h"],
                    "severity": "medium",
                }
            ]
        },
    }
    r = client.post("/api/v1/rulepacks", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    pack = r.json()
    assert pack["version"] == "1.0.0"

    r = client.get(f"/api/v1/rulepacks/{pack['id']}", headers=headers)
    assert r.status_code == 200
    got = r.json()
    assert got["name"] == payload["name"]
    assert got["version"] == "1.0.0"
