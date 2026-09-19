import json

from werkzeug.security import generate_password_hash

from packbridge import create_app
from packbridge.config import Config


def make_app(tmp_path, auth_enabled=True):
    users = tmp_path / "users.json"
    users.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "viewer",
                        "role": "viewer",
                        "password_hash": generate_password_hash("viewer-password"),
                    },
                    {
                        "username": "admin",
                        "role": "admin",
                        "password_hash": generate_password_hash("admin-password"),
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "AUTH_ENABLED": auth_enabled,
            "USERS_FILE": users,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
            "LOG_ROOT": tmp_path / "logs",
            "BACKUP_ROOT": tmp_path / "backups",
        },
    )
    return create_app(TestConfig)


def login(client, username, password):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=False,
    )


def test_auth_redirects_anonymous_browser_request(tmp_path):
    app = make_app(tmp_path)
    response = app.test_client().get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_viewer_can_read_but_cannot_change_settings(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    assert login(client, "viewer", "viewer-password").status_code == 302

    assert client.get("/").status_code == 200
    response = client.post(
        "/settings/",
        data={"ollama_url": "http://localhost:11434", "ollama_model": "qwen3:14b"},
    )
    assert response.status_code == 403


def test_admin_can_access_settings(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    assert login(client, "admin", "admin-password").status_code == 302
    assert client.get("/settings/").status_code == 200


def test_auth_disabled_preserves_local_development_flow(tmp_path):
    app = make_app(tmp_path, auth_enabled=False)
    assert app.test_client().get("/").status_code == 200
