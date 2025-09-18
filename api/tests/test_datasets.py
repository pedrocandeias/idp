import json
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


def get_auth_headers(client):
    # Create organization
    r = client.post("/api/v1/organizations", json={"name": "orgD"})
    assert r.status_code == 201
    org_id = r.json()["id"]
    # Register user
    email = "d@example.com"
    password = "secret123"
    r = client.post("/auth/register", json={"email": email, "password": password, "org_id": org_id})
    assert r.status_code == 201
    # Login
    r = client.post(
        "/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_anthro_percentiles(client):
    headers = get_auth_headers(client)

    ds = {
        "name": "Anthro Test",
        "source": "unit",
        "schema": {"units": {"stature": "cm"}},
        "distributions": {
            "stature": [
                {"region": "NA", "sex": "M", "age": "18-25", "percentiles": {"p5": 165.0, "p50": 177.0, "p95": 190.0}}
            ]
        }
    }
    r = client.post("/api/v1/datasets/anthropometrics", json=ds, headers=headers)
    assert r.status_code == 201, r.text
    dataset = r.json()

    for p, expected in [(5, 165.0), (50, 177.0), (95, 190.0)]:
        r = client.get(
            f"/api/v1/datasets/anthropometrics/{dataset['id']}/percentile",
            params={"metric": "stature", "percentile": p, "region": "NA", "sex": "M", "age": "18-25"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        val = r.json()["value"]
        assert abs(val - expected) < 1e-6

    # List datasets
    r = client.get("/api/v1/datasets/anthropometrics", headers=headers)
    assert r.status_code == 200
    assert any(item["id"] == dataset["id"] for item in r.json())

