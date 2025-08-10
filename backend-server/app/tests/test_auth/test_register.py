from app.service.db.utils import delete_username

def test_register_new_user(client):
    delete_username("newuser")
    response = client.post("/auth/register", json={
        "username": "newuser",
        "password": "newpass123",
        "email": "new@example.com",
        "name": "New User",
        "github": None,
        "discord_username": None,
        "about": "test",
    })
    assert response.status_code == 201
    assert "access_token" in response.json()
    delete_username("newuser")

def test_register_duplicate_user(client, test_user):
    response = client.post("/auth/register", json={
        "username": "testuser",
        "password": "anything",
        "email": "dup@example.com",
        "name": "Duplicate",
        "github": None,
        "discord_username": None,
        "about": "test",
    })
    assert response.status_code == 400
    delete_username("testuser")
