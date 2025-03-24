from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Optional

from .config import settings
from .schemas import User, TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class AuthHandler:
    @staticmethod
    def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            return User(username=username)
        except JWTError:
            raise credentials_exception

get_current_user = AuthHandler().get_current_user