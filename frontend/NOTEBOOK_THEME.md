# Notebook Theme for Codex

A notebook-inspired theme system inspired by [Obsidian Notebook Themes](https://github.com/CyanVoxel/Obsidian-Notebook-Themes).

## Overview

Transforms the markdown editor into a digital notebook with paper textures, ruled/grid patterns, color schemes, and typography mimicking traditional notebooks.

## Theme Files

- `src/notebook-theme.css` - Main theme stylesheet
- `tailwind.config.js` - Extended notebook color palette
- `style.css` - Imports the notebook theme

## Usage

### Page Backgrounds

```html
<div class="theme-cream">
  <!-- Cream/off-white paper -->
  <div class="theme-manila">
    <!-- Manila/tan paper -->
    <div class="theme-white">
      <!-- Pure white paper -->
      <div class="theme-blueprint"><!-- Dark blue blueprint --></div>
    </div>
  </div>
</div>
```

### Paper Patterns

```html
<div class="ruled-paper">
  <!-- Horizontal ruled lines -->
  <div class="graph-paper">
    <!-- Grid pattern -->
    <div class="dotted-paper">
      <!-- Dot grid pattern -->
      <div class="notebook-texture"><!-- Paper texture overlay --></div>
    </div>
  </div>
</div>
```

### Pen Colors

```html
<span class="pen-black">
  <!-- Black ink (default) -->
  <span class="pen-blue">
    <!-- Blue ink -->
    <span class="pen-red"> <!-- Red ink --></span></span
  ></span
>
```

### Layout Classes

```html
<div class="notebook-page">
  <!-- Page container with shadow -->
  <div class="notebook-content">
    <!-- Content area with typography -->
    <div class="notebook-editor"><!-- Editor with notebook styling --></div>
  </div>
</div>
```

## Customization

### CSS Variables

Customize in `notebook-theme.css`:

```css
:root {
  --pen-black: #1a1a1a;
  --page-cream: #fef9f3;
  --grid-size: 24px;
}
```

### Tailwind Colors

```html
<div class="bg-notebook-page-cream text-notebook-pen-black"></div>
```

Available: `notebook-page-{white|cream|manila|blueprint}`, `notebook-pen-{black|gray|blue|red|green|purple}`

## Example

```vue
<div class="notebook-page ruled-paper theme-cream">
  <div class="notebook-content">
    <h1>My Notes</h1>
    <p>Content goes here...</p>
  </div>
</div>
```

## References

- [Obsidian Notebook Themes](https://github.com/CyanVoxel/Obsidian-Notebook-Themes)
- [Obsidian CSS Variables](https://docs.obsidian.md/Reference/CSS+variables/CSS+variables)

---

For more information about Codex, see the main [README](../README.md).
