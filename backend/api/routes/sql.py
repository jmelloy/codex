"""SQL execution API routes for the SQL Viewer."""

import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


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


class SQLExecuteRequest(BaseModel):
    """Request model for executing SQL directly."""

    workspace_path: Optional[str] = None
    connection_string: str
    query: str
    parameters: Optional[dict] = None
    max_rows: int = 1000


class SQLExecuteResponse(BaseModel):
    """Response model for SQL execution."""

    row_count: int
    columns: list[str]
    results: list[dict]
    duration_seconds: float
    affected_rows: Optional[int] = None
    error: Optional[str] = None
    query: str


@router.post("/execute", response_model=SQLExecuteResponse)
async def execute_sql(request: SQLExecuteRequest):
    """Execute SQL query directly without creating an entry.

    This endpoint is used by the SQL Viewer for quick query execution
    when the user doesn't want to save the query as an experiment.
    """
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import SQLAlchemyError

    start_time = time.time()

    try:
        engine = create_engine(request.connection_string)

        with engine.connect() as conn:
            # Execute query with parameters
            if request.parameters:
                result = conn.execute(text(request.query), request.parameters)
            else:
                result = conn.execute(text(request.query))

            duration = time.time() - start_time

            # Get column names if available
            columns = list(result.keys()) if result.returns_rows else []

            # Fetch results if it's a SELECT-like query
            if result.returns_rows:
                rows = result.fetchmany(request.max_rows)
                results = [_serialize_row(row, columns) for row in rows]
                row_count = len(results)
                affected_rows = None
            else:
                # For INSERT/UPDATE/DELETE, commit the transaction
                conn.commit()
                results = []
                row_count = 0
                affected_rows = result.rowcount

            return SQLExecuteResponse(
                row_count=row_count,
                columns=columns,
                results=results,
                duration_seconds=duration,
                affected_rows=affected_rows,
                query=request.query,
            )

    except SQLAlchemyError as e:
        duration = time.time() - start_time
        return SQLExecuteResponse(
            row_count=0,
            columns=[],
            results=[],
            duration_seconds=duration,
            error=str(e),
            query=request.query,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
