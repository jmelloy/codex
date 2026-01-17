# Notebook Theme for Codex

This document describes the notebook-inspired theme system for Codex, inspired by [Obsidian Notebook Themes](https://github.com/CyanVoxel/Obsidian-Notebook-Themes).

## Overview

The notebook theme transforms the Codex markdown editor into a digital notebook experience with:

- **Paper textures**: Subtle background textures mimicking real paper
- **Ruled/Grid patterns**: Optional lined or graph paper backgrounds
- **Color schemes**: Multiple notebook paper colors (cream, manila, white, blueprint)
- **Typography**: Serif fonts for a traditional writing feel
- **Pen colors**: Different text colors mimicking various writing instruments

## Theme Files

- `src/notebook-theme.css` - Main theme stylesheet with all notebook styles
- `tailwind.config.js` - Extended with notebook color palette
- `style.css` - Imports the notebook theme

## Available Theme Classes

### Page Backgrounds

Apply these classes to switch between different notebook paper styles:

```html
<div class="theme-cream">      <!-- Default: Cream/off-white paper -->
<div class="theme-manila">     <!-- Manila/tan paper -->
<div class="theme-white">      <!-- Pure white paper -->
<div class="theme-blueprint">  <!-- Dark blue blueprint style -->
```

### Paper Patterns

Add visual patterns to the paper:

```html
<div class="ruled-paper">      <!-- Horizontal ruled lines like notebook paper -->
<div class="graph-paper">      <!-- Grid pattern like graph paper -->
<div class="dotted-paper">     <!-- Dot grid pattern -->
<div class="notebook-texture"> <!-- Subtle paper texture overlay -->
```

### Pen Colors

Override text colors to mimic different pen colors:

```html
<span class="pen-black">   <!-- Black ink (default) -->
<span class="pen-gray">    <!-- Gray ink -->
<span class="pen-blue">    <!-- Blue ink -->
<span class="pen-red">     <!-- Red ink -->
<span class="pen-green">   <!-- Green ink -->
<span class="pen-purple">  <!-- Purple ink -->
```

### Layout Classes

```html
<div class="notebook-page">     <!-- Page container with shadow and border -->
<div class="notebook-content">  <!-- Content area with notebook typography -->
<div class="notebook-editor">   <!-- Editor with notebook styling -->
<div class="notebook-sidebar">  <!-- Sidebar with subtle gradient -->
```

## Customization

### CSS Variables

You can customize the theme by modifying CSS variables in `notebook-theme.css`:

```css
:root {
  /* Pen Colors */
  --pen-black: #1a1a1a;
  --pen-blue: #2563eb;
  /* ... more colors */

  /* Page Colors */
  --page-cream: #fef9f3;
  --page-manila: #f4e8d0;
  /* ... more colors */

  /* Grid Settings */
  --grid-size: 24px;
  --ruled-line-color: rgba(100, 149, 237, 0.2);
}
```

### Tailwind Colors

Notebook colors are also available as Tailwind classes:

```html
<div class="bg-notebook-page-cream text-notebook-pen-black">
  <!-- Your content -->
</div>
```

Available Tailwind colors:
- `notebook-page-{white|cream|manila|blueprint}`
- `notebook-pen-{black|gray|blue|red|green|purple}`

### Font Families

```html
<div class="font-notebook">     <!-- Georgia, Palatino, serif -->
<div class="font-handwriting">  <!-- Caveat, cursive -->
```

## Usage Examples

### Basic Cream Notebook with Ruled Lines

```vue
<div class="notebook-page ruled-paper theme-cream">
  <div class="notebook-content">
    <h1>My Notes</h1>
    <p>Content goes here...</p>
  </div>
</div>
```

### Blueprint Style with Grid

```vue
<div class="notebook-page graph-paper theme-blueprint">
  <div class="notebook-content">
    <h1>Technical Diagrams</h1>
    <p>Blueprint-style notes...</p>
  </div>
</div>
```

### Manila Notebook with Texture

```vue
<div class="notebook-page theme-manila notebook-texture">
  <div class="notebook-content">
    <h1>Research Notes</h1>
    <p>Vintage-looking notes...</p>
  </div>
</div>
```

## Implementation Details

### Current Components

The following components have been updated to use the notebook theme:

1. **MarkdownView.vue**
   - Background: cream paper with texture
   - Sidebar: subtle gradient
   - Main content area: centered with max-width

2. **MarkdownEditor.vue**
   - Ruled paper background
   - Serif typography (Georgia)
   - Left margin spacing (80px) for the red margin line
   - Line height matches grid size (24px)

3. **MarkdownViewer.vue**
   - Notebook content styling
   - Enhanced typography for markdown elements
   - Proper spacing and borders

### Design Principles

Based on Obsidian's notebook themes, this implementation uses:

1. **CSS Custom Properties** - For easy theming and customization
2. **Color Mixing** - Using `color-mix()` for transparent variations
3. **Background Patterns** - CSS gradients for ruled/grid lines
4. **SVG Textures** - Inline SVG for paper texture noise
5. **Backdrop Filters** - Glass-morphism effect on toolbars

## Compatibility with Obsidian Themes

While we cannot directly use Obsidian theme CSS files (they're built for Obsidian's specific DOM structure), we've adapted the key design principles:

- Color variable system
- Page background theming
- Pen color variations
- Grid/ruled patterns
- Paper textures

## Future Enhancements

Potential improvements:

- [ ] Theme switcher UI component
- [ ] Custom CSS snippet support (user-defined styles)
- [ ] Import/export theme configurations
- [ ] Additional paper textures (parchment, recycled, etc.)
- [ ] Handwriting font option (requires web font)
- [ ] Image recoloring filters (like Obsidian)
- [ ] Per-notebook theme settings
- [ ] Dark mode variants

## References

- [Obsidian Notebook Themes](https://github.com/CyanVoxel/Obsidian-Notebook-Themes)
- [Obsidian CSS Variables](https://docs.obsidian.md/Reference/CSS+variables/CSS+variables)
- [Minimal Theme](https://github.com/kepano/obsidian-minimal)

## Contributing

To add new themes or patterns:

1. Add CSS variables to `notebook-theme.css`
2. Create theme class (`.theme-yourname`)
3. Update Tailwind config if needed
4. Document in this README
5. Add examples

---

For more information about Codex, see the main [README](../README.md) and [CLAUDE.md](../CLAUDE.md).
