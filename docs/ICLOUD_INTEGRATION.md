# iCloud Photo Album Integration

The Codex system includes integration with iCloud to download shared photo albums (also known as shared photo streams). This feature allows you to download photos from albums that aren't necessarily part of your main photo library.

## Features

- **List Shared Albums**: Discover all shared photo streams associated with your iCloud account
- **Get Album Details**: View metadata and photo information for specific albums
- **Download Photos**: Download all photos from a shared album to a local directory
- **Automatic Deduplication**: Handles duplicate filenames automatically
- **Metadata Tracking**: Preserves photo metadata including dates, dimensions, and file types

## Installation

The pyicloud library is included in the project dependencies. Install it with:

```bash
pip install -e ".[dev]"
```

## Authentication

iCloud authentication requires your Apple ID credentials. The system stores session cookies to avoid repeated authentication.

**Important Notes:**
- Two-factor authentication (2FA) must be handled interactively on first use
- Session cookies are stored in `~/.pyicloud` by default
- Credentials are not stored; only session cookies

## API Usage

### 1. List Shared Albums

List all shared photo albums/streams:

```bash
curl -X POST "http://localhost:8000/api/v1/icloud/albums/list" \
  -H "Content-Type: application/json" \
  -d '{
    "apple_id": "your.email@icloud.com",
    "password": "your-password"
  }'
```

Response:
```json
[
  {
    "id": "album-id-1",
    "name": "Vacation 2024",
    "title": "Vacation 2024",
    "photo_count": 42
  },
  {
    "id": "album-id-2",
    "name": "Family Photos",
    "title": "Family Photos",
    "photo_count": 108
  }
]
```

### 2. Get Album Information

Get detailed information about a specific album:

```bash
curl -X POST "http://localhost:8000/api/v1/icloud/albums/info" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "apple_id": "your.email@icloud.com",
      "password": "your-password"
    },
    "album_name": "Vacation 2024"
  }'
```

Response:
```json
{
  "id": "album-id-1",
  "name": "Vacation 2024",
  "title": "Vacation 2024",
  "photo_count": 42,
  "photos": [
    {
      "id": "photo-id-1",
      "filename": "IMG_1234.jpg",
      "size": 2048576,
      "asset_date": "2024-06-15T10:30:00",
      "dimensions": [4032, 3024],
      "item_type": "image/jpeg",
      "is_live_photo": false
    }
  ]
}
```

### 3. Download Album Photos

Download all photos from a shared album:

```bash
curl -X POST "http://localhost:8000/api/v1/icloud/albums/download" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "apple_id": "your.email@icloud.com",
      "password": "your-password"
    },
    "album_name": "Vacation 2024",
    "destination_path": "/path/to/download/directory",
    "version": "original"
  }'
```

**Parameters:**
- `version`: Photo quality to download
  - `original` (default): Full resolution original
  - `medium`: Medium resolution
  - `thumb`: Thumbnail

Response:
```json
[
  {
    "filename": "IMG_1234.jpg",
    "filepath": "/path/to/download/directory/IMG_1234.jpg",
    "photo_id": "photo-id-1",
    "size": 2048576,
    "asset_date": "2024-06-15T10:30:00",
    "dimensions": [4032, 3024],
    "is_live_photo": false
  }
]
```

## Python Usage

You can also use the iCloud manager directly in Python code:

```python
from backend.core.icloud_manager import ICloudManager

# Initialize manager
manager = ICloudManager(
    apple_id="your.email@icloud.com",
    password="your-password"
)

# List albums
albums = manager.list_shared_albums()
for album in albums:
    print(f"{album['name']}: {album['photo_count']} photos")

# Get album details
album_info = manager.get_album_info("Vacation 2024")
print(f"Album has {len(album_info['photos'])} photos")

# Download photos
downloaded = manager.download_album_photos(
    album_name="Vacation 2024",
    destination_path="/path/to/download",
    version="original"
)
print(f"Downloaded {len(downloaded)} photos")
```

## Security Considerations

1. **Credentials**: Never commit credentials to source control
2. **Session Cookies**: Keep `~/.pyicloud` directory secure
3. **2FA**: Enable two-factor authentication on your iCloud account
4. **API Access**: Restrict API access to trusted networks in production

## Troubleshooting

### Two-Factor Authentication Required

If you get a "Two-factor authentication required" error:

1. Run authentication interactively first:
   ```python
   from pyicloud import PyiCloudService
   api = PyiCloudService('your.email@icloud.com', 'your-password')
   
   # Enter 2FA code when prompted
   if api.requires_2fa:
       code = input("Enter 2FA code: ")
       api.validate_2fa_code(code)
       api.trust_session()
   ```

2. Session cookies will be saved in `~/.pyicloud`
3. Subsequent API calls will use the trusted session

### Album Not Found

Ensure the album name matches exactly. Use the list endpoint to see available albums.

### Download Failures

- Check network connectivity
- Verify sufficient disk space
- Ensure write permissions on destination directory
- Large albums may take time; consider downloading in batches

## Integration with Codex Notebooks

Photos downloaded from iCloud can be automatically tracked in Codex notebooks:

1. Set the download destination to a notebook directory
2. The watcher service will detect new files
3. Metadata will be indexed automatically
4. Photos will appear in the notebook file browser

Example:
```python
from backend.core.icloud_manager import ICloudManager
from backend.core.git_manager import GitManager

# Download to notebook
notebook_path = "/path/to/workspace/notebooks/vacation-photos"
manager = ICloudManager("your.email@icloud.com", "password")

downloaded = manager.download_album_photos(
    album_name="Vacation 2024",
    destination_path=notebook_path
)

# Git tracking (optional)
git_manager = GitManager(notebook_path)
for photo in downloaded:
    # Binary files are auto-ignored by .gitignore
    pass

print(f"Downloaded {len(downloaded)} photos to notebook")
```

## Limitations

- Shared albums only (not main library photos)
- Requires valid iCloud credentials
- Rate limiting may apply for large downloads
- Live photos download as static images
- Videos in shared albums are supported

## API Reference

See the OpenAPI documentation at `/docs` when the server is running for complete API reference including request/response schemas.
