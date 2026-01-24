"""Link resolution utility for resolving file references between documents."""

from pathlib import Path
from typing import Optional
from urllib.parse import unquote


class LinkResolver:
    """Resolves links between documents in a notebook.

    Supports:
    - Absolute paths: "/path/to/file.md" or "path/to/file.md"
    - Relative paths: "./file.md", "../other/file.md"
    - Filename only: "file.md" (searches from current directory)
    """

    @staticmethod
    def resolve_link(
        link: str,
        current_file_path: Optional[str] = None,
        notebook_root: Optional[Path] = None
    ) -> str:
        """Resolve a link to a target file path.

        Args:
            link: The link to resolve (can be URL-encoded)
            current_file_path: Path of the current file (relative to notebook root)
            notebook_root: Root path of the notebook (for validation)

        Returns:
            Resolved file path relative to notebook root

        Raises:
            ValueError: If link is invalid or resolves outside notebook
        """
        # URL decode the link
        decoded_link = unquote(link)

        # Remove any anchor fragments (#section)
        if "#" in decoded_link:
            decoded_link = decoded_link.split("#")[0]

        # Remove any query parameters (?param=value)
        if "?" in decoded_link:
            decoded_link = decoded_link.split("?")[0]

        # Handle empty link
        if not decoded_link:
            if current_file_path:
                return current_file_path
            raise ValueError("Empty link with no current file context")

        # Convert to Path for manipulation
        link_path = Path(decoded_link)

        # Case 1: Absolute path (starts with /)
        if decoded_link.startswith("/"):
            # Remove leading slash for relative-to-root path
            resolved = str(link_path).lstrip("/")
        # Case 2: Relative path (contains ./ or ../)
        elif decoded_link.startswith("./") or decoded_link.startswith("../"):
            if not current_file_path:
                raise ValueError("Relative link requires current file context")
            # Get the directory of the current file
            current_dir = Path(current_file_path).parent
            # Resolve relative path
            resolved_path = (current_dir / link_path).resolve()
            # Make it relative to notebook root
            if notebook_root:
                try:
                    resolved = str(resolved_path.relative_to(notebook_root.resolve()))
                except ValueError:
                    # Path is outside notebook
                    raise ValueError(f"Link resolves outside notebook: {decoded_link}")
            else:
                resolved = str(resolved_path)
        # Case 3: Simple filename or path without prefix
        else:
            # If it contains a path separator, treat as absolute within notebook
            if "/" in decoded_link:
                resolved = decoded_link
            # If it's just a filename, search from current directory
            elif current_file_path:
                current_dir = Path(current_file_path).parent
                if current_dir == Path("."):
                    resolved = decoded_link
                else:
                    resolved = str(current_dir / decoded_link)
            else:
                # No context, use as-is
                resolved = decoded_link

        # Normalize path (remove redundant separators, etc.)
        resolved = str(Path(resolved))

        # Validate that resolved path doesn't escape notebook if we have a root
        if notebook_root:
            try:
                resolved_abs = (notebook_root / resolved).resolve()
                notebook_abs = notebook_root.resolve()
                if not str(resolved_abs).startswith(str(notebook_abs)):
                    raise ValueError(f"Link resolves outside notebook: {decoded_link}")
            except (OSError, ValueError) as e:
                raise ValueError(f"Invalid link path: {decoded_link}") from e

        return resolved

    @staticmethod
    def make_relative_link(
        target_path: str,
        from_path: str,
        use_relative: bool = True
    ) -> str:
        """Create a link from one file to another.

        Args:
            target_path: Path to the target file
            from_path: Path of the file containing the link
            use_relative: If True, use relative paths; if False, use absolute

        Returns:
            Link string (relative or absolute)
        """
        if not use_relative:
            # Return absolute path with leading slash
            return f"/{target_path}"

        # Calculate relative path
        from_dir = Path(from_path).parent
        target = Path(target_path)

        try:
            # Try to calculate relative path
            if from_dir == Path("."):
                # Same directory
                relative = target
            else:
                # Different directory
                relative = Path("../" * len(from_dir.parts)) / target
                # Simplify if possible
                try:
                    # This normalizes the path
                    relative = Path(from_dir / relative).relative_to(from_dir)
                except ValueError:
                    pass

            return str(relative)
        except ValueError:
            # Can't make relative, return absolute
            return f"/{target_path}"
