import uuid as uuid_module
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import ReferenceProject
from app.schemas import ReferenceProjectCreate, ReferenceProjectResponse
from app.services.mistral import embed_text

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ReferenceProjectResponse], summary="List reference projects")
async def list_projects(
    profile_id: Optional[uuid_module.UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ReferenceProject).order_by(ReferenceProject.created_at.desc())
    if profile_id:
        query = query.where(ReferenceProject.profile_id == profile_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ReferenceProjectResponse, summary="Add a reference project and generate its embedding")
async def create_project(data: ReferenceProjectCreate, db: AsyncSession = Depends(get_db)):
    embed_input = f"{data.title}\n{data.description}\n{' '.join(data.skills or [])}\n{' '.join(data.tech_stack or [])}"
    embedding = await embed_text(embed_input)

    project = ReferenceProject(
        profile_id=data.profile_id,
        title=data.title,
        description=data.description,
        skills=data.skills,
        tech_stack=data.tech_stack,
        outcome=data.outcome,
    )
    db.add(project)
    await db.flush()

    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    await db.execute(
        text("UPDATE reference_projects SET embedding = CAST(:emb AS vector) WHERE id = CAST(:id AS UUID)"),
        {"emb": embedding_str, "id": str(project.id)},
    )
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ReferenceProjectResponse, summary="Get a reference project by ID")
async def get_project(project_id: uuid_module.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReferenceProject).where(ReferenceProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Reference project not found")
    return project


@router.delete("/{project_id}", summary="Delete a reference project")
async def delete_project(project_id: uuid_module.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReferenceProject).where(ReferenceProject.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Reference project not found")
    await db.delete(project)
    await db.commit()
    return {"message": "Reference project deleted"}
