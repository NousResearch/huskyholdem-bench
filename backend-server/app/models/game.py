import enum
import uuid
from sqlmodel import Field, SQLModel, Session, Relationship
from sqlalchemy import Column, Boolean, false
from sqlalchemy.dialects.postgresql import JSONB
import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.job import Job

class GameStatus(enum.Enum):
    NOT_STARTED = "NOT STARTED"
    IN_PROGRESS = "RUNNING"
    COMPLETED = "DONE"
    NON_EXISTENT = "NON EXISTENT"

class GameLog(SQLModel, table=True):
    __tablename__ = "game_logs"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    game_uuid: Optional[str] = Field(nullable=True)
    game_data: dict = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, nullable=False)
    job_id: Optional[str] = Field(default=None, foreign_key="job.id", index=True)
    job: Optional["Job"] = Relationship(back_populates="game_logs")
    is_public: bool = Field(default=False, sa_column=Column(Boolean, nullable=False, server_default=false()))