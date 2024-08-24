from typing import List
from pydantic import BaseModel, EmailStr, Field


# Shared properties
class UserBase(BaseModel):
    # 用户名
    name: str | None = Field(default=None, max_length=255)
    # 邮箱，未启用
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    # 状态
    is_active: bool = True
    # 超级管理员
    is_superuser: bool = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(BaseModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(BaseModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: int

    class Config:
        from_attributes = True


class UsersPublic(BaseModel):
    data: List[UserPublic]
    count: int
