"""Tests for iCloud integration."""

import os
from unittest.mock import Mock, patch

import pytest
from pyicloud.exceptions import PyiCloudFailedLoginException

from backend.core.icloud_manager import ICloudManager


class MockPhotoAsset:
    """Mock photo asset for testing."""

    def __init__(self, photo_id, filename="test_photo.jpg"):
        self.id = photo_id
        self.filename = filename
        self.size = 1024
        self.asset_date = None
        self.dimensions = (1920, 1080)
        self.item_type = "image/jpeg"
        self.is_live_photo = False
        self._data = b"fake_photo_data"

    def download(self, version='original'):
        """Mock download method."""
        return self._data


class MockPhotoAlbum:
    """Mock photo album for testing."""

    def __init__(self, album_id, name, photo_count=3):
        self.id = album_id
        self.name = name
        self.title = name
        self._photos = [MockPhotoAsset(f"photo_{i}", f"photo_{i}.jpg") for i in range(photo_count)]

    def __len__(self):
        return len(self._photos)

    @property
    def photos(self):
        return self._photos


class MockPhotosService:
    """Mock photos service for testing."""

    def __init__(self):
        self._shared_streams = [
            MockPhotoAlbum("album1", "Vacation 2024", 3),
            MockPhotoAlbum("album2", "Family Photos", 5),
        ]

    @property
    def shared_streams(self):
        return self._shared_streams


class MockPyiCloudService:
    """Mock PyiCloudService for testing."""

    def __init__(self, apple_id, password, cookie_directory=None):
        self.apple_id = apple_id
        self.requires_2fa = False
        self.photos = MockPhotosService()


@pytest.fixture
def mock_pyicloud():
    """Fixture to mock PyiCloudService."""
    with patch('backend.core.icloud_manager.PyiCloudService', MockPyiCloudService):
        yield


def test_icloud_manager_initialization(mock_pyicloud):
    """Test ICloudManager initialization."""
    manager = ICloudManager(
        apple_id="test@example.com",
        password="test_password"
    )

    assert manager.apple_id == "test@example.com"
    assert manager.api is not None


def test_list_shared_albums(mock_pyicloud):
    """Test listing shared albums."""
    manager = ICloudManager(
        apple_id="test@example.com",
        password="test_password"
    )

    albums = manager.list_shared_albums()

    assert len(albums) == 2
    assert albums[0]['name'] == "Vacation 2024"
    assert albums[0]['photo_count'] == 3
    assert albums[1]['name'] == "Family Photos"
    assert albums[1]['photo_count'] == 5


def test_get_album_info(mock_pyicloud):
    """Test getting album information."""
    manager = ICloudManager(
        apple_id="test@example.com",
        password="test_password"
    )

    album_info = manager.get_album_info("Vacation 2024")

    assert album_info is not None
    assert album_info['name'] == "Vacation 2024"
    assert album_info['photo_count'] == 3
    assert len(album_info['photos']) == 3


def test_get_album_info_not_found(mock_pyicloud):
    """Test getting info for non-existent album."""
    manager = ICloudManager(
        apple_id="test@example.com",
        password="test_password"
    )

    album_info = manager.get_album_info("Nonexistent Album")

    assert album_info is None


def test_download_album_photos(mock_pyicloud, tmp_path):
    """Test downloading album photos."""
    manager = ICloudManager(
        apple_id="test@example.com",
        password="test_password"
    )

    destination = str(tmp_path / "photos")
    downloaded = manager.download_album_photos(
        album_name="Vacation 2024",
        destination_path=destination
    )

    assert len(downloaded) == 3
    assert os.path.exists(destination)

    # Check files were created
    for file_info in downloaded:
        assert os.path.exists(file_info['filepath'])
        assert file_info['size'] > 0


def test_download_album_photos_with_duplicates(mock_pyicloud, tmp_path):
    """Test downloading with duplicate filenames."""
    manager = ICloudManager(
        apple_id="test@example.com",
        password="test_password"
    )

    destination = str(tmp_path / "photos")

    # Download once
    downloaded1 = manager.download_album_photos(
        album_name="Vacation 2024",
        destination_path=destination
    )

    # Download again - should create new files with different names
    downloaded2 = manager.download_album_photos(
        album_name="Vacation 2024",
        destination_path=destination
    )

    # All files should have unique paths
    all_paths = [f['filepath'] for f in downloaded1] + [f['filepath'] for f in downloaded2]
    assert len(all_paths) == len(set(all_paths))


def test_download_nonexistent_album(mock_pyicloud, tmp_path):
    """Test downloading from non-existent album."""
    manager = ICloudManager(
        apple_id="test@example.com",
        password="test_password"
    )

    destination = str(tmp_path / "photos")

    with pytest.raises(Exception) as exc_info:
        manager.download_album_photos(
            album_name="Nonexistent Album",
            destination_path=destination
        )

    assert "not found" in str(exc_info.value).lower()


def test_authentication_failure():
    """Test authentication failure handling."""
    with patch('backend.core.icloud_manager.PyiCloudService') as mock_service:
        mock_service.side_effect = PyiCloudFailedLoginException("Invalid credentials")

        with pytest.raises(Exception) as exc_info:
            ICloudManager(
                apple_id="test@example.com",
                password="wrong_password"
            )
        assert "Failed to login" in str(exc_info.value)


def test_2fa_required():
    """Test 2FA requirement detection."""
    with patch('backend.core.icloud_manager.PyiCloudService') as mock_service:
        mock_api = Mock()
        mock_api.requires_2fa = True
        mock_service.return_value = mock_api

        with pytest.raises(Exception) as exc_info:
            ICloudManager(
                apple_id="test@example.com",
                password="test_password"
            )
        assert "Two-factor authentication required" in str(exc_info.value)
