from typing import Dict
from fastapi import APIRouter, HTTPException

from chacra.asynch import checks


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/")
async def health_check() -> Dict:
    if not checks.is_healthy():
        raise HTTPException(status_code=500, detail="Unhealthy")
    return {}