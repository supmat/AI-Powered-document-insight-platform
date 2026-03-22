from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from gateway.core.config import settings
from gateway.models.token import TokenPayload
from gateway.models.user import User
from gateway.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from gateway.models.db_models import DBUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.APP_V1_STR}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception

    # Query Database
    result = await db.execute(select(DBUser).where(DBUser.email == token_data.sub))
    db_user = result.scalars().first()

    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not db_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return User(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
    )
