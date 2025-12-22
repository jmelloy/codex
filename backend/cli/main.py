"""Codex CLI."""

from pathlib import Path

import click

# Import command groups from commands module
from cli.commands.config import config
from cli.commands.daily_note import daily_note
from cli.commands.db import db
from cli.commands.entry import entry
from cli.commands.hooks import hooks
from cli.commands.notebook import notebook
from cli.commands.page import page
from core.workspace import Workspace


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Codex - A hierarchical digital laboratory journal system."""
    pass


# Register command groups
cli.add_command(notebook)
cli.add_command(page)
cli.add_command(entry)
cli.add_command(config)
cli.add_command(db)
cli.add_command(hooks)
cli.add_command(daily_note)


@cli.command()
@click.argument("path", type=click.Path())
@click.option("--name", "-n", required=True, help="Workspace name")
def init(path: str, name: str):
    """Initialize a new workspace."""
    try:
        ws_path = Path(path).resolve()
        ws = Workspace.initialize(ws_path, name)
        click.echo(f"Initialized workspace '{name}' at {ws.path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--query", "-q", default=None, help="Search query")
@click.option("--type", "-t", "entry_type", default=None, help="Entry type filter")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def search(query: str, entry_type: str, workspace: str):
    """Search entries."""
    try:
        ws = Workspace.load(Path(workspace).resolve())

        results = ws.search_entries(query=query, entry_type=entry_type)

        if not results:
            click.echo("No entries found.")
            return

        click.echo(f"Found {len(results)} result(s):")
        for r in results:
            click.echo(f"  {r['id']}: {r['title']} [{r['entry_type']}]")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("entry_id")
@click.option("--depth", "-d", default=3, help="Lineage depth")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def lineage(entry_id: str, depth: int, workspace: str):
    """View entry lineage."""
    try:
        ws = Workspace.load(Path(workspace).resolve())

        from core.entry import Entry

        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            click.echo(f"Entry not found: {entry_id}", err=True)
            raise click.Abort()

        e = Entry.from_dict(ws, entry_data)
        lineage_data = e.get_lineage(depth)

        click.echo(f"Lineage for: {e.title} ({e.id})")
        click.echo(f"  Ancestors: {len(lineage_data['ancestors'])}")
        for a in lineage_data["ancestors"]:
            click.echo(f"    - {a['id']}: {a['title']}")

        click.echo(f"  Descendants: {len(lineage_data['descendants'])}")
        for d in lineage_data["descendants"]:
            click.echo(f"    - {d['id']}: {d['title']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--port", "-p", default=8765, help="Port to bind to")
@click.option("--reload", "-r", is_flag=True, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    """Start the web UI server."""
    import uvicorn

    click.echo(f"Starting Codex server at http://{host}:{port}")
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    cli()
