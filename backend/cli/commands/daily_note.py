"""Daily note management commands."""

import platform
from datetime import datetime
from pathlib import Path

import click


@click.group(name="daily-note")
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
    from core.git_hooks import DailyNoteManager

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
    from core.git_hooks import DailyNoteManager

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
    from core.git_hooks import DailyNoteManager

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
    from core.git_hooks import DailyNoteManager

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
    from core.git_hooks import DailyNoteManager

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
                from core.mac_windows import MacWindowDetector

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
