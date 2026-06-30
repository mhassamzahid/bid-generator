import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    bio = Column(Text)
    skills = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class ReferenceProject(Base):
    __tablename__ = "reference_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    skills = Column(JSON)
    tech_stack = Column(JSON)
    outcome = Column(Text)
    embedding = Column(Vector(1024))
    created_at = Column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True)
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


class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(100), nullable=False, unique=True)
    prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AiMemory(Base):
    __tablename__ = "ai_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"))
    bid_id = Column(UUID(as_uuid=True), ForeignKey("bids.id", ondelete="SET NULL"))
    user_message = Column(Text, nullable=False)
    user_instruction = Column(Text)
    ai_response = Column(Text)
    memory_type = Column(String(100), nullable=False, default="bid_generation")
    memory_metadata = Column("metadata", JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
