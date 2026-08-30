from typing import Any
from fastapi import APIRouter, Depends, HTTPException

from bonita.api.deps import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser
)
from bonita import schemas
from bonita.services.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError
from bonita.services.user_service import UserService

router = APIRouter()


def _http_from_service_error(exc: Exception) -> None:
    if isinstance(exc, NotFoundError):
        raise HTTPException(status_code=404, detail=exc.message)
    if isinstance(exc, ConflictError):
        raise HTTPException(status_code=409, detail=exc.message)
    if isinstance(exc, ForbiddenError):
        raise HTTPException(status_code=403, detail=exc.message)
    if isinstance(exc, InvalidInputError):
        raise HTTPException(status_code=400, detail=exc.message)
    raise exc


@router.get("/", response_model=schemas.UsersPublic)
def read_users(session: SessionDep, skip: int = 0, limit: int = 100) -> Any:
    """
    Retrieve users.
    """
    users, count = UserService(session).list_users(skip=skip, limit=limit)
    user_list = [schemas.UserPublic.model_validate(user) for user in users]
    return schemas.UsersPublic(data=user_list, count=count)


@router.post(
    "/", dependencies=[Depends(get_current_active_superuser)], response_model=schemas.UserPublic
)
def create_user(*, session: SessionDep, user_in: schemas.UserCreate) -> Any:
    """
    Create new user.
    """
    try:
        return UserService(session).create_user(user_in)
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)


@router.patch("/me", response_model=schemas.UserPublic)
def update_user_me(
    *, session: SessionDep, user_in: schemas.UserUpdateMe, current_user: CurrentUser
) -> Any:
    """
    Update own user.
    """
    try:
        return UserService(session).update_me(current_user, user_in)
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)


@router.patch("/me/password", response_model=schemas.Response)
def update_password_me(
    *, session: SessionDep, body: schemas.UpdatePassword, current_user: CurrentUser
) -> Any:
    """
    Update own password.
    """
    try:
        UserService(session).update_password(
            current_user, body.current_password, body.new_password
        )
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)
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
    try:
        UserService(session).delete_me(current_user)
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)
    return schemas.Response(message="User deleted successfully")


@router.post("/signup", response_model=schemas.UserPublic)
def register_user(session: SessionDep, user_in: schemas.UserRegister) -> Any:
    """
    Create new user without the need to be logged in.
    """
    try:
        return UserService(session).register_user(user_in)
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)


@router.get("/{user_id}", response_model=schemas.UserPublic)
def read_user_by_id(
    user_id: int, session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Get a specific user by id.
    """
    try:
        return UserService(session).get_visible_to(user_id, current_user)
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)


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
    try:
        return UserService(session).update_user(user_id, user_in)
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)


@router.delete("/{user_id}", dependencies=[Depends(get_current_active_superuser)])
def delete_user(
    session: SessionDep, current_user: CurrentUser, user_id: int
) -> schemas.Response:
    """
    Delete a user.
    """
    try:
        UserService(session).delete_user(user_id, current_user)
    except (InvalidInputError, ForbiddenError, ConflictError, NotFoundError) as e:
        _http_from_service_error(e)
    return schemas.Response(message="User deleted successfully")
