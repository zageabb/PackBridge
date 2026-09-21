from packbridge import create_app
from packbridge.config import Config
from packbridge.services import runtime_settings


def make_app(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "AUTH_ENABLED": False,
            "OLLAMA_URL": "http://127.0.0.1:11434",
            "OLLAMA_MODEL": "qwen3:14b",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
            "LOG_ROOT": tmp_path / "logs",
            "BACKUP_ROOT": tmp_path / "backups",
        },
    )
    return create_app(TestConfig)


def test_saved_runtime_model_is_used_by_new_clients(tmp_path):
    app = make_app(tmp_path)

    with app.app_context():
        before = runtime_settings.client()
        assert before.model == "qwen3:14b"

        runtime_settings.save(
            {
                "ollama_url": "http://127.0.0.1:11434",
                "ollama_model": "gpt-oss:120b-cloud",
            }
        )

        after = runtime_settings.client()
        assert after.model == "gpt-oss:120b-cloud"
        assert runtime_settings.current()["ollama_model"] == "gpt-oss:120b-cloud"
