#!/usr/bin/env tsx
/**
 * Codex Plugin Build Script
 *
 * Compiles Vue components from plugins into ES modules that can be
 * dynamically loaded by the frontend.
 *
 * Usage:
 *   npm run build                     - Build all plugin components
 *   npm run build -- --plugin=PLUGIN  - Build a specific plugin only
 *   npm run build:watch               - Watch mode for development
 *   npm run clean                     - Remove all dist directories
 *
 * Examples:
 *   npm run build -- --plugin=weather-api
 *   npm run build -- --plugin=opengraph
 */

import { build, type InlineConfig } from "vite"
import vue from "@vitejs/plugin-vue"
import * as fs from "fs"
import * as path from "path"
import { glob } from "glob"
import * as yaml from "js-yaml"
import { execSync } from "child_process"

const PLUGINS_DIR = path.dirname(new URL(import.meta.url).pathname)

interface PluginManifest {
  id: string
  name: string
  version: string
  type: "view" | "theme" | "integration"
  blocks?: Array<{
    id: string
    name: string
    component?: string
    description?: string
    icon?: string
  }>
}

interface DiscoveredPlugin {
  manifest: PluginManifest
  directory: string // The actual directory name (may differ from manifest.id)
}

interface ComponentEntry {
  pluginId: string
  pluginDir: string // Directory name for file paths
  pluginName: string
  pluginVersion: string
  blockId: string
  blockName: string
  componentFile: string
  outputFile: string
  icon?: string
  description?: string
}

interface PluginComponentManifest {
  version: string
  buildTime: string
  components: Record<
    string,
    {
      pluginId: string
      pluginName: string
      pluginVersion: string
      blockId: string
      blockName: string
      file: string
      icon?: string
      description?: string
    }
  >
}

/**
 * Check if a plugin has its own package.json
 */
function hasPluginPackageJson(pluginDir: string): boolean {
  const packageJsonPath = path.join(PLUGINS_DIR, pluginDir, "package.json")
  return fs.existsSync(packageJsonPath)
}

/**
 * Install plugin-specific dependencies
 */
function installPluginDependencies(pluginDir: string): void {
  const pluginPath = path.join(PLUGINS_DIR, pluginDir)
  const packageJsonPath = path.join(pluginPath, "package.json")
  
  if (!fs.existsSync(packageJsonPath)) {
    return
  }
  
  console.log(`  Installing dependencies for ${pluginDir}...`)
  
  try {
    // Run npm install in the plugin directory
    execSync("npm install", {
      cwd: pluginPath,
      stdio: "inherit",
    })
    
    console.log(`  ✓ Dependencies installed for ${pluginDir}`)
  } catch (err) {
    console.error(`  ✗ Failed to install dependencies for ${pluginDir}:`, err)
    throw err
  }
}

/**
 * Find all plugin manifests
 */
async function discoverPlugins(): Promise<Map<string, DiscoveredPlugin>> {
  const plugins = new Map<string, DiscoveredPlugin>()

  // Look for plugin.yaml, theme.yaml, or integration.yaml in each plugin directory
  const manifestFiles = await glob("*/+(plugin|theme|integration).yaml", {
    cwd: PLUGINS_DIR,
    absolute: true,
  })

  for (const manifestPath of manifestFiles) {
    try {
      const content = fs.readFileSync(manifestPath, "utf-8")
      const manifest = yaml.load(content) as PluginManifest
      if (manifest?.id) {
        // Get the actual directory name from the path
        const directory = path.basename(path.dirname(manifestPath))
        plugins.set(manifest.id, { manifest, directory })
      }
    } catch (err) {
      console.warn(`Warning: Could not parse ${manifestPath}:`, err)
    }
  }

  return plugins
}

/**
 * Find Vue components in a plugin directory
 */
async function findPluginComponents(
  pluginDir: string
): Promise<Map<string, string>> {
  const components = new Map<string, string>()

  const vueFiles = await glob("**/*.vue", {
    cwd: pluginDir,
    absolute: true,
    ignore: ["**/dist/**", "**/node_modules/**"],
  })

  for (const vuePath of vueFiles) {
    const componentName = path.basename(vuePath, ".vue")
    components.set(componentName, vuePath)
  }

  return components
}

/**
 * Discover all components that need to be built
 */
async function discoverComponents(): Promise<ComponentEntry[]> {
  const entries: ComponentEntry[] = []
  const plugins = await discoverPlugins()

  for (const [pluginId, { manifest, directory }] of plugins) {
    const pluginDir = path.join(PLUGINS_DIR, directory)

    if (!fs.existsSync(pluginDir)) {
      continue
    }

    // Find all Vue components in the plugin
    const components = await findPluginComponents(pluginDir)

    if (components.size === 0) {
      continue
    }

    // If plugin has blocks defined, map them to components
    if (manifest.blocks && manifest.blocks.length > 0) {
      for (const block of manifest.blocks) {
        // Try to find the component file
        let componentFile: string | undefined

        if (block.component) {
          // Explicit component path in manifest
          const explicitPath = path.join(pluginDir, block.component)
          if (fs.existsSync(explicitPath)) {
            componentFile = explicitPath
          }
        }

        if (!componentFile) {
          // Try common naming conventions
          // Convert kebab-case to PascalCase for component names
          const pascalId = pascalCase(block.id)
          const possibleNames = [
            `${pascalId}Block`,         // e.g., "link-preview" -> "LinkPreviewBlock"
            pascalId,                    // e.g., "link-preview" -> "LinkPreview"
            `${capitalize(block.id)}Block`, // e.g., "weather" -> "WeatherBlock"
            capitalize(block.id),        // e.g., "weather" -> "Weather"
            block.id,                    // exact match
          ]

          for (const name of possibleNames) {
            if (components.has(name)) {
              componentFile = components.get(name)
              break
            }
          }
        }

        if (componentFile) {
          entries.push({
            pluginId,
            pluginDir: directory,
            pluginName: manifest.name,
            pluginVersion: manifest.version,
            blockId: block.id,
            blockName: block.name,
            componentFile,
            outputFile: `${block.id}.js`,
            icon: block.icon,
            description: block.description,
          })
        }
      }
    } else {
      // No blocks defined, build all Vue components found
      for (const [componentName, componentPath] of components) {
        const blockId = kebabCase(componentName.replace(/Block$/, ""))
        entries.push({
          pluginId,
          pluginDir: directory,
          pluginName: manifest.name,
          pluginVersion: manifest.version,
          blockId,
          blockName: componentName,
          componentFile: componentPath,
          outputFile: `${blockId}.js`,
        })
      }
    }
  }

  return entries
}

/**
 * Build a single component
 */
async function buildComponent(entry: ComponentEntry): Promise<void> {
  const outputDir = path.join(PLUGINS_DIR, entry.pluginDir, "dist")
  const pluginPath = path.join(PLUGINS_DIR, entry.pluginDir)

  const config: InlineConfig = {
    plugins: [vue()],
    build: {
      lib: {
        entry: entry.componentFile,
        name: pascalCase(entry.blockId),
        formats: ["es"],
        fileName: () => entry.outputFile,
      },
      outDir: outputDir,
      emptyOutDir: false,
      rollupOptions: {
        external: ["vue"],
        output: {
          globals: {
            vue: "Vue",
          },
        },
      },
      minify: false, // Keep readable for debugging
      sourcemap: true,
    },
    logLevel: "warn",
    // Use plugin-specific root if it has its own package.json
    root: hasPluginPackageJson(entry.pluginDir) ? pluginPath : PLUGINS_DIR,
  }

  await build(config)
}

/**
 * Generate the component manifest
 */
function generateManifest(entries: ComponentEntry[]): PluginComponentManifest {
  const manifest: PluginComponentManifest = {
    version: "1.0.0",
    buildTime: new Date().toISOString(),
    components: {},
  }

  for (const entry of entries) {
    const key = `${entry.pluginDir}/${entry.blockId}`
    manifest.components[key] = {
      pluginId: entry.pluginId,
      pluginName: entry.pluginName,
      pluginVersion: entry.pluginVersion,
      blockId: entry.blockId,
      blockName: entry.blockName,
      file: `${entry.pluginDir}/dist/${entry.outputFile}`,
      icon: entry.icon,
      description: entry.description,
    }
  }

  return manifest
}

/**
 * Clean all dist directories
 */
async function clean(): Promise<void> {
  console.log("Cleaning plugin dist directories...")

  const distDirs = await glob("*/dist", {
    cwd: PLUGINS_DIR,
    absolute: true,
  })

  for (const distDir of distDirs) {
    fs.rmSync(distDir, { recursive: true, force: true })
    console.log(`  Removed: ${path.relative(PLUGINS_DIR, distDir)}`)
  }

  const manifestPath = path.join(PLUGINS_DIR, "components.json")
  if (fs.existsSync(manifestPath)) {
    fs.rmSync(manifestPath)
    console.log("  Removed: components.json")
  }

  console.log("Clean complete!")
}

/**
 * Main build function
 */
async function main(): Promise<void> {
  const args = process.argv.slice(2)

  if (args.includes("--clean")) {
    await clean()
    return
  }

  const watchMode = args.includes("--watch")
  
  // Check for plugin filter argument
  const pluginArg = args.find((arg) => arg.startsWith("--plugin="))
  let pluginFilter: string | undefined
  
  if (pluginArg) {
    pluginFilter = pluginArg.split("=")[1]
    // Validate that a plugin name was provided
    if (!pluginFilter || pluginFilter.trim() === "") {
      console.error("Error: --plugin flag requires a plugin name")
      console.error("Usage: npm run build -- --plugin=weather-api")
      process.exit(1)
    }
  }

  console.log("Codex Plugin Build")
  console.log("==================")
  console.log(`Mode: ${watchMode ? "watch" : "build"}`)
  if (pluginFilter) {
    console.log(`Filter: ${pluginFilter}`)
  }
  console.log("")

  // Discover components to build
  console.log("Discovering plugin components...")
  let entries = await discoverComponents()
  
  // Filter by plugin if specified
  if (pluginFilter) {
    entries = entries.filter(
      (entry) =>
        entry.pluginId === pluginFilter || entry.pluginDir === pluginFilter
    )
    if (entries.length === 0) {
      console.error(`No components found for plugin: ${pluginFilter}`)
      console.error(
        "Available plugins:",
        Array.from(new Set((await discoverComponents()).map((e) => e.pluginId)))
      )
      process.exit(1)
    }
  }

  if (entries.length === 0) {
    console.log("No Vue components found in plugins.")
    return
  }

  console.log(`Found ${entries.length} component(s) to build:`)
  for (const entry of entries) {
    console.log(`  - ${entry.pluginId}/${entry.blockId} (${entry.blockName})`)
  }
  console.log("")

  // Install plugin-specific dependencies
  const pluginsWithDeps = new Set<string>()
  for (const entry of entries) {
    if (hasPluginPackageJson(entry.pluginDir)) {
      pluginsWithDeps.add(entry.pluginDir)
    }
  }
  
  if (pluginsWithDeps.size > 0) {
    console.log("Installing plugin-specific dependencies...")
    for (const pluginDir of pluginsWithDeps) {
      installPluginDependencies(pluginDir)
    }
    console.log("")
  }

  // Build each component
  console.log("Building components...")
  for (const entry of entries) {
    console.log(`  Building: ${entry.pluginDir}/${entry.blockId}...`)
    try {
      await buildComponent(entry)
      console.log(`    -> ${entry.pluginDir}/dist/${entry.outputFile}`)
    } catch (err) {
      console.error(`    Error building ${entry.pluginDir}/${entry.blockId}:`, err)
    }
  }
  console.log("")

  // Generate manifest
  console.log("Generating component manifest...")
  const manifest = generateManifest(entries)
  const manifestPath = path.join(PLUGINS_DIR, "components.json")
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2))
  console.log(`  -> components.json`)
  console.log("")

  console.log("Build complete!")

  if (watchMode) {
    console.log("")
    console.log("Watching for changes... (Ctrl+C to stop)")
    // For watch mode, we'd need to set up file watchers
    // This is a simplified version - full watch mode would use chokidar
    const { watch } = await import("fs")
    for (const entry of entries) {
      const dir = path.dirname(entry.componentFile)
      watch(dir, { recursive: true }, async (eventType, filename) => {
        if (filename?.endsWith(".vue")) {
          console.log(`\nChange detected: ${filename}`)
          try {
            await buildComponent(entry)
            console.log(`  Rebuilt: ${entry.pluginId}/${entry.blockId}`)
          } catch (err) {
            console.error(`  Error:`, err)
          }
        }
      })
    }
  }
}

// Utility functions
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

function pascalCase(str: string): string {
  return str
    .split(/[-_]/)
    .map(capitalize)
    .join("")
}

function kebabCase(str: string): string {
  return str
    .replace(/([a-z])([A-Z])/g, "$1-$2")
    .replace(/[\s_]+/g, "-")
    .toLowerCase()
}

// Run the build
main().catch((err) => {
  console.error("Build failed:", err)
  process.exit(1)
})
