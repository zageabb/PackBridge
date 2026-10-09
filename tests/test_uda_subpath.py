"""UDA reverse-proxy regression for PackBridge."""
from packbridge import create_app
from packbridge.config import Config

def test_prefix_and_local_mode(tmp_path):
    config = type("TestConfig", (Config,), {
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
        "DATA_ROOT": tmp_path / "data",
        "KNOWLEDGE_ROOT": tmp_path / "knowledge",
        "TEMPLATE_ROOT": tmp_path / "templates",
        "LOG_ROOT": tmp_path / "logs",
        "BACKUP_ROOT": tmp_path / "backups",
        "AUTH_ENABLED": False,
    })
    app = create_app(config)
    client = app.test_client()
    local = client.get("/")
    assert local.status_code == 200
    assert '<base href="/">' in local.get_data(as_text=True)

    headers = {
        "X-Forwarded-Prefix": "/apps/packbridge",
        "X-Forwarded-Host": "tanyaanne.ddns.net",
        "X-Forwarded-Proto": "https",
    }
    proxied = client.get("/", headers=headers)
    assert proxied.status_code == 200
    html = proxied.get_data(as_text=True)
    assert '<base href="/apps/packbridge/">' in html
    assert '/apps/packbridge/static/css/app.css' in html
    assert '/apps/packbridge/projects/' in html
    assert client.get("/health", headers=headers).status_code == 200
