from typing import Optional, List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ClientInfo(BaseModel):
    country: Optional[str] = None
    hire_rate: Optional[str] = None
    reviews: Optional[float] = None
    total_spent: Optional[str] = None
    member_since: Optional[str] = None


class JobCreate(BaseModel):
    title: str
    description: str
    budget: Optional[str] = None
    skills: Optional[List[str]] = None
    client_info: Optional[ClientInfo] = None


class BidSeed(BaseModel):
    title: str
    description: str
    budget: Optional[str] = None
    skills: Optional[List[str]] = None
    client_info: Optional[ClientInfo] = None
    bid_text: str


class JobResponse(BaseModel):
    id: UUID
    title: str
    description: str
    budget: Optional[str] = None
    skills: Optional[List[str]] = None
    client_info: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BidResponse(BaseModel):
    id: UUID
    job_id: UUID
    bid_text: str
    is_manual: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SeedResponse(BaseModel):
    job_id: UUID
    bid_id: UUID
    message: str


class PromptCreate(BaseModel):
    type: str
    prompt: str


class PromptUpdate(BaseModel):
    prompt: str


class PromptResponse(BaseModel):
    id: UUID
    type: str
    prompt: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MemoryResponse(BaseModel):
    id: UUID
    job_id: Optional[UUID] = None
    bid_id: Optional[UUID] = None
    user_message: str
    ai_response: Optional[str] = None
    memory_type: str
    metadata: Optional[dict] = Field(
        default=None,
        validation_alias="memory_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime

    model_config = {"from_attributes": True}
