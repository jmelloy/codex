"""API routes for iCloud integration."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from backend.core.icloud_manager import ICloudManager


router = APIRouter(prefix="/api/v1/icloud", tags=["icloud"])


class ICloudCredentials(BaseModel):
    """iCloud authentication credentials."""
    apple_id: str = Field(..., description="Apple ID email address")
    password: str = Field(..., description="Apple ID password")


class AlbumInfo(BaseModel):
    """Shared album information."""
    id: str
    name: str
    title: str
    photo_count: int


class PhotoInfo(BaseModel):
    """Photo information."""
    id: str
    filename: Optional[str]
    size: Optional[int]
    asset_date: Optional[str]
    dimensions: Optional[tuple]
    item_type: Optional[str]
    is_live_photo: bool


class DetailedAlbumInfo(BaseModel):
    """Detailed shared album information."""
    id: str
    name: str
    title: str
    photo_count: int
    photos: List[PhotoInfo]


class AlbumInfoRequest(BaseModel):
    """Request for album information."""
    credentials: ICloudCredentials
    album_name: str = Field(..., description="Name of the album")


class DownloadRequest(BaseModel):
    """Photo download request."""
    credentials: ICloudCredentials
    album_name: str = Field(..., description="Name of the album to download")
    destination_path: str = Field(..., description="Directory to save photos")
    version: str = Field(default="original", description="Photo version: original, medium, thumb")


class DownloadResponse(BaseModel):
    """Photo download response."""
    filename: str
    filepath: str
    photo_id: str
    size: int
    asset_date: Optional[str]
    dimensions: Optional[tuple]
    is_live_photo: bool


@router.post("/albums/list", response_model=List[AlbumInfo])
async def list_shared_albums(credentials: ICloudCredentials):
    """List all shared photo albums from iCloud.
    
    This endpoint retrieves shared photo streams that aren't necessarily 
    part of the main photo library.
    """
    try:
        manager = ICloudManager(
            apple_id=credentials.apple_id,
            password=credentials.password
        )
        albums = manager.list_shared_albums()
        return albums
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing albums: {str(e)}"
        )


@router.post("/albums/info", response_model=Optional[DetailedAlbumInfo])
async def get_album_info(request: AlbumInfoRequest):
    """Get detailed information about a specific shared album."""
    try:
        manager = ICloudManager(
            apple_id=request.credentials.apple_id,
            password=request.credentials.password
        )
        album_info = manager.get_album_info(request.album_name)
        
        if not album_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Album '{request.album_name}' not found"
            )
        
        return album_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting album info: {str(e)}"
        )


@router.post("/albums/download", response_model=List[DownloadResponse])
async def download_album(request: DownloadRequest):
    """Download all photos from a shared album.
    
    Downloads photos from an iCloud shared album to the specified directory.
    The photos are not necessarily part of the main photo library.
    """
    try:
        manager = ICloudManager(
            apple_id=request.credentials.apple_id,
            password=request.credentials.password
        )
        
        downloaded_files = manager.download_album_photos(
            album_name=request.album_name,
            destination_path=request.destination_path,
            version=request.version
        )
        
        return downloaded_files
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error downloading album: {str(e)}"
        )
