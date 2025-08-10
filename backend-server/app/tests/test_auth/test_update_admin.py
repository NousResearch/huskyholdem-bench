from passlib.hash import bcrypt
from app.api.routes.auth import create_access_token
from app.models.user import User
from app.service.db.utils import delete_username, delete_token
from sqlmodel import Session, select
from app.service.db.postgres import engine

def test_make_admin(client, test_user: User):
    with Session(engine) as db:
        user = db.exec(select(User).where(User.username == "testuser")).first()
        user.admin = True
        db.commit()

    token = create_access_token("testuser")
    token_id = token.id  # Get the ID before the session closes
    with Session(engine) as db:
        db.add(token)
        db.commit()

    client.post("/auth/register", json={
        "username": "second",
        "password": "newpass123",
        "email": "new@example.com",
        "name": "Second User"
    })

    headers = {"Authorization": f"Bearer {token_id}"}
    response = client.post("/auth/update-admin", headers=headers, json={
        "username": "second",
        "admin": True
    })
    assert response.status_code == 200

    with Session(engine) as db:
        updated = db.exec(select(User).where(User.username == "second")).first()
        assert updated.admin is True

    delete_username("testuser")
    delete_token(token_id)
    delete_username("second")

def test_revoke_admin(client, test_user: User):
    with Session(engine) as db:
        user = db.exec(select(User).where(User.username == "testuser")).first()
        user.admin = True
        db.commit()

    token = create_access_token("testuser")
    token_id = token.id  # Get the ID before the session closes
    with Session(engine) as db:
        db.add(token)
        db.commit()

    user = User(
        username="second_revoke",  # Use unique username
        password=bcrypt.hash("testpass"),
        email="test@example.com",
        name="Test User",
        admin=True,
        github=None,
        discord_username=None,
        about=None,
    )
    with Session(engine) as db:
        db.add(user)
        db.commit()

    headers = {"Authorization": f"Bearer {token_id}"}
    response = client.post("/auth/update-admin", headers=headers, json={
        "username": "second_revoke",
        "admin": False
    })
    assert response.status_code == 200
    assert "revoked" in response.json()["message"]

    with Session(engine) as db:
        updated = db.exec(select(User).where(User.username == "second_revoke")).first()
        assert updated.admin is False

    delete_username("testuser")
    delete_token(token_id)
    delete_username("second_revoke")