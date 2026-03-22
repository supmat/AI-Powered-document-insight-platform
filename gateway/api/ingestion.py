from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from gateway.models.user import User
from gateway.api.deps import get_current_user
from gateway.models.document import IngestionResponse
from gateway.services.minio_client import upload_file_to_minio
from gateway.services.rabbitmq_client import publish_document_event
import uuid


router = APIRouter()


async def process_upload(
    file_data: bytes, filename: str, content_type: str, user_email: str, task_id: str
):
    """Background task to handle the actual upload and publishing."""
    try:
        # 1. Upload to MinIO
        s3_key = f"{user_email}/{task_id}_{filename}"
        upload_file_to_minio(file_data, s3_key, content_type)

        # 2. Publish to RabbitMQ
        await publish_document_event(
            document_id=task_id,
            file_path=s3_key,
            tenant_id=user_email,
        )
    except Exception as e:
        print(f"Error processing upload: {e}")


@router.post("/", response_model=IngestionResponse, status_code=202)
async def ingest_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Ingests a document.
    Returns 202 Accepted and processes the file upload in the background to avoid blocking.
    """
    filename = file.filename or ""
    if not filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are currently supported"
        )
    content_type = file.content_type or "application/pdf"

    task_id = str(uuid.uuid4())

    # Read file into memory (for large files, consider stream uploading)
    file_data = await file.read()
    if len(file_data) > 15 * 1024 * 1024:  # 15MB limit
        raise HTTPException(status_code=413, detail="File too large. Max 15MB")

    background_tasks.add_task(
        process_upload,
        file_data,
        filename,
        content_type,
        current_user.email,
        task_id,
    )

    return IngestionResponse(
        task_id=task_id,
        status="PENDING",
        filename=filename,
        message="Document received and scheduled for processing.",
    )
