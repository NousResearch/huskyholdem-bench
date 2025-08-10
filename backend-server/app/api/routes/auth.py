from datetime import datetime, timedelta
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status as http_status,
)

from fastapi.responses import RedirectResponse
from passlib.hash import bcrypt
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.middleware.auth import get_current_user, require_admin
from app.service.cache.redis import RedisService
from app.service.mail.mailing import MailService
from app.config.setting import settings

from app.models.user import (
    User,
    UserLogin,
    UserSignup,
    UserMetadata,
    AccessToken,
)
from app.service.db.postgres import engine

router = APIRouter(prefix="/auth", tags=["Authentication"])

redis_service = RedisService(host=settings.REDIS_URL)
mail_service = MailService()

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas for docs / responses
# ──────────────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    """Returned by /login and /register."""
    access_token: str = Field(
        ...,
        example="1f0c0fef‑b585‑4db7‑a3bd‑c5a3975b14f1",
        description="Opaque bearer token",
    )
    token_type: str = Field("bearer", example="bearer")


class MessageResponse(BaseModel):
    message: str = Field(..., example="Logged out successfully")


class ErrorResponse(BaseModel):
    error: str = Field(..., example="Invalid credentials")
    status_code: int = Field(http_status.HTTP_401_UNAUTHORIZED, example=401)


class UpdateAdminAccessRequest(BaseModel):
    username: str = Field(..., example="admin_user")
    admin: bool = Field(..., example=True)


# ──────────────────────────────────────────────────────────────────────────────
# Helper utilities
# ──────────────────────────────────────────────────────────────────────────────
def create_access_token(username: str) -> AccessToken:
    """Issue a new 24‑hour bearer token for *username*."""
    return AccessToken(
        id=str(uuid.uuid4()),
        exp=datetime.utcnow() + timedelta(days=1),
        username=username,
    )


def get_token_from_header(request: Request) -> str:
    """Extract Bearer token from the *Authorization* header."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
        )
    return auth.split(" ", 1)[1]

def _send_verification_email(user: User):
    token = str(uuid.uuid4())
    redis_service.put(f"verification:{token}", user.username, expire=settings.VERIFIED_TOKEN_TTL)
    verification_link = f"{settings.API_URL}/auth/verify-email/{token}"

    try:
        mail_service.send_verification_email(
            to_email=user.email,
            username=user.username,
            verification_link=verification_link
        )
    except Exception as e:
        print(f"Failed to send verification email for {user.username}: {e}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not send verification email. Please try again later."
        )


# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@router.post(
    "/register",
    summary="Create a new user account",
    response_model=TokenResponse,
    status_code=http_status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def register(creds: UserSignup):
    """
    Register a **new** user.

    *Validates* that the username is unique, persists the user, and returns a
    bearer token valid for 24 hours.
    """
    with Session(engine) as db:
        if db.exec(select(User).where(User.username == creds.username)).first():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

        if db.exec(select(User).where(User.email == creds.email)).first():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Email address already in use.",
            )

        user = User(
            username=creds.username,
            password=bcrypt.hash(creds.password),
            email=creds.email,
            admin=False,
            is_verified=False,
            name=creds.name,
            github=creds.github,
            discord_username=creds.discord_username,
            about=creds.about,
        )
        db.add(user)

        try:
            _send_verification_email(user)
            token = create_access_token(user.username)
            db.add(token)
            db.commit()
            return TokenResponse(access_token=token.id)
        except HTTPException as http_exc:
            db.rollback()
            raise http_exc
        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during registration."
            )

@router.post(
    "/login",
    summary="Authenticate and obtain a token",
    response_model=TokenResponse,
    status_code=http_status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def login(creds: UserLogin):
    """
    Verify credentials and return a **bearer token** good for 24 hours.
    """
    with Session(engine) as db:
        user = db.exec(select(User).where(User.username == creds.username)).first()
        if not user or not bcrypt.verify(creds.password, user.password):
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        token = create_access_token(user.username)
        db.add(token)
        db.commit()

        return TokenResponse(access_token=token.id)


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification_email(user: User = Depends(get_current_user)):
    if user.is_verified:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="This account is already verified."
        )
    _send_verification_email(user)
    return MessageResponse(message="A new verification email has been sent.")

@router.get("/verify-email/{verification_token}",
            summary="Verify user's email address and redirect",
            status_code=http_status.HTTP_307_TEMPORARY_REDIRECT,
            responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
    )
async def verify_email(verification_token: str):
    username = redis_service.get(f"verification:{verification_token}")
    success_url = f"{settings.FRONTEND_URL.strip('/')}/verification-success"
    if not username:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )
    
    with Session(engine) as db:
        user = db.exec(select(User).where(User.username == username)).first()
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="User associated with this token not found."
            )
        
        if user.is_verified:
             return RedirectResponse(url=success_url)
        
        user.is_verified = True
        db.add(user)
        db.commit()

        redis_service.remove(f"verification:{verification_token}")

    return RedirectResponse(url=success_url)

@router.get(
    "/whoami",
    summary="Get profile of the token owner",
    response_model=UserMetadata,
    status_code=http_status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def whoami(request: Request):
    """
    Return public metadata for the *currently authenticated* user.
    """
    token_id = get_token_from_header(request)

    with Session(engine) as db:
        token = db.get(AccessToken, token_id)
        if not token:
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

        if token.exp < datetime.utcnow():
            db.delete(token)
            db.commit()
            raise HTTPException(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        user = db.exec(select(User).where(User.username == token.username)).first()
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserMetadata(
            username=user.username,
            name=user.name,
            github=user.github,
            discord_username=user.discord_username,
            about=user.about,
            admin=user.admin,
            is_verified=user.is_verified,
        )


@router.post(
    "/logout",
    summary="Invalidate the current token",
    response_model=MessageResponse,
    status_code=http_status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def logout(request: Request):
    """
    Delete the bearer token presented in the *Authorization* header.
    """
    token_id = get_token_from_header(request)
    with Session(engine) as db:
        token = db.get(AccessToken, token_id)
        if token:
            db.delete(token)
            db.commit()

    return MessageResponse(message="Logged out successfully")

@router.post(
    "/update-admin",
    summary="Update admin privileges of a user",
    response_model=MessageResponse,
    status_code=http_status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_admin_access(
    creds: UpdateAdminAccessRequest,
    _ = Depends(require_admin),
):
    """
    Grant admin privileges to a user.
    """
    with Session(engine) as db:
        user = db.exec(select(User).where(User.username == creds.username)).first()
        if not user:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user.admin = creds.admin
        db.add(user)
        db.commit()

    return MessageResponse(message=f"Admin access {'granted' if creds.admin else 'revoked'} for {creds.username}"
)
