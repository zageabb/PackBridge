from sqlalchemy import inspect

from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db


def test_alembic_initial_migration_creates_current_schema(tmp_path):
    database = tmp_path / "migration.sqlite3"
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "AUTO_CREATE_DB": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(database),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
        },
    )
    app = create_app(TestConfig)

    with app.app_context():
        assert inspect(db.engine).get_table_names() == []

    result = app.test_cli_runner().invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output

    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
        assert "jobs" in tables
        assert "validation_acknowledgements" in tables
        assert "knowledge_proposals" in tables
        assert "alembic_version" in tables
