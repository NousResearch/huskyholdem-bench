import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select, func
from app.api.routes.auth import ErrorResponse
from app.middleware.auth import require_user, require_admin
from app.models.submission import Submission
from app.models.user import User
from app.service.db.supabase import SupabaseBucketService
import uuid
from dotenv import load_dotenv

from app.service.db.postgres import engine
from app.service.docker.main import DockerService
from app.config.setting import settings
from app.utils.file import check_input_stat, clone_bytes, create_tar_from_files, extract_file_from_tar

load_dotenv()

router = APIRouter(prefix="/submission", tags=["upload"])

SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

bucket_service = SupabaseBucketService(SUPABASE_BUCKET)  # Your Supabase bucket name

# ──────────────────────────────────────────────────────────────────────────────
# Pydantic schemas for docs / responses
# ──────────────────────────────────────────────────────────────────────────────

class MarkSubmissionRequest(BaseModel):
    submission_id: str

# ──────────────────────────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────────────────────────
@router.post("/upload")
async def upload_file(
    python_file: UploadFile = File(...),
    packages_file: UploadFile = File(...),
    user : User = Depends(require_user),
):
    # Filename checks (reuse same logic as /async_run) ------------------------
    if python_file.filename != "player.py":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Python file must be named player.py",
        )

    if packages_file.filename != "requirements.txt":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Packages file must be named requirements.txt",
        )
    
    # Check if user past the limit of 5 files in our db
    with Session(engine) as session:
        submission_count = session.exec(select(func.count()).where(Submission.username == user.username)).one()
        if submission_count >= 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have reached the limit of 5 submissions, please delete one to upload a new one",
            )
        

    # Run dry run of the file to check for errors ------------------------
    docker_service = DockerService()
    submission_id = uuid.uuid4()
    container_name = f"client_test_{submission_id}"

    docker_service.client.containers.run(
        image=settings.RUNNER_IMAGE,
        name=container_name,
        detach=True,
        mem_limit="100m",
    )

    tarstream = create_tar_from_files(
        {"player.py": python_file, "requirements.txt": packages_file}
    )

    # create a clone to use later
    tarstream_clone = clone_bytes(tarstream)

    docker_service.client.containers.get(container_name).put_archive("/app", tarstream)

    ok, err = check_input_stat(docker_service, container_name)

    if not ok:
        return ErrorResponse(error=err, status_code=status.HTTP_400_BAD_REQUEST)
    

    docker_service.stop_and_remove_container(container_name)
    
    # Upload files to Supabase --------------------------------------------
    python_file_ext = python_file.filename.split(".")[-1]
    packages_file_ext = packages_file.filename.split(".")[-1]

    dest_name = f"{uuid.uuid4()}.{python_file_ext}"
    dest_name2 = f"{uuid.uuid4()}.{packages_file_ext}"

    # untar the files to get the content
    files = extract_file_from_tar(tarstream_clone)

    python_file_bytes = files["player.py"]
    packages_file_bytes = files["requirements.txt"]

    try:
        bucket_service.upload_file_from_bytes(
            data=python_file_bytes,
            dest_name=dest_name,
            content_type=python_file.content_type,
        )

        bucket_service.upload_file_from_bytes(
            data=packages_file_bytes,
            dest_name=dest_name2,
            content_type=packages_file.content_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Save submission to DB --------------------------------------------
    with Session(engine) as session:
        submission = Submission(
            id=str(submission_id),
            username=user.username,
            player_file=dest_name,
            package_file=dest_name2,
        )
        session.add(submission)
        session.commit()
        session.refresh(submission)
        session.close()

    return {
        "submission_id": str(submission_id),
        "message": "Uploaded files successfully",
        "python_file": python_file.filename,
        "stored_as": f"{dest_name}",
        "packages_file": packages_file.filename,
        "stored_as2": f"{dest_name2}",
        "status_code": 200,
    }

@router.get("/list")
async def list_files(user = Depends(require_user)):
    try:
        with Session(engine) as session:
            results = session.exec(select(Submission).where(Submission.username == user.username)).all()
            if not results:
                return {
                    "message": "No files found",
                    "files": [],
                }
            files = [{"id": result.id, "player_file": result.player_file, "package_file": result.package_file, "final": result.final, "created_at": result.created_at} for result in results]
            return {
                "message": "Files found",
                "files": files,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/{submission_id}")
async def delete_file(submission_id: str, user = Depends(require_user)):
    with Session(engine) as session:
        # Check if submission exists and belongs to the user

        submission = session.exec(select(Submission).where(Submission.id == submission_id)).first()
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        if submission.username != user.username:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to delete this file")
            
        try:
            # delete the files from supabase
            bucket_service.delete_file(submission.player_file)
            bucket_service.delete_file(submission.package_file)

            # delete the submission from the db
            session.delete(submission)
            session.commit()
            session.close()
            return {
                "message": "File deleted successfully",
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/admin/delete/{submission_id}")
async def delete_file(submission_id: str, user = Depends(require_admin)):
    with Session(engine) as session:
        submission = session.exec(select(Submission).where(Submission.id == submission_id)).first()
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        
        try:
            # delete the files from supabase
            bucket_service.delete_file(submission.player_file)
            bucket_service.delete_file(submission.package_file)

            # delete the submission from the db
            session.delete(submission)
            session.commit()
            session.close()
            return {
                "message": "File deleted successfully",
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/all")
async def get_all_submissions(user = Depends(require_admin)):
    try:
        with Session(engine) as session:
            submissions = session.exec(select(Submission)).all()
            if not submissions:
                return {
                    "message": "No files found",
                    "files": [],
                }
            submission_list = []
            for sub in submissions:
                submission = {
                    "id": sub.id,
                    "username": sub.username,
                    "created_at": sub.created_at.isoformat(),
                    "player_file": sub.player_file,
                    "package_file": sub.package_file
                }
                submission_list.append(submission)
            return {
                "message": "All submissions retrieved successfully",
                "submissions": submission_list,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/with-final")
async def get_users_with_final_submission(user=Depends(require_admin)):
    try:
        with Session(engine) as session:
            statement = (
                select(Submission.username)
                .where(Submission.final == True)
                .group_by(Submission.username) # just incase multiple final sub
            )

            results = session.exec(statement).all()

        return {
            "message": "Users with final submission retrieved successfully",
            "users_list": results,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/files/{file_name}")
async def download_file(file_name: str):
    try:
        file_data = bucket_service.download_file(file_name)
        return {
            "file_name": file_name,
            "file_data": file_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/unmark_final")
async def unmark_final(data: MarkSubmissionRequest, user = Depends(require_user)):
    submission_id = data.submission_id

    
    with Session(engine) as session:
        submission = session.exec(select(Submission).where(Submission.id == submission_id)).first()
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        
        if submission.username != user.username:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to unmark this file as final")
        
        if not submission.final:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is not marked as final")
        
        try:
            # unmark the submission as final
            submission.final = False
            session.commit()
            session.refresh(submission)
            session.close()
            return {
                "message": "File unmarked as final successfully",
                "status_code": status.HTTP_200_OK,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/mark_final")
async def mark_final(data: MarkSubmissionRequest, user = Depends(require_user)):
    # check if user had already marked a file as final
    submission_id = data.submission_id
    with Session(engine) as session:
        results = session.exec(select(Submission).where(Submission.username == user.username, Submission.final == True)).all()
        if len(results) >= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already marked a file as final")

    with Session(engine) as session:
        submission = session.exec(select(Submission).where(Submission.id == submission_id)).first()
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
        
        if submission.username != user.username:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to mark this file as final")
        
        if submission.final:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File is already marked as final")
        
        try:    
            # mark the submission as final
            submission.final = True
            session.commit()
            session.refresh(submission)
            session.close()
            return {
                "message": "File marked as final successfully",
                "status_code": status.HTTP_200_OK,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))