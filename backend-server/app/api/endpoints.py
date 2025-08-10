from fastapi import APIRouter

from app.api.routes.utils import router as utils_router
from app.api.routes.docker import router as docker_router
from app.api.routes.auth import router as auth_router
from app.api.routes.user import router as user_router
from app.api.routes.game import router as game_router
from app.api.routes.leaderboard import router as leaderboard_router
from app.api.routes.submission import router as submission_router
from app.api.routes.profile import router as profile_router
from app.api.routes.admin import router as admin_router
from app.api.routes.live import router as live_router
from app.api.routes.llm import router as llm_router

api_router = APIRouter()
api_router.include_router(utils_router)
api_router.include_router(docker_router)
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(game_router)
api_router.include_router(leaderboard_router)
api_router.include_router(submission_router)
api_router.include_router(profile_router)
api_router.include_router(admin_router)
api_router.include_router(live_router)
api_router.include_router(llm_router)