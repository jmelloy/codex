"""Git hooks management commands."""

from pathlib import Path

import click


@click.group()
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
@click.option(
    "--global", "is_global", is_flag=True, help="Set as global git hooks path"
)
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
    from core.git_hooks import GitHookManager

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
    from core.git_hooks import GitHookManager

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
            click.echo(f"Warning: No post-commit hook found at: {hooks_path}", err=True)

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
    from core.git_hooks import GitHookManager

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
