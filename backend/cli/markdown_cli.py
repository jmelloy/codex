"""CLI commands for markdown-based storage."""

from datetime import datetime
from pathlib import Path

import click

from core.markdown_storage import MarkdownWorkspace


@click.group()
@click.version_option(version="0.2.0")
def markdown_cli():
    """Codex - Markdown-first digital laboratory journal system."""
    pass


@markdown_cli.command()
@click.argument("path", type=click.Path())
@click.option("--name", "-n", required=True, help="Workspace name")
def init(path: str, name: str):
    """Initialize a new markdown workspace."""
    try:
        ws_path = Path(path).resolve()
        ws = MarkdownWorkspace.initialize(ws_path, name)
        click.echo(f"✓ Initialized markdown workspace '{name}' at {ws.path}")
        click.echo(f"  Config: {ws.config_file}")
        click.echo(f"  Notebooks: {ws.notebooks_path}")
        click.echo(f"  Artifacts: {ws.artifacts_path}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@markdown_cli.group()
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
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.create_notebook(title, description, list(tags))
        click.echo(f"✓ Created notebook: {nb.id}")
        click.echo(f"  Title: {nb.title}")
        click.echo(f"  Path: {nb.path}")
        click.echo(f"  Index: {nb.index_file}")
        if tags:
            click.echo(f"  Tags: {', '.join(tags)}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@notebook.command("list")
@click.option("--workspace", "-w", default=".", help="Workspace path")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def notebook_list(workspace: str, verbose: bool):
    """List all notebooks."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        notebooks = ws.list_notebooks()

        if not notebooks:
            click.echo("No notebooks found.")
            return

        click.echo(f"Found {len(notebooks)} notebook(s):\n")
        
        for nb in notebooks:
            click.echo(f"  📓 {nb.title}")
            click.echo(f"     ID: {nb.id}")
            if verbose:
                click.echo(f"     Path: {nb.path}")
                click.echo(f"     Description: {nb.description or '(none)'}")
                if nb.tags:
                    click.echo(f"     Tags: {', '.join(nb.tags)}")
                click.echo(f"     Created: {nb.created_at.strftime('%Y-%m-%d %H:%M')}")
                page_count = len(nb.list_pages())
                click.echo(f"     Pages: {page_count}")
            click.echo()
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@notebook.command("show")
@click.argument("notebook_id")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def notebook_show(notebook_id: str, workspace: str):
    """Show notebook details."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.get_notebook(notebook_id)
        
        if not nb:
            click.echo(f"✗ Notebook not found: {notebook_id}", err=True)
            raise click.Abort()
        
        click.echo(f"📓 {nb.title}\n")
        click.echo(f"ID: {nb.id}")
        click.echo(f"Description: {nb.description or '(none)'}")
        click.echo(f"Path: {nb.path}")
        if nb.tags:
            click.echo(f"Tags: {', '.join(nb.tags)}")
        click.echo(f"Created: {nb.created_at.strftime('%Y-%m-%d %H:%M')}")
        click.echo(f"Updated: {nb.updated_at.strftime('%Y-%m-%d %H:%M')}")
        
        pages = nb.list_pages()
        click.echo(f"\nPages: {len(pages)}")
        for page_file in pages:
            click.echo(f"  - {page_file.name}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@markdown_cli.group()
def page():
    """Page management commands."""
    pass


@page.command("create")
@click.argument("title")
@click.option("--notebook", "-n", required=True, help="Notebook ID")
@click.option("--date", "-d", default=None, help="Page date (YYYY-MM-DD)")
@click.option("--goals", "-g", default="", help="Page goals")
@click.option("--hypothesis", "-h", default="", help="Page hypothesis")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def page_create(
    title: str,
    notebook: str,
    date: str,
    goals: str,
    hypothesis: str,
    workspace: str,
):
    """Create a new page."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.get_notebook(notebook)
        
        if not nb:
            click.echo(f"✗ Notebook not found: {notebook}", err=True)
            raise click.Abort()

        page_date = datetime.strptime(date, "%Y-%m-%d") if date else None
        narrative = {}
        if goals:
            narrative["goals"] = goals
        if hypothesis:
            narrative["hypothesis"] = hypothesis

        p = nb.create_page(title, page_date, narrative or None)
        click.echo(f"✓ Created page: {p.id}")
        click.echo(f"  Title: {p.title}")
        click.echo(f"  Date: {p.date.strftime('%Y-%m-%d')}")
        click.echo(f"  File: {p.path}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@page.command("list")
@click.option("--notebook", "-n", required=True, help="Notebook ID")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def page_list(notebook: str, workspace: str):
    """List all pages in a notebook."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.get_notebook(notebook)
        
        if not nb:
            click.echo(f"✗ Notebook not found: {notebook}", err=True)
            raise click.Abort()

        pages_files = nb.list_pages()

        if not pages_files:
            click.echo(f"No pages found in notebook: {nb.title}")
            return

        click.echo(f"Found {len(pages_files)} page(s) in '{nb.title}':\n")
        
        from core.markdown_storage import MarkdownPage
        for page_file in pages_files:
            p = MarkdownPage(page_file)
            date_str = p.date.strftime("%Y-%m-%d") if p.date else "undated"
            entries_count = len(p.entries)
            click.echo(f"  📄 {p.title}")
            click.echo(f"     ID: {p.id}")
            click.echo(f"     Date: {date_str}")
            click.echo(f"     Entries: {entries_count}")
            click.echo()
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@page.command("show")
@click.argument("page_id")
@click.option("--notebook", "-n", required=True, help="Notebook ID")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def page_show(page_id: str, notebook: str, workspace: str):
    """Show page details."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.get_notebook(notebook)
        
        if not nb:
            click.echo(f"✗ Notebook not found: {notebook}", err=True)
            raise click.Abort()
        
        p = nb.get_page(page_id)
        if not p:
            click.echo(f"✗ Page not found: {page_id}", err=True)
            raise click.Abort()
        
        click.echo(f"📄 {p.title}\n")
        click.echo(f"ID: {p.id}")
        click.echo(f"Date: {p.date.strftime('%Y-%m-%d')}")
        click.echo(f"File: {p.path}")
        click.echo(f"Created: {p.created_at.strftime('%Y-%m-%d %H:%M')}")
        click.echo(f"Updated: {p.updated_at.strftime('%Y-%m-%d %H:%M')}")
        
        click.echo("\n=== Narrative ===\n")
        if p.narrative.get("goals"):
            click.echo(f"Goals:\n{p.narrative['goals']}\n")
        if p.narrative.get("hypothesis"):
            click.echo(f"Hypothesis:\n{p.narrative['hypothesis']}\n")
        if p.narrative.get("observations"):
            click.echo(f"Observations:\n{p.narrative['observations']}\n")
        if p.narrative.get("conclusions"):
            click.echo(f"Conclusions:\n{p.narrative['conclusions']}\n")
        if p.narrative.get("next_steps"):
            click.echo(f"Next Steps:\n{p.narrative['next_steps']}\n")
        
        click.echo(f"\n=== Entries ({len(p.entries)}) ===\n")
        for entry in p.entries:
            click.echo(f"  • {entry.get('title', 'Untitled')}")
            click.echo(f"    Type: {entry.get('entry_type', 'unknown')}")
            click.echo(f"    Status: {entry.get('status', 'unknown')}")
            if entry.get("artifacts"):
                click.echo(f"    Artifacts: {len(entry['artifacts'])}")
            click.echo()
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@page.command("update")
@click.argument("page_id")
@click.option("--notebook", "-n", required=True, help="Notebook ID")
@click.option("--goals", "-g", help="Update goals")
@click.option("--hypothesis", "-h", help="Update hypothesis")
@click.option("--observations", "-o", help="Update observations")
@click.option("--conclusions", "-c", help="Update conclusions")
@click.option("--next-steps", "-s", help="Update next steps")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def page_update(
    page_id: str,
    notebook: str,
    goals: str,
    hypothesis: str,
    observations: str,
    conclusions: str,
    next_steps: str,
    workspace: str,
):
    """Update page narrative."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.get_notebook(notebook)
        
        if not nb:
            click.echo(f"✗ Notebook not found: {notebook}", err=True)
            raise click.Abort()
        
        p = nb.get_page(page_id)
        if not p:
            click.echo(f"✗ Page not found: {page_id}", err=True)
            raise click.Abort()
        
        updates = []
        if goals is not None:
            p.update_narrative("goals", goals)
            updates.append("goals")
        if hypothesis is not None:
            p.update_narrative("hypothesis", hypothesis)
            updates.append("hypothesis")
        if observations is not None:
            p.update_narrative("observations", observations)
            updates.append("observations")
        if conclusions is not None:
            p.update_narrative("conclusions", conclusions)
            updates.append("conclusions")
        if next_steps is not None:
            p.update_narrative("next_steps", next_steps)
            updates.append("next_steps")
        
        if updates:
            click.echo(f"✓ Updated page: {p.title}")
            click.echo(f"  Fields: {', '.join(updates)}")
        else:
            click.echo("No updates specified.")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@markdown_cli.group()
def entry():
    """Entry management commands."""
    pass


@entry.command("add")
@click.argument("title")
@click.option("--page", "-p", required=True, help="Page ID")
@click.option("--notebook", "-n", required=True, help="Notebook ID")
@click.option("--type", "-t", "entry_type", default="custom", help="Entry type")
@click.option("--input", "-i", "inputs", multiple=True, help="Input key=value pairs")
@click.option("--output", "-o", "outputs", multiple=True, help="Output key=value pairs")
@click.option("--artifact", "-a", "artifacts", multiple=True, help="Artifact paths")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def entry_add(
    title: str,
    page: str,
    notebook: str,
    entry_type: str,
    inputs: tuple,
    outputs: tuple,
    artifacts: tuple,
    workspace: str,
):
    """Add an entry to a page."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.get_notebook(notebook)
        
        if not nb:
            click.echo(f"✗ Notebook not found: {notebook}", err=True)
            raise click.Abort()
        
        p = nb.get_page(page)
        if not p:
            click.echo(f"✗ Page not found: {page}", err=True)
            raise click.Abort()
        
        # Parse inputs
        input_dict = {}
        for inp in inputs:
            if "=" in inp:
                key, value = inp.split("=", 1)
                input_dict[key] = value
        
        # Parse outputs
        output_dict = {}
        for out in outputs:
            if "=" in out:
                key, value = out.split("=", 1)
                output_dict[key] = value
        
        # Parse artifacts
        artifact_list = []
        for art in artifacts:
            artifact_list.append({
                "path": art,
                "type": "unknown"
            })
        
        entry_id = p.add_entry(
            title=title,
            entry_type=entry_type,
            inputs=input_dict,
            outputs=output_dict if output_dict else None,
            artifacts=artifact_list if artifact_list else None,
        )
        
        click.echo(f"✓ Added entry: {entry_id}")
        click.echo(f"  Title: {title}")
        click.echo(f"  Type: {entry_type}")
        click.echo(f"  Inputs: {len(input_dict)} key(s)")
        if output_dict:
            click.echo(f"  Outputs: {len(output_dict)} key(s)")
        if artifact_list:
            click.echo(f"  Artifacts: {len(artifact_list)}")
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


@entry.command("list")
@click.option("--page", "-p", required=True, help="Page ID")
@click.option("--notebook", "-n", required=True, help="Notebook ID")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def entry_list(page: str, notebook: str, workspace: str):
    """List entries in a page."""
    try:
        ws = MarkdownWorkspace(Path(workspace).resolve())
        nb = ws.get_notebook(notebook)
        
        if not nb:
            click.echo(f"✗ Notebook not found: {notebook}", err=True)
            raise click.Abort()
        
        p = nb.get_page(page)
        if not p:
            click.echo(f"✗ Page not found: {page}", err=True)
            raise click.Abort()
        
        if not p.entries:
            click.echo(f"No entries in page: {p.title}")
            return
        
        click.echo(f"Found {len(p.entries)} entry/entries in '{p.title}':\n")
        for entry in p.entries:
            click.echo(f"  📝 {entry.get('title', 'Untitled')}")
            click.echo(f"     ID: {entry.get('id', 'unknown')}")
            click.echo(f"     Type: {entry.get('entry_type', 'unknown')}")
            click.echo(f"     Status: {entry.get('status', 'unknown')}")
            click.echo(f"     Created: {entry.get('created_at', 'unknown')}")
            if entry.get('artifacts'):
                click.echo(f"     Artifacts: {len(entry['artifacts'])}")
            click.echo()
    except Exception as e:
        click.echo(f"✗ Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    markdown_cli()
