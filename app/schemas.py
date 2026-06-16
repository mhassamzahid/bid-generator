from typing import Optional, List
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


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
