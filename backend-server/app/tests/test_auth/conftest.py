import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.service.db.postgres import engine
from app.api.routes.auth import create_access_token
from sqlmodel import Session
from passlib.hash import bcrypt
from app.service.db.utils import delete_username, delete_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture
def test_user():
    delete_username("testuser")
    user = User(
        username="testuser",
        password=bcrypt.hash("testpass"),
        email="test@example.com",
        name="Test User",
        admin=False,
        github=None,
        discord_username=None,
        about=None,
    )
    with Session(engine) as db:
        db.add(user)
        db.commit()
    return user

@pytest.fixture
def access_token(test_user):
    token = create_access_token(test_user.username)
    with Session(engine) as db:
        db.add(token)
        db.commit()
    return token.id

@pytest.fixture
def auth_header(client, test_user):
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    token_id = response.json()["access_token"]

    yield {"Authorization": f"Bearer {token_id}"}

    # This block runs after the test finishes
    delete_token(token_id)

