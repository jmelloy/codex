"""Register filesystem plugins into the system database.

Scans the plugins directory for manifest.yml files and registers each plugin
in the database. This ensures all plugin blocks, endpoints, and configuration
are discoverable via the API.

Usage:
    python -m codex.scripts.register_plugins
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from sqlmodel import select

# Ensure backend is on the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from codex.db.database import async_session_maker, init_system_db
from codex.db.models import Plugin


async def register_plugins(plugins_dir: str | None = None):
    """Scan plugins directory and register all plugins in the database."""
    if plugins_dir is None:
        plugins_dir = os.getenv(
            "CODEX_PLUGINS_DIR",
            str(Path(__file__).parent.parent.parent.parent / "backend" / "plugins"),
        )

    plugins_path = Path(plugins_dir)
    if not plugins_path.exists():
        print(f"Plugins directory not found: {plugins_path}")
        return

    await init_system_db()

    registered = 0
    async with async_session_maker() as session:
        for manifest_file in sorted(plugins_path.glob("*/manifest.yml")):
            try:
                with open(manifest_file) as f:
                    manifest = yaml.safe_load(f)

                plugin_id = manifest.get("id")
                if not plugin_id:
                    print(f"  Skipping {manifest_file}: no 'id' field")
                    continue

                # Check if already exists
                stmt = select(Plugin).where(Plugin.plugin_id == plugin_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                now = datetime.now(UTC)

                if existing:
                    existing.name = manifest.get("name", plugin_id)
                    existing.version = manifest.get("version", "0.0.0")
                    existing.type = manifest.get("type", "integration")
                    existing.manifest = manifest
                    existing.updated_at = now
                    session.add(existing)
                    print(f"  Updated: {plugin_id} v{manifest.get('version', '?')}")
                else:
                    plugin = Plugin(
                        plugin_id=plugin_id,
                        name=manifest.get("name", plugin_id),
                        version=manifest.get("version", "0.0.0"),
                        type=manifest.get("type", "integration"),
                        enabled=True,
                        manifest=manifest,
                        installed_at=now,
                        updated_at=now,
                    )
                    session.add(plugin)
                    print(f"  Registered: {plugin_id} v{manifest.get('version', '?')}")

                registered += 1
            except Exception as e:
                print(f"  Error processing {manifest_file}: {e}")

        await session.commit()

    print(f"\nDone. {registered} plugin(s) processed.")


if __name__ == "__main__":
    asyncio.run(register_plugins())
