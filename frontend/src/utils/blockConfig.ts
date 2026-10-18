/** Parse YAML-like block config: JSON, a ```lang code fence, or plain `key: value` lines (one level of nesting). */
export function parseBlockConfig(content: string): Record<string, any> {
  // Try JSON first
  const trimmed = content.trim()
  if (trimmed.startsWith("{")) {
    try {
      return JSON.parse(trimmed)
    } catch {
      // fall through to YAML parsing
    }
  }
  // Strip code fence markers: ```database\n...\n``` or ```api\n...\n```
  const match = trimmed.match(/^```\w*\n([\s\S]*?)\n```$/)
  const body = match ? match[1] : trimmed
  const config: Record<string, any> = {}
  let currentParent: string | null = null
  body.split("\n").forEach((line) => {
    const indented = line.match(/^[ \t]+([\w-]+):\s*(.+)$/)
    if (indented && indented[1] && indented[2] && currentParent) {
      if (typeof config[currentParent] !== "object" || config[currentParent] === null) {
        config[currentParent] = {}
      }
      config[currentParent][indented[1]] = indented[2].trim()
      return
    }
    const kv = line.match(/^([\w-]+):\s*(.+)$/)
    if (kv && kv[1] && kv[2]) {
      config[kv[1]] = kv[2].trim()
      currentParent = null
      return
    }
    const parent = line.match(/^([\w-]+):\s*$/)
    if (parent && parent[1]) {
      currentParent = parent[1]
      config[currentParent] = {}
    }
  })
  return config
}
