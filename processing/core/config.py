from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_URL: str
    RABBITMQ_QUEUE_NAME: str = "document_processing_queue"

    MINIO_URL: str = "localhost:9000"
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET_NAME: str = "documents"
    MINIO_SECURE: bool = False

    GEMINI_API_KEY: str = ""

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_DB: str = "document_insights"
    DATA_ENCRYPTION_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
