# Open Graph Link Unfurling

Display rich previews of any URL with Open Graph metadata in your Codex notebooks.

## Features

- Automatic link preview generation
- Open Graph metadata extraction
- Support for any URL with OG tags
- No configuration required

## Installation

This integration requires no API keys or configuration. Just install and use!

## Usage

### Link Preview Block

Embed a rich preview of any URL in your markdown files:

```link-preview
url: https://github.com
```

The integration will automatically fetch and display:
- Page title
- Description
- Preview image
- Site name
- URL

### Auto-Detection

The integration can optionally auto-detect URLs in your markdown and render them as previews.

## Example

A link preview for GitHub:

```link-preview
url: https://github.com
```

Will display:
- Title: "GitHub: Let's build from here"
- Description: GitHub's description
- Preview image from GitHub's OG tags
- Site name: GitHub
- Clean URL

## Privacy

This integration makes HTTP requests to fetch page metadata. The URLs you preview are sent to those websites to retrieve the Open Graph tags.

## License

MIT
