"""API routes for themes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_themes():
    """List all available themes.
    
    Returns:
        List of theme definitions with styling information
    """
    # Built-in themes
    themes = [
        {
            "id": "cream",
            "name": "cream",
            "label": "Cream",
            "description": "Classic notebook with cream pages",
            "className": "theme-cream",
            "category": "light",
            "version": "1.0.0",
            "author": "Codex Team",
        },
        {
            "id": "manila",
            "name": "manila",
            "label": "Manila",
            "description": "Vintage manila folder aesthetic",
            "className": "theme-manila",
            "category": "light",
            "version": "1.0.0",
            "author": "Codex Team",
        },
        {
            "id": "white",
            "name": "white",
            "label": "White",
            "description": "Clean white pages",
            "className": "theme-white",
            "category": "light",
            "version": "1.0.0",
            "author": "Codex Team",
        },
        {
            "id": "blueprint",
            "name": "blueprint",
            "label": "Blueprint",
            "description": "Dark mode with blueprint styling",
            "className": "theme-blueprint",
            "category": "dark",
            "version": "1.0.0",
            "author": "Codex Team",
        },
    ]
    
    return themes
