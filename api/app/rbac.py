from __future__ import annotations

from typing import Iterable

from fastapi import HTTPException, status

from . import models

ALL_ROLES = {"superadmin", "org_admin", "designer", "researcher", "reviewer"}


def has_role(user: models.User, allowed: Iterable[str]) -> bool:
    uroles = set((user.roles or []))
    return bool(uroles.intersection(set(allowed))) or ("superadmin" in uroles)


def require_role(user: models.User, allowed: Iterable[str]) -> None:
    if not has_role(user, allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role"
        )
