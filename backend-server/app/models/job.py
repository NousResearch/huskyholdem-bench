from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional, List

from sqlmodel import Column, DateTime, Relationship, SQLModel, Field
from sqlalchemy.sql import func
from sqlalchemy import Enum


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.game import GameLog
    from app.models.batch_llm import BatchLLMQueue

class JobStatus(str, PyEnum):
    """
    Enum for job status.
    """
    PENDING = "Pending"
    RUNNING = "Running"
    FINISHED = "Finished"
    FAILED = "Failed"

class JobType(str, PyEnum):
    SIM_USER = "sim_user"
    SIM_ADMIN = "sim_admin"
    SCALING = "scaling"
    LLM_BATCH_RUN = "llm_batch_run"

class Job(SQLModel, table=True):
    """
    Job model for storing job information.
    """
    id: str = Field(default=None, primary_key=True)
    username: str = Field(foreign_key="user.username", index=True)
    tag: Optional[JobType] = Field(
        sa_column=Column(Enum(JobType), default=None, nullable=True)
    )
    status: JobStatus = Field(
        sa_column=Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    completed_at: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    result_data: Optional[str] = Field(default=None)

    user: Optional["User"] = Relationship(back_populates="jobs")
    game_logs: List["GameLog"] = Relationship(back_populates="job")
    batch_llm_queue: Optional["BatchLLMQueue"] = Relationship(back_populates="job")
    tournaments_2025_added: bool = Field(default=False)