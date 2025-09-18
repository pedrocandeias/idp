import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db


SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_org_register_login_create_project_flow(client):
    # Create organization
    r = client.post("/api/v1/organizations", json={"name": "org1"})
    assert r.status_code == 201, r.text
    org = r.json()
    org_id = org["id"]

    # Register user in the org
    email = "user@example.com"
    password = "secret123"
    r = client.post("/auth/register", json={"email": email, "password": password, "org_id": org_id})
    assert r.status_code == 201, r.text

    # Login to get token
    r = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project in the user's org
    r = client.post("/api/v1/projects", json={"name": "proj1", "description": "test"}, headers=headers)
    assert r.status_code == 201, r.text
    proj = r.json()
    assert proj["name"] == "proj1"
    assert proj["org_id"] == org_id

    # List projects, should include the created one
    r = client.get("/api/v1/projects", headers=headers)
    assert r.status_code == 200
    items = r.json()
    assert any(p["id"] == proj["id"] for p in items)

