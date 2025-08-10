import datetime
from itertools import combinations
import io
import os
from types import SimpleNamespace
from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlmodel import Session

from app.api.routes.admin import get_session
from app.middleware.auth import require_admin
from app.models.batch_llm import BatchLLMQueue
from app.models.game import GameLog
from app.models.job import Job, JobStatus, JobType
from app.models.submission import Submission
from app.models.user import User
from app.service.cache.redis import RedisService
from app.service.db.postgres import engine
from app.service.db.supabase import SupabaseBucketService
from app.utils.file import create_tar_from_files

# Get supabase bucket
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")
bucket_service = SupabaseBucketService(SUPABASE_BUCKET)  # Your Supabase bucket name

router = APIRouter(prefix="/llm", tags=["llm"])

@router.post("/batch-run")
async def batch_run(
    user_ids: List[str],
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # if there is less than 6 users, return an error
    if len(user_ids) < 6:
        raise HTTPException(status_code=400, detail="There must be at least 6 users to run a batch")
    
    print(f"DEBUG - Batch run requested for users: {user_ids}")

    # check if users are valid and have final submissions
    for user_id in user_ids:
        temp_user = session.exec(select(User).where(User.username == user_id)).first()
        if not temp_user:
            raise HTTPException(status_code=404, detail=f"User with id {user_id} not found")
        
        # Check if user has a final submission (same validation as async_run_user_simulation)
        temp_sub = session.exec(select(Submission).where(Submission.username == user_id, Submission.final == True)).first()
        if not temp_sub:
            raise HTTPException(status_code=404, detail=f"Final submission for user {user_id} not found")

    # Generate all possible combinations of 6 users from the provided user_ids
    user_combinations = list(combinations(user_ids, 6))
    
    # save each user's final submission as cache in redis
    users_file = {} # store users -> tarstream
    for username in user_ids:
        #  Get file path
        python_file_path = session.exec(select(Submission.player_file).
                        where(Submission.username == username, Submission.final == True)).first()
        packages_file_path = session.exec(select(Submission.package_file).
            where(Submission.username == username, Submission.final == True)).first()
        
        if not python_file_path or not packages_file_path:
            raise HTTPException(status_code=404, detail=f"Final submission for user {username} not found")

        try:
            python_file_bytes = bucket_service.download_file(python_file_path[0])
            packages_file_bytes = bucket_service.download_file(packages_file_path[0])
        except Exception as e:
            print(f"DEBUG - Download failed for user {username}: {e}")
            raise HTTPException(status_code=500, detail=f"Download failed for user {username}: {e}") from e
        
        # Create in-memory files using BytesIO
        python_file_io = io.BytesIO(python_file_bytes)
        packages_file_io = io.BytesIO(packages_file_bytes)
        
        # Create tarstream using in-memory files
        tarstream = create_tar_from_files({
            "player.py": SimpleNamespace(file=python_file_io),
            "requirements.txt": SimpleNamespace(file=packages_file_io)
        })

        # store user -> tarstream bytes in the dict
        users_file[username] = tarstream.getvalue()

    # save each user's final submission as cache in redis
    redis_service = RedisService()
    redis_service.flush_all_tarstreams()
    for username, tarstream_bytes in users_file.items():
        redis_service.store_tarstream(username, tarstream_bytes)


    # create a batch job
    batch_id = str(uuid.uuid4())
    for user_combination in user_combinations:
        # create according job to store in the database
        job = Job(
            status=JobStatus.PENDING,
            tag=JobType.LLM_BATCH_RUN,
            id=str(uuid.uuid4()),
            username=admin_user.username,
            error_message=None,
            result_data=None,
        )
        session.add(job)

        # create a batch job
        batch_job = BatchLLMQueue(
            users_to_run=user_combination,
            batch_id=batch_id,
            worker_id=None,
            last_updated=None,
            job_id=job.id,
            job=job
        )
        session.add(batch_job)

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create batch jobs: {e}") from e

    return {"message": f"Batch job created with {len(user_combinations)} combinations"}

@router.delete("/batch/{batch_id}")
async def delete_batch(
    batch_id: str,
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Delete a batch and all related jobs and game logs.
    
    Args:
        batch_id: The batch_id to delete
    
    Returns:
        Summary of deleted items
    """
    print(f"DEBUG - Attempting to delete batch: {batch_id}")
    
    try:
        # Find all BatchLLMQueue entries with this batch_id
        batch_entries = session.exec(
            select(BatchLLMQueue).where(BatchLLMQueue.batch_id == batch_id)
        ).all()
        
        print(f"DEBUG - Found {len(batch_entries)} batch entries")
        
        if not batch_entries:
            raise HTTPException(status_code=404, detail=f"Batch with id {batch_id} not found")
        
        deleted_jobs = []
        deleted_game_logs = []
        deleted_batch_entries : List[BatchLLMQueue] = []
        
        # For each batch entry, delete related data in proper order
        for container in batch_entries:
            batch_entry = container[0]
            print(f"DEBUG - batch_entry: {batch_entry}")
            print(f"DEBUG - Processing batch entry: {batch_entry.id}, job_id: {batch_entry.job_id}")
            
            if batch_entry.job_id:
                try:
                    # Find all game logs for this job
                    game_logs = session.exec(
                        select(GameLog).where(GameLog.job_id == batch_entry.job_id)
                    ).all()
                    
                    print(f"DEBUG - Found {len(game_logs)} game logs for job {batch_entry.job_id}")
                    
                    # Delete game logs first (they reference jobs)
                    for game_log_container in game_logs:
                        game_log = game_log_container[0]
                        print(f"DEBUG - Deleting game log: {game_log.id}")
                        deleted_game_logs.append(str(game_log.id))
                        session.delete(game_log)
                    
                    # Then delete the job
                    job_container = session.exec(select(Job).where(Job.id == batch_entry.job_id)).first()
                    if job_container:
                        job = job_container[0]
                        print(f"DEBUG - Deleting job: {job.id}")
                        deleted_jobs.append(job.id)
                        session.delete(job)
                    else:
                        print(f"DEBUG - Job {batch_entry.job_id} not found")
                        
                except Exception as job_error:
                    print(f"DEBUG - Error processing job {batch_entry.job_id}: {job_error}")
                    raise
            
            # Finally delete the batch entry
            print(f"DEBUG - Deleting batch entry: {batch_entry.id}")
            deleted_batch_entries.append(batch_entry.id)
            session.delete(batch_entry)
        
        # Commit all deletions
        print(f"DEBUG - Committing deletions...")
        session.commit()
        print(f"DEBUG - Successfully committed deletions")
        
        return {
            "message": f"Successfully deleted batch {batch_id}",
            "deleted_batch_entries": len(deleted_batch_entries),
            "deleted_jobs": len(deleted_jobs),
            "deleted_game_logs": len(deleted_game_logs),
            "batch_entry_ids": deleted_batch_entries,
            "job_ids": deleted_jobs,
            "game_log_ids": deleted_game_logs
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        print(f"DEBUG - HTTPException occurred")
        raise
    except Exception as e:
        print(f"DEBUG - Exception occurred: {e}")
        print(f"DEBUG - Exception type: {type(e)}")
        import traceback
        print(f"DEBUG - Traceback: {traceback.format_exc()}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete batch: {str(e)}") from e

@router.get("/batches")
async def list_batches(
    admin_user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    List all batch jobs with their status and related information.
    
    Returns:
        List of all batches with job counts and status
    """
    try:
        # Get all batch entries with job information
        batch_entries = session.exec(
            select(BatchLLMQueue, Job)
            .join(Job, BatchLLMQueue.job_id == Job.id, isouter=True)
        ).all()
        
        # Group by batch_id
        batches = {}
        for batch_entry, job in batch_entries:
            batch_id = batch_entry.batch_id
            if batch_id not in batches:
                batches[batch_id] = {
                    "batch_id": batch_id,
                    "created_at": batch_entry.created_at.isoformat() if batch_entry.created_at else None,
                    "jobs": [],
                    "total_jobs": 0,
                    "job_statuses": {"PENDING": 0, "RUNNING": 0, "FINISHED": 0, "FAILED": 0}
                }
            
            if job:
                batches[batch_id]["jobs"].append({
                    "job_id": job.id,
                    "status": job.status,
                    "username": job.username,
                    "users_to_run": batch_entry.users_to_run
                })
                batches[batch_id]["total_jobs"] += 1
                batches[batch_id]["job_statuses"][job.status.upper()] = batches[batch_id]["job_statuses"].get(job.status.upper(), 0) + 1
        
        return {
            "message": f"Found {len(batches)} batches",
            "batches": list(batches.values())
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list batches: {e}") from e
