import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import Prompt
from app.schemas import PromptCreate, PromptResponse, PromptUpdate

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptResponse], summary="List editable AI prompts")
async def list_prompts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).order_by(Prompt.type.asc()))
    return result.scalars().all()


@router.post("", response_model=PromptResponse, summary="Create an editable AI prompt")
async def create_prompt(data: PromptCreate, db: AsyncSession = Depends(get_db)):
    prompt_type = data.type.strip()
    if not prompt_type:
        raise HTTPException(status_code=400, detail="Prompt type is required")

    existing = await db.execute(select(Prompt).where(Prompt.type == prompt_type))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Prompt type already exists")

    prompt = Prompt(type=prompt_type, prompt=data.prompt)
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse, summary="Update an editable AI prompt")
async def update_prompt(
    prompt_id: uuid_module.UUID,
    data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Prompt).where(Prompt.id == prompt_id))
    prompt = result.scalar_one_or_none()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt.prompt = data.prompt
    await db.commit()
    await db.refresh(prompt)
    return prompt
