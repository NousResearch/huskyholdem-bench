from app.service.db.utils import delete_username, delete_token


def test_login_success(client, test_user):
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    delete_username("testuser")
    # delete_token(response.json()["access_token"])
    print(response.json())

def test_login_user_doesnt_exist(client):
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass",
    })
    assert response.status_code == 401

def test_login_wrongpass(client, test_user):
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    delete_username("testuser")
    # Don't try to delete token since login failed and no token was created
