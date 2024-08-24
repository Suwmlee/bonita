

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import Session

from app.core.db import Base
from app.core.security import verify_password


class User(Base):
    """
    用户表
    """
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    @staticmethod
    def authenticate(session: Session, email: str, password: str):
        db_user = session.query(User).filter(User.email == email).first()
        if not db_user:
            return None
        if not verify_password(password, db_user.hashed_password):
            return None
        return db_user

    @staticmethod
    def get_user_by_email(session: Session, email: str):
        return session.query(User).filter(User.email == email).first()
