from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from gateway.core import security
from gateway.core.config import settings
from gateway.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from gateway.models.db_models import DBUser
from gateway.models.user import UserCreate


router = APIRouter()


@router.post("/register")
async def register_user(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user to test the login functionality!
    """
    # Check if user exists
    result = await db.execute(select(DBUser).where(DBUser.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    db_user = DBUser(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_active=True,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return {"msg": "User created successfully. You can now login!"}


@router.post("/login")
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login, getting an access token for future requests.
    Queries the PostgreSQL database to verify credentials.
    """
    result = await db.execute(select(DBUser).where(DBUser.email == form_data.username))
    db_user = result.scalars().first()

    if not db_user or not security.verify_password(
        form_data.password, db_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            db_user.email, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
