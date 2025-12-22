"""Notebook management commands."""

from pathlib import Path

import click

from core.workspace import Workspace


@click.group()
def notebook():
    """Notebook management commands."""
    pass


@notebook.command("create")
@click.argument("title")
@click.option("--description", "-d", default="", help="Notebook description")
@click.option("--tags", "-t", multiple=True, help="Tags for the notebook")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def notebook_create(title: str, description: str, tags: tuple, workspace: str):
    """Create a new notebook."""
    try:
        ws = Workspace.load(Path(workspace).resolve())
        nb = ws.create_notebook(title, description, list(tags))
        click.echo(f"Created notebook: {nb.id}")
        click.echo(f"  Title: {nb.title}")
        click.echo(f"  Path: {nb.get_directory()}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@notebook.command("list")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def notebook_list(workspace: str):
    """List all notebooks."""
    try:
        ws = Workspace.load(Path(workspace).resolve())
        notebooks = ws.list_notebooks()

        if not notebooks:
            click.echo("No notebooks found.")
            return

        click.echo(f"Found {len(notebooks)} notebook(s):")
        for nb in notebooks:
            tags_str = ", ".join(nb.tags) if nb.tags else "none"
            click.echo(f"  {nb.id}: {nb.title} [tags: {tags_str}]")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
