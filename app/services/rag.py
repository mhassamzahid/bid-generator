from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


async def find_similar_bids(
    db: AsyncSession,
    embedding: list[float],
    top_k: int,
) -> list[dict]:
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    result = await db.execute(
        text("""
            SELECT
                j.title,
                j.description,
                b.bid_text
            FROM jobs j
            JOIN bids b ON b.job_id = j.id
            WHERE j.embedding IS NOT NULL
            ORDER BY j.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """),
        {"embedding": embedding_str, "top_k": top_k},
    )

    return [dict(row._mapping) for row in result.fetchall()]


def build_messages(job: dict, similar_bids: list[dict]) -> list[dict]:
    skills_str = ", ".join(job.get("skills") or []) or "Not specified"
    budget_str = job.get("budget") or "Not specified"

    client_info = job.get("client_info") or {}
    client_parts = []
    if client_info.get("country"):
        client_parts.append(f"Country: {client_info['country']}")
    if client_info.get("hire_rate"):
        client_parts.append(f"Hire Rate: {client_info['hire_rate']}")
    if client_info.get("reviews") is not None:
        client_parts.append(f"Rating: {client_info['reviews']}/5")
    if client_info.get("total_spent"):
        client_parts.append(f"Total Spent: {client_info['total_spent']}")
    client_str = " | ".join(client_parts) or "Not provided"

    context_block = ""
    if similar_bids:
        context_block = "\n\n---\n## Past Winning Bids for Similar Jobs (use as inspiration only — do NOT copy):\n"
        for i, bid in enumerate(similar_bids, 1):
            context_block += f"\n### Reference {i}\n"
            context_block += f"**Job:** {bid['title']}\n"
            context_block += f"**Bid:**\n{bid['bid_text']}\n"
        context_block += "\n---\n"

    user_prompt = f"""Write a compelling Upwork bid proposal for this job:

**Title:** {job['title']}
**Budget:** {budget_str}
**Required Skills:** {skills_str}
**Client:** {client_str}

**Job Description:**
{job['description']}
{context_block}
Write a 200–300 word bid proposal that:
- Opens with a specific hook that addresses their exact problem (never start with "I am writing to express...")
- Shows you understand what they actually need
- Briefly mentions relevant experience naturally
- Is conversational and direct — not corporate
- Ends with a confident, low-friction call-to-action

Output the bid text only, no extra commentary."""

    return [
        {
            "role": "system",
            "content": (
                "You are a top-rated Upwork freelancer with a 100% Job Success Score. "
                "You write bids that win because they are specific, client-focused, and never generic. "
                "You never use hollow filler phrases or copy-paste language."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]
