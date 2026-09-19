from packbridge import create_app
from packbridge.config import Config
from packbridge.extensions import db
from packbridge.models import SSDProject
from packbridge.ssd_schemas import SSDContext


def make_app(tmp_path):
    TestConfig = type(
        "TestConfig",
        (Config,),
        {
            "TESTING": True,
            "AUTH_ENABLED": False,
            "SAP_OUTPUT_APPROVED": False,
            "SAP_SOCS_ONLY_APPROVED": False,
            "SAP_MACRO_FREE_APPROVED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///" + str(tmp_path / "test.sqlite3"),
            "DATA_ROOT": tmp_path / "data",
            "KNOWLEDGE_ROOT": tmp_path / "knowledge",
            "TEMPLATE_ROOT": tmp_path / "templates",
            "LOG_ROOT": tmp_path / "logs",
            "BACKUP_ROOT": tmp_path / "backups",
        },
    )
    return create_app(TestConfig)


def test_production_generation_is_locked_until_external_sap_acceptance(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        project = SSDProject(
            name="Release Gate",
            context_json=SSDContext().model_dump_json(),
        )
        db.session.add(project)
        db.session.commit()
        project_id = project.id

    response = app.test_client().post(
        f"/projects/{project_id}/build-production",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"locked until SAP acceptance" in response.data
    with app.app_context():
        project = db.session.get(SSDProject, project_id)
        assert project.outputs == []
