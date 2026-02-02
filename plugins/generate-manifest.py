#!/usr/bin/env python3
"""
Generate combined manifest.yml from individual plugin manifests.

This script scans all plugin directories and combines their individual
manifest files (plugin.yaml, theme.yaml, integration.yaml) into a single
manifest.yml file.

Usage:
    python generate-manifest.py

The script will:
1. Find all plugin directories with manifest files
2. Load each manifest and add a _directory field
3. Combine all manifests into a single manifest.yml
4. Preserve all plugin configuration including templates, views, themes, etc.
"""

import yaml
from pathlib import Path
from typing import Any


def generate_combined_manifest(plugins_dir: Path, output_path: Path | None = None) -> None:
    """Generate combined manifest.yml from individual plugin manifests.
    
    Args:
        plugins_dir: Directory containing plugin subdirectories
        output_path: Path to output manifest.yml (defaults to plugins_dir/manifest.yml)
    """
    if output_path is None:
        output_path = plugins_dir / "manifest.yml"
    
    # Initialize the combined manifest structure
    combined_manifest: dict[str, Any] = {
        'version': '1.0.0',
        'plugins': []
    }
    
    # Iterate through all plugin directories
    for plugin_path in sorted(plugins_dir.iterdir()):
        if not plugin_path.is_dir():
            continue
        
        # Skip non-plugin directories
        if plugin_path.name in ['shared', 'node_modules', 'dist', '.git']:
            continue
        
        # Look for manifest files
        manifest_files = ['plugin.yaml', 'theme.yaml', 'integration.yaml']
        for manifest_file in manifest_files:
            manifest_path = plugin_path / manifest_file
            if manifest_path.exists():
                print(f"Processing {plugin_path.name}/{manifest_file}")
                with open(manifest_path, 'r') as f:
                    plugin_data = yaml.safe_load(f)
                
                # Add plugin directory name for reference
                plugin_data['_directory'] = plugin_path.name
                
                combined_manifest['plugins'].append(plugin_data)
                break  # Only process one manifest per plugin
    
    # Write the combined manifest
    with open(output_path, 'w') as f:
        yaml.dump(combined_manifest, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"\n✓ Generated {output_path.name} with {len(combined_manifest['plugins'])} plugins")


def main():
    """Main entry point."""
    # Get the plugins directory (where this script is located)
    plugins_dir = Path(__file__).parent
    
    print("Generating combined manifest from individual plugin files...")
    print("=" * 60)
    
    generate_combined_manifest(plugins_dir)
    
    print("=" * 60)
    print("✓ Done!")
    print("\nThe manifest.yml file can now be used by:")
    print("  - Python plugin loader (backend/codex/plugins/loader.py)")
    print("  - TypeScript build script (plugins/build.ts)")
    print("\nTo regenerate this file after adding/updating plugins, run:")
    print("  python plugins/generate-manifest.py")


if __name__ == "__main__":
    main()
