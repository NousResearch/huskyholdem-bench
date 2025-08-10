import enum
import uuid
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.job import Job

class BatchLLMQueue(SQLModel, table=True):
    __tablename__ = "batch_llm_queue"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    job_id: Optional[str] = Field(default=None, foreign_key="job.id", index=True)
    job: Optional["Job"] = Relationship(back_populates="batch_llm_queue")
    users_to_run: Optional[List[str]] = Field(
        default=None, 
        sa_column=Column(JSONB, nullable=True)
    )
    batch_id: Optional[str] = Field(default=None, nullable=True)
    worker_id: Optional[str] = Field(default=None, nullable=True)
    last_updated: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )