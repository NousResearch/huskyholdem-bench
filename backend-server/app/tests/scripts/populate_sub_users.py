from pathlib import Path
import requests
import time
from sqlmodel import Session, select
from app.service.db.postgres import engine
from app.models.submission import Submission
from app.models.user import User
from app.service.db.utils import delete_username
from passlib.hash import bcrypt

# Import all models to ensure SQLAlchemy can resolve relationships
import app.models

"""
    Execute w/ command: docker compose exec server python app/tests/scripts/populate_sub_users.py
"""

BASE_URL = "http://localhost:8002"
users_list = ["testuser1", "testuser2", "testuser3", "testuser4", "testuser5", "testuser6"] # body for /sim/async_run_user
users_pass = users = {
    "testuser1": "password483",
    "testuser2": "password927",
    "testuser3": "password312",
    "testuser4": "password740",
    "testuser5": "password658",
    "testuser6": "password194"
}

def get_submission_id(username: str) -> str | None:
    with Session(engine) as session:
        row = session.exec(
            select(Submission.id).where(Submission.username == username)
        ).first()
        return str(row) if row else None
    
def delete_submission(token: str, submission_id: str):
    response = requests.delete(
        f"{BASE_URL}/submission/{submission_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    return response.json()

def register_user_db(username: str, password: str, email: str):
    """Register user directly in database to avoid email verification issues during testing"""
    with Session(engine) as db:
        # Check if user already exists
        existing_user = db.exec(select(User).where(User.username == username)).first()
        if existing_user:
            print(f"User {username} already exists, skipping creation")
            return
        
        # Create new user directly in database
        user = User(
            username=username,
            password=bcrypt.hash(password),
            email=email,
            admin=False,
            is_verified=True,  # Set to True for testing to skip email verification
            name=username,
            github=None,
            discord_username=None,
            about=None,
        )
        db.add(user)
        db.commit()
        print(f"User {username} created directly in database")

def login_user(username: str, password: str):
    response = requests.post(f"{BASE_URL}/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]

def submit_file(token: str, python_path: str, reqs_path: str):
    base_dir = Path(__file__).resolve().parent
    python_path = (base_dir.parent / "data" / "player.py").resolve()
    reqs_path   = (base_dir.parent / "data" / "requirements.txt").resolve()
    
    with open(python_path, "rb") as py_file, open(reqs_path, "rb") as req_file:
        response = requests.post(
            f"{BASE_URL}/submission/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "python_file": ("player.py",  py_file,  "text/x-python"),
                "packages_file": ("requirements.txt", req_file, "text/plain")
            }
        )

    assert response.status_code == 200
    return response.json()

def file_mark_final(token: str, submission_id: str):
    response = requests.post(
        f"{BASE_URL}/submission/mark_final",
        headers={"Authorization": f"Bearer {token}"},
        json={"submission_id": submission_id}
    )

    assert response.status_code == 200
    return response.json()

def main():
    for user in users_list:
        # Clean up: delete submission & user
        print(f"Deleting submission and user for {user} if exist")
        sub_id = get_submission_id(user)
        if sub_id:
            tmp_token = login_user(user, users_pass[user])
            delete_submission(tmp_token, sub_id)
        
        delete_username(user)
        
        # Create and login users, and populate with final submissions
        register_user_db(user, users_pass[user], f"{user}@uw.edu")
        tmp_token = login_user(user, users_pass[user])
        print (f"Uploading submission for user {user} and marking submission as final")
        sub_response = submit_file(tmp_token, "../data/player.py", "../data/requirements.txt")
        file_mark_final(tmp_token, sub_response["submission_id"]) 
        print (f"Done marking submission as final for user {user}")

    time.sleep(5)
    print("Populate submission users done")
if __name__ == "__main__":
    main()