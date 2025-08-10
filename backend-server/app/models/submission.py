from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy.sql import func
from sqlmodel import Column, DateTime, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User 


class Submission(SQLModel, table=True):
    """
    Submission model for storing submission information.
    """
    id: str = Field(default=None, primary_key=True)
    username: str = Field(foreign_key="user.username", index=True)
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    )
    player_file: str = Field(default=None, nullable=False)
    package_file: str = Field(default=None, nullable=False)
    final: bool = Field(default=False, nullable=False)

    user: Optional["User"] = Relationship(back_populates="submissions")
