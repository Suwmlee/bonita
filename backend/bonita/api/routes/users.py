
from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from bonita.core.config import settings
from bonita.core.security import get_password_hash, verify_password
from bonita.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser
)
from bonita import schemas
from bonita.db.models.user import User

router = APIRouter()


@router.get("/", response_model=schemas.UsersPublic)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """
    users = session.query(User).offset(skip).limit(limit).all()
    count = session.query(User).count()

    user_list = [schemas.UserPublic.model_validate(user) for user in users]
    return schemas.UsersPublic(data=user_list, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=schemas.UserPublic
)
def create_user(*, session: SessionDep, user_in: schemas.UserCreate) -> Any:
    """
    Create new user.
    """
    user = User.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user_info = user_in.__dict__
    if user_info.get("password"):
        user_info["hashed_password"] = get_password_hash(user_info["password"])
        user_info.pop("password")
    user = User(**user_info)
    user.create(session)
    session.refresh(user)
    return user


@router.patch("/me", response_model=schemas.UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: schemas.UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """
    if user_in.email:
        existing_user = User.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.update(session, user_data)
    session.commit()
    session.refresh(current_user)
    return current_user


@router.patch("/me/password", response_model=schemas.Response)
def update_password_me(
    *, session: SessionDep, body: schemas.UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.commit()
    return schemas.Response(message="Password updated successfully")


@router.get("/me", response_model=schemas.UserPublic)
def read_user_me(current_user: CurrentUser) -> Any:
    """
    Get current user.
    """
    return current_user


@router.delete("/me", response_model=schemas.Response)
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Any:
    """
    Delete own user.
    """
    if current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(current_user)
    session.commit()
    return schemas.Response(message="User deleted successfully")


@router.post("/signup", response_model=schemas.UserPublic)
def register_user(session: SessionDep, user_in: schemas.UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    if not settings.USERS_OPEN_REGISTRATION:
        raise HTTPException(
            status_code=403,
            detail="Open user registration is forbidden on this server",
        )
    user = User.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system",
        )
    user_info = user_in.__dict__
    if user_info.get("password"):
        user_info["hashed_password"] = get_password_hash(user_info["password"])
        user_info.pop("password")
    user = User(**user_info)
    user.create(session)
    session.refresh(user)
    return user


@router.get("/{user_id}", response_model=schemas.UserPublic)
def read_user_by_id(
    user_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="The user doesn't have enough privileges",
        )
    return user


@router.patch(
    "/{user_id}",
    dependencies=[Depends(get_current_active_superuser)],
    response_model=schemas.UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    user_id: int,
    user_in: schemas.UserUpdate,
) -> Any:
    """
    Update a user.
    """
    db_user = session.get(User, user_id)
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail="The user with this id does not exist in the system",
        )
    if user_in.email:
        existing_user = User.get_user_by_email(session=session, email=user_in.email)
        if existing_user and existing_user.id != user_id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )
    update_dict = user_in.model_dump(exclude_unset=True)
    db_user.update(session, update_dict)
    session.commit()
    session.refresh(db_user)
    return db_user


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: int
) -> schemas.Response:
    """
    Delete a user.
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user == current_user:
        raise HTTPException(
            status_code=403, detail="Super users are not allowed to delete themselves"
        )
    session.delete(user)
    session.commit()
    return schemas.Response(message="User deleted successfully")
