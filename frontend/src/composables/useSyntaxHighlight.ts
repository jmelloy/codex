import hljs from 'highlight.js'

/**
 * Composable for syntax highlighting code with highlight.js
 */
export function useSyntaxHighlight() {
  /**
   * Map file extensions to highlight.js language names
   */
  const extensionToLanguage: Record<string, string> = {
    // JavaScript/TypeScript
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'mjs': 'javascript',
    'cjs': 'javascript',
    // Python
    'py': 'python',
    'pyw': 'python',
    'pyx': 'python',
    // Web
    'html': 'xml',
    'htm': 'xml',
    'css': 'css',
    'scss': 'scss',
    'sass': 'scss',
    'less': 'less',
    'vue': 'xml',
    'svelte': 'xml',
    // Data formats
    'json': 'json',
    'yaml': 'yaml',
    'yml': 'yaml',
    'xml': 'xml',
    'toml': 'ini',
    // Shell
    'sh': 'bash',
    'bash': 'bash',
    'zsh': 'bash',
    'fish': 'bash',
    'ps1': 'powershell',
    'bat': 'dos',
    'cmd': 'dos',
    // Systems
    'c': 'c',
    'h': 'c',
    'cpp': 'cpp',
    'cc': 'cpp',
    'cxx': 'cpp',
    'hpp': 'cpp',
    'hxx': 'cpp',
    'cs': 'csharp',
    'java': 'java',
    'kt': 'kotlin',
    'kts': 'kotlin',
    'scala': 'scala',
    'go': 'go',
    'rs': 'rust',
    'swift': 'swift',
    // Scripting
    'rb': 'ruby',
    'php': 'php',
    'pl': 'perl',
    'pm': 'perl',
    'lua': 'lua',
    'r': 'r',
    'R': 'r',
    // Functional
    'hs': 'haskell',
    'ml': 'ocaml',
    'fs': 'fsharp',
    'fsx': 'fsharp',
    'clj': 'clojure',
    'cljs': 'clojure',
    'ex': 'elixir',
    'exs': 'elixir',
    'erl': 'erlang',
    // Config
    'ini': 'ini',
    'conf': 'ini',
    'cfg': 'ini',
    'properties': 'properties',
    'env': 'bash',
    // Documentation
    'md': 'markdown',
    'markdown': 'markdown',
    'rst': 'plaintext',
    'tex': 'latex',
    // Database
    'sql': 'sql',
    'graphql': 'graphql',
    'gql': 'graphql',
    // Build
    'dockerfile': 'dockerfile',
    'makefile': 'makefile',
    'cmake': 'cmake',
    'gradle': 'gradle',
    // Other
    'diff': 'diff',
    'patch': 'diff',
    'vim': 'vim',
    'nginx': 'nginx',
    'apache': 'apache'
  }

  /**
   * Detect language from filename
   */
  const detectLanguageFromFilename = (filename: string): string | undefined => {
    const ext = filename.split('.').pop()?.toLowerCase()
    return ext ? extensionToLanguage[ext] : undefined
  }

  /**
   * Escape HTML special characters
   */
  const escapeHtml = (text: string): string => {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  /**
   * Highlight code with automatic language detection
   */
  const highlightCode = (code: string, language?: string): string => {
    try {
      if (language && hljs.getLanguage(language)) {
        return hljs.highlight(code, { language }).value
      } else {
        const result = hljs.highlightAuto(code)
        return result.value
      }
    } catch (err) {
      console.error('Syntax highlighting error:', err)
      return escapeHtml(code)
    }
  }

  /**
   * Get detected language name
   */
  const detectLanguage = (code: string, filename?: string): string => {
    if (filename) {
      const lang = detectLanguageFromFilename(filename)
      if (lang && hljs.getLanguage(lang)) {
        return lang
      }
    }

    try {
      const result = hljs.highlightAuto(code)
      return result.language || 'plaintext'
    } catch {
      return 'plaintext'
    }
  }

  return {
    extensionToLanguage,
    detectLanguageFromFilename,
    escapeHtml,
    highlightCode,
    detectLanguage
  }
}
