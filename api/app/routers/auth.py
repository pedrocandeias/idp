from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import models
from ..db import get_db
from ..schemas import TokenResponse, UserCreate
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenResponse:
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    # Pick org: provided by client or default
    org = None
    if payload.org_id:
        org = db.get(models.Org, payload.org_id)
        if not org:
            raise HTTPException(status_code=400, detail="Invalid org_id")
    else:
        org = db.query(models.Org).filter(models.Org.name == "default").first()
        if not org:
            org = models.Org(name="default")
            db.add(org)
            db.flush()

    user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        org_id=org.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)


@router.post("/token", response_model=TokenResponse)
def token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    # OAuth2PasswordRequestForm uses 'username' field for identifier
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(subject=str(user.id))
    return TokenResponse(access_token=token)
