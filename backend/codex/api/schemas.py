"""API schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    username: str
    email: str
    is_active: bool
    theme_setting: str | None = None

    class Config:
        from_attributes = True


class ThemeUpdate(BaseModel):
    """Schema for updating user theme setting."""

    theme: str
