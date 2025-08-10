from app.service.db.utils import delete_username

def test_logout(client, auth_header):
    response = client.post("/auth/logout", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    delete_username("testuser")

def test_logout_invalid_token(client):
    response = client.post("/auth/logout", headers={"Authorization": "Bearer fake"})
    assert response.status_code == 200  # logout silently succeeds
