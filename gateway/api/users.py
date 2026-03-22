from fastapi import APIRouter, Depends
from gateway.models.user import User
from gateway.api import deps

router = APIRouter()


@router.get("/me", response_model=User)
def read_current_user(current_user: User = Depends(deps.get_current_user)):
    """
    Get current user safely using FastAPI's dependency injection.
    """
    return current_user
