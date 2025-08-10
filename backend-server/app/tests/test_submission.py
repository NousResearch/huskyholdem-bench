import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.service.db.utils import create_admin_user, delete_username, verify_user
from unittest.mock import patch

client = TestClient(app)

def register_user(username: str, password: str, email: str):
    response = client.post("/auth/register", json={"username": username, "password": password, "email": email})
    assert response.status_code in (200, 201)
    return response.json()

def login_user(username: str, password: str):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
def authenticated_user():
    username = "user1"
    password = "pass1"
    email = "user1@example.com"
    delete_username(username)
    register_user(username, password, email)
    verify_user(username)
    token = login_user(username, password)
    yield {"token": token, "username": username}
    delete_username(username)

@pytest.fixture
def authenticated_admin():
    username = "admin1"
    password = "adminpass1"
    email = "admin1@example.com"
    delete_username(username)
    create_admin_user(username, password, email)
    verify_user(username)
    token = login_user(username, password)
    yield {"token": token, "username": username}
    delete_username(username)

@pytest.fixture
def mock_file_services():
    with patch("app.utils.file.check_input_stat", return_value=(True, None)) as mock_stat, \
    patch("app.service.db.supabase.SupabaseBucketService.upload_file_from_bytes", return_value=None) as mock_upload:
        yield mock_stat, mock_upload

def test_upload_submission(authenticated_user, mock_file_services):
    token = authenticated_user["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }

    response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "submission_id" in data
    assert data["message"] == "Uploaded files successfully"

def test_list_submissions(authenticated_user, mock_file_services):
    token = authenticated_user["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }
    client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token}"})

    response = client.get("/submission/list", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert "files" in data
    assert len(data["files"]) == 1
    assert "id" in data["files"][0]

def test_list_no_submissions(authenticated_user):
    token = authenticated_user["token"]

    response = client.get("/submission/list", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "No files found"
    assert data["files"] == []

def test_delete_own_submission(authenticated_user, mock_file_services):
    token = authenticated_user["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }

    upload_response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    submission_id = upload_response.json()["submission_id"]
    with patch("app.service.db.supabase.SupabaseBucketService.delete_file", return_value=None):
        delete_response = client.delete(f"/submission/{submission_id}", headers={"Authorization": f"Bearer {token}"})
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "File deleted successfully"

def test_delete_nonexistent_submission(authenticated_user):
    token = authenticated_user["token"]
    non_existent_id = "123456789-demirhan"
    response = client.delete(f"/submission/{non_existent_id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404
    assert response.json()["detail"] == "File not found"

def test_cannot_delete_other_submission(authenticated_user, mock_file_services):
    token1 = authenticated_user["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }
    upload_response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token1}"})
    submission_id = upload_response.json()["submission_id"]

    username2 = "user2"
    password2 = "pass2"
    email2 = "user2@example.com"
    delete_username(username2)
    register_user(username2, password2, email2)
    verify_user(username2)
    token2 = login_user(username2, password2)

    with patch("app.service.db.supabase.SupabaseBucketService.delete_file", return_value=None):
        response = client.delete(f"/submission/{submission_id}", headers={"Authorization": f"Bearer {token2}"})
        assert response.status_code == 403
        assert response.json()["detail"] == "You are not allowed to delete this file"
    delete_username(username2)

def test_admin_delete_any_submission(authenticated_user, authenticated_admin, mock_file_services):
    user_token = authenticated_user["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
       "packages_file": ("requirements.txt", b"", "text/plain"),
    }

    upload_response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {user_token}"})
    submission_id = upload_response.json()["submission_id"]
    admin_token = authenticated_admin["token"]

    with patch("app.service.db.supabase.SupabaseBucketService.delete_file", return_value=None):
        response = client.delete(f"/submission/admin/delete/{submission_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert response.json()["message"] == "File deleted successfully"

def test_admin_get_all_submissions(authenticated_user, authenticated_admin, mock_file_services):
    user_token = authenticated_user["token"]
    user_username = authenticated_user["username"]
    admin_token = authenticated_admin["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }

    client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {user_token}"})
    response = client.get("/submission/all", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["submissions"]) == 1
    assert data["submissions"][0]["username"] == user_username

def test_user_cannot_get_all_submissions(authenticated_user):
    token = authenticated_user["token"]

    response = client.get("/submission/all", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"

def test_upload_wrong_filename(authenticated_user):
    token = authenticated_user["token"]
    files = {
        "python_file": ("wrong.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }

    response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert "detail" in response.json()
    assert response.json()["detail"] == "Python file must be named player.py"

def test_upload_submission_limit(authenticated_user, mock_file_services):
    token = authenticated_user["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }

    for _ in range(5):
        response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200

    response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 400
    assert "You have reached the limit" in response.json()["detail"]

def test_mark_and_unmark_final_submission(authenticated_user, mock_file_services):
    token = authenticated_user["token"]
    files1 = {
        "python_file": ("player.py", b"p1", "text/plain"), 
        "packages_file": ("requirements.txt", b"r1", "text/plain")
    }
    response1 = client.post("/submission/upload", files=files1, headers={"Authorization": f"Bearer {token}"})
    submission_id1 = response1.json()["submission_id"]

    files2 = {
        "python_file": ("player.py", b"p2", "text/plain"), 
        "packages_file": ("requirements.txt", b"r2", "text/plain")
    }
    response2 = client.post("/submission/upload", files=files2, headers={"Authorization": f"Bearer {token}"})
    submission_id2 = response2.json()["submission_id"]

    mark_response = client.post("/submission/mark_final", json={"submission_id": submission_id1}, headers={"Authorization": f"Bearer {token}"})
    assert mark_response.status_code == 200
    assert mark_response.json()["message"] == "File marked as final successfully"

    list_response = client.get("/submission/list", headers={"Authorization": f"Bearer {token}"})
    subs = {
        submission["id"]: submission
        for submission in list_response.json()["files"]
    }
    assert subs[submission_id1]["final"] is True
    assert subs[submission_id2]["final"] is False

    fail_mark_response = client.post("/submission/mark_final", json={"submission_id": submission_id2}, headers={"Authorization": f"Bearer {token}"})
    assert fail_mark_response.status_code == 400
    assert "You have already marked a file as final" in fail_mark_response.json()["detail"]

    unmark_response = client.post("/submission/unmark_final", json={"submission_id": submission_id1}, headers={"Authorization": f"Bearer {token}"})
    assert unmark_response.status_code == 200
    assert unmark_response.json()["message"] == "File unmarked as final successfully"

    list_response_after = client.get("/submission/list", headers={"Authorization": f"Bearer {token}"})
    assert list_response_after.json()["files"][0]["final"] is False

def test_mark_nonexistent_submission(authenticated_user):
    token = authenticated_user["token"]
    non_existent_id = "this-id-does-not-exist"
    
    response = client.post(
        "/submission/mark_final", 
        json={"submission_id": non_existent_id}, 
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 404
    assert response.json()["detail"] == "Submission not found"

def test_cannot_mark_other_users_submission(authenticated_user, mock_file_services):
    token1 = authenticated_user["token"]
    files = {
        "python_file": ("player.py", b"print('hello')", "text/plain"),
        "packages_file": ("requirements.txt", b"", "text/plain"),
    }
    upload_response = client.post("/submission/upload", files=files, headers={"Authorization": f"Bearer {token1}"})
    submission_id_user1 = upload_response.json()["submission_id"]

    username2, password2, email2 = "user2", "pass2", "user2@example.com"
    delete_username(username2)
    register_user(username2, password2, email2)
    verify_user(username2)
    token2 = login_user(username2, password2)

    response = client.post("/submission/mark_final", json={"submission_id": submission_id_user1}, headers={"Authorization": f"Bearer {token2}"})
    assert response.status_code == 403
    assert response.json()["detail"] == "You are not allowed to mark this file as final"
    delete_username(username2)