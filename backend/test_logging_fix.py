#!/usr/bin/env python
"""Test script to verify logging isn't clobbered by notebook migrations."""

import logging
import logging.config
import tempfile
from pathlib import Path

# Setup logging before importing anything else
from codex.core.logging import get_logging_config

logging.config.dictConfig(get_logging_config(log_level="INFO", log_format="colored"))

# Now import codex modules
from codex.db.database import init_notebook_db

# Get loggers
root_logger = logging.getLogger()
uvicorn_access_logger = logging.getLogger("uvicorn.access")

print("=" * 80)
print("Testing logging configuration before and after notebook migration")
print("=" * 80)

# Log before migration
print("\nBefore migration:")
print(f"Root logger level: {root_logger.level} (handlers: {len(root_logger.handlers)})")
print(f"Uvicorn access logger level: {uvicorn_access_logger.level} (handlers: {len(uvicorn_access_logger.handlers)})")

root_logger.info("Root logger test message BEFORE migration")
uvicorn_access_logger.info("Uvicorn access logger test message BEFORE migration")

# Run a notebook migration
print("\nRunning notebook migration...")
with tempfile.TemporaryDirectory() as tmpdir:
    notebook_path = Path(tmpdir) / "test_notebook"
    notebook_path.mkdir()
    init_notebook_db(str(notebook_path))

# Log after migration
print("\nAfter migration:")
print(f"Root logger level: {root_logger.level} (handlers: {len(root_logger.handlers)})")
print(f"Uvicorn access logger level: {uvicorn_access_logger.level} (handlers: {len(uvicorn_access_logger.handlers)})")

root_logger.info("Root logger test message AFTER migration")
uvicorn_access_logger.info("Uvicorn access logger test message AFTER migration")

print("\n" + "=" * 80)
print("If you see all 4 log messages above, the fix is working!")
print("=" * 80)
