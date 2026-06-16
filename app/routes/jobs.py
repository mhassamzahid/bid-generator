import json
import uuid as uuid_module
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.models import Job, Bid
from app.schemas import JobCreate, JobResponse, BidResponse
from app.services.mistral import embed_text, stream_chat
from app.services.rag import find_similar_bids, build_messages

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def _bid_stream(
    job_id: uuid_module.UUID,
    messages: list[dict],
) -> AsyncGenerator[bytes, None]:
    """Stream bid chunks via SSE, then persist the full bid in a fresh session."""
    full_text = ""

    async for chunk in stream_chat(messages):
        full_text += chunk
        yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n".encode()

    # The dependency-injected session is closed once the route handler returns,
    # so we open a dedicated session here to persist the generated bid.
    async with AsyncSessionLocal() as save_db:
        bid = Bid(job_id=job_id, bid_text=full_text, is_manual=False)
        save_db.add(bid)
        await save_db.commit()
        await save_db.refresh(bid)

    yield f"data: {json.dumps({'type': 'done', 'bid_id': str(bid.id), 'job_id': str(job_id)})}\n\n".encode()


@router.post("/generate-bid", summary="Submit an Upwork job and stream back an AI-generated bid")
async def generate_bid(data: JobCreate, db: AsyncSession = Depends(get_db)):
    embed_input = f"{data.title}\n{data.description}\n{' '.join(data.skills or [])}"
    embedding = await embed_text(embed_input)

    job = Job(
        title=data.title,
        description=data.description,
        budget=data.budget,
        skills=data.skills,
        client_info=data.client_info.model_dump() if data.client_info else None,
    )
    db.add(job)
    await db.flush()

    # pgvector requires an explicit CAST from text; this bypasses asyncpg OID issues.
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    await db.execute(
        text("UPDATE jobs SET embedding = CAST(:emb AS vector) WHERE id = CAST(:id AS UUID)"),
        {"emb": embedding_str, "id": str(job.id)},
    )
    await db.commit()
    await db.refresh(job)

    similar_bids = await find_similar_bids(db, embedding, settings.RAG_TOP_K)
    prompt_messages = build_messages(data.model_dump(), similar_bids)

    return StreamingResponse(
        _bid_stream(job.id, prompt_messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Job-ID": str(job.id)},
    )


@router.get("/", response_model=list[JobResponse], summary="List all submitted jobs")
async def list_jobs(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobResponse, summary="Get a single job by ID")
async def get_job(job_id: uuid_module.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/bid", response_model=BidResponse, summary="Get the latest bid for a job")
async def get_job_bid(job_id: uuid_module.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Bid).where(Bid.job_id == job_id).order_by(Bid.created_at.desc())
    )
    bid = result.scalars().first()
    if not bid:
        raise HTTPException(status_code=404, detail="No bid found for this job")
    return bid
