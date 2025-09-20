import pytest
from app import models
from app.db import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"


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
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # Ensure middleware uses same session
    import app.db as app_db

    app_db.SessionLocal = lambda: db_session

    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def auth_headers(client, db_session):
    # Create orgs
    # Need superadmin to create orgs
    # Bootstrap by creating default org via auth.register
    r = client.post("/api/v1/organizations", json={"name": "OrgA"})
    # As of RBAC, create_org requires superadmin; we will create orgs directly
    orgA = models.Org(name="OrgA")
    orgB = models.Org(name="OrgB")
    db_session.add_all([orgA, orgB])
    db_session.commit()
    # Create users directly
    ua = models.User(
        email="a@x", hashed_password="hpw", org_id=orgA.id, roles=["designer"]
    )
    ub = models.User(
        email="b@x", hashed_password="hpw", org_id=orgB.id, roles=["designer"]
    )
    db_session.add_all([ua, ub])
    db_session.commit()
    db_session.refresh(ua)
    db_session.refresh(ub)
    # Issue tokens via API login flow is not available; directly craft JWT via auth endpoints not possible in tests.
    # Instead, use token route with same password won't work (not set). For simplicity, we hit token via registering real users.
    # Create via API register to get token for A
    ra = client.post(
        "/auth/register",
        json={"email": "userA@example.com", "password": "p", "org_id": orgA.id},
    )
    ta = client.post(
        "/auth/token",
        data={"username": "userA@example.com", "password": "p"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    rb = client.post(
        "/auth/register",
        json={"email": "userB@example.com", "password": "p", "org_id": orgB.id},
    )
    tb = client.post(
        "/auth/token",
        data={"username": "userB@example.com", "password": "p"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    return {
        "A": {"h": {"Authorization": f"Bearer {ta}"}, "org": orgA},
        "B": {"h": {"Authorization": f"Bearer {tb}"}, "org": orgB},
    }


def test_rbac_denied_cross_org_access_and_audit(client, db_session):
    auth = auth_headers(client, db_session)
    # Create project in org A
    rp = client.post(
        "/api/v1/projects", json={"name": "PA"}, headers=auth["A"]["h"]
    ).json()
    # User B attempts to access project A
    r = client.get(
        f"/api/v1/projects/{rp['id']}", headers=auth["B"]["h"]
    )  # should be 403
    assert r.status_code == 403
    # Audit record exists
    # Count events
    evts = db_session.query(models.AuditEvent).all()
    assert any("/api/v1/projects" in e.action for e in evts)
