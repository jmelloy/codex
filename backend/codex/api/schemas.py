"""API schemas for request/response validation."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    is_active: bool
    theme_setting: str | None = None


class ThemeUpdate(BaseModel):
    """Schema for updating user theme setting."""

    theme: str


class ThemeResponse(BaseModel):
    """Schema for theme information."""

    id: str
    name: str
    label: str
    description: str
    className: str
    category: str
    version: str
    author: str
