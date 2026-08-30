from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from bonita import schemas
from bonita.core.config import settings
from bonita.core.security import get_password_hash, verify_password
from bonita.db.models.user import User
from bonita.services.errors import ConflictError, ForbiddenError, InvalidInputError, NotFoundError


class UserService:
    """用户与登录相关业务逻辑。"""

    def __init__(self, session: Session):
        self.session = session

    def list_users(self, skip: int = 0, limit: int = 100) -> Tuple[List[User], int]:
        users = self.session.query(User).offset(skip).limit(limit).all()
        count = self.session.query(User).count()
        return users, count

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        return User.get_user_by_email(session=self.session, email=email)

    def authenticate(self, email: str, password: str) -> User:
        user = User.authenticate(session=self.session, email=email, password=password)
        if not user:
            raise InvalidInputError("Incorrect email or password")
        if not user.is_active:
            raise InvalidInputError("Inactive user")
        return user

    def _hash_user_payload(self, payload: dict) -> dict:
        user_info = dict(payload)
        if user_info.get("password"):
            user_info["hashed_password"] = get_password_hash(user_info["password"])
            user_info.pop("password")
        return user_info

    def create_user(self, user_in: schemas.UserCreate) -> User:
        if self.get_by_email(user_in.email):
            raise InvalidInputError("The user with this email already exists in the system.")
        user_info = self._hash_user_payload(user_in.model_dump())
        user = User(**user_info)
        user.create(self.session)
        self.session.refresh(user)
        return user

    def register_user(self, user_in: schemas.UserRegister) -> User:
        if not settings.USERS_OPEN_REGISTRATION:
            raise ForbiddenError("Open user registration is forbidden on this server")
        if self.get_by_email(user_in.email):
            raise InvalidInputError("The user with this email already exists in the system")
        user_info = self._hash_user_payload(user_in.model_dump())
        user = User(**user_info)
        user.create(self.session)
        self.session.refresh(user)
        return user

    def update_me(self, current_user: User, user_in: schemas.UserUpdateMe) -> User:
        if user_in.email:
            existing_user = self.get_by_email(user_in.email)
            if existing_user and existing_user.id != current_user.id:
                raise ConflictError("User with this email already exists")
        user_data = user_in.model_dump(exclude_unset=True)
        current_user.update(self.session, user_data)
        self.session.commit()
        self.session.refresh(current_user)
        return current_user

    def update_password(self, current_user: User, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, current_user.hashed_password):
            raise InvalidInputError("Incorrect password")
        if current_password == new_password:
            raise InvalidInputError("New password cannot be the same as the current one")
        current_user.hashed_password = get_password_hash(new_password)
        self.session.commit()

    def delete_me(self, current_user: User) -> None:
        if current_user.is_superuser:
            raise ForbiddenError("Super users are not allowed to delete themselves")
        self.session.delete(current_user)
        self.session.commit()

    def get_visible_to(self, user_id: int, current_user: User) -> Optional[User]:
        user = self.get_by_id(user_id)
        if user == current_user:
            return user
        if not current_user.is_superuser:
            raise ForbiddenError("The user doesn't have enough privileges")
        return user

    def update_user(self, user_id: int, user_in: schemas.UserUpdate) -> User:
        db_user = self.get_by_id(user_id)
        if not db_user:
            raise NotFoundError("The user with this id does not exist in the system")
        if user_in.email:
            existing_user = self.get_by_email(user_in.email)
            if existing_user and existing_user.id != user_id:
                raise ConflictError("User with this email already exists")
        update_dict = user_in.model_dump(exclude_unset=True)
        db_user.update(self.session, update_dict)
        self.session.commit()
        self.session.refresh(db_user)
        return db_user

    def delete_user(self, user_id: int, current_user: User) -> None:
        user = self.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        if user == current_user:
            raise ForbiddenError("Super users are not allowed to delete themselves")
        self.session.delete(user)
        self.session.commit()
