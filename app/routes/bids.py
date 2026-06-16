from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.models import Job, Bid
from app.schemas import BidSeed, SeedResponse
from app.services.mistral import embed_text

router = APIRouter(prefix="/bids", tags=["bids"])


@router.post("/seed", response_model=SeedResponse, summary="Seed a past job + bid to improve future RAG recommendations")
async def seed_bid(data: BidSeed, db: AsyncSession = Depends(get_db)):
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

    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    await db.execute(
        text("UPDATE jobs SET embedding = CAST(:emb AS vector) WHERE id = CAST(:id AS UUID)"),
        {"emb": embedding_str, "id": str(job.id)},
    )
    await db.flush()

    bid = Bid(job_id=job.id, bid_text=data.bid_text, is_manual=True)
    db.add(bid)
    await db.commit()

    return SeedResponse(
        job_id=job.id,
        bid_id=bid.id,
        message="Past bid seeded successfully. It will be used as context for future similar jobs.",
    )
