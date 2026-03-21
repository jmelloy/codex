import { describe, it, expect } from "vitest"
import {
  findNode,
  findParentNode,
  insertBlockNode,
  removeNode,
  updateBlockNode,
  getAllBlocks,
  moveNode,
  type BlockTreeNode,
} from "../../utils/blockTree"
import type { Block } from "../../services/codex"

function createMockBlock(overrides: Partial<Block> = {}): Block {
  return {
    id: 1,
    block_id: "blk_1",
    parent_block_id: null,
    notebook_id: 1,
    path: "test.md",
    filename: "test.md",
    block_type: "leaf",
    content_format: "markdown",
    order_index: 0,
    content_type: "text/markdown",
    size: 100,
    created_at: "2024-01-01",
    updated_at: "2024-01-01",
    ...overrides,
  }
}

describe("blockTree utilities", () => {
  describe("findNode", () => {
    it("finds a file at root level", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" },
      ]

      const node = findNode(tree, "file.md")

      expect(node).not.toBeNull()
      expect(node?.name).toBe("file.md")
    })

    it("finds a nested file", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [
            { name: "file.md", path: "folder/file.md", type: "leaf" },
          ],
        },
      ]

      const node = findNode(tree, "folder/file.md")

      expect(node).not.toBeNull()
      expect(node?.path).toBe("folder/file.md")
    })

    it("finds a page", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [],
        },
      ]

      const node = findNode(tree, "folder")

      expect(node).not.toBeNull()
      expect(node?.type).toBe("page")
    })

    it("returns null for non-existent path", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" },
      ]

      const node = findNode(tree, "nonexistent.md")

      expect(node).toBeNull()
    })

    it("returns null for empty path", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" },
      ]

      const node = findNode(tree, "")

      expect(node).toBeNull()
    })

    it("returns null when traversing through file instead of folder", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" },
      ]

      const node = findNode(tree, "file.md/nested.md")

      expect(node).toBeNull()
    })
  })

  describe("findParentNode", () => {
    it("returns null for root-level items", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" },
      ]

      const parent = findParentNode(tree, "file.md")

      expect(parent).toBeNull()
    })

    it("finds parent of nested file", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [
            { name: "file.md", path: "folder/file.md", type: "leaf" },
          ],
        },
      ]

      const parent = findParentNode(tree, "folder/file.md")

      expect(parent).not.toBeNull()
      expect(parent?.name).toBe("folder")
    })

    it("finds parent in deep nesting", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "a",
          path: "a",
          type: "page",
          children: [
            {
              name: "b",
              path: "a/b",
              type: "page",
              children: [
                { name: "file.md", path: "a/b/file.md", type: "leaf" },
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

  describe("insertBlockNode", () => {
    it("inserts file at root level", () => {
      const tree: BlockTreeNode[] = []
      const file = createMockBlock({ id: 1, path: "new.md", filename: "new.md" })

      insertBlockNode(tree, file)

      expect(tree).toHaveLength(1)
      expect(tree[0].name).toBe("new.md")
      expect(tree[0].leafBlock).toEqual(file)
    })

    it("creates parent folders when needed", () => {
      const tree: BlockTreeNode[] = []
      const file = createMockBlock({ id: 1, path: "a/b/c/file.md", filename: "file.md" })

      insertBlockNode(tree, file)

      expect(tree[0].name).toBe("a")
      expect(tree[0].children![0].name).toBe("b")
      expect(tree[0].children![0].children![0].name).toBe("c")
      expect(tree[0].children![0].children![0].children![0].name).toBe("file.md")
    })

    it("uses existing folders", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [],
        },
      ]
      const file = createMockBlock({ id: 1, path: "folder/new.md", filename: "new.md" })

      insertBlockNode(tree, file)

      expect(tree).toHaveLength(1)
      expect(tree[0].children).toHaveLength(1)
    })

    it("replaces existing file at same path", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "file.md",
          path: "file.md",
          type: "leaf",
          file: createMockBlock({ id: 1 }),
        },
      ]
      const updatedFile = createMockBlock({ id: 2, path: "file.md", filename: "file.md" })

      insertBlockNode(tree, updatedFile)

      expect(tree).toHaveLength(1)
      expect(tree[0].leafBlock?.id).toBe(2)
    })

    it("maintains sort order after insertion", () => {
      const tree: BlockTreeNode[] = [
        { name: "zebra.md", path: "zebra.md", type: "leaf" },
      ]
      const file = createMockBlock({ id: 1, path: "alpha.md", filename: "alpha.md" })

      insertBlockNode(tree, file)

      expect(tree[0].name).toBe("alpha.md")
      expect(tree[1].name).toBe("zebra.md")
    })

    it("handles empty path", () => {
      const tree: BlockTreeNode[] = []
      const file = createMockBlock({ id: 1, path: "", filename: "" })

      insertBlockNode(tree, file)

      expect(tree).toHaveLength(0)
    })
  })

  describe("removeNode", () => {
    it("removes file from root level", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" },
      ]

      const result = removeNode(tree, "file.md")

      expect(result).toBe(true)
      expect(tree).toHaveLength(0)
    })

    it("removes file from nested location", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [
            { name: "file.md", path: "folder/file.md", type: "leaf" },
          ],
        },
      ]

      const result = removeNode(tree, "folder/file.md")

      expect(result).toBe(true)
      expect(tree[0].children).toHaveLength(0)
    })

    it("removes folder with children", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [
            { name: "file.md", path: "folder/file.md", type: "leaf" },
          ],
        },
      ]

      const result = removeNode(tree, "folder")

      expect(result).toBe(true)
      expect(tree).toHaveLength(0)
    })

    it("returns false for non-existent path", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" },
      ]

      const result = removeNode(tree, "nonexistent.md")

      expect(result).toBe(false)
      expect(tree).toHaveLength(1)
    })

    it("returns false for empty path", () => {
      const tree: BlockTreeNode[] = []

      const result = removeNode(tree, "")

      expect(result).toBe(false)
    })

    it("returns false when parent has no children", () => {
      const tree: BlockTreeNode[] = [
        { name: "folder", path: "folder", type: "page" },
      ]

      const result = removeNode(tree, "folder/file.md")

      expect(result).toBe(false)
    })
  })

  describe("updateBlockNode", () => {
    it("updates file metadata", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "file.md",
          path: "file.md",
          type: "leaf",
          file: createMockBlock({ id: 1, title: "Old Title" }),
        },
      ]
      const updatedFile = createMockBlock({ id: 1, path: "file.md", title: "New Title" })

      const result = updateBlockNode(tree, updatedFile)

      expect(result).toBe(true)
      expect(tree[0].leafBlock?.title).toBe("New Title")
    })

    it("updates nested file", () => {
      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [
            {
              name: "file.md",
              path: "folder/file.md",
              type: "leaf",
              file: createMockBlock({ id: 1, path: "folder/file.md" }),
            },
          ],
        },
      ]
      const updatedFile = createMockBlock({ id: 1, path: "folder/file.md", title: "Updated" })

      const result = updateBlockNode(tree, updatedFile)

      expect(result).toBe(true)
      expect(tree[0].children![0].leafBlock?.title).toBe("Updated")
    })

    it("returns false for non-existent path", () => {
      const tree: BlockTreeNode[] = []
      const file = createMockBlock({ id: 1, path: "nonexistent.md" })

      const result = updateBlockNode(tree, file)

      expect(result).toBe(false)
    })

    it("returns false when trying to update a folder", () => {
      const tree: BlockTreeNode[] = [
        { name: "folder", path: "folder", type: "page", children: [] },
      ]
      const file = createMockBlock({ id: 1, path: "folder" })

      const result = updateBlockNode(tree, file)

      expect(result).toBe(false)
    })
  })

  describe("getAllBlocks", () => {
    it("returns empty array for empty tree", () => {
      const files = getAllBlocks([])
      expect(files).toEqual([])
    })

    it("returns files from flat tree", () => {
      const mockFile = createMockBlock({ id: 1, path: "file.md" })
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf", leafBlock: mockFile },
      ]

      const files = getAllBlocks(tree)

      expect(files).toHaveLength(1)
      expect(files[0]).toEqual(mockFile)
    })

    it("returns files from nested folders", () => {
      const file1 = createMockBlock({ id: 1, path: "root.md" })
      const file2 = createMockBlock({ id: 2, path: "folder/nested.md" })
      const file3 = createMockBlock({ id: 3, path: "folder/deep/file.md" })

      const tree: BlockTreeNode[] = [
        {
          name: "folder",
          path: "folder",
          type: "page",
          children: [
            {
              name: "deep",
              path: "folder/deep",
              type: "page",
              children: [
                { name: "file.md", path: "folder/deep/file.md", type: "leaf", leafBlock: file3 },
              ],
            },
            { name: "nested.md", path: "folder/nested.md", type: "leaf", leafBlock: file2 },
          ],
        },
        { name: "root.md", path: "root.md", type: "leaf", leafBlock: file1 },
      ]

      const files = getAllBlocks(tree)

      expect(files).toHaveLength(3)
      expect(files.map((f) => f.id).sort()).toEqual([1, 2, 3])
    })

    it("skips nodes without file metadata", () => {
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf" }, // No file property
      ]

      const files = getAllBlocks(tree)

      expect(files).toHaveLength(0)
    })
  })

  describe("moveNode", () => {
    it("moves file to new location", () => {
      const file = createMockBlock({ id: 1, path: "old.md", filename: "old.md" })
      const tree: BlockTreeNode[] = [
        { name: "old.md", path: "old.md", type: "leaf", leafBlock: file },
      ]

      const result = moveNode(tree, "old.md", "new.md")

      expect(result).toBe(true)
      const movedNode = findNode(tree, "new.md")
      expect(movedNode).not.toBeNull()
      expect(movedNode?.leafBlock?.path).toBe("new.md")
    })

    it("moves file to nested location", () => {
      const file = createMockBlock({ id: 1, path: "file.md", filename: "file.md" })
      const tree: BlockTreeNode[] = [
        { name: "file.md", path: "file.md", type: "leaf", leafBlock: file },
      ]

      const result = moveNode(tree, "file.md", "folder/file.md")

      expect(result).toBe(true)
      expect(findNode(tree, "file.md")).toBeNull()
      expect(findNode(tree, "folder/file.md")).not.toBeNull()
    })

    it("moves folder with children", () => {
      const file = createMockBlock({ id: 1, path: "old/file.md", filename: "file.md" })
      const tree: BlockTreeNode[] = [
        {
          name: "old",
          path: "old",
          type: "page",
          children: [
            { name: "file.md", path: "old/file.md", type: "leaf", leafBlock: file },
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
      const tree: BlockTreeNode[] = []

      const result = moveNode(tree, "nonexistent", "new")

      expect(result).toBe(false)
    })

    it("updates file metadata paths when moving", () => {
      const file = createMockBlock({ id: 1, path: "old.md", filename: "old.md" })
      const tree: BlockTreeNode[] = [
        { name: "old.md", path: "old.md", type: "leaf", leafBlock: file },
      ]

      moveNode(tree, "old.md", "new.md")

      const movedNode = findNode(tree, "new.md")
      expect(movedNode?.leafBlock?.filename).toBe("new.md")
    })
  })
})
