"""Database management commands."""

from pathlib import Path

import click

from core.workspace import Workspace


@click.group()
def db():
    """Database management commands."""
    pass


@db.command("migrate")
@click.option(
    "--revision", "-r", default="head", help="Target revision (default: head)"
)
@click.option("--workspace", "-w", default=".", help="Workspace path")
def db_migrate(revision: str, workspace: str):
    """Run database migrations.

    Updates the database schema to the specified revision.
    By default, migrates to the latest version (head).

    Examples:

    \b
    # Migrate to latest version
    codex db migrate

    \b
    # Migrate to specific revision
    codex db migrate -r 001_initial_schema
    """
    try:
        ws = Workspace.load(Path(workspace).resolve())
        click.echo(f"Running migrations to revision: {revision}")
        ws.db_manager.run_migrations(revision)
        click.echo("Migrations completed successfully.")
    except Exception as e:
        click.echo(f"Error running migrations: {e}", err=True)
        raise click.Abort()


@db.command("status")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def db_status(workspace: str):
    """Show database migration status.

    Displays the current migration revision, available migrations,
    and whether the database is up to date.
    """
    try:
        ws = Workspace.load(Path(workspace).resolve())
        status = ws.db_manager.get_migration_status()

        click.echo("Database Migration Status")
        click.echo("-" * 40)
        click.echo(f"Current revision: {status['current_revision'] or '(none)'}")
        click.echo(f"Head revision:    {status['head_revision'] or '(none)'}")

        if status["is_up_to_date"]:
            click.echo("\nDatabase is up to date.")
        else:
            pending = status["pending_migrations"]
            click.echo(f"\nPending migrations: {len(pending)}")
            for rev in pending:
                click.echo(f"  - {rev}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@db.command("history")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def db_history(workspace: str):
    """Show migration history.

    Lists all available migrations and indicates which have been applied.
    """
    try:
        ws = Workspace.load(Path(workspace).resolve())
        history = ws.db_manager.get_migration_history()

        if not history:
            click.echo("No migrations available.")
            return

        click.echo("Migration History")
        click.echo("-" * 60)
        for entry in history:
            status_char = "✓" if entry["is_applied"] else " "
            current_char = " ← current" if entry["is_current"] else ""
            desc = entry["description"] or "(no description)"
            if len(desc) > 40:
                desc = desc[:37] + "..."
            click.echo(f"[{status_char}] {entry['revision']}: {desc}{current_char}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
