from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request

import jwt

from .config import settings
from .db import SessionLocal
from . import models


async def audit_middleware(request: Request, call_next: Callable):
    user_id = None
    org_id = None
    # Try extract user from Authorization header
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            user_id = int(payload.get("sub"))
        except Exception:
            user_id = None
    body_bytes = b""
    try:
        body_bytes = await request.body()
        # re-inject body so downstream can read it
        async def _receive():  # type: ignore
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request._receive = _receive  # type: ignore[attr-defined]
    except Exception:
        pass
    # sanitize
    before = None
    try:
        before = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
        if isinstance(before, dict) and "password" in before:
            before["password"] = "***"
    except Exception:
        before = None

    response = await call_next(request)

    # after snapshot
    after = None
    try:
        # don't consume response body stream; store status only
        after = {"status_code": response.status_code}
    except Exception:
        after = None

    # persist audit event
    try:
        with SessionLocal() as db:
            if user_id:
                u = db.get(models.User, user_id)
                if u:
                    org_id = u.org_id
            evt = models.AuditEvent(
                org_id=org_id,
                user_id=user_id,
                action=f"{request.method} {request.url.path}",
                details={"before": before, "after": after},
                created_at=datetime.now(timezone.utc),
            )
            db.add(evt)
            db.commit()
    except Exception:
        # fail-open for audit log
        pass

    return response
