"""Codex CLI."""

from datetime import datetime
from pathlib import Path

import click

from codex.core.utils import format_table
from codex.core.workspace import Workspace


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Codex - A hierarchical digital laboratory journal system."""
    pass


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


@cli.group()
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


@cli.group()
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


@cli.group()
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

        from codex.core.page import Page

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

        from codex.core.page import Page

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

        from codex.core.entry import Entry

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

        from codex.core.entry import Entry

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
        "codex.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.group()
def config():
    """Configuration management commands for integration variables."""
    pass


@config.command("set")
@click.argument("integration_type")
@click.argument("name")
@click.argument("value")
@click.option("--description", "-d", default=None, help="Description of the variable")
@click.option("--secret", "-s", is_flag=True, help="Mark as sensitive data")
@click.option("--json", "is_json", is_flag=True, help="Parse value as JSON")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def config_set(
    integration_type: str,
    name: str,
    value: str,
    description: str,
    secret: bool,
    is_json: bool,
    workspace: str,
):
    """Set an integration variable (default value for a plugin).

    Examples:

    \b
    # Set base URL for API calls
    codex config set api_call base_url https://api.example.com

    \b
    # Set default headers (as JSON)
    codex config set api_call headers '{"Authorization": "Bearer token"}' --json --secret

    \b
    # Set database connection string
    codex config set database_query connection_string "postgresql://user:pass@localhost/db" --secret

    \b
    # Set GraphQL endpoint
    codex config set graphql url https://api.example.com/graphql
    """
    import json as json_module

    try:
        ws = Workspace.load(Path(workspace).resolve())

        # Check if integration type exists
        from codex.integrations import IntegrationRegistry

        if not IntegrationRegistry.has_integration(integration_type):
            click.echo(
                f"Warning: Unknown integration type '{integration_type}'. "
                f"Available types: {IntegrationRegistry.list_integrations()}",
                err=True,
            )

        # Parse value as JSON if requested
        if is_json:
            try:
                parsed_value = json_module.loads(value)
            except json_module.JSONDecodeError as e:
                click.echo(f"Error parsing JSON: {e}", err=True)
                raise click.Abort()
        else:
            parsed_value = value

        variable = ws.db_manager.set_integration_variable(
            integration_type=integration_type,
            name=name,
            value=parsed_value,
            description=description,
            is_secret=secret,
        )

        click.echo(f"Set {integration_type}.{name}")
        if description:
            click.echo(f"  Description: {description}")
        if secret:
            click.echo("  Value: [SECRET]")
        else:
            click.echo(f"  Value: {variable['value']}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@config.command("get")
@click.argument("integration_type")
@click.argument("name", required=False)
@click.option("--workspace", "-w", default=".", help="Workspace path")
def config_get(integration_type: str, name: str, workspace: str):
    """Get integration variable(s).

    If NAME is provided, gets a single variable. Otherwise, lists all
    variables for the integration type.

    Examples:

    \b
    # Get a single variable
    codex config get api_call base_url

    \b
    # List all variables for an integration
    codex config get api_call
    """
    try:
        ws = Workspace.load(Path(workspace).resolve())

        if name:
            variable = ws.db_manager.get_integration_variable(integration_type, name)
            if not variable:
                click.echo(
                    f"Variable '{name}' not found for integration '{integration_type}'",
                    err=True,
                )
                raise click.Abort()

            click.echo(f"{integration_type}.{name}:")
            if variable.get("is_secret"):
                click.echo("  Value: [SECRET]")
            else:
                click.echo(f"  Value: {variable['value']}")
            if variable.get("description"):
                click.echo(f"  Description: {variable['description']}")
        else:
            variables = ws.db_manager.list_integration_variables(integration_type)
            if not variables:
                click.echo(f"No variables found for integration '{integration_type}'")
                return

            click.echo(f"Variables for {integration_type}:")
            for var in variables:
                if var.get("is_secret"):
                    value_str = "[SECRET]"
                else:
                    value_str = str(var["value"])
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                click.echo(f"  {var['name']}: {value_str}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@config.command("list")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def config_list(workspace: str):
    """List all integration variables.

    Shows all configured default values for all integration types.
    """
    try:
        ws = Workspace.load(Path(workspace).resolve())
        variables = ws.db_manager.list_integration_variables()

        if not variables:
            click.echo("No integration variables configured.")
            click.echo(
                "\nUse 'codex config set <type> <name> <value>' to add defaults."
            )
            return

        # Group by integration type
        by_type: dict = {}
        for var in variables:
            itype = var["integration_type"]
            if itype not in by_type:
                by_type[itype] = []
            by_type[itype].append(var)

        click.echo("Integration variables:")
        for itype, vars in sorted(by_type.items()):
            click.echo(f"\n  {itype}:")
            for var in vars:
                if var.get("is_secret"):
                    value_str = "[SECRET]"
                else:
                    value_str = str(var["value"])
                    if len(value_str) > 40:
                        value_str = value_str[:37] + "..."
                click.echo(f"    {var['name']}: {value_str}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@config.command("delete")
@click.argument("integration_type")
@click.argument("name")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def config_delete(integration_type: str, name: str, workspace: str):
    """Delete an integration variable.

    Example:

    \b
    codex config delete api_call base_url
    """
    try:
        ws = Workspace.load(Path(workspace).resolve())
        success = ws.db_manager.delete_integration_variable(integration_type, name)

        if success:
            click.echo(f"Deleted {integration_type}.{name}")
        else:
            click.echo(
                f"Variable '{name}' not found for integration '{integration_type}'",
                err=True,
            )
            raise click.Abort()
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.group()
def db():
    """Database management commands."""
    pass


@db.command("migrate")
@click.option("--revision", "-r", default="head", help="Target revision (default: head)")
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


@cli.group()
def hooks():
    """Git hooks management commands."""
    pass


@hooks.command("install")
@click.option(
    "--hooks-path",
    "-p",
    default=None,
    help="Git hooks directory path (default: ~/.git-hooks)",
)
@click.option("--workspace", "-w", default=None, help="Workspace path for daily notes")
@click.option("--global", "is_global", is_flag=True, help="Set as global git hooks path")
def hooks_install(hooks_path: str, workspace: str, is_global: bool):
    """Install the Codex post-commit git hook.

    This hook automatically logs commits to daily notes in your workspace.

    Examples:

    \b
    # Install with default settings
    codex hooks install --global

    \b
    # Install with custom hooks path and workspace
    codex hooks install --hooks-path ~/.my-hooks --workspace ~/lab --global
    """
    from codex.core.git_hooks import GitHookManager

    try:
        # Determine hooks path
        if hooks_path is None:
            hooks_path = Path.home() / ".git-hooks"
        else:
            hooks_path = Path(hooks_path).expanduser().resolve()

        # Determine workspace path
        ws_path = None
        if workspace:
            ws_path = Path(workspace).expanduser().resolve()

        # Install the hook
        success = GitHookManager.install_post_commit_hook(hooks_path, ws_path)

        if not success:
            click.echo("Error: Failed to install post-commit hook", err=True)
            raise click.Abort()

        click.echo(f"✓ Installed post-commit hook to: {hooks_path}")

        # Set as global hooks path if requested
        if is_global:
            if GitHookManager.set_global_hooks_path(hooks_path):
                click.echo(f"✓ Set global git hooks path to: {hooks_path}")
            else:
                click.echo(
                    f"Warning: Could not set global git hooks path. "
                    f"Run manually: git config --global core.hooksPath {hooks_path}",
                    err=True,
                )

        click.echo("\nThe post-commit hook will now log commits to daily notes.")
        if ws_path:
            click.echo(f"Daily notes location: {ws_path / 'daily-notes'}")
        else:
            click.echo(
                "Note: No workspace specified. Use --workspace flag "
                "or the hook will use the current directory."
            )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@hooks.command("uninstall")
@click.option(
    "--hooks-path",
    "-p",
    default=None,
    help="Git hooks directory path (default: ~/.git-hooks)",
)
def hooks_uninstall(hooks_path: str):
    """Uninstall the Codex post-commit git hook.

    Example:

    \b
    codex hooks uninstall
    """
    from codex.core.git_hooks import GitHookManager

    try:
        # Determine hooks path
        if hooks_path is None:
            hooks_path = Path.home() / ".git-hooks"
        else:
            hooks_path = Path(hooks_path).expanduser().resolve()

        # Uninstall the hook
        success = GitHookManager.uninstall_post_commit_hook(hooks_path)

        if success:
            click.echo(f"✓ Uninstalled post-commit hook from: {hooks_path}")
        else:
            click.echo(
                f"Warning: No post-commit hook found at: {hooks_path}", err=True
            )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@hooks.command("status")
def hooks_status():
    """Show git hooks configuration status.

    Example:

    \b
    codex hooks status
    """
    from codex.core.git_hooks import GitHookManager

    try:
        hooks_path = GitHookManager.get_global_hooks_path()

        if hooks_path:
            click.echo(f"Global git hooks path: {hooks_path}")

            post_commit = hooks_path / "post-commit"
            if post_commit.exists():
                click.echo("✓ Post-commit hook: Installed")
                # Check if it's executable
                if post_commit.stat().st_mode & 0o111:
                    click.echo("  Status: Executable")
                else:
                    click.echo("  Status: Not executable (may not work)")
            else:
                click.echo("✗ Post-commit hook: Not installed")
        else:
            click.echo("Global git hooks path: Not configured")
            click.echo("\nRun 'codex hooks install --global' to set up git hooks.")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@cli.group(name="daily-note")
def daily_note():
    """Daily note management commands."""
    pass


@daily_note.command("create")
@click.option("--workspace", "-w", default=".", help="Workspace path")
@click.option("--date", "-d", default=None, help="Date (YYYY-MM-DD, default: today)")
def daily_note_create(workspace: str, date: str):
    """Create a new daily note.

    Example:

    \b
    # Create today's daily note
    codex daily-note create

    \b
    # Create a daily note for a specific date
    codex daily-note create --date 2024-12-20
    """
    from codex.core.git_hooks import DailyNoteManager

    try:
        ws_path = Path(workspace).expanduser().resolve()
        manager = DailyNoteManager(ws_path)

        note_date = None
        if date:
            note_date = datetime.strptime(date, "%Y-%m-%d")

        note_path = manager.create_daily_note(note_date)
        click.echo(f"✓ Created daily note: {note_path}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@daily_note.command("list")
@click.option("--workspace", "-w", default=".", help="Workspace path")
@click.option("--limit", "-n", default=10, help="Number of notes to show")
def daily_note_list(workspace: str, limit: int):
    """List daily notes.

    Example:

    \b
    # List last 10 daily notes
    codex daily-note list

    \b
    # List last 30 daily notes
    codex daily-note list --limit 30
    """
    from codex.core.git_hooks import DailyNoteManager

    try:
        ws_path = Path(workspace).expanduser().resolve()
        manager = DailyNoteManager(ws_path)

        notes = manager.list_daily_notes(limit)

        if not notes:
            click.echo("No daily notes found.")
            click.echo(f"\nDaily notes location: {manager.daily_notes_path}")
            return

        click.echo(f"Daily notes ({len(notes)}):")
        for note in notes:
            click.echo(f"  {note.stem}: {note}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@daily_note.command("add-commit")
@click.option("--sha", required=True, help="Commit SHA")
@click.option("--message", required=True, help="Commit message")
@click.option("--branch", required=True, help="Branch name")
@click.option("--repo", required=True, help="Repository name")
@click.option("--workspace", "-w", default=".", help="Workspace path")
def daily_note_add_commit(
    sha: str, message: str, branch: str, repo: str, workspace: str
):
    """Add a commit entry to today's daily note.

    This command is typically called by the post-commit git hook.

    Example:

    \b
    codex daily-note add-commit \\
        --sha abc123 \\
        --message "Fix bug" \\
        --branch main \\
        --repo myproject
    """
    from codex.core.git_hooks import DailyNoteManager

    try:
        ws_path = Path(workspace).expanduser().resolve()
        manager = DailyNoteManager(ws_path)

        manager.add_commit_entry(sha, message, branch, repo)
        # Silent success for hook usage
        # click.echo(f"✓ Added commit to: {note_path}")

    except Exception:
        # Silently fail for hook usage
        pass


@daily_note.command("view")
@click.option("--workspace", "-w", default=".", help="Workspace path")
@click.option("--date", "-d", default=None, help="Date (YYYY-MM-DD, default: today)")
def daily_note_view(workspace: str, date: str):
    """View a daily note.

    Example:

    \b
    # View today's daily note
    codex daily-note view

    \b
    # View a specific date's daily note
    codex daily-note view --date 2024-12-20
    """
    from codex.core.git_hooks import DailyNoteManager

    try:
        ws_path = Path(workspace).expanduser().resolve()
        manager = DailyNoteManager(ws_path)

        note_date = None
        if date:
            note_date = datetime.strptime(date, "%Y-%m-%d")

        note_path = manager.get_daily_note_path(note_date)

        if not note_path.exists():
            date_str = (note_date or datetime.now()).strftime("%Y-%m-%d")
            click.echo(f"Daily note for {date_str} does not exist.")
            click.echo(f"Create it with: codex daily-note create --date {date_str}")
            return

        content = note_path.read_text()
        click.echo(content)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@daily_note.command("add-window")
@click.option("--workspace", "-w", default=".", help="Workspace path")
@click.option("--app", help="Application name (auto-detected on Mac if not provided)")
@click.option("--window", help="Window title (auto-detected on Mac if not provided)")
@click.option("--url", help="URL (auto-detected for browsers on Mac if not provided)")
def daily_note_add_window(workspace: str, app: str, window: str, url: str):
    """Add active window information to today's daily note.

    On macOS, this command automatically detects the currently active window
    and its details. For web browsers, it also captures the current URL.

    Example:

    \b
    # Auto-detect active window (macOS only)
    codex daily-note add-window

    \b
    # Manually specify window information
    codex daily-note add-window \\
        --app "Visual Studio Code" \\
        --window "main.py - myproject"

    \b
    # Manually specify browser with URL
    codex daily-note add-window \\
        --app "Safari" \\
        --window "GitHub" \\
        --url "https://github.com"
    """
    from codex.core.git_hooks import DailyNoteManager
    import platform

    try:
        ws_path = Path(workspace).expanduser().resolve()
        manager = DailyNoteManager(ws_path)

        # If no manual input provided, try auto-detection on macOS
        if not app or not window:
            if platform.system() != "Darwin":
                click.echo(
                    "Error: Auto-detection is only supported on macOS. "
                    "Please provide --app and --window options.",
                    err=True,
                )
                raise click.Abort()

            try:
                from codex.core.mac_windows import MacWindowDetector

                window_info = MacWindowDetector.get_active_window_info()
                if not window_info:
                    click.echo("Error: Could not detect active window.", err=True)
                    raise click.Abort()

                app = window_info.get("app_name", "Unknown")
                window = window_info.get("window_name", "Unknown")
                if not url and "url" in window_info:
                    url = window_info["url"]

            except ImportError:
                click.echo(
                    "Error: Mac window detection not available. "
                    "Please provide --app and --window options.",
                    err=True,
                )
                raise click.Abort()

        # Add the window entry
        note_path = manager.add_window_entry(app, window, url)
        click.echo(f"✓ Added window entry to: {note_path}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    cli()
