from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from app.models.leaderboard import LeaderBoard, LeaderBoardTopEntry
from app.models.user import User
from app.service.db.postgres import engine
from app.middleware.auth import require_user, require_admin
from typing import List, Optional

class AddEntryResponse(BaseModel):
    message: str
    entry: LeaderBoard
    status_code: int
    username: str

class RemoveEntryResponse(BaseModel):
    message: str
    status_code: int

class TopNResponse(BaseModel):
    message: str
    top_entries: List[LeaderBoardTopEntry]
    status_code: int

class TagsResponse(BaseModel):
    message: str
    tags: List[str]
    status_code: int

class UserEntriesResponse(BaseModel):
    message: str
    entries: List[LeaderBoardTopEntry]
    status_code: int

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.post("/add", response_model=AddEntryResponse, status_code=status.HTTP_200_OK)
def add_leaderboard_entry(score: int, 
                          tag: str = None,
                          user = Depends(require_admin)):
    
    # check if the username is valid
    with Session(engine) as session:
        query = select(User).where(User.username == user.username)
        existing_user = session.exec(query).first()

        if not existing_user:
            raise HTTPException(status_code=400, detail="Invalid username")

    with Session(engine) as session:
        new_entry = LeaderBoard(username=user.username, score=score, tag=tag)
        session.add(new_entry)
        session.commit()
        session.refresh(new_entry)
        return {"message": "Leaderboard entry added", "entry": new_entry, "status_code": status.HTTP_200_OK, "username": user.username}

@router.delete("/remove/{entry_id}", response_model=RemoveEntryResponse, status_code=status.HTTP_200_OK)
def remove_leaderboard_entry(entry_id: str, user = Depends(require_user)):
    with Session(engine) as session:
        entry = session.get(LeaderBoard, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Leaderboard entry not found")
        if entry.username != user.username:
            raise HTTPException(status_code=403, detail="You can only remove your own entries")
        
        session.delete(entry)
        session.commit()
        return {"message": f"Leaderboard entry {entry_id} removed", "status_code": status.HTTP_200_OK}
    
@router.get("/top/{n}", response_model=TopNResponse, status_code=status.HTTP_200_OK)
def get_top_n(n: int, tag: Optional[str] = Query(None, description="Filter by tag")):
    with Session(engine) as session:
        query = select(LeaderBoard).order_by(LeaderBoard.score.desc())
        
        # Filter by tag if provided
        if tag is not None:
            query = query.where(LeaderBoard.tag == tag)
        
        top_n_entries = session.exec(query.limit(n)).all()
        
        tag_filter_msg = f" with tag '{tag}'" if tag else ""
        return {"message": f"Top {n} leaderboard entries{tag_filter_msg} retrieved successfully", 
                "top_entries": top_n_entries[:n], 
                "status_code": status.HTTP_200_OK}

@router.get("/tags", response_model=TagsResponse, status_code=status.HTTP_200_OK)
def get_all_tags():
    """Get all unique tags from leaderboard entries."""
    with Session(engine) as session:
        # Get all distinct non-null tags
        query = select(LeaderBoard.tag).distinct().where(LeaderBoard.tag.is_not(None))
        tags = session.exec(query).all()
        
        # Filter out None values and convert to list
        unique_tags = [tag for tag in tags if tag is not None]
        
        return {"message": "All tags retrieved successfully", 
                "tags": unique_tags, 
                "status_code": status.HTTP_200_OK}

@router.get("/user/{username}", response_model=UserEntriesResponse, status_code=status.HTTP_200_OK)
def get_user_entries(username: str, tag: Optional[str] = Query(None, description="Filter by tag")):
    """Get all leaderboard entries for a specific user."""
    with Session(engine) as session:
        # Check if user exists
        user_query = select(User).where(User.username == username)
        user = session.exec(user_query).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's leaderboard entries
        query = select(LeaderBoard).where(LeaderBoard.username == username).order_by(LeaderBoard.score.desc())
        
        # Filter by tag if provided
        if tag is not None:
            query = query.where(LeaderBoard.tag == tag)
        
        entries = session.exec(query).all()
        
        tag_filter_msg = f" with tag '{tag}'" if tag else ""
        return {"message": f"Leaderboard entries for user '{username}'{tag_filter_msg} retrieved successfully", 
                "entries": entries, 
                "status_code": status.HTTP_200_OK}