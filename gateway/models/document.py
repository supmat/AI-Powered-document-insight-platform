from pydantic import BaseModel


class IngestionResponse(BaseModel):
    task_id: str
    status: str
    filename: str
    message: str
