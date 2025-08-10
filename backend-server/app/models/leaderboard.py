from typing import Optional, TYPE_CHECKING
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Column, DateTime, Field, SQLModel, Relationship
from datetime import datetime
import uuid

if TYPE_CHECKING:
    from app.models.user import User  # Avoid circular import issues

class LeaderBoard(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, unique=True, nullable=False)
    username: str = Field(foreign_key="user.username", index=True)
    time_created: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    score: int = Field(nullable=False)
    tag: Optional[str] = Field(default=None, nullable=True)
    
    user: Optional["User"] = Relationship(back_populates="leaderboard_entries")

class LeaderBoardTopEntry(BaseModel):
    username: str
    score: int
    tag: Optional[str] = None
    time_created: datetime