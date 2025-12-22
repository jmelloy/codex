"""Entry management commands."""

from pathlib import Path

import click

from core.utils import format_table
from core.workspace import Workspace


@click.group()
def entry():
    """Entry management commands."""
    pass


@entry.command("create")
@click.argument("entry_type")
@click.option("--page", "-p", required=True, help="Page ID")
@click.option("--title", "-t", required=True, help="Entry title")
@click.option("--param", "-P", multiple=True, help="Input parameters (key=value)")
@click.option("--execute", "-x", is_flag=True, help="Execute immediately")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def entry_create(
    entry_type: str, page: str, title: str, param: tuple, execute: bool, workspace: str
):
    """Create a new entry."""
    try:
        ws = Workspace.load(Path(workspace).resolve())

        from core.page import Page

        page_data = ws.db_manager.get_page(page)
        if not page_data:
            click.echo(f"Page not found: {page}", err=True)
            raise click.Abort()

        p = Page.from_dict(ws, page_data)

        # Parse parameters
        inputs = {}
        for p_str in param:
            key, value = p_str.split("=", 1)
            # Try to parse as number or boolean
            if value.lower() == "true":
                inputs[key] = True
            elif value.lower() == "false":
                inputs[key] = False
            else:
                try:
                    inputs[key] = float(value) if "." in value else int(value)
                except ValueError:
                    inputs[key] = value

        e = p.create_entry(entry_type, title, inputs)
        click.echo(f"Created entry: {e.id}")
        click.echo(f"  Type: {e.entry_type}")
        click.echo(f"  Title: {e.title}")

        if execute:
            import asyncio

            click.echo("Executing entry...")
            asyncio.run(e.execute())
            click.echo(f"  Status: {e.status}")

            # Display formatted table for database_query results
            if e.entry_type == "database_query" and e.status == "completed":
                outputs = e.outputs
                if outputs.get("columns") and outputs.get("results"):
                    click.echo(f"  Rows: {outputs.get('row_count', 0)}")
                    table = format_table(outputs["columns"], outputs["results"])
                    click.echo(table)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@entry.command("list")
@click.option("--page", "-p", required=True, help="Page ID")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def entry_list(page: str, workspace: str):
    """List all entries in a page."""
    try:
        ws = Workspace.load(Path(workspace).resolve())

        from core.page import Page

        page_data = ws.db_manager.get_page(page)
        if not page_data:
            click.echo(f"Page not found: {page}", err=True)
            raise click.Abort()

        p = Page.from_dict(ws, page_data)
        entries = p.list_entries()

        if not entries:
            click.echo(f"No entries found in page: {p.title}")
            return

        click.echo(f"Found {len(entries)} entry(ies) in '{p.title}':")
        for e in entries:
            click.echo(f"  {e.id}: {e.title} [{e.entry_type}] - {e.status}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@entry.command("variation")
@click.argument("entry_id")
@click.option("--title", "-t", required=True, help="Variation title")
@click.option("--override", "-o", multiple=True, help="Input overrides (key=value)")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def entry_variation(entry_id: str, title: str, override: tuple, workspace: str):
    """Create a variation of an entry."""
    try:
        ws = Workspace.load(Path(workspace).resolve())

        from core.entry import Entry

        entry_data = ws.db_manager.get_entry(entry_id)
        if not entry_data:
            click.echo(f"Entry not found: {entry_id}", err=True)
            raise click.Abort()

        e = Entry.from_dict(ws, entry_data)

        # Parse overrides
        overrides = {}
        for o_str in override:
            key, value = o_str.split("=", 1)
            if value.lower() == "true":
                overrides[key] = True
            elif value.lower() == "false":
                overrides[key] = False
            else:
                try:
                    overrides[key] = float(value) if "." in value else int(value)
                except ValueError:
                    overrides[key] = value

        variation = e.create_variation(title, overrides)
        click.echo(f"Created variation: {variation.id}")
        click.echo(f"  Parent: {e.id}")
        click.echo(f"  Title: {variation.title}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
