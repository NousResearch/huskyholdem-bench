from fastapi.testclient import TestClient
from app.main import app  # Your FastAPI app
from app.service.db.utils import create_admin_user, delete_username

client = TestClient(app)

def register_user(username: str, password: str, email: str):
    response = client.post("/auth/register", json={"username": username, "password": password, "email": email})
    assert response.status_code == 200
    return response.json()

def login_user(username: str, password: str):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]

def test_add_remove_leaderboard_entry():
    username1 = "user1"
    username2 = "user2"
    password1 = "1231"
    password2 = "1232"
    email1 = "mail1@uw.edu"
    email2 = "mail2@uw.edu"
    delete_username(username1)
    delete_username(username2)

    create_admin_user(username1, password1, email1)
    create_admin_user(username2, password2, email2)

    token1 = login_user(username1, password1)
    token2 = login_user(username2, password2)

    score = 100
    tag = "tournament_2025"
    response = client.post("/leaderboard/add", json={"score": score, "tag": tag}, headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    entry = response.json()["entry"]
    entry_id = entry["id"]
    assert entry["username"] == username1
    assert entry["score"] == score
    assert entry["tag"] == tag
    assert "time_created" in entry

    response = client.delete(f"/leaderboard/remove/{entry_id}", headers={"Authorization": f"Bearer {token2}"})
    assert response.status_code == 403
    assert response.json() == {"detail": "You can only remove your own entries"}

    response = client.delete(f"/leaderboard/remove/{entry_id}", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    assert response.json() == {"message": f"Leaderboard entry {entry_id} removed"}

    response = client.delete(f"/leaderboard/remove/{entry_id}", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Leaderboard entry not found"}

def test_get_top_n():
    username1 = "user1"
    username2 = "user2"
    password1 = "1231"
    password2 = "1232"
    email1 = "mail1@uw.edu"
    email2 = "mail2@uw.edu"
    delete_username(username1)
    delete_username(username2)

    create_admin_user(username1, password1, email1)
    create_admin_user(username2, password2, email2)

    token1 = login_user(username1, password1)
    token2 = login_user(username2, password2)
    client.post("/leaderboard/add", json={"score": 100, "tag": "weekly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 150, "tag": "monthly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 120, "tag": "weekly"}, headers={"Authorization": f"Bearer {token2}"})

    response = client.get("/leaderboard/top/2")
    assert response.status_code == 200
    top_entries = response.json()["top_entries"]
    assert len(top_entries) == 2
    assert top_entries[0]["username"] == username1
    assert top_entries[0]["score"] == 150
    assert top_entries[0]["tag"] == "monthly"
    assert "time_created" in top_entries[0]
    assert top_entries[1]["username"] == username2
    assert top_entries[1]["score"] == 120
    assert top_entries[1]["tag"] == "weekly"
    assert "time_created" in top_entries[1]

def test_get_tags():
    username1 = "user1"
    username2 = "user2"
    password1 = "1231"
    password2 = "1232"
    email1 = "mail1@uw.edu"
    email2 = "mail2@uw.edu"
    delete_username(username1)
    delete_username(username2)

    create_admin_user(username1, password1, email1)
    create_admin_user(username2, password2, email2)

    token1 = login_user(username1, password1)
    token2 = login_user(username2, password2)
    
    # Add entries with different tags
    client.post("/leaderboard/add", json={"score": 100, "tag": "weekly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 150, "tag": "monthly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 120, "tag": "weekly"}, headers={"Authorization": f"Bearer {token2}"})
    client.post("/leaderboard/add", json={"score": 90}, headers={"Authorization": f"Bearer {token2}"})  # No tag

    response = client.get("/leaderboard/tags")
    assert response.status_code == 200
    tags = response.json()["tags"]
    assert "weekly" in tags
    assert "monthly" in tags
    assert len(tags) == 2  # Should not include None values

def test_get_top_n_with_tag_filter():
    username1 = "user1"
    username2 = "user2"
    password1 = "1231"
    password2 = "1232"
    email1 = "mail1@uw.edu"
    email2 = "mail2@uw.edu"
    delete_username(username1)
    delete_username(username2)

    create_admin_user(username1, password1, email1)
    create_admin_user(username2, password2, email2)

    token1 = login_user(username1, password1)
    token2 = login_user(username2, password2)
    
    # Add entries with different tags
    client.post("/leaderboard/add", json={"score": 100, "tag": "weekly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 150, "tag": "monthly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 120, "tag": "weekly"}, headers={"Authorization": f"Bearer {token2}"})

    # Test filtering by "weekly" tag
    response = client.get("/leaderboard/top/5?tag=weekly")
    assert response.status_code == 200
    top_entries = response.json()["top_entries"]
    assert len(top_entries) == 2  # Only entries with "weekly" tag
    assert all(entry["tag"] == "weekly" for entry in top_entries)
    assert top_entries[0]["score"] == 120  # Higher score first
    assert top_entries[1]["score"] == 100
    assert all("time_created" in entry for entry in top_entries)

def test_get_user_entries():
    username1 = "user1"
    password1 = "1231"
    email1 = "mail1@uw.edu"
    delete_username(username1)

    create_admin_user(username1, password1, email1)
    token1 = login_user(username1, password1)
    
    # Add entries for user
    client.post("/leaderboard/add", json={"score": 100, "tag": "weekly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 150, "tag": "monthly"}, headers={"Authorization": f"Bearer {token1}"})
    client.post("/leaderboard/add", json={"score": 80, "tag": "weekly"}, headers={"Authorization": f"Bearer {token1}"})

    # Test getting all entries for user
    response = client.get(f"/leaderboard/user/{username1}")
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 3
    assert entries[0]["score"] == 150  # Ordered by score desc
    assert entries[1]["score"] == 100
    assert entries[2]["score"] == 80
    assert all("time_created" in entry for entry in entries)

    # Test filtering by tag
    response = client.get(f"/leaderboard/user/{username1}?tag=weekly")
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) == 2  # Only weekly entries
    assert all(entry["tag"] == "weekly" for entry in entries)
    assert entries[0]["score"] == 100  # Higher score first
    assert entries[1]["score"] == 80
    assert all("time_created" in entry for entry in entries)

    # Test non-existent user
    response = client.get("/leaderboard/user/nonexistent")
    assert response.status_code == 404