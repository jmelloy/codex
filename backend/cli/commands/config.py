"""Configuration management commands for integration variables."""

import json as json_module
from pathlib import Path

import click

from core.workspace import Workspace


@click.group()
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
    try:
        ws = Workspace.load(Path(workspace).resolve())

        # Check if integration type exists
        from integrations import IntegrationRegistry

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
