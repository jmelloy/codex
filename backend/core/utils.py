"""Utility functions for Lab Notebook."""

import re


def slugify(text: str) -> str:
    """Convert title to filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def format_table(columns: list[str], rows: list[dict]) -> str:
    """Format data as an ASCII table.

    Args:
        columns: List of column names
        rows: List of row dictionaries

    Returns:
        Formatted ASCII table string
    """
    if not columns:
        return ""

    # Convert all values to strings and calculate column widths
    str_rows = []
    for row in rows:
        str_row = {col: str(row.get(col, "")) for col in columns}
        str_rows.append(str_row)

    # Calculate column widths (minimum of header width or max value width)
    col_widths = {}
    for col in columns:
        header_width = len(col)
        max_value_width = max((len(row[col]) for row in str_rows), default=0)
        col_widths[col] = max(header_width, max_value_width)

    # Build separator line
    separator = "+" + "+".join("-" * (col_widths[col] + 2) for col in columns) + "+"

    # Build header row
    header = "|" + "|".join(f" {col.ljust(col_widths[col])} " for col in columns) + "|"

    # Build data rows
    data_lines = []
    for row in str_rows:
        line = (
            "|"
            + "|".join(f" {row[col].ljust(col_widths[col])} " for col in columns)
            + "|"
        )
        data_lines.append(line)

    # Combine all parts
    lines = [separator, header, separator]
    lines.extend(data_lines)
    lines.append(separator)

    return "\n".join(lines)
