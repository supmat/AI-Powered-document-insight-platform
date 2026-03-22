from minio import Minio
from gateway.core.config import settings
import io


# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_URL,
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=settings.MINIO_SECURE,
)


def ensure_bucket_exists():
    """Ensure the target bucket exists before starting the app."""
    if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
        minio_client.make_bucket(settings.MINIO_BUCKET_NAME)


def upload_file_to_minio(file_stream: bytes, file_name: str, content_type: str) -> str:
    """
    Uploads a file stream directly to MinIO.
    Returns the object name (S3 key).
    """
    file_io = io.BytesIO(file_stream)
    file_size = len(file_stream)

    minio_client.put_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=file_name,
        data=file_io,
        length=file_size,
        content_type=content_type,
    )
    return file_name
