from pydantic import BaseModel
from typing import List


class TaskInfo(BaseModel):
    task_id: str
    filename: str
    status: str


class IngestionBatchResponse(BaseModel):
    message: str
    tasks: List[TaskInfo]
