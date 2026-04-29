from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import PasswordChange, UserOut, UserUpdate
from app.services import user_service
from app.services.user_service import WrongPasswordError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(current: User = Depends(get_current_user)):
    return UserOut.model_validate(current)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = user_service.update_profile(db, current, payload)
    return UserOut.model_validate(updated)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_service.change_password(db, current, payload)
    except WrongPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return None
