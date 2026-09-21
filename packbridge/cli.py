from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click
from flask import Flask

from packbridge.extensions import db
from packbridge.services.auth import password_hash, role_options
from packbridge.services.benchmarking import run_benchmark
from packbridge.services import runtime_settings
from packbridge.services.operations import (
    apply_retention,
    create_backup,
    inspect_backup,
    prune_backups,
    restore_backup,
)


def register_cli(app: Flask) -> None:
    @app.cli.group("packbridge")
    def packbridge_group():
        """PackBridge administration and operations."""

    @packbridge_group.command("init-user")
    @click.option("--username", prompt=True)
    @click.option(
        "--role",
        type=click.Choice(list(role_options()), case_sensitive=True),
        default="admin",
        show_default=True,
    )
    def init_user(username: str, role: str):
        """Create or replace a local PackBridge user in the configured users file."""

        username = username.strip()
        if not username:
            raise click.ClickException("Username is required.")
        password = click.prompt(
            "Password",
            hide_input=True,
            confirmation_prompt=True,
        )
        digest = password_hash(password)

        path = Path(app.config["USERS_FILE"])
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"users": []}
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and isinstance(loaded.get("users"), list):
                    payload = loaded
            except (OSError, json.JSONDecodeError):
                pass

        users = [
            item
            for item in payload["users"]
            if isinstance(item, dict) and item.get("username") != username
        ]
        users.append(
            {
                "username": username,
                "role": role,
                "password_hash": digest,
            }
        )
        payload["users"] = sorted(users, key=lambda item: item["username"].casefold())

        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
        click.echo(f"Updated {path} with user {username!r} role={role}.")

    @packbridge_group.command("backup")
    @click.option("--destination", type=click.Path(path_type=Path))
    def backup(destination: Path | None):
        """Create an offline-restorable operational backup without secrets."""

        if destination is None:
            root = Path(app.config["BACKUP_ROOT"])
            root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            destination = root / f"packbridge-{stamp}.zip"
        output = create_backup(
            database_uri=app.config["SQLALCHEMY_DATABASE_URI"],
            data_root=Path(app.config["DATA_ROOT"]),
            knowledge_root=Path(app.config["KNOWLEDGE_ROOT"]),
            template_root=Path(app.config["TEMPLATE_ROOT"]),
            destination=destination,
        )
        click.echo(str(output))

    @packbridge_group.command("backup-inspect")
    @click.argument("archive", type=click.Path(exists=True, path_type=Path))
    def backup_inspect(archive: Path):
        """Validate and describe a PackBridge backup archive."""

        click.echo(json.dumps(inspect_backup(archive), indent=2))

    @packbridge_group.command("restore")
    @click.argument("archive", type=click.Path(exists=True, path_type=Path))
    @click.option("--yes", is_flag=True, help="Confirm destructive restore.")
    def restore(archive: Path, yes: bool):
        """Restore a PackBridge backup. Stop the web service first."""

        if not yes:
            raise click.ClickException(
                "Restore replaces operational files. Stop PackBridge and rerun with --yes."
            )
        db.session.remove()
        db.engine.dispose()
        result = restore_backup(
            archive,
            database_uri=app.config["SQLALCHEMY_DATABASE_URI"],
            data_root=Path(app.config["DATA_ROOT"]),
            knowledge_root=Path(app.config["KNOWLEDGE_ROOT"]),
            template_root=Path(app.config["TEMPLATE_ROOT"]),
        )
        click.echo(json.dumps(result, indent=2))

    @packbridge_group.command("backup-prune")
    @click.option("--apply", "do_apply", is_flag=True, help="Actually remove expired backup archives.")
    @click.option("--days", type=int, default=None)
    def backup_prune(do_apply: bool, days: int | None):
        """List or remove backup archives older than the configured policy."""

        policy_days = days if days is not None else int(app.config["BACKUP_RETENTION_DAYS"])
        candidates = prune_backups(
            Path(app.config["BACKUP_ROOT"]),
            days=policy_days,
            dry_run=not do_apply,
        )
        for path in candidates:
            click.echo(str(path))
        click.echo(
            f"{'Removed' if do_apply else 'Would remove'} {len(candidates)} backup(s) "
            f"older than {policy_days} day(s)."
        )
    @packbridge_group.command("retention")
    @click.option("--apply", "do_apply", is_flag=True, help="Actually remove expired operational folders.")
    @click.option("--days", type=int, default=None)
    def retention(do_apply: bool, days: int | None):
        """List or delete operational job/project folders older than policy."""

        policy_days = days if days is not None else int(app.config["RETENTION_DAYS"])
        candidates = apply_retention(
            Path(app.config["DATA_ROOT"]),
            days=policy_days,
            dry_run=not do_apply,
        )
        for item in candidates:
            click.echo(f"{item.kind}\t{item.age_days}d\t{item.path}")
        click.echo(
            f"{'Removed' if do_apply else 'Would remove'} {len(candidates)} folder(s) "
            f"older than {policy_days} day(s)."
        )

    @packbridge_group.command("benchmark")
    @click.option("--model", required=True, help="Ollama model name, for example qwen3:14b.")
    @click.option("--base-url", default=None, help="Override configured Ollama URL.")
    @click.option("--golden-root", type=click.Path(path_type=Path), default=None)
    @click.option("--output", type=click.Path(path_type=Path), default=None)
    def benchmark(model: str, base_url: str | None, golden_root: Path | None, output: Path | None):
        """Run the controlled golden-document benchmark against one local model."""

        settings = runtime_settings.current()
        root = golden_root or (Path(app.root_path).parent / "benchmarks" / "golden")
        if not root.is_dir():
            raise click.ClickException(f"Golden benchmark directory does not exist: {root}")

        report = run_benchmark(
            root=root,
            base_url=(base_url or settings["ollama_url"]),
            model=model,
        )
        if output is None:
            result_root = Path(app.config["DATA_ROOT"]) / "benchmarks"
            result_root.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            safe_model = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in model)
            output = result_root / f"{safe_model}-{stamp}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

        aggregate = report["aggregate"]
        click.echo(json.dumps(aggregate, indent=2))
        click.echo(f"Report: {output}")

        passed = (
            aggregate["json_validity_rate"] == 1.0
            and aggregate["package_grouping_rate"] == 1.0
            and aggregate["null_preservation_rate"] == 1.0
            and aggregate["field_accuracy"] >= 0.99
            and aggregate["item_accuracy"] >= 0.99
        )
        if not passed:
            raise click.ClickException("Model did not meet PackBridge acceptance thresholds.")

    @packbridge_group.command("benchmark-compare")
    @click.argument("baseline", type=click.Path(exists=True, path_type=Path))
    @click.argument("candidate", type=click.Path(exists=True, path_type=Path))
    def benchmark_compare(baseline: Path, candidate: Path):
        """Compare models primarily for speed while enforcing a minimum correctness floor."""

        left = json.loads(baseline.read_text(encoding="utf-8"))["aggregate"]
        right = json.loads(candidate.read_text(encoding="utf-8"))["aggregate"]

        quality_floor = (
            right["json_validity_rate"] == 1.0
            and right["package_grouping_rate"] == 1.0
            and right["null_preservation_rate"] == 1.0
            and right["field_accuracy"] >= 0.99
            and right["item_accuracy"] >= 0.99
        )
        speedup = (
            left["average_seconds"] / right["average_seconds"]
            if right["average_seconds"] > 0
            else None
        )
        faster = bool(speedup is not None and speedup > 1.0)
        comparison = {
            "baseline": left,
            "candidate": right,
            "candidate_meets_minimum_quality_floor": quality_floor,
            "candidate_speedup": speedup,
            "candidate_is_faster": faster,
            "candidate_preferred_for_speed": bool(quality_floor and faster),
        }
        click.echo(json.dumps(comparison, indent=2))
        if not quality_floor:
            raise click.ClickException(
                "Candidate model is faster/available but does not meet PackBridge's minimum correctness floor."
            )
