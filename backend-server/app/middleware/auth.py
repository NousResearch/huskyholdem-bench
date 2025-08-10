# app/middleware/auth.py

from fastapi import Request, HTTPException, status, Depends
from sqlmodel import Session, select
from datetime import datetime

from app.service.db.postgres import engine
from app.models.user import User, AccessToken

def get_token_from_header(request: Request) -> str:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    return auth.split(" ")[1]


def get_current_user(request: Request) -> User:
    token_id = get_token_from_header(request)
    with Session(engine) as db:
        token = db.get(AccessToken, token_id)
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing access token")
        if token.exp < datetime.utcnow():
            db.delete(token)
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token expired")

        user = db.exec(select(User).where(User.username == token.username)).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user


def require_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account not verified. Please check your email for a verification link.")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
