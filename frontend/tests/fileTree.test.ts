import { describe, it, expect } from 'vitest'
import { buildFileTree } from '../src/utils/fileTree'
import type { FileMetadata } from '../src/services/codex'

describe('buildFileTree', () => {
  it('should build a flat list for files without folders', () => {
    const files: FileMetadata[] = [
      {
        id: 1,
        notebook_id: 1,
        path: 'README.md',
        filename: 'README.md',
        file_type: 'markdown',
        size: 100,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      },
      {
        id: 2,
        notebook_id: 1,
        path: 'notes.md',
        filename: 'notes.md',
        file_type: 'markdown',
        size: 200,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      }
    ]

    const tree = buildFileTree(files)
    
    expect(tree).toHaveLength(2)
    // Files are sorted alphabetically using localeCompare
    // In this case, 'notes.md' sorts before 'README.md'
    expect(tree[0].type).toBe('file')
    expect(tree[0].name).toBe('notes.md')
    expect(tree[1].type).toBe('file')
    expect(tree[1].name).toBe('README.md')
  })

  it('should create folders for nested paths', () => {
    const files: FileMetadata[] = [
      {
        id: 1,
        notebook_id: 1,
        path: 'docs/README.md',
        filename: 'README.md',
        file_type: 'markdown',
        size: 100,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      },
      {
        id: 2,
        notebook_id: 1,
        path: 'docs/setup.md',
        filename: 'setup.md',
        file_type: 'markdown',
        size: 200,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      }
    ]

    const tree = buildFileTree(files)
    
    expect(tree).toHaveLength(1)
    expect(tree[0].type).toBe('folder')
    expect(tree[0].name).toBe('docs')
    expect(tree[0].children).toHaveLength(2)
    expect(tree[0].children![0].name).toBe('README.md')
    expect(tree[0].children![1].name).toBe('setup.md')
  })

  it('should handle deeply nested folders', () => {
    const files: FileMetadata[] = [
      {
        id: 1,
        notebook_id: 1,
        path: 'src/utils/helpers/string.ts',
        filename: 'string.ts',
        file_type: 'text',
        size: 100,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      }
    ]

    const tree = buildFileTree(files)
    
    expect(tree).toHaveLength(1)
    expect(tree[0].type).toBe('folder')
    expect(tree[0].name).toBe('src')
    expect(tree[0].children).toHaveLength(1)
    expect(tree[0].children![0].type).toBe('folder')
    expect(tree[0].children![0].name).toBe('utils')
    expect(tree[0].children![0].children).toHaveLength(1)
    expect(tree[0].children![0].children![0].type).toBe('folder')
    expect(tree[0].children![0].children![0].name).toBe('helpers')
    expect(tree[0].children![0].children![0].children).toHaveLength(1)
    expect(tree[0].children![0].children![0].children![0].type).toBe('file')
    expect(tree[0].children![0].children![0].children![0].name).toBe('string.ts')
  })

  it('should sort folders before files', () => {
    const files: FileMetadata[] = [
      {
        id: 1,
        notebook_id: 1,
        path: 'root.md',
        filename: 'root.md',
        file_type: 'markdown',
        size: 100,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      },
      {
        id: 2,
        notebook_id: 1,
        path: 'docs/README.md',
        filename: 'README.md',
        file_type: 'markdown',
        size: 200,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      }
    ]

    const tree = buildFileTree(files)
    
    expect(tree).toHaveLength(2)
    expect(tree[0].type).toBe('folder')
    expect(tree[0].name).toBe('docs')
    expect(tree[1].type).toBe('file')
    expect(tree[1].name).toBe('root.md')
  })

  it('should handle mixed folder structures', () => {
    const files: FileMetadata[] = [
      {
        id: 1,
        notebook_id: 1,
        path: 'src/components/Button.vue',
        filename: 'Button.vue',
        file_type: 'text',
        size: 100,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      },
      {
        id: 2,
        notebook_id: 1,
        path: 'src/utils/helper.ts',
        filename: 'helper.ts',
        file_type: 'text',
        size: 200,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      },
      {
        id: 3,
        notebook_id: 1,
        path: 'README.md',
        filename: 'README.md',
        file_type: 'markdown',
        size: 300,
        created_at: '2024-01-01',
        updated_at: '2024-01-01'
      }
    ]

    const tree = buildFileTree(files)
    
    expect(tree).toHaveLength(2)
    // Folder first
    expect(tree[0].type).toBe('folder')
    expect(tree[0].name).toBe('src')
    expect(tree[0].children).toHaveLength(2)
    expect(tree[0].children![0].name).toBe('components')
    expect(tree[0].children![1].name).toBe('utils')
    // Then file
    expect(tree[1].type).toBe('file')
    expect(tree[1].name).toBe('README.md')
  })
})
