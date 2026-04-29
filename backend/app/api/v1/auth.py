from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.schemas.user import (
    AuthResponse,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services import user_service
from app.services.user_service import InvalidCredentialsError, UserAlreadyExistsError

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for(user_id: int) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(str(user_id)),
        refresh_token=create_refresh_token(str(user_id)),
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        user = user_service.create_user(db, payload)
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return AuthResponse(user=UserOut.model_validate(user), tokens=_tokens_for(user.id))


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    try:
        user = user_service.authenticate(db, payload.username, payload.password)
    except InvalidCredentialsError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return AuthResponse(user=UserOut.model_validate(user), tokens=_tokens_for(user.id))


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    if data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="wrong token type")
    user = user_service.get_by_id(db, int(data["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found")
    return _tokens_for(user.id)
