import uuid

from sqlmodel import Session
from fastapi import (APIRouter, HTTPException, Depends, status)
from app.service.docker.shared_manager import SharedDockerPoolManager
from app.service.rabbitmq.producer import MQProducer
from app.models.rabbit_message import SimulationMessageType
from app.models.job import Job, JobStatus, JobType
from app.service.db.postgres import engine
from app.middleware.auth import require_admin
from app.models.user import User
from pydantic import BaseModel, Field
from app.config.setting import settings

router = APIRouter(prefix="/docker", tags=["docker"])

class SimulationQueuedResponse(BaseModel):
    """Returned when a simulation request is accepted and queued."""
    job_id: str = Field(..., example="9a11ee55-4deb-4889-baa1-1a3cee051a2c")
    job_status: str = Field("Pending", example="Pending")
    status_code: int = Field(status.HTTP_200_OK, example=200)
    message: str = Field(
        ...,
        example="Files uploaded and simulation started",
    )

class ErrorResponse(BaseModel):
    """Standard error wrapper used by every endpoint."""
    error: str
    status_code: int = Field(status.HTTP_400_BAD_REQUEST, example=400)

class GameLogResponse(BaseModel):
    """Response model for game log content."""
    port: int
    container_name: str
    log_content: str
    success: bool
    message: str

@router.get("/pool/status")
async def get_pool_status():
    """Get the current status of the shared Docker container pool."""
    try:
        pool_manager = SharedDockerPoolManager()
        status = pool_manager.get_pool_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pool status: {str(e)}")

@router.post("/pool/scale", 
            status_code=status.HTTP_200_OK,
            responses={
                400: {"model": ErrorResponse},
                500: {"model": ErrorResponse},
            },)
async def scale_pool(
    target_size: int, 
    user: User = Depends(require_admin) 
    ):
    """Scale the shared Docker container pool to a target size."""

    if (target_size < settings.DOCKER_POOL_SIZE):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"target_size must have more than {settings.DOCKER_POOL_SIZE}")
    
    try:
        # Create DB job -----------------------------------------------------------
        job_id = str(uuid.uuid4())
        with Session(engine) as session:
            job = Job(id=job_id, username=user.username, status=JobStatus.PENDING, tag=JobType.SCALING)
            session.add(job)
            session.commit()
        
        # send the job to the queue
        producer = MQProducer()
        await producer.send_message(
            "simulation_queue", {
                "job_id": job_id,
                "username": user.username,
                "target_size": target_size,
                "job_retries": 0,
                "type": SimulationMessageType.SCALE_DOCKER.value
            }
        )
        await producer.close()

        return SimulationQueuedResponse(job_id=job_id, message="Scale docker container pool started")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scale pool")
    
    
    

@router.get("/containers")
async def get_all_containers():
    """Get information about all Docker containers."""
    try:
        pool_manager = SharedDockerPoolManager()
        containers = pool_manager.docker_service.get_all_containers_live_status()
        return {
            "success": True,
            "data": containers,
            "count": len(containers)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get containers: {str(e)}")

@router.get("/pool/detailed")
async def get_detailed_pool_status():
    """Get detailed information about the shared pool including individual container states."""
    try:
        pool_manager = SharedDockerPoolManager()
        
        # Get basic pool status
        pool_status = pool_manager.get_pool_status()
        
        # Get detailed container information
        pool_containers = pool_manager._get_pool_containers()
        active_containers = pool_manager._get_active_containers()
        
        detailed_info = {
            "pool_summary": pool_status,
            "idle_containers": [
                {
                    "port": container.port,
                    "container_name": container.container_name,
                    "state": container.state.value,
                    "created_by": container.created_by
                }
                for container in pool_containers
            ],
            "active_containers": [
                {
                    "port": container.port,
                    "container_name": container.container_name,
                    "state": container.state.value,
                    "acquired_by": container.acquired_by,
                    "acquired_at": container.acquired_at,
                    "created_by": container.created_by
                }
                for container in active_containers
            ]
        }
        
        return {
            "success": True,
            "data": detailed_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get detailed pool status: {str(e)}")

@router.get("/game-log/{port}", 
            response_model=GameLogResponse,
            status_code=status.HTTP_200_OK,
            responses={
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse},
            })
async def get_game_log_by_port(port: int, user: User = Depends(require_admin)):
    """Get the game log content from a game server container running on the specified port."""
    try:
        pool_manager = SharedDockerPoolManager()
        docker_service = pool_manager.docker_service
        
        # Get container name for the port
        container_name = docker_service.get_game_server_container_name(port)
        
        # Check if container exists
        container = docker_service._get_container(container_name)
        if not container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game server container on port {port} not found"
            )
        
        # Read the game log
        log_content = docker_service.get_log_file_content(container_name, "/app/output/game.log")
        
        # Check if log content indicates an error
        if log_content.startswith("Container") and "not found" in log_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game server container on port {port} not found"
            )
        
        if log_content.startswith("Failed to read") or log_content.startswith("Error reading"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read game log from container: {log_content}"
            )
        
        return GameLogResponse(
            port=port,
            container_name=container_name,
            log_content=log_content,
            success=True,
            message=f"Successfully retrieved game log from container {container_name}"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game log: {str(e)}"
        )