from minio import Minio
from processing.core.config import settings
from tenacity import retry, stop_after_attempt, wait_exponential

minio_client = Minio(
    settings.MINIO_URL,
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=settings.MINIO_SECURE,
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def download_file_from_minio(object_path: str) -> bytes:
    """
    Downloads a file directly from the MinIO bucket into a bytearray.
    Retries up to 3 times on network failure.
    """
    response = None
    try:
        response = minio_client.get_object(settings.MINIO_BUCKET_NAME, object_path)
        return response.read()
    except Exception as e:
        print(f"Failed to download object {object_path}: {e}")
        raise
    finally:
        if response is not None:
            try:
                response.close()
                response.release_conn()
            except Exception:  # nosec B110
                pass
