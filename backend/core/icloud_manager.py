"""iCloud integration for downloading shared photo albums."""

import os
from typing import Any

from pyicloud import PyiCloudService
from pyicloud.exceptions import PyiCloudFailedLoginException


class ICloudManager:
    """Manager for iCloud operations, specifically for shared photo albums."""

    def __init__(self, apple_id: str, password: str, cookie_directory: str | None = None):
        """Initialize iCloud manager with credentials.

        Args:
            apple_id: Apple ID email address
            password: Apple ID password
            cookie_directory: Optional directory to store session cookies
        """
        self.apple_id = apple_id
        self.cookie_directory = cookie_directory or os.path.expanduser('~/.pyicloud')
        self.api: PyiCloudService | None = None
        self._authenticate(password)

    def _authenticate(self, password: str):
        """Authenticate with iCloud."""
        try:
            self.api = PyiCloudService(
                apple_id=self.apple_id,
                password=password,
                cookie_directory=self.cookie_directory
            )

            # Check if 2FA is required
            if self.api.requires_2fa:
                raise Exception(
                    "Two-factor authentication required. Please run the authentication "
                    "interactively first to trust this session."
                )

        except PyiCloudFailedLoginException as e:
            raise Exception(f"Failed to login to iCloud: {e}")

    def list_shared_albums(self) -> list[dict[str, Any]]:
        """List all shared photo streams/albums.

        Returns:
            List of dictionaries containing album information
        """
        if not self.api:
            raise Exception("Not authenticated with iCloud")

        albums = []

        # Access shared streams
        try:
            shared_streams = self.api.photos.shared_streams

            for album in shared_streams:
                albums.append({
                    'id': album.id,
                    'name': album.name,
                    'title': album.title,
                    'photo_count': len(album)
                })
        except Exception as e:
            print(f"Error listing shared albums: {e}")

        return albums

    def download_album_photos(
        self,
        album_name: str,
        destination_path: str,
        version: str = 'original'
    ) -> list[dict[str, Any]]:
        """Download all photos from a shared album.

        Args:
            album_name: Name of the album to download
            destination_path: Directory to save photos
            version: Photo version to download ('original', 'medium', 'thumb')

        Returns:
            List of dictionaries containing download information
        """
        if not self.api:
            raise Exception("Not authenticated with iCloud")

        # Create destination directory
        os.makedirs(destination_path, exist_ok=True)

        downloaded_files = []

        try:
            # Find the album
            shared_streams = self.api.photos.shared_streams
            target_album = None

            for album in shared_streams:
                if album.name == album_name or album.title == album_name:
                    target_album = album
                    break

            if not target_album:
                raise Exception(f"Album '{album_name}' not found in shared streams")

            # Download each photo
            for photo in target_album.photos:
                try:
                    # Download photo data
                    photo_data = photo.download(version=version)

                    if photo_data:
                        # Determine filename
                        filename = photo.filename or f"photo_{photo.id}.jpg"
                        filepath = os.path.join(destination_path, filename)

                        # Avoid overwriting existing files
                        if os.path.exists(filepath):
                            name, ext = os.path.splitext(filename)
                            counter = 1
                            while os.path.exists(filepath):
                                filename = f"{name}_{counter}{ext}"
                                filepath = os.path.join(destination_path, filename)
                                counter += 1

                        # Save photo
                        with open(filepath, 'wb') as f:
                            f.write(photo_data)

                        downloaded_files.append({
                            'filename': filename,
                            'filepath': filepath,
                            'photo_id': photo.id,
                            'size': len(photo_data),
                            'asset_date': photo.asset_date.isoformat() if photo.asset_date else None,
                            'dimensions': photo.dimensions,
                            'is_live_photo': photo.is_live_photo
                        })

                        print(f"Downloaded: {filename}")

                except Exception as e:
                    print(f"Error downloading photo {photo.id}: {e}")
                    continue

        except Exception as e:
            raise Exception(f"Error downloading album photos: {e}")

        return downloaded_files

    def get_album_info(self, album_name: str) -> dict[str, Any] | None:
        """Get detailed information about a shared album.

        Args:
            album_name: Name of the album

        Returns:
            Dictionary containing album information or None if not found
        """
        if not self.api:
            raise Exception("Not authenticated with iCloud")

        try:
            shared_streams = self.api.photos.shared_streams

            for album in shared_streams:
                if album.name == album_name or album.title == album_name:
                    # Get photos info
                    photos_info = []
                    for photo in album.photos:
                        photos_info.append({
                            'id': photo.id,
                            'filename': photo.filename,
                            'size': photo.size,
                            'asset_date': photo.asset_date.isoformat() if photo.asset_date else None,
                            'dimensions': photo.dimensions,
                            'item_type': photo.item_type,
                            'is_live_photo': photo.is_live_photo
                        })

                    return {
                        'id': album.id,
                        'name': album.name,
                        'title': album.title,
                        'photo_count': len(album),
                        'photos': photos_info
                    }

            return None

        except Exception as e:
            print(f"Error getting album info: {e}")
            return None
