from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import PasswordChange, UserCreate, UserUpdate


class UserAlreadyExistsError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class WrongPasswordError(Exception):
    pass


def create_user(db: Session, data: UserCreate) -> User:
    exists = (
        db.query(User)
        .filter((User.username == data.username) | (User.email == data.email))
        .first()
    )
    if exists:
        raise UserAlreadyExistsError("username or email already registered")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("invalid username or password")
    return user


def get_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def update_profile(db: Session, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, data: PasswordChange) -> None:
    if not verify_password(data.old_password, user.password_hash):
        raise WrongPasswordError("old password incorrect")
    user.password_hash = hash_password(data.new_password)
    db.commit()
