from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime

if TYPE_CHECKING:
    from app.models.job import Job  # Avoid circular import issues
    from app.models.leaderboard import LeaderBoard
    from app.models.submission import Submission  # Avoid circular import issues

class AccessToken(SQLModel, table=True):
    id: str = Field(primary_key=True, unique=True, nullable=False)
    exp: datetime = Field(nullable=False)  # Use datetime for expiry
    username: str = Field(foreign_key="user.username", nullable=False)
    user: Optional["User"] = Relationship(back_populates="access_tokens")

class User(SQLModel, table=True):
    username: str = Field(primary_key=True, unique=True, nullable=False)
    password: str = Field(nullable=False)
    email: str = Field(nullable=False)
    is_verified: bool = Field(default=False, nullable=False)
    admin: bool = Field(default=False)
    access_tokens: List[AccessToken] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    name: Optional[str] = Field(default=None, nullable=True)
    github: Optional[str] = Field(default=None, nullable=True)
    discord_username: Optional[str] = Field(default=None, nullable=True)
    about: Optional[str] = Field(default=None, nullable=True)
    jobs: List["Job"] = Relationship(back_populates="user")
    submissions: List["Submission"] = Relationship(back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    
    leaderboard_entries: List["LeaderBoard"] = Relationship(back_populates="user")

class UserSignup(BaseModel):
    username: str
    password: str
    email: str
    name: Optional[str] = None
    github: Optional[str] = None
    discord_username: Optional[str] = None
    about: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserMetadata(BaseModel):
    username: str
    name: Optional[str] = None
    github: Optional[str] = None
    discord_username: Optional[str] = None
    about: Optional[str] = None
    admin: bool = False
    is_verified: bool = False