from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import AiMemory
from app.schemas import MemoryResponse

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/", response_model=list[MemoryResponse], summary="List stored AI memory entries")
async def list_memory(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AiMemory)
        .order_by(AiMemory.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
