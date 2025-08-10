from fastapi.testclient import TestClient
from app.main import app  # Your FastAPI app
from app.service.db.utils import delete_username

client = TestClient(app)

def test_register_api():
    delete_username("user")
    response = client.post("/auth/register", json={"username": "user", "password": "securepass"})
    assert response.status_code == 200  # Adjust based on your API response

def test_register_duplicate_api():
    delete_username("duplicate_user")
    response1 = client.post("/auth/register", json={"username": "duplicate_user", "password": "securepass"})
    assert response1.json() == {"message": "User created successfully"}
    response2 = client.post("/auth/register", json={"username": "duplicate_user", "password": "securepass"})
    assert response2.status_code == 400  # Expect failure for duplicate users

