from datetime import datetime, timedelta, timezone
import os

from packbridge.services.operations import (
    apply_retention,
    create_backup,
    inspect_backup,
    retention_candidates,
)


def test_backup_contains_database_knowledge_templates_and_data(tmp_path):
    db_path = tmp_path / "packbridge.sqlite3"
    import sqlite3
    connection = sqlite3.connect(db_path)
    connection.execute("create table test (id integer primary key, value text)")
    connection.execute("insert into test(value) values ('ok')")
    connection.commit()
    connection.close()

    knowledge = tmp_path / "knowledge"
    templates = tmp_path / "templates"
    data = tmp_path / "data"
    knowledge.mkdir()
    templates.mkdir()
    data.mkdir()
    (knowledge / "rules.md").write_text("# Rules\n", encoding="utf-8")
    (templates / "active.json").write_text("{}", encoding="utf-8")
    (data / "note.txt").write_text("data", encoding="utf-8")

    archive = create_backup(
        database_uri="sqlite:///" + str(db_path),
        data_root=data,
        knowledge_root=knowledge,
        template_root=templates,
        destination=tmp_path / "backup.zip",
    )

    inspection = inspect_backup(archive)
    assert inspection["manifest"]["contains"]["database"] is True
    assert inspection["manifest"]["contains"]["knowledge"] is True
    assert inspection["entries"] >= 4


def test_retention_dry_run_and_apply(tmp_path):
    root = tmp_path / "data"
    old = root / "jobs" / "10"
    recent = root / "jobs" / "11"
    old.mkdir(parents=True)
    recent.mkdir(parents=True)

    now = datetime.now(timezone.utc)
    old_time = (now - timedelta(days=120)).timestamp()
    os.utime(old, (old_time, old_time))

    candidates = retention_candidates(root, days=90, now=now)
    assert [item.path.name for item in candidates] == ["10"]

    dry = apply_retention(root, days=90, dry_run=True)
    assert len(dry) == 1
    assert old.exists()

    removed = apply_retention(root, days=90, dry_run=False)
    assert len(removed) == 1
    assert not old.exists()
    assert recent.exists()
