from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    RABBITMQ_URL: str = "amqp://admin:password@localhost:5672/"
    RABBITMQ_QUEUE_NAME: str = "document_processing_queue"

    MINIO_URL: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin123"
    MINIO_BUCKET_NAME: str = "documents"
    MINIO_SECURE: bool = False

    GEMINI_API_KEY: str = ""

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "document_insights"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
