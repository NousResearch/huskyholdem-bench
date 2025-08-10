import asyncio
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import api_router
from app.config.setting import settings
from app.service.db.postgres import create_db_and_tables
from app.service.docker.startup import initialize_docker_pool, shutdown_docker_pool

from dotenv import load_dotenv


def format_username_for_container(username: str) -> str:
    """
    Format username for use in container names by replacing spaces with 'gspaceg'
    
    Args:
        username (str): The original username
        
    Returns:
        str: The formatted username safe for container names
    """
    return username.replace(" ", "gspaceg")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting")

    # supabase 
    load_dotenv()
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    print("Supabase bucket: ", SUPABASE_BUCKET)
    print("Supabase url: ", SUPABASE_URL)
    print("Supabase key: ", SUPABASE_KEY)
    
    # Initialize Docker pool
    try:
        docker_pool = initialize_docker_pool()
        print("Docker pool initialized")
    except Exception as e:
        print(f"Failed to initialize Docker pool: {e}")
        # Continue startup even if Docker pool fails
    
    yield
    
    # Shutdown Docker pool
    try:
        shutdown_docker_pool()
        print("Docker pool shutdown complete")
    except Exception as e:
        print(f"Error during Docker pool shutdown: {e}")

def get_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME, 
        version=settings.PROJECT_VERSION,
        description=settings.PROJECT_DESCRIPTION,
        lifespan=lifespan,
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], #TODO: change this to use the settings.ALLOWED_HOSTS
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="")
    return app

app = get_application()
