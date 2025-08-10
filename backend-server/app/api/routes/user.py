from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, func
from pydantic import BaseModel
from typing import Annotated, Optional

from app.middleware.auth import require_admin, require_user
from app.service.db.postgres import engine
from app.models.user import User

router = APIRouter(prefix="/user", tags=["user"])

class UserUpdateRequest(BaseModel):
    name: str
    github: str
    discord_username: str
    about: str

class BasicResponse(BaseModel):
    status: int
    message: str

class UserInfoResponse(BaseModel):
    username: str
    admin: bool

class UserSearchResponse(BaseModel):
    username: str
    name: Optional[str] = None
    github: Optional[str] = None
    discord_username: Optional[str] = None
    about: Optional[str] = None

class PaginatedUsersResponse(BaseModel):
    message: str
    users: list[UserSearchResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    status_code: int

# ──────────────────────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/search", response_model=list[UserSearchResponse])
def search_users(
    q: Annotated[str, Query(description="Search query to find users by name or username")]
):
    """Search for users by name or username"""
    with Session(engine) as db:
        # Search users where name or username contains the query (case-insensitive)
        users = db.exec(
            select(User).where(
                (User.name.ilike(f"%{q}%")) | 
                (User.username.ilike(f"%{q}%"))
            )
        ).all()
    
    return [
        {
            "username": user.username,
            "name": user.name,
            "github": user.github,
            "discord_username": user.discord_username,
            "about": user.about
        } for user in users
    ]

@router.get("/me", response_model=UserInfoResponse)
def get_my_info(user: Annotated[User, Depends(require_user)]):
    return {
        "username": user.username,
        "admin": user.admin
    }

@router.get("/admin-only", response_model=dict)
def dangerous_action(user: Annotated[User, Depends(require_admin)]):
    return {"message": f"Admin action allowed for {user.username}"}

@router.post("/update", response_model=BasicResponse)
def update_user_info(
    metadata: UserUpdateRequest,
    user: Annotated[User, Depends(require_user)]
):
    with Session(engine) as db:
        db_user = db.exec(select(User).where(User.username == user.username)).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        db_user.name = metadata.name
        db_user.github = metadata.github
        db_user.discord_username = metadata.discord_username
        db_user.about = metadata.about

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

    return {
        "status": status.HTTP_200_OK,
        "message": "User information updated successfully"
    }

@router.get("/all", response_model=PaginatedUsersResponse)
def get_all_users(
    _: Annotated[User, Depends(require_user)],
    page: Annotated[int, Query(description="Page number (1-based)", ge=1)] = 1,
    page_size: Annotated[int, Query(description="Number of users per page", ge=1, le=100)] = 25
):
    """Get all users with pagination. Default page size is 25."""
    with Session(engine) as db:
        # Get total count
        total_count = db.exec(select(func.count(User.username))).first()
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get paginated users
        users = db.exec(
            select(User)
            .offset(offset)
            .limit(page_size)
        ).all()
        
        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size
        
        user_list = [
            {
                "username": user.username,
                "name": user.name,
                "github": user.github,
                "discord_username": user.discord_username,
                "about": user.about
            } for user in users
        ]

        return PaginatedUsersResponse(
            message=f"Retrieved page {page} of {total_pages} with {len(user_list)} users",
            users=user_list,
            total=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            status_code=status.HTTP_200_OK
        )