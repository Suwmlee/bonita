
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app import schemas
from app.api.deps import SessionDep
from app.core import security
from app.core.config import settings
from app.db.models.user import User


router = APIRouter()


@router.post("/access-token", summary="获取token", response_model=schemas.Token)
async def login_access_token(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> schemas.Token:
    """
    获取认证Token
    """
    # 检查数据库
    user = User.authenticate(
        session=session,
        email=form_data.username,
        password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return schemas.Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )
