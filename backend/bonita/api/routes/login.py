from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from bonita import schemas
from bonita.api.deps import SessionDep
from bonita.core import security
from bonita.core.config import settings
from bonita.services.errors import InvalidInputError
from bonita.services.user_service import UserService


router = APIRouter()


@router.post("/access-token", summary="获取token", response_model=schemas.Token)
async def login_access_token(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> schemas.Token:
    """
    获取认证Token
    """
    try:
        user = UserService(session).authenticate(
            email=form_data.username,
            password=form_data.password,
        )
    except InvalidInputError as e:
        raise HTTPException(status_code=400, detail=e.message)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return schemas.Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )
