import { describe, it, expect } from "vitest"
import {
  buildFileTree,
  findNode,
  findParentNode,
  insertFileNode,
  insertFolderNode,
  removeNode,
  updateFileNode,
  mergeFolderContents,
  getAllFiles,
  moveNode,
  type FileTreeNode,
} from "../../utils/fileTree"
import type { FileMetadata, FolderWithFiles } from "../../services/codex"

// Helper to create a mock file
function createMockFile(overrides: Partial<FileMetadata> = {}): FileMetadata {
  return {
    id: 1,
    notebook_id: 1,
    path: "test.md",
    filename: "test.md",
    content_type: "text/markdown",
    size: 100,
    created_at: "2024-01-01",
    updated_at: "2024-01-01",
    ...overrides,
  }
}

describe("fileTree utilities", () => {
  describe("buildFileTree", () => {
    it("builds a flat list for files without folders", () => {
      const files = [
        createMockFile({ id: 1, path: "README.md", filename: "README.md" }),
        createMockFile({ id: 2, path: "notes.md", filename: "notes.md" }),
      ]

      const tree = buildFileTree(files)

      expect(tree).toHaveLength(2)
      expect(tree.every((n) => n.type === "file")).toBe(true)
    })

    it("creates folders for nested paths", () => {
      const files = [
        createMockFile({ id: 1, path: "docs/README.md", filename: "README.md" }),
      ]

      const tree = buildFileTree(files)

      expect(tree).toHaveLength(1)
      expect(tree[0].type).toBe("folder")
      expect(tree[0].name).toBe("docs")
      expect(tree[0].children).toHaveLength(1)
      expect(tree[0].children![0].name).toBe("README.md")
    })

    it("handles deeply nested folders", () => {
      const files = [
        createMockFile({ id: 1, path: "a/b/c/d/file.md", filename: "file.md" }),
      ]

      const tree = buildFileTree(files)

      expect(tree[0].name).toBe("a")
      expect(tree[0].children![0].name).toBe("b")
      expect(tree[0].children![0].children![0].name).toBe("c")
      expect(tree[0].children![0].children![0].children![0].name).toBe("d")
      expect(tree[0].children![0].children![0].children![0].children![0].name).toBe("file.md")
    })

    it("sorts folders before files", () => {
      const files = [
        createMockFile({ id: 1, path: "zebra.md", filename: "zebra.md" }),
        createMockFile({ id: 2, path: "alpha/file.md", filename: "file.md" }),
      ]

      const tree = buildFileTree(files)

      expect(tree[0].type).toBe("folder")
      expect(tree[0].name).toBe("alpha")
      expect(tree[1].type).toBe("file")
      expect(tree[1].name).toBe("zebra.md")
    })

    it("sorts alphabetically within same type", () => {
      const files = [
        createMockFile({ id: 1, path: "zebra.md", filename: "zebra.md" }),
        createMockFile({ id: 2, path: "alpha.md", filename: "alpha.md" }),
      ]

      const tree = buildFileTree(files)

      expect(tree[0].name).toBe("alpha.md")
      expect(tree[1].name).toBe("zebra.md")
    })

    it("handles empty file list", () => {
      const tree = buildFileTree([])
      expect(tree).toEqual([])
    })

    it("handles files with empty path parts", () => {
      const files = [createMockFile({ id: 1, path: "", filename: "" })]

      const tree = buildFileTree(files)

      expect(tree).toEqual([])
    })
  })

  describe("findNode", () => {
    it("finds a file at root level", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" },
      ]

      const node = findNode(tree, "file.md")

      expect(node).not.toBeNull()
      expect(node?.name).toBe("file.md")
    })

    it("finds a nested file", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            { name: "file.md", path: "folder/file.md", type: "file" },
          ],
        },
      ]

      const node = findNode(tree, "folder/file.md")

      expect(node).not.toBeNull()
      expect(node?.path).toBe("folder/file.md")
    })

    it("finds a folder", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [],
        },
      ]

      const node = findNode(tree, "folder")

      expect(node).not.toBeNull()
      expect(node?.type).toBe("folder")
    })

    it("returns null for non-existent path", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" },
      ]

      const node = findNode(tree, "nonexistent.md")

      expect(node).toBeNull()
    })

    it("returns null for empty path", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" },
      ]

      const node = findNode(tree, "")

      expect(node).toBeNull()
    })

    it("returns null when traversing through file instead of folder", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" },
      ]

      const node = findNode(tree, "file.md/nested.md")

      expect(node).toBeNull()
    })
  })

  describe("findParentNode", () => {
    it("returns null for root-level items", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" },
      ]

      const parent = findParentNode(tree, "file.md")

      expect(parent).toBeNull()
    })

    it("finds parent of nested file", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            { name: "file.md", path: "folder/file.md", type: "file" },
          ],
        },
      ]

      const parent = findParentNode(tree, "folder/file.md")

      expect(parent).not.toBeNull()
      expect(parent?.name).toBe("folder")
    })

    it("finds parent in deep nesting", () => {
      const tree: FileTreeNode[] = [
        {
          name: "a",
          path: "a",
          type: "folder",
          children: [
            {
              name: "b",
              path: "a/b",
              type: "folder",
              children: [
                { name: "file.md", path: "a/b/file.md", type: "file" },
              ],
            },
          ],
        },
      ]

      const parent = findParentNode(tree, "a/b/file.md")

      expect(parent?.name).toBe("b")
      expect(parent?.path).toBe("a/b")
    })
  })

  describe("insertFileNode", () => {
    it("inserts file at root level", () => {
      const tree: FileTreeNode[] = []
      const file = createMockFile({ id: 1, path: "new.md", filename: "new.md" })

      insertFileNode(tree, file)

      expect(tree).toHaveLength(1)
      expect(tree[0].name).toBe("new.md")
      expect(tree[0].file).toEqual(file)
    })

    it("creates parent folders when needed", () => {
      const tree: FileTreeNode[] = []
      const file = createMockFile({ id: 1, path: "a/b/c/file.md", filename: "file.md" })

      insertFileNode(tree, file)

      expect(tree[0].name).toBe("a")
      expect(tree[0].children![0].name).toBe("b")
      expect(tree[0].children![0].children![0].name).toBe("c")
      expect(tree[0].children![0].children![0].children![0].name).toBe("file.md")
    })

    it("uses existing folders", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [],
        },
      ]
      const file = createMockFile({ id: 1, path: "folder/new.md", filename: "new.md" })

      insertFileNode(tree, file)

      expect(tree).toHaveLength(1)
      expect(tree[0].children).toHaveLength(1)
    })

    it("replaces existing file at same path", () => {
      const tree: FileTreeNode[] = [
        {
          name: "file.md",
          path: "file.md",
          type: "file",
          file: createMockFile({ id: 1 }),
        },
      ]
      const updatedFile = createMockFile({ id: 2, path: "file.md", filename: "file.md" })

      insertFileNode(tree, updatedFile)

      expect(tree).toHaveLength(1)
      expect(tree[0].file?.id).toBe(2)
    })

    it("maintains sort order after insertion", () => {
      const tree: FileTreeNode[] = [
        { name: "zebra.md", path: "zebra.md", type: "file" },
      ]
      const file = createMockFile({ id: 1, path: "alpha.md", filename: "alpha.md" })

      insertFileNode(tree, file)

      expect(tree[0].name).toBe("alpha.md")
      expect(tree[1].name).toBe("zebra.md")
    })

    it("handles empty path", () => {
      const tree: FileTreeNode[] = []
      const file = createMockFile({ id: 1, path: "", filename: "" })

      insertFileNode(tree, file)

      expect(tree).toHaveLength(0)
    })
  })

  describe("insertFolderNode", () => {
    it("inserts folder at root level", () => {
      const tree: FileTreeNode[] = []

      const node = insertFolderNode(tree, "new-folder")

      expect(tree).toHaveLength(1)
      expect(tree[0].name).toBe("new-folder")
      expect(tree[0].type).toBe("folder")
      expect(node.name).toBe("new-folder")
    })

    it("creates parent folders when needed", () => {
      const tree: FileTreeNode[] = []

      insertFolderNode(tree, "a/b/c")

      expect(tree[0].name).toBe("a")
      expect(tree[0].children![0].name).toBe("b")
      expect(tree[0].children![0].children![0].name).toBe("c")
    })

    it("applies metadata to final folder", () => {
      const tree: FileTreeNode[] = []
      const meta = {
        path: "folder",
        name: "folder",
        title: "My Folder",
        description: "A test folder",
        properties: { key: "value" },
      }

      insertFolderNode(tree, "folder", meta)

      expect(tree[0].folderMeta?.title).toBe("My Folder")
      expect(tree[0].folderMeta?.description).toBe("A test folder")
      expect(tree[0].folderMeta?.properties).toEqual({ key: "value" })
    })

    it("throws error for empty path", () => {
      const tree: FileTreeNode[] = []

      expect(() => insertFolderNode(tree, "")).toThrow("Cannot insert folder at root")
    })

    it("reuses existing folder", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [{ name: "existing.md", path: "folder/existing.md", type: "file" }],
        },
      ]

      const node = insertFolderNode(tree, "folder")

      expect(tree).toHaveLength(1)
      expect(node.children).toHaveLength(1)
    })
  })

  describe("removeNode", () => {
    it("removes file from root level", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" },
      ]

      const result = removeNode(tree, "file.md")

      expect(result).toBe(true)
      expect(tree).toHaveLength(0)
    })

    it("removes file from nested location", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            { name: "file.md", path: "folder/file.md", type: "file" },
          ],
        },
      ]

      const result = removeNode(tree, "folder/file.md")

      expect(result).toBe(true)
      expect(tree[0].children).toHaveLength(0)
    })

    it("removes folder with children", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            { name: "file.md", path: "folder/file.md", type: "file" },
          ],
        },
      ]

      const result = removeNode(tree, "folder")

      expect(result).toBe(true)
      expect(tree).toHaveLength(0)
    })

    it("returns false for non-existent path", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" },
      ]

      const result = removeNode(tree, "nonexistent.md")

      expect(result).toBe(false)
      expect(tree).toHaveLength(1)
    })

    it("returns false for empty path", () => {
      const tree: FileTreeNode[] = []

      const result = removeNode(tree, "")

      expect(result).toBe(false)
    })

    it("returns false when parent has no children", () => {
      const tree: FileTreeNode[] = [
        { name: "folder", path: "folder", type: "folder" },
      ]

      const result = removeNode(tree, "folder/file.md")

      expect(result).toBe(false)
    })
  })

  describe("updateFileNode", () => {
    it("updates file metadata", () => {
      const tree: FileTreeNode[] = [
        {
          name: "file.md",
          path: "file.md",
          type: "file",
          file: createMockFile({ id: 1, title: "Old Title" }),
        },
      ]
      const updatedFile = createMockFile({ id: 1, path: "file.md", title: "New Title" })

      const result = updateFileNode(tree, updatedFile)

      expect(result).toBe(true)
      expect(tree[0].file?.title).toBe("New Title")
    })

    it("updates nested file", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            {
              name: "file.md",
              path: "folder/file.md",
              type: "file",
              file: createMockFile({ id: 1, path: "folder/file.md" }),
            },
          ],
        },
      ]
      const updatedFile = createMockFile({ id: 1, path: "folder/file.md", title: "Updated" })

      const result = updateFileNode(tree, updatedFile)

      expect(result).toBe(true)
      expect(tree[0].children![0].file?.title).toBe("Updated")
    })

    it("returns false for non-existent path", () => {
      const tree: FileTreeNode[] = []
      const file = createMockFile({ id: 1, path: "nonexistent.md" })

      const result = updateFileNode(tree, file)

      expect(result).toBe(false)
    })

    it("returns false when trying to update a folder", () => {
      const tree: FileTreeNode[] = [
        { name: "folder", path: "folder", type: "folder", children: [] },
      ]
      const file = createMockFile({ id: 1, path: "folder" })

      const result = updateFileNode(tree, file)

      expect(result).toBe(false)
    })
  })

  describe("mergeFolderContents", () => {
    it("merges files into existing folder", () => {
      const tree: FileTreeNode[] = []
      const folderData: FolderWithFiles = {
        path: "folder",
        name: "folder",
        notebook_id: 1,
        file_count: 1,
        files: [createMockFile({ id: 1, path: "folder/file.md", filename: "file.md" })],
        subfolders: [],
      }

      mergeFolderContents(tree, "folder", folderData)

      expect(tree[0].children).toHaveLength(1)
      expect(tree[0].children![0].name).toBe("file.md")
      expect(tree[0].loaded).toBe(true)
    })

    it("merges subfolders", () => {
      const tree: FileTreeNode[] = []
      const folderData: FolderWithFiles = {
        path: "folder",
        name: "folder",
        notebook_id: 1,
        file_count: 0,
        files: [],
        subfolders: [
          { path: "folder/sub", name: "sub", title: "Subfolder" },
        ],
      }

      mergeFolderContents(tree, "folder", folderData)

      expect(tree[0].children).toHaveLength(1)
      expect(tree[0].children![0].name).toBe("sub")
      expect(tree[0].children![0].type).toBe("folder")
      expect(tree[0].children![0].folderMeta?.title).toBe("Subfolder")
    })

    it("updates folder metadata", () => {
      const tree: FileTreeNode[] = []
      const folderData: FolderWithFiles = {
        path: "folder",
        name: "folder",
        notebook_id: 1,
        title: "My Folder",
        description: "Description",
        file_count: 5,
        files: [],
      }

      mergeFolderContents(tree, "folder", folderData)

      expect(tree[0].folderMeta?.title).toBe("My Folder")
      expect(tree[0].folderMeta?.description).toBe("Description")
      expect(tree[0].folderMeta?.file_count).toBe(5)
    })

    it("merges at root level when folderPath is empty", () => {
      const tree: FileTreeNode[] = []
      const folderData: FolderWithFiles = {
        path: "",
        name: "",
        notebook_id: 1,
        file_count: 1,
        files: [createMockFile({ id: 1, path: "root.md", filename: "root.md" })],
      }

      mergeFolderContents(tree, "", folderData)

      expect(tree).toHaveLength(1)
      expect(tree[0].name).toBe("root.md")
    })

    it("updates existing subfolder metadata without replacing children", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            {
              name: "sub",
              path: "folder/sub",
              type: "folder",
              children: [
                { name: "existing.md", path: "folder/sub/existing.md", type: "file" },
              ],
              loaded: true,
            },
          ],
        },
      ]
      const folderData: FolderWithFiles = {
        path: "folder",
        name: "folder",
        notebook_id: 1,
        file_count: 0,
        files: [],
        subfolders: [
          { path: "folder/sub", name: "sub", title: "Updated Title" },
        ],
      }

      mergeFolderContents(tree, "folder", folderData)

      const subfolder = tree[0].children![0]
      expect(subfolder.folderMeta?.title).toBe("Updated Title")
      expect(subfolder.children).toHaveLength(1)
      expect(subfolder.loaded).toBe(true)
    })

    it("updates existing file instead of duplicating", () => {
      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            {
              name: "file.md",
              path: "folder/file.md",
              type: "file",
              file: createMockFile({ id: 1, path: "folder/file.md", title: "Old" }),
            },
          ],
        },
      ]
      const folderData: FolderWithFiles = {
        path: "folder",
        name: "folder",
        notebook_id: 1,
        file_count: 1,
        files: [createMockFile({ id: 1, path: "folder/file.md", filename: "file.md", title: "New" })],
      }

      mergeFolderContents(tree, "folder", folderData)

      expect(tree[0].children).toHaveLength(1)
      expect(tree[0].children![0].file?.title).toBe("New")
    })

    it("sorts after merge", () => {
      const tree: FileTreeNode[] = []
      const folderData: FolderWithFiles = {
        path: "folder",
        name: "folder",
        notebook_id: 1,
        file_count: 2,
        files: [
          createMockFile({ id: 1, path: "folder/zebra.md", filename: "zebra.md" }),
          createMockFile({ id: 2, path: "folder/alpha.md", filename: "alpha.md" }),
        ],
        subfolders: [
          { path: "folder/sub", name: "sub" },
        ],
      }

      mergeFolderContents(tree, "folder", folderData)

      // Folder first, then files alphabetically
      expect(tree[0].children![0].name).toBe("sub")
      expect(tree[0].children![1].name).toBe("alpha.md")
      expect(tree[0].children![2].name).toBe("zebra.md")
    })
  })

  describe("getAllFiles", () => {
    it("returns empty array for empty tree", () => {
      const files = getAllFiles([])
      expect(files).toEqual([])
    })

    it("returns files from flat tree", () => {
      const mockFile = createMockFile({ id: 1, path: "file.md" })
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file", file: mockFile },
      ]

      const files = getAllFiles(tree)

      expect(files).toHaveLength(1)
      expect(files[0]).toEqual(mockFile)
    })

    it("returns files from nested folders", () => {
      const file1 = createMockFile({ id: 1, path: "root.md" })
      const file2 = createMockFile({ id: 2, path: "folder/nested.md" })
      const file3 = createMockFile({ id: 3, path: "folder/deep/file.md" })

      const tree: FileTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "folder",
          children: [
            {
              name: "deep",
              path: "folder/deep",
              type: "folder",
              children: [
                { name: "file.md", path: "folder/deep/file.md", type: "file", file: file3 },
              ],
            },
            { name: "nested.md", path: "folder/nested.md", type: "file", file: file2 },
          ],
        },
        { name: "root.md", path: "root.md", type: "file", file: file1 },
      ]

      const files = getAllFiles(tree)

      expect(files).toHaveLength(3)
      expect(files.map((f) => f.id).sort()).toEqual([1, 2, 3])
    })

    it("skips nodes without file metadata", () => {
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file" }, // No file property
      ]

      const files = getAllFiles(tree)

      expect(files).toHaveLength(0)
    })
  })

  describe("moveNode", () => {
    it("moves file to new location", () => {
      const file = createMockFile({ id: 1, path: "old.md", filename: "old.md" })
      const tree: FileTreeNode[] = [
        { name: "old.md", path: "old.md", type: "file", file },
      ]

      const result = moveNode(tree, "old.md", "new.md")

      expect(result).toBe(true)
      const movedNode = findNode(tree, "new.md")
      expect(movedNode).not.toBeNull()
      expect(movedNode?.file?.path).toBe("new.md")
    })

    it("moves file to nested location", () => {
      const file = createMockFile({ id: 1, path: "file.md", filename: "file.md" })
      const tree: FileTreeNode[] = [
        { name: "file.md", path: "file.md", type: "file", file },
      ]

      const result = moveNode(tree, "file.md", "folder/file.md")

      expect(result).toBe(true)
      expect(findNode(tree, "file.md")).toBeNull()
      expect(findNode(tree, "folder/file.md")).not.toBeNull()
    })

    it("moves folder with children", () => {
      const file = createMockFile({ id: 1, path: "old/file.md", filename: "file.md" })
      const tree: FileTreeNode[] = [
        {
          name: "old",
          path: "old",
          type: "folder",
          children: [
            { name: "file.md", path: "old/file.md", type: "file", file },
          ],
        },
      ]

      const result = moveNode(tree, "old", "new")

      expect(result).toBe(true)
      expect(findNode(tree, "old")).toBeNull()
      const newFolder = findNode(tree, "new")
      expect(newFolder).not.toBeNull()
      expect(newFolder?.children).toHaveLength(1)
    })

    it("returns false for non-existent source", () => {
      const tree: FileTreeNode[] = []

      const result = moveNode(tree, "nonexistent", "new")

      expect(result).toBe(false)
    })

    it("updates file metadata paths when moving", () => {
      const file = createMockFile({ id: 1, path: "old.md", filename: "old.md" })
      const tree: FileTreeNode[] = [
        { name: "old.md", path: "old.md", type: "file", file },
      ]

      moveNode(tree, "old.md", "new.md")

      const movedNode = findNode(tree, "new.md")
      expect(movedNode?.file?.filename).toBe("new.md")
    })
  })
})
