import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  parseViewDefinition,
  validateViewDefinition,
  type ViewDefinition,
} from '../../services/viewParser'

describe('View Parser', () => {
  describe('parseViewDefinition', () => {
    it('should parse valid view definition with frontmatter', () => {
      const content = `---
type: view
view_type: kanban
title: My Kanban Board
description: Task board
query:
  tags:
    - project
  limit: 50
config:
  columns:
    - id: todo
      title: To Do
    - id: done
      title: Done
---
# Additional content
This is markdown content after the frontmatter.`

      const result = parseViewDefinition(content)

      expect(result.type).toBe('view')
      expect(result.view_type).toBe('kanban')
      expect(result.title).toBe('My Kanban Board')
      expect(result.description).toBe('Task board')
      expect(result.query?.tags).toEqual(['project'])
      expect(result.query?.limit).toBe(50)
      expect(result.config).toBeDefined()
      expect(result.content).toContain('Additional content')
    })

    it('should parse view without markdown content', () => {
      const content = `---
type: view
view_type: gallery
title: Photo Gallery
---`

      const result = parseViewDefinition(content)

      expect(result.type).toBe('view')
      expect(result.view_type).toBe('gallery')
      expect(result.title).toBe('Photo Gallery')
      expect(result.content).toBeUndefined()
    })

    it('should throw error when frontmatter is missing', () => {
      const content = `Just some content without frontmatter`

      expect(() => parseViewDefinition(content)).toThrow(
        'Invalid view definition: missing frontmatter'
      )
    })

    it('should throw error when type is not "view"', () => {
      const content = `---
type: page
view_type: kanban
---`

      expect(() => parseViewDefinition(content)).toThrow(
        'Not a valid view definition: type must be "view"'
      )
    })

    it('should throw error when view_type is missing', () => {
      const content = `---
type: view
title: My View
---`

      expect(() => parseViewDefinition(content)).toThrow(
        'Not a valid view definition: view_type is required'
      )
    })

    it('should throw error on invalid YAML', () => {
      const content = `---
type: view
  invalid yaml: [
---`

      expect(() => parseViewDefinition(content)).toThrow(
        'Failed to parse YAML frontmatter'
      )
    })

    it('should set default title when not provided', () => {
      const content = `---
type: view
view_type: gallery
---`

      const result = parseViewDefinition(content)

      expect(result.title).toBe('Untitled View')
    })

    it('should parse all view types', () => {
      const viewTypes = [
        'kanban',
        'gallery',
        'rollup',
        'dashboard',
        'corkboard',
        'task-list',
      ]

      viewTypes.forEach((viewType) => {
        const content = `---
type: view
view_type: ${viewType}
title: Test View
---`

        const result = parseViewDefinition(content)
        expect(result.view_type).toBe(viewType)
      })
    })

    it('should parse complex query with all fields', () => {
      const content = `---
type: view
view_type: gallery
title: Photo Gallery
query:
  notebook_ids:
    - 1
    - 2
  paths:
    - "photos/*.jpg"
  tags:
    - vacation
  tags_any:
    - family
    - friends
  file_types:
    - jpg
    - png
  properties:
    camera: Canon
    location: Beach
  properties_exists:
    - gps_coords
  created_after: "2024-01-01"
  created_before: "2024-12-31"
  modified_after: "2024-06-01"
  modified_before: "2024-12-31"
  date_property: taken_at
  date_after: "2024-01-01"
  date_before: "2024-12-31"
  content_search: "sunset"
  sort: "created_at desc"
  limit: 100
  offset: 0
  group_by: "properties.location"
---`

      const result = parseViewDefinition(content)

      expect(result.query?.notebook_ids).toEqual([1, 2])
      expect(result.query?.paths).toEqual(['photos/*.jpg'])
      expect(result.query?.tags).toEqual(['vacation'])
      expect(result.query?.tags_any).toEqual(['family', 'friends'])
      expect(result.query?.file_types).toEqual(['jpg', 'png'])
      expect(result.query?.properties).toEqual({
        camera: 'Canon',
        location: 'Beach',
      })
      expect(result.query?.properties_exists).toEqual(['gps_coords'])
      expect(result.query?.created_after).toBe('2024-01-01')
      expect(result.query?.content_search).toBe('sunset')
      expect(result.query?.sort).toBe('created_at desc')
      expect(result.query?.limit).toBe(100)
      expect(result.query?.group_by).toBe('properties.location')
    })

    it('should parse kanban config', () => {
      const content = `---
type: view
view_type: kanban
title: Task Board
config:
  columns:
    - id: todo
      title: To Do
      filter:
        status: todo
    - id: done
      title: Done
      filter:
        status: done
  card_fields:
    - title
    - priority
  drag_drop: true
  editable: true
---`

      const result = parseViewDefinition(content)
      const config = result.config as any

      expect(config.columns).toHaveLength(2)
      expect(config.columns[0].id).toBe('todo')
      expect(config.columns[0].filter).toEqual({ status: 'todo' })
      expect(config.card_fields).toEqual(['title', 'priority'])
      expect(config.drag_drop).toBe(true)
      expect(config.editable).toBe(true)
    })

    it('should parse gallery config', () => {
      const content = `---
type: view
view_type: gallery
title: Photo Gallery
config:
  layout: grid
  columns: 3
  thumbnail_size: 200
  show_metadata: true
  lightbox: true
---`

      const result = parseViewDefinition(content)
      const config = result.config as any

      expect(config.layout).toBe('grid')
      expect(config.columns).toBe(3)
      expect(config.thumbnail_size).toBe(200)
      expect(config.show_metadata).toBe(true)
      expect(config.lightbox).toBe(true)
    })

    it('should parse dashboard layout', () => {
      const content = `---
type: view
view_type: dashboard
title: Home Dashboard
layout:
  - type: row
    components:
      - type: mini-view
        span: 6
        view: "tasks.cdx"
      - type: mini-view
        span: 6
        view: "calendar.cdx"
---`

      const result = parseViewDefinition(content)

      expect(result.layout).toHaveLength(1)
      expect(result.layout![0].type).toBe('row')
      expect(result.layout![0].components).toHaveLength(2)
      expect(result.layout![0].components[0].span).toBe(6)
    })
  })

  describe('template variable processing', () => {
    it('should replace {{ today }} template', () => {
      const content = `---
type: view
view_type: task-list
title: Today's Tasks
query:
  date_property: due_date
  date_after: "{{ todayStart }}"
  date_before: "{{ todayEnd }}"
---`

      const result = parseViewDefinition(content)

      // Template should be replaced with actual date
      expect(result.query?.date_after).not.toContain('{{')
      expect(result.query?.date_after).toMatch(/^\d{4}-\d{2}-\d{2}T/)
      expect(result.query?.date_before).not.toContain('{{')
    })

    it('should replace {{ startOfWeek }} and {{ endOfWeek }}', () => {
      const content = `---
type: view
view_type: rollup
title: This Week
query:
  created_after: "{{ startOfWeek }}"
  created_before: "{{ endOfWeek }}"
---`

      const result = parseViewDefinition(content)

      expect(result.query?.created_after).not.toContain('{{')
      expect(result.query?.created_before).not.toContain('{{')
      expect(result.query?.created_after).toMatch(/^\d{4}-\d{2}-\d{2}T/)
      expect(result.query?.created_before).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('should replace {{ startOfMonth }} and {{ endOfMonth }}', () => {
      const content = `---
type: view
view_type: rollup
title: This Month
query:
  created_after: "{{ startOfMonth }}"
  created_before: "{{ endOfMonth }}"
---`

      const result = parseViewDefinition(content)

      expect(result.query?.created_after).not.toContain('{{')
      expect(result.query?.created_before).not.toContain('{{')
    })

    it('should replace {{ now }} template', () => {
      const content = `---
type: view
view_type: task-list
title: Current Tasks
query:
  modified_after: "{{ now }}"
---`

      const result = parseViewDefinition(content)

      expect(result.query?.modified_after).not.toContain('{{')
      expect(result.query?.modified_after).toMatch(/^\d{4}-\d{2}-\d{2}T/)
    })

    it('should handle templates with whitespace', () => {
      const content = `---
type: view
view_type: task-list
title: Test
query:
  date_after: "{{  today  }}"
---`

      const result = parseViewDefinition(content)

      expect(result.query?.date_after).not.toContain('{{')
    })

    it('should preserve non-template strings', () => {
      const content = `---
type: view
view_type: gallery
title: Test View
query:
  content_search: "This is {{ not a template"
---`

      const result = parseViewDefinition(content)

      // Invalid template syntax should be preserved
      expect(result.query?.content_search).toContain('{{')
    })

    it('should process templates in nested objects', () => {
      const content = `---
type: view
view_type: kanban
title: Test
query:
  properties:
    due_date: "{{ today }}"
---`

      const result = parseViewDefinition(content)

      expect(result.query?.properties?.due_date).not.toContain('{{')
    })

    it('should process templates in arrays', () => {
      const content = `---
type: view
view_type: gallery
title: Test
query:
  paths:
    - "photos/{{ today }}/*.jpg"
---`

      const result = parseViewDefinition(content)

      expect(result.query?.paths![0]).not.toContain('{{')
    })
  })

  describe('validateViewDefinition', () => {
    it('should validate correct view definition', () => {
      const viewDef: ViewDefinition = {
        type: 'view',
        view_type: 'kanban',
        title: 'Task Board',
        config: {
          columns: [
            { id: 'todo', title: 'To Do' },
            { id: 'done', title: 'Done' },
          ],
        },
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(true)
      expect(result.errors).toHaveLength(0)
    })

    it('should fail when type is not "view"', () => {
      const viewDef: any = {
        type: 'page',
        view_type: 'kanban',
        title: 'Test',
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('View definition must have type="view"')
    })

    it('should fail when view_type is missing', () => {
      const viewDef: any = {
        type: 'view',
        title: 'Test',
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('View definition must have view_type')
    })

    it('should fail when view_type is invalid', () => {
      const viewDef: ViewDefinition = {
        type: 'view',
        view_type: 'invalid-type',
        title: 'Test',
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(false)
      expect(result.errors.length).toBeGreaterThan(0)
      expect(result.errors[0]).toContain('must be one of')
    })

    it('should validate all valid view types', () => {
      const validTypes = [
        'kanban',
        'gallery',
        'rollup',
        'dashboard',
        'corkboard',
        'calendar',
        'task-list',
      ]

      validTypes.forEach((viewType) => {
        const viewDef: ViewDefinition = {
          type: 'view',
          view_type: viewType,
          title: 'Test',
        }

        // Add required fields for specific types
        if (viewType === 'kanban') {
          viewDef.config = { columns: [] }
        } else if (viewType === 'dashboard') {
          viewDef.layout = []
        }

        const result = validateViewDefinition(viewDef)
        expect(result.valid).toBe(true)
      })
    })

    it('should fail when kanban lacks columns', () => {
      const viewDef: ViewDefinition = {
        type: 'view',
        view_type: 'kanban',
        title: 'Task Board',
        config: {},
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(false)
      expect(result.errors).toContain(
        'Kanban view requires columns array in config'
      )
    })

    it('should pass when kanban has columns array', () => {
      const viewDef: ViewDefinition = {
        type: 'view',
        view_type: 'kanban',
        title: 'Task Board',
        config: {
          columns: [{ id: 'todo', title: 'To Do' }],
        },
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(true)
    })

    it('should fail when dashboard lacks layout', () => {
      const viewDef: ViewDefinition = {
        type: 'view',
        view_type: 'dashboard',
        title: 'Dashboard',
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(false)
      expect(result.errors).toContain('Dashboard view requires layout field')
    })

    it('should pass when dashboard has layout', () => {
      const viewDef: ViewDefinition = {
        type: 'view',
        view_type: 'dashboard',
        title: 'Dashboard',
        layout: [
          {
            type: 'row',
            components: [
              {
                type: 'mini-view',
                span: 12,
                view: 'test.cdx',
              },
            ],
          },
        ],
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(true)
    })

    it('should collect multiple validation errors', () => {
      const viewDef: any = {
        type: 'invalid',
        title: 'Test',
      }

      const result = validateViewDefinition(viewDef)

      expect(result.valid).toBe(false)
      expect(result.errors.length).toBeGreaterThan(1)
    })
  })
})
