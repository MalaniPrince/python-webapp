import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


def get_token(client):
    html = client.get("/").get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([a-f0-9]+)"', html).group(1)


def test_create_complete_delete_and_persist(tmp_path):
    config = {"TESTING": True, "DATA_DIR": str(tmp_path)}
    client = create_app(config).test_client()
    token = get_token(client)
    response = client.post("/tasks", data={"title": "Deploy the Python app", "csrf_token": token})
    assert response.status_code == 303
    tasks = client.get("/api/tasks").json["tasks"]
    task_id = tasks[0]["id"]
    assert tasks[0]["title"] == "Deploy the Python app"
    # A fresh application instance must read the existing SQLite data.
    restarted = create_app(config).test_client()
    assert restarted.get("/api/tasks").json["tasks"] == tasks
    assert client.post(f"/tasks/{task_id}/toggle", data={"csrf_token": token}).status_code == 303
    assert client.get("/api/tasks").json["tasks"][0]["completed"] == 1
    assert "Deploy the Python app" not in client.get("/?filter=active").get_data(as_text=True)
    assert client.post(f"/tasks/{task_id}/delete", data={"csrf_token": token}).status_code == 303
    assert client.get("/api/tasks").json["tasks"] == []


def test_validation_and_csrf(tmp_path):
    client = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)}).test_client()
    assert client.post("/tasks", data={"title": "Blocked"}).status_code == 400
    token = get_token(client)
    assert client.post("/tasks", data={"title": "Blocked", "csrf_token": "invalid-☃"}).status_code == 400
    for title in [" ", "x" * 161]:
        assert client.post("/tasks", data={"title": title, "csrf_token": token}).status_code == 303
    assert client.get("/api/tasks").json["tasks"] == []
    assert client.post("/tasks/999/toggle", data={"csrf_token": token}).status_code == 404
    assert client.post("/tasks/999/delete", data={"csrf_token": token}).status_code == 404


def test_html_escaping_and_database_health(tmp_path):
    client = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)}).test_client()
    token = get_token(client)
    title = '<script>alert("x")</script>'
    client.post("/tasks", data={"title": title, "csrf_token": token})
    page = client.get("/").get_data(as_text=True)
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert client.get("/api/tasks").json["tasks"][0]["title"] == title
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json["database"] == "connected"
