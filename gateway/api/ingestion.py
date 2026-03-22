from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException
from gateway.models.user import User
from gateway.api.deps import get_current_user
from gateway.models.document import IngestionBatchResponse, TaskInfo
from typing import List
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


@router.post("/", response_model=IngestionBatchResponse, status_code=202)
async def ingest_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Ingests multiple documents or images.
    Returns 202 Accepted and processes HTTP requests in the background.
    """
    results = []
    valid_extensions = (".pdf", ".png", ".jpg", ".jpeg")

    for file in files:
        filename = file.filename or ""
        if not filename.lower().endswith(valid_extensions):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {filename}. Allowed: PDF, PNG, JPG, JPEG",
            )
        content_type = file.content_type or "application/octet-stream"

        task_id = str(uuid.uuid4())

        # Read file into memory
        file_data = await file.read()
        if len(file_data) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=413, detail=f"File {filename} too large. Max 50MB"
            )

        background_tasks.add_task(
            process_upload,
            file_data,
            filename,
            content_type,
            current_user.email,
            task_id,
        )

        results.append(TaskInfo(task_id=task_id, filename=filename, status="PENDING"))

    return IngestionBatchResponse(
        message=f"{len(files)} documents received and scheduled.", tasks=results
    )
