from datetime import datetime, timedelta

from app.models.user import AccessToken, User
from app.service.db.utils import delete_username
from sqlmodel import Session
from app.service.db.postgres import engine
from passlib.hash import bcrypt
from sqlalchemy import text

def test_whoami_success(client, auth_header):
    response = client.get("/auth/whoami", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"
    delete_username("testuser")

def test_whoami_invalid_token(client):
    response = client.get("/auth/whoami", headers={"Authorization": "Bearer fake-token-id"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"

def test_whoami_expired_token(client, test_user):
    expired_token = AccessToken(
        id="expired-token",
        username="testuser",
        exp=datetime.utcnow() - timedelta(hours=1)  # expired
    )
    with Session(engine) as db:
        db.add(expired_token)
        db.commit()

    response = client.get("/auth/whoami", headers={"Authorization": "Bearer expired-token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"
    delete_username("testuser")