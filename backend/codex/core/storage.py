"""Content-addressable storage manager for Lab Notebook."""

import hashlib
import io
from pathlib import Path
from typing import Optional

from PIL import Image


class StorageManager:
    """Manager for content-addressable storage of artifacts."""

    def __init__(self, storage_path: Path):
        """Initialize the storage manager."""
        self.storage_path = storage_path
        self.blobs_path = storage_path / "blobs"
        self.thumbnails_path = storage_path / "thumbnails"

    def initialize(self):
        """Initialize storage directories."""
        self.blobs_path.mkdir(parents=True, exist_ok=True)
        self.thumbnails_path.mkdir(parents=True, exist_ok=True)

    def store(self, data: bytes, artifact_type: str) -> str:
        """
        Store data in content-addressable storage.

        Returns the SHA256 hash of the data.
        """
        # Calculate hash
        hash_value = hashlib.sha256(data).hexdigest()

        # Create subdirectories based on hash prefix for better distribution
        subdir = self.blobs_path / hash_value[:2] / hash_value[2:4]
        subdir.mkdir(parents=True, exist_ok=True)

        # Store the blob
        blob_path = subdir / hash_value
        if not blob_path.exists():
            blob_path.write_bytes(data)

        # Generate thumbnail for images
        if artifact_type.startswith("image/"):
            self._generate_thumbnail(data, hash_value)

        return f"sha256:{hash_value}"

    def retrieve(self, hash_value: str) -> Optional[bytes]:
        """Retrieve data by hash."""
        # Handle full hash format (sha256:...)
        if hash_value.startswith("sha256:"):
            hash_value = hash_value[7:]

        blob_path = self.blobs_path / hash_value[:2] / hash_value[2:4] / hash_value
        if blob_path.exists():
            return blob_path.read_bytes()
        return None

    def get_blob_path(self, hash_value: str) -> Path:
        """Get the path to a blob."""
        if hash_value.startswith("sha256:"):
            hash_value = hash_value[7:]
        return self.blobs_path / hash_value[:2] / hash_value[2:4] / hash_value

    def get_thumbnail(self, hash_value: str) -> Optional[bytes]:
        """Get thumbnail for an artifact."""
        if hash_value.startswith("sha256:"):
            hash_value = hash_value[7:]

        thumb_path = (
            self.thumbnails_path
            / hash_value[:2]
            / hash_value[2:4]
            / f"{hash_value}.thumb.jpg"
        )
        if thumb_path.exists():
            return thumb_path.read_bytes()
        return None

    def get_thumbnail_path(self, hash_value: str) -> Path:
        """Get the path to a thumbnail."""
        if hash_value.startswith("sha256:"):
            hash_value = hash_value[7:]
        return (
            self.thumbnails_path
            / hash_value[:2]
            / hash_value[2:4]
            / f"{hash_value}.thumb.jpg"
        )

    def _generate_thumbnail(
        self, data: bytes, hash_value: str, max_size: tuple = (256, 256)
    ):
        """Generate a thumbnail for an image."""
        try:
            # Create subdirectories
            subdir = self.thumbnails_path / hash_value[:2] / hash_value[2:4]
            subdir.mkdir(parents=True, exist_ok=True)

            thumb_path = subdir / f"{hash_value}.thumb.jpg"
            if not thumb_path.exists():
                with Image.open(io.BytesIO(data)) as img:
                    # Convert to RGB if necessary (for PNG with transparency)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")

                    # Create thumbnail
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                    img.save(thumb_path, "JPEG", quality=85)
        except Exception:
            # Silently ignore thumbnail generation failures
            pass

    def exists(self, hash_value: str) -> bool:
        """Check if a blob exists."""
        if hash_value.startswith("sha256:"):
            hash_value = hash_value[7:]
        blob_path = self.blobs_path / hash_value[:2] / hash_value[2:4] / hash_value
        return blob_path.exists()

    def delete(self, hash_value: str) -> bool:
        """Delete a blob and its thumbnail."""
        if hash_value.startswith("sha256:"):
            hash_value = hash_value[7:]

        deleted = False

        blob_path = self.blobs_path / hash_value[:2] / hash_value[2:4] / hash_value
        if blob_path.exists():
            blob_path.unlink()
            deleted = True

        thumb_path = (
            self.thumbnails_path
            / hash_value[:2]
            / hash_value[2:4]
            / f"{hash_value}.thumb.jpg"
        )
        if thumb_path.exists():
            thumb_path.unlink()

        return deleted

    def get_size(self, hash_value: str) -> Optional[int]:
        """Get the size of a blob in bytes."""
        if hash_value.startswith("sha256:"):
            hash_value = hash_value[7:]

        blob_path = self.blobs_path / hash_value[:2] / hash_value[2:4] / hash_value
        if blob_path.exists():
            return blob_path.stat().st_size
        return None
