from typing import AsyncGenerator

from mistralai import Mistral

from app.core.config import settings

_client = Mistral(api_key=settings.MISTRAL_API_KEY)


async def embed_text(text: str) -> list[float]:
    response = await _client.embeddings.create_async(
        model=settings.MISTRAL_EMBED_MODEL,
        inputs=[text],
    )
    return response.data[0].embedding


async def stream_chat(messages: list[dict]) -> AsyncGenerator[str, None]:
    async with _client.chat.stream_async(
        model=settings.MISTRAL_CHAT_MODEL,
        messages=messages,
    ) as stream:
        async for chunk in stream.get_text_stream():
            yield chunk
