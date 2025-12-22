"""Page management commands."""

from datetime import datetime
from pathlib import Path

import click

from core.workspace import Workspace


@click.group()
def page():
    """Page management commands."""
    pass


@page.command("create")
@click.argument("title")
@click.option("--notebook", "-n", required=True, help="Notebook ID or title")
@click.option("--date", "-d", default=None, help="Page date (YYYY-MM-DD)")
@click.option("--goal", "-g", default="", help="Page goal")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def page_create(title: str, notebook: str, date: str, goal: str, workspace: str):
    """Create a new page."""
    try:
        ws = Workspace.load(Path(workspace).resolve())

        # Find notebook by ID or title
        nb = ws.get_notebook(notebook)
        if not nb:
            # Try to find by title
            notebooks = ws.list_notebooks()
            for n in notebooks:
                if n.title.lower() == notebook.lower():
                    nb = n
                    break

        if not nb:
            click.echo(f"Notebook not found: {notebook}", err=True)
            raise click.Abort()

        page_date = datetime.strptime(date, "%Y-%m-%d") if date else None
        narrative = {"goals": goal} if goal else None

        p = nb.create_page(title, page_date, narrative)
        click.echo(f"Created page: {p.id}")
        click.echo(f"  Title: {p.title}")
        click.echo(f"  Date: {p.date}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@page.command("list")
@click.option("--notebook", "-n", required=True, help="Notebook ID or title")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def page_list(notebook: str, workspace: str):
    """List all pages in a notebook."""
    try:
        ws = Workspace.load(Path(workspace).resolve())

        # Find notebook
        nb = ws.get_notebook(notebook)
        if not nb:
            notebooks = ws.list_notebooks()
            for n in notebooks:
                if n.title.lower() == notebook.lower():
                    nb = n
                    break

        if not nb:
            click.echo(f"Notebook not found: {notebook}", err=True)
            raise click.Abort()

        pages = nb.list_pages()

        if not pages:
            click.echo(f"No pages found in notebook: {nb.title}")
            return

        click.echo(f"Found {len(pages)} page(s) in '{nb.title}':")
        for p in pages:
            date_str = p.date.strftime("%Y-%m-%d") if p.date else "undated"
            click.echo(f"  {p.id}: {p.title} ({date_str})")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
