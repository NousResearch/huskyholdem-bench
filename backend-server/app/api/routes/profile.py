from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List

from app.models.user import User, UserMetadata
from app.models.leaderboard import LeaderBoard, LeaderBoardTopEntry
from app.middleware.auth import require_user
from app.service.db.postgres import engine

class PublicProfileResponse(BaseModel):
    profile: UserMetadata
    leaderboard_entries: List[LeaderBoardTopEntry]

class OwnProfileResponse(BaseModel):
    profile: dict
    leaderboard_entries: List[LeaderBoardTopEntry]

router = APIRouter(prefix="/profile", tags=["profile"])

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/{username}", response_model=PublicProfileResponse)
def get_public_profile(username: str, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == username)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user's leaderboard entries for public view
    leaderboard_entries = session.exec(
        select(LeaderBoard)
        .where(LeaderBoard.username == username)
        .order_by(LeaderBoard.score.desc())
    ).all()

    # Convert to LeaderBoardTopEntry format for consistent API response
    formatted_entries = [
        LeaderBoardTopEntry(
            username=entry.username,
            score=entry.score,
            tag=entry.tag,
            time_created=entry.time_created
        ) for entry in leaderboard_entries
    ]

    return {
        "profile": UserMetadata(
            username=user.username,
            name=user.name,
            github=user.github,
            discord_username=user.discord_username,
            about=user.about,
            admin=user.admin
        ),
        "leaderboard_entries": formatted_entries
    }


@router.get("/", response_model=OwnProfileResponse)
def get_own_profile(user: User = Depends(require_user), session: Session = Depends(get_session)):
    # Get user's leaderboard entries
    leaderboard_entries = session.exec(
        select(LeaderBoard)
        .where(LeaderBoard.username == user.username)
        .order_by(LeaderBoard.score.desc())
    ).all()

    # Convert to LeaderBoardTopEntry format for consistent API response
    formatted_entries = [
        LeaderBoardTopEntry(
            username=entry.username,
            score=entry.score,
            tag=entry.tag,
            time_created=entry.time_created
        ) for entry in leaderboard_entries
    ]

    return {
        "profile": {
            "username": user.username,
            "email": user.email,
            "name": user.name,
            "github": user.github,
            "discord_username": user.discord_username,
            "about": user.about,
            "admin": user.admin
        },
        "leaderboard_entries": formatted_entries
    }