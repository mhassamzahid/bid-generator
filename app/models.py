import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    budget = Column(String(200))
    skills = Column(JSON)
    client_info = Column(JSON)
    embedding = Column(Vector(1024))
    created_at = Column(DateTime, default=datetime.utcnow)


class Bid(Base):
    __tablename__ = "bids"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    bid_text = Column(Text, nullable=False)
    is_manual = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
