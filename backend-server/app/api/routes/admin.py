from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func, update
from app.models.user import User
from app.models.submission import Submission
from app.models.leaderboard import LeaderBoard
from app.models.job import Job, JobType
from app.models.game import GameLog
from app.middleware.auth import require_admin
from app.service.db.postgres import engine
from app.config.setting import settings
import json

router = APIRouter(prefix="/admin", tags=["admin"])

def get_session():
    with Session(engine) as session:
        yield session

@router.get("/user-count")
def get_user_count(user: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"user_count": session.exec(select(func.count()).select_from(User)).one()}

@router.get("/job-count")
def get_job_count(user: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"job_count": session.exec(select(func.count()).select_from(Job)).one()}

@router.get("/submission-count")
def get_submission_count(user: User = Depends(require_admin), session: Session = Depends(get_session)):
    return {"submission_count": session.exec(select(func.count()).select_from(Submission)).one()}

@router.get("/users")
def get_users(user: User = Depends(require_admin), session: Session = Depends(get_session)):
    return session.exec(select(User)).all()

@router.get("/jobs")
def get_jobs(user: User = Depends(require_admin), session: Session = Depends(get_session)):
    return session.exec(select(Job)).all()

@router.post("/toggle-admin/{target_username}")
def toggle_admin(target_username: str, user: User = Depends(require_admin), session: Session = Depends(get_session)):
    if target_username == user.username:
        raise HTTPException(status_code=400, detail="You cannot change your own admin status.")

    target_user = session.exec(select(User).where(User.username == target_username)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.admin = not target_user.admin
    session.add(target_user)
    session.commit()
    session.refresh(target_user)
    return {"username": target_user.username, "admin": target_user.admin}

@router.post("/verify-user/{target_username}")
def verify_user(target_username: str, user: User = Depends(require_admin), session: Session = Depends(get_session)):
    target_user = session.exec(select(User).where(User.username == target_username)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    target_user.is_verified = not target_user.is_verified
    session.add(target_user)
    session.commit()
    session.refresh(target_user)
    return {"username": target_user.username, "is_verified": target_user.is_verified}

@router.delete("/user/{target_username}")
def delete_user(target_username: str, user: User = Depends(require_admin), session: Session = Depends(get_session)):
    if target_username == user.username:
        raise HTTPException(status_code=400, detail="You cannot delete your own account.")

    target_user = session.exec(select(User).where(User.username == target_username)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete all jobs associated with the user first
    user_jobs = session.exec(select(Job).where(Job.username == target_username)).all()
    for job in user_jobs:
        session.delete(job)
    
    # Delete all leaderboard entries associated with the user
    user_leaderboard_entries = session.exec(select(LeaderBoard).where(LeaderBoard.username == target_username)).all()
    for entry in user_leaderboard_entries:
        session.delete(entry)
    
    # Delete the user
    session.delete(target_user)
    session.commit()
    return {"message": f"User '{target_username}', {len(user_jobs)} associated jobs, and {len(user_leaderboard_entries)} leaderboard entries have been successfully deleted"}

@router.get("/scaling-jobs")
def get_scaling_jobs(user: User = Depends(require_admin), session: Session = Depends(get_session)):
    res = session.exec(
        select(Job).where(Job.tag == JobType.SCALING)
    ).all()
    
    return res if res else []

@router.get("/sim-admin-jobs")
def get_sim_admin_jobs(user: User = Depends(require_admin), session: Session = Depends(get_session)):
    res = session.exec(
        select(Job).where(
            (Job.tag == JobType.SIM_ADMIN)
        )
    ).all()
    
    return res if res else [] 

@router.post("/toggle-job-public/{job_id}")
def toggle_job_public(
    job_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Toggle job public status.
    """
    # Check if job exists
    job_exists = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job_exists:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Get current public status by checking first log for this job
    first_log = session.exec(
        select(GameLog).where(GameLog.job_id == job_id)
    ).first()
    if not first_log:
        raise HTTPException(status_code=404, detail=f"No logs found for job '{job_id}'")

    # Flip status
    new_status = not first_log.is_public

    # Bulk update all logs
    session.exec(
        update(GameLog)
        .where(GameLog.job_id == job_id)
        .values(is_public=new_status)
    )
    session.commit()

    # Count logs affected
    log_count = session.exec(
        select(func.count()).select_from(GameLog).where(GameLog.job_id == job_id)
    ).one()

    return {
        "message": f"Toggled job '{job_id}' to {'PUBLIC' if new_status else 'PRIVATE'}",
        "job_id": job_id,
        "is_public": new_status,
        "affected_logs": log_count
    }

@router.get("/2025-job-status/{job_id}")
def get_2025_added(job_id: str, user: User = Depends(require_admin), session: Session = Depends(get_session)):
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return  {
        "job_id": job_id,
        "tournaments_2025_added": job.tournaments_2025_added
    }

@router.post("/process-tournament-2025-job/{job_id}")
def process_tournament_2025_job(
    job_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # Fetch job
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.tag != JobType.SIM_ADMIN:
        raise HTTPException(status_code=400, detail="Job is not SIM_ADMIN")
    if job.tournaments_2025_added:
        raise HTTPException(status_code=400, detail="Job already processed for tournament 2025")
    if not job.result_data:
        raise HTTPException(status_code=400, detail="Job result_data is empty")

    try:
        result = json.loads(job.result_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid result_data format: {e}")

    updated = []
    created = []
    for username, score in result.items():
        # Check user exists
        user_obj = session.exec(select(User).where(User.username == username)).first()
        if not user_obj:
            continue  # skip unknown users
        # Check for existing leaderboard entry for this user/tag
        entry = session.exec(
            select(LeaderBoard).where(
                (LeaderBoard.username == username) & (LeaderBoard.tag == settings.TOURNAMENT_2025_TAG)
            )
        ).first()
        if entry:
            entry.score += score
            session.add(entry)
            updated.append(username)
        else:
            new_entry = LeaderBoard(
                username=username,
                score=score,
                tag=settings.TOURNAMENT_2025_TAG
            )
            session.add(new_entry)
            created.append(username)
    # Mark job as processed
    job.tournaments_2025_added = True
    session.add(job)
    session.commit()
    return {
        "message": "Processed tournament 2025 leaderboard for job.",
        "job_id": job_id,
        "updated": updated,
        "created": created
    }

@router.post("/delete-tournament-2025-job/{job_id}")
def delete_tournament_2025_job(
    job_id: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    # Fetch job
    job = session.exec(select(Job).where(Job.id == job_id)).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.tag != JobType.SIM_ADMIN:
        raise HTTPException(status_code=400, detail="Job is not SIM_ADMIN")
    if not job.tournaments_2025_added:
        raise HTTPException(status_code=400, detail="Job has not been processed for tournament 2025 (cannot remove)")
    if not job.result_data:
        raise HTTPException(status_code=400, detail="Job result_data is empty")

    try:
        result = json.loads(job.result_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid result_data format: {e}")

    updated = []
    skipped = []
    for username, score in result.items():
        # Check user exists
        user_obj = session.exec(select(User).where(User.username == username)).first()
        if not user_obj:
            skipped.append(username)
            continue  # skip unknown users
        # Check for existing leaderboard entry for this user/tag
        entry = session.exec(
            select(LeaderBoard).where(
                (LeaderBoard.username == username) & (LeaderBoard.tag == settings.TOURNAMENT_2025_TAG)
            )
        ).first()
        if entry:
            entry.score -= score
            session.add(entry)
            updated.append(username)
        else:
            skipped.append(username)
    # After successful removal, set job.tournaments_2025_added to False
    job.tournaments_2025_added = False
    session.add(job)
    session.commit()
    return {
        "message": "Removed tournament 2025 leaderboard scores for job and marked job as not added.",
        "job_id": job_id,
        "updated": updated,
        "skipped": skipped
    }

@router.get("/user-final-submission/{username}")
def get_user_final_submission(
    username: str,
    user: User = Depends(require_admin),
    session: Session = Depends(get_session)
):
    """
    Check if a user has a final submission and return the file information.
    """
    # Check if user exists
    target_user = session.exec(select(User).where(User.username == username)).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get the final submission for the user
    final_submission = session.exec(
        select(Submission).where(
            Submission.username == username,
            Submission.final == True
        )
    ).first()

    if not final_submission:
        return {
            "username": username,
            "has_final_submission": False,
            "message": f"User '{username}' does not have a final submission"
        }

    return {
        "username": username,
        "has_final_submission": True,
        "submission_id": final_submission.id,
        "player_file": final_submission.player_file,
        "package_file": final_submission.package_file,
        "created_at": final_submission.created_at.isoformat(),
        "message": f"User '{username}' has a final submission"
    }
