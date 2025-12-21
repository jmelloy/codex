"""Database query integration for Lab Notebook.

This integration supports executing SQL queries against various database backends
including SQLite, PostgreSQL, and MySQL.

Supports storing default variables for:
- connection_string: Default database connection string
- max_rows: Default maximum number of rows to return
"""

import json
import time
from typing import Any, Optional

from integrations.base import IntegrationBase
from integrations.registry import IntegrationRegistry


def _serialize_value(value: Any) -> Any:
    """Convert database values to JSON-serializable format."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    # For datetime and other types, convert to string
    return str(value)


def _serialize_row(row: Any, columns: Optional[list[str]] = None) -> dict:
    """Convert a database row to a JSON-serializable dict."""
    if hasattr(row, "_asdict"):
        # Named tuple (like sqlalchemy Row)
        return {k: _serialize_value(v) for k, v in row._asdict().items()}
    if hasattr(row, "keys"):
        # Dict-like row
        return {k: _serialize_value(row[k]) for k in row.keys()}
    if columns:
        # Tuple with column names
        return {col: _serialize_value(val) for col, val in zip(columns, row)}
    # Fallback: return as list
    return {"values": [_serialize_value(v) for v in row]}


@IntegrationRegistry.register("database_query")
class DatabaseQueryIntegration(IntegrationBase):
    """Database query execution integration.

    Supports multiple database backends:
    - SQLite: Use connection_string like "sqlite:///path/to/db.sqlite"
    - PostgreSQL: Use connection_string like "postgresql://user:pass@host:port/dbname"
    - MySQL: Use connection_string like "mysql://user:pass@host:port/dbname"

    Default Variables (stored via integration variables):
        connection_string: Default database connection string
        max_rows: Default maximum number of rows to return

    Inputs:
        connection_string: Database connection string (SQLAlchemy format)
        query: SQL query to execute
        parameters: Optional dict or list of query parameters
        max_rows: Maximum number of rows to return (default: 1000)

    Outputs:
        row_count: Number of rows returned
        columns: List of column names
        results: List of row dictionaries (limited by max_rows)
        duration_seconds: Query execution time
        affected_rows: Number of rows affected (for INSERT/UPDATE/DELETE)
    """

    integration_type = "database_query"

    async def execute(self, inputs: dict) -> dict:
        """Execute a database query."""
        from sqlalchemy import create_engine, text
        from sqlalchemy.exc import SQLAlchemyError

        # Merge inputs with stored defaults
        merged = self.merge_inputs_with_defaults(inputs)

        connection_string = merged["connection_string"]
        query = merged["query"]
        parameters = merged.get("parameters")
        max_rows = merged.get("max_rows", 1000)

        start_time = time.time()

        try:
            engine = create_engine(connection_string)

            with engine.begin() as conn:
                # Execute query with parameters
                if parameters:
                    if isinstance(parameters, list):
                        # Positional parameters
                        result = conn.execute(text(query), parameters)
                    else:
                        # Named parameters
                        result = conn.execute(text(query), parameters)
                else:
                    result = conn.execute(text(query))

                duration = time.time() - start_time

                # Get column names if available
                columns = list(result.keys()) if result.returns_rows else []

                # Fetch results if it's a SELECT-like query
                if result.returns_rows:
                    rows = result.fetchmany(max_rows)
                    results = [_serialize_row(row, columns) for row in rows]
                    row_count = len(results)
                    affected_rows = None
                else:
                    # For INSERT/UPDATE/DELETE
                    results = []
                    row_count = 0
                    affected_rows = result.rowcount

                # Create output data
                output_data = {
                    "row_count": row_count,
                    "columns": columns,
                    "results": results,
                    "duration_seconds": duration,
                    "affected_rows": affected_rows,
                    "query": query,
                }

                # Create JSON artifact
                artifact_data = json.dumps(
                    {
                        "columns": columns,
                        "results": results,
                        "row_count": row_count,
                        "duration_seconds": duration,
                    },
                    indent=2,
                )

                return {
                    "outputs": output_data,
                    "artifacts": [
                        {
                            "type": "application/json",
                            "data": artifact_data.encode("utf-8"),
                            "metadata": {
                                "row_count": row_count,
                                "columns": columns,
                            },
                        }
                    ],
                }

        except SQLAlchemyError as e:
            duration = time.time() - start_time
            error_msg = str(e)
            return {
                "outputs": {
                    "error": error_msg,
                    "duration_seconds": duration,
                    "query": query,
                },
                "artifacts": [
                    {
                        "type": "application/json",
                        "data": json.dumps({"error": error_msg}).encode("utf-8"),
                        "metadata": {"error": True},
                    }
                ],
            }

    def validate_inputs(self, inputs: dict) -> bool:
        """Validate inputs for database query.

        Validates against merged inputs (including defaults).
        """
        merged = self.merge_inputs_with_defaults(inputs)
        if "connection_string" not in merged:
            return False
        if "query" not in merged:
            return False
        return True
