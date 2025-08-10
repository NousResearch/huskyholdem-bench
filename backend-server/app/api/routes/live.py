from fastapi import APIRouter, status, HTTPException, Query
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from sqlalchemy import func, cast, Integer
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.models.game import GameLog
from app.service.db.postgres import engine

router = APIRouter(prefix="/live", tags=["live"])

class GameDataResponse(BaseModel):
    """Response model for game data."""
    message: str
    game_id: str
    game_uuid: str
    job_id: str
    game_data: Dict[str, Any]

class GameSummaryResponse(BaseModel):
    """Response model for game summary with ID and players."""
    game_id: str
    game_uuid: str
    job_id: str
    players: List[str]

class AllGamesResponse(BaseModel):
    """Response model for all games summary."""
    message: str
    games: List[GameSummaryResponse]

class JobGameInfo(BaseModel):
    """Response model for individual game info within a job."""
    game_id: str
    game_uuid: str

class JobGamesResponse(BaseModel):
    """Response model for games related to a job."""
    message: str
    job_id: str
    games: List[JobGameInfo]

class PaginatedJobGamesResponse(BaseModel):
    """Response model for paginated games related to a job."""
    message: str
    job_id: str
    games: List[JobGameInfo]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool

class JobIdWithPlayers(BaseModel):
    """Response model for job ID with its players and creation time."""
    job_id: str
    players: List[str]
    first_game_created_at: datetime
    is_public: bool

class AllJobIdsResponse(BaseModel):
    """Response model for all job IDs in game logs."""
    message: str
    jobs: List[JobIdWithPlayers]

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    status_code: int = Field(status.HTTP_400_BAD_REQUEST, example=400)

# ──────────────────────────────────────────────────────────────────────────────
# Router
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/status")
async def live_status():
    return {"status": "live"}

@router.get(
    "/job-ids",
    summary="Retrieve all unique job IDs from game logs with their players and creation times",
    response_model=AllJobIdsResponse,
    status_code=status.HTTP_200_OK,
    responses={500: {"model": ErrorResponse}},
)
def get_all_job_ids():
    """
    Fetches all unique job IDs from the game logs table along with their players and creation time.
    Since all games with the same job_id have the same players, we extract players from one game per job.
    We also track the earliest created_at time for each job_id.
    """
    with Session(engine) as session:
        try:
            # Get all game logs
            game_logs = session.exec(select(GameLog)).all()
            
            # Group games by job_id and extract players and earliest creation time for each job
            job_id_to_info = {}
            
            for game_log in game_logs:
                if game_log.job_id is None:
                    continue
                    
                # If we haven't seen this job_id yet, extract players and set creation time
                if game_log.job_id not in job_id_to_info:
                    game_data = game_log.game_data
                    players = []
                    
                    # Extract players from game data
                    if "playerIdToUsername" in game_data:
                        if isinstance(game_data["playerIdToUsername"], dict):
                            players = list(game_data["playerIdToUsername"].values())
                    
                    job_id_to_info[game_log.job_id] = {
                        "players": players,
                        "first_game_created_at": game_log.created_at,
                        "is_public": game_log.is_public
                    }
                else:
                    # Update earliest creation time if this game was created earlier
                    if game_log.created_at < job_id_to_info[game_log.job_id]["first_game_created_at"]:
                        job_id_to_info[game_log.job_id]["first_game_created_at"] = game_log.created_at
            
            # Create response with job IDs, their players, and creation times
            jobs = [
                JobIdWithPlayers(
                    job_id=job_id, 
                    players=info["players"],
                    first_game_created_at=info["first_game_created_at"],
                    is_public=info["is_public"]
                )
                for job_id, info in job_id_to_info.items()
            ]
            
            # Sort by job_id for consistent ordering
            jobs.sort(key=lambda x: x.job_id)
            
            return AllJobIdsResponse(
                message=f"Retrieved {len(jobs)} unique job IDs with players and creation times successfully.",
                jobs=jobs
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving job IDs: {str(e)}"
            )

@router.get(
    "/job/{job_id}/games",
    summary="Retrieve all game IDs related to a specific job",
    response_model=JobGamesResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ErrorResponse},
               403: {"model": ErrorResponse}},
)
def get_job_games(job_id: str):
    """
    Fetches all game IDs that are related to a specific job.
    """
    with Session(engine) as session:
        # Optimized: Use database-side sorting and only select needed fields
        # Also combine the public check in the same query
        game_logs = session.exec(
            select(GameLog.id, GameLog.game_uuid, GameLog.is_public)
            .where(GameLog.job_id == job_id)
            .order_by(cast(GameLog.game_uuid, Integer))
        ).all()
        
        if not game_logs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No games found for job ID '{job_id}'."
            )
        
        # Check if all games are public (optimized)
        all_public = all(log.is_public for log in game_logs)
        if not all_public:
            raise HTTPException(status_code=403, detail="This job is private and cannot be accessed.")
        
        # Extract game info (id and game_uuid)
        games = [
            JobGameInfo(
                game_id=str(game_log.id),
                game_uuid=game_log.game_uuid or ""
            )
            for game_log in game_logs
        ]
        
        return JobGamesResponse(
            message=f"Found {len(games)} games for job {job_id}.",
            job_id=job_id,
            games=games
        )

@router.get(
    "/job/{job_id}/games/paginated",
    summary="Retrieve paginated game IDs related to a specific job",
    response_model=PaginatedJobGamesResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ErrorResponse},
               403: {"model": ErrorResponse}},
)
def get_job_games_paginated(
    job_id: str,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(100, ge=1, le=1000, description="Number of games per page")
):
    """
    Fetches paginated game IDs that are related to a specific job.
    Use this endpoint for jobs with many games (500+) to avoid memory issues.
    """
    with Session(engine) as session:
        # Get total count first
        total_count = session.exec(
            select(func.count(GameLog.id))
            .where(GameLog.job_id == job_id)
        ).one()
        
        if total_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No games found for job ID '{job_id}'."
            )
        
        # Check if all games are public (using a sample)
        sample_logs = session.exec(
            select(GameLog.is_public)
            .where(GameLog.job_id == job_id)
            .limit(10)
        ).all()
        
        if not all(sample_logs):
            raise HTTPException(status_code=403, detail="This job is private and cannot be accessed.")
        
        # Calculate pagination
        offset = (page - 1) * page_size
        has_next = offset + page_size < total_count
        has_previous = page > 1
        
        # Get paginated game logs
        game_logs = session.exec(
            select(GameLog.id, GameLog.game_uuid)
            .where(GameLog.job_id == job_id)
            .order_by(cast(GameLog.game_uuid, Integer))
            .offset(offset)
            .limit(page_size)
        ).all()
        
        # Extract game info
        games = [
            JobGameInfo(
                game_id=str(game_log.id),
                game_uuid=game_log.game_uuid or ""
            )
            for game_log in game_logs
        ]
        
        return PaginatedJobGamesResponse(
            message=f"Found {len(games)} games for job {job_id} (page {page} of {(total_count + page_size - 1) // page_size}).",
            job_id=job_id,
            games=games,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous
        )

@router.get(
    "/games",
    summary="Retrieve all game IDs and their players",
    response_model=AllGamesResponse,
    status_code=status.HTTP_200_OK,
    responses={500: {"model": ErrorResponse}},
)
def get_all_games():
    """
    Fetches all games from the database and returns their IDs and players.
    """
    with Session(engine) as session:
        try:
            # Get all game logs
            game_logs = session.exec(select(GameLog)).all()
            
            games_summary = []
            for game_log in game_logs:
                game_data = game_log.game_data
                
                # Extract players from game data
                players = []
                if "playerIdToUsername" in game_data:
                    # Get usernames from playerIdToUsername mapping
                    if isinstance(game_data["playerIdToUsername"], dict):
                        players = list(game_data["playerIdToUsername"].values())
                
                games_summary.append(GameSummaryResponse(
                    game_id=str(game_log.id),
                    game_uuid=game_log.game_uuid or "",
                    job_id=game_log.job_id or "",
                    players=players
                ))
            
            return AllGamesResponse(
                message=f"Retrieved {len(games_summary)} games successfully.",
                games=games_summary
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving games: {str(e)}"
            )

@router.get(
    "/game/{game_id}",
    summary="Retrieve game data by game ID",
    response_model=GameDataResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"model": ErrorResponse},
               403: {"model": ErrorResponse}},
)
def get_game_data(game_id: str):
    """
    Fetches game data from the database using the game ID (UUID).
    """
    with Session(engine) as session:
        # Find by id (UUID) only
        game_log_record = session.exec(select(GameLog).where(GameLog.id == game_id)).first()

        if not game_log_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game with ID '{game_id}' not found."
            )

        if not game_log_record.is_public:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This game is private and cannot be accessed."
            )
        
        return GameDataResponse(
            message="Game data retrieved successfully.",
            game_id=str(game_log_record.id),
            game_uuid=game_log_record.game_uuid or "",
            job_id=game_log_record.job_id or "",
            game_data=game_log_record.game_data
        )

@router.get(
    "/public-job-ids",
    summary="Retrieve all public job IDs (all logs are public) with players and creation time",
    response_model=AllJobIdsResponse,
    status_code=status.HTTP_200_OK
)
def get_public_job_ids():
    """
    Returns all job IDs where every log is public,
    including players and first_game_created_at (same format as /job-ids).
    """
    with Session(engine) as session:
        try:
            # Get job IDs where all logs are public
            rows = session.exec(
                select(
                    GameLog.job_id,
                    func.min(GameLog.created_at).label("first_game_created_at")
                )
                .where(GameLog.job_id != None)
                .group_by(GameLog.job_id)
                .having(func.bool_and(GameLog.is_public))  # Only jobs where all logs are public
            ).all()

            if not rows:
                return AllJobIdsResponse(message="No public jobs found", jobs=[])

            jobs = []
            for job_id, first_game_created_at in rows:
                # Get one log for this job to extract players
                log = session.exec(
                    select(GameLog).where(GameLog.job_id == job_id).limit(1)
                ).first()

                players = []
                if log and "playerIdToUsername" in log.game_data and isinstance(log.game_data["playerIdToUsername"], dict):
                    players = list(log.game_data["playerIdToUsername"].values())

                jobs.append(JobIdWithPlayers(
                    job_id=job_id,
                    players=players,
                    first_game_created_at=first_game_created_at,
                    is_public=True 
                ))

            return AllJobIdsResponse(
                message=f"Retrieved {len(jobs)} public jobs successfully",
                jobs=jobs
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving public jobs: {str(e)}")

@router.get(
    "/job/{job_id}/user-performance",
    summary="Get user performance (finalDelta) for each game in a job, sorted by game_uuid",
    response_model=Dict[str, List[int]],
    status_code=status.HTTP_200_OK,
    responses={403: {"model": ErrorResponse}}
)
def get_user_performance_for_job(job_id: str):
    """
    For a given job_id, return a mapping of each user to a list of their finalDelta values (one per game, sorted by game_uuid).
    Output: {user: [finalDelta, ...]}
    """
    with Session(engine) as session:
        # Optimized: Use database-side sorting and only select needed fields
        # Also combine the public check in the same query
        game_logs = session.exec(
            select(GameLog.game_uuid, GameLog.game_data, GameLog.is_public)
            .where(GameLog.job_id == job_id)
            .order_by(cast(GameLog.game_uuid, Integer))
        ).all()
        
        if not game_logs:
            raise HTTPException(status_code=404, detail=f"No games found for job ID '{job_id}'.")
        
        # Check if all games are public (optimized)
        all_public = all(log.is_public for log in game_logs)
        if not all_public:
            raise HTTPException(status_code=403, detail="This job is private and cannot be accessed.")
        
        # Build user -> [finalDelta, ...] map
        user_performance = {}
        for log in game_logs:
            game_data = log.game_data
            # Get playerIdToUsername and finalDelta
            player_id_to_username = game_data.get("playerIdToUsername", {})
            final_delta = game_data.get("playerMoney", {}).get("finalDelta", {})
            for player_id, username in player_id_to_username.items():
                delta = final_delta.get(player_id)
                if username not in user_performance:
                    user_performance[username] = []
                user_performance[username].append(delta)
        return user_performance