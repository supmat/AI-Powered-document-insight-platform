import secrets
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Document Insight Gateway API"

    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 1 week
    ALGORITHM: str = "HS256"

    # Database Settings
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_SERVER: str = "localhost"  # Docker compose exposes this to localhost
    POSTGRES_DB: str = "document_insights"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
