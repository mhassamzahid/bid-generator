from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

DEFAULT_SYSTEM_PROMPT = (
    "You are a top-rated Upwork freelancer with a 100% Job Success Score. "
    "You write bids that win because they are specific, client-focused, and never generic. "
    "You never use hollow filler phrases or copy-paste language."
)

DEFAULT_BID_GENERATION_PROMPT = """Write a compelling Upwork bid proposal for this job.

Use the job title, budget, required skills, client info, job description, past similar bids, and memory context provided by the backend.

Write a 200-300 word bid proposal that:
- Opens with a specific hook that addresses their exact problem
- Never starts with "I am writing to express..."
- Shows you understand what they actually need
- Briefly mentions relevant experience naturally
- Is conversational and direct, not corporate
- Uses past winning bids only as inspiration and never copies them
- Ends with a confident, low-friction call-to-action

Output the bid text only, no extra commentary."""


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


def build_user_message(
    job: dict,
    bid_generation_prompt: str,
    similar_bids: list[dict],
    memories: list[dict],
) -> str:
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

    memory_block = ""
    if memories:
        memory_block = "\n\n---\n## Recent AI Memory (use for continuity and style context only):\n"
        for i, memory in enumerate(memories, 1):
            memory_block += f"\n### Memory {i}\n"
            memory_block += f"**User Context:**\n{memory['user_message']}\n"
            if memory.get("ai_response"):
                memory_block += f"**AI Response:**\n{memory['ai_response']}\n"
        memory_block += "\n---\n"

    return f"""{bid_generation_prompt}

## Current Job

**Title:** {job['title']}
**Budget:** {budget_str}
**Required Skills:** {skills_str}
**Client:** {client_str}

**Job Description:**
{job['description']}
{context_block}
{memory_block}"""


def build_messages(
    job: dict,
    prompts: dict[str, str],
    similar_bids: list[dict],
    memories: list[dict],
) -> list[dict]:
    user_message = build_user_message(
        job=job,
        bid_generation_prompt=prompts.get("bid_generation") or DEFAULT_BID_GENERATION_PROMPT,
        similar_bids=similar_bids,
        memories=memories,
    )
    return [
        {
            "role": "system",
            "content": prompts.get("system") or DEFAULT_SYSTEM_PROMPT,
        },
        {"role": "user", "content": user_message},
    ]


def build_revision_messages(
    job: dict,
    current_bid: str,
    instruction: str,
    prompts: dict[str, str],
) -> list[dict]:
    """Build a focused prompt for revising one saved bid version."""
    skills_str = ", ".join(job.get("skills") or []) or "Not specified"
    budget_str = job.get("budget") or "Not specified"

    return [
        {
            "role": "system",
            "content": prompts.get("system") or DEFAULT_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": f"""{prompts.get("bid_generation") or DEFAULT_BID_GENERATION_PROMPT}

## Current Job

**Title:** {job['title']}
**Budget:** {budget_str}
**Required Skills:** {skills_str}

**Job Description:**
{job['description']}

## Current Bid Version

{current_bid}

## User's Requested Edits

{instruction}

Rewrite the bid to apply the requested edits. Keep useful details from the current version unless the instruction changes them. Output only the complete revised bid text, with no commentary.""",
        },
    ]
