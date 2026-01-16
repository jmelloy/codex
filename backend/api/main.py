"""Main FastAPI application."""

import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import init_system_db, get_system_session
from backend.api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    verify_password,
    get_password_hash,
    get_current_active_user,
)
from backend.db.models import User
from backend.api.schemas import UserCreate, UserResponse
from backend.api.routes import workspaces, notebooks, files, search, tasks, markdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_system_db()
    yield


app = FastAPI(
    title="Codex API",
    description="A hierarchical digital laboratory journal system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Codex API", "version": "0.1.0", "docs": "/docs"}


@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_system_session)):
    """Login endpoint to get access token."""
    from sqlmodel import select

    result = await session.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)

    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_system_session)):
    """Register a new user."""
    from sqlmodel import select
    from pathlib import Path
    from backend.db.database import DATA_DIRECTORY
    from backend.db.models import Workspace
    from backend.api.routes.workspaces import slugify

    # Check if username already exists
    result = await session.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    # Check if email already exists
    result = await session.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(username=user_data.username, email=user_data.email, hashed_password=hashed_password, is_active=True)

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    # Create default workspace using username
    base_path = Path(DATA_DIRECTORY)
    slug = slugify(user_data.username)
    workspace_path = base_path / slug
    
    # Handle name collisions by appending a number
    counter = 1
    original_slug = slug
    while workspace_path.exists():
        slug = f"{original_slug}-{counter}"
        workspace_path = base_path / slug
        counter += 1
    
    # Create the workspace directory
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Create default workspace
    default_workspace = Workspace(
        name=user_data.username,
        path=str(workspace_path),
        owner_id=new_user.id
    )
    session.add(default_workspace)
    await session.commit()

    return new_user


# Include routers
app.include_router(workspaces.router, prefix="/api/v1/workspaces", tags=["workspaces"])
app.include_router(notebooks.router, prefix="/api/v1/notebooks", tags=["notebooks"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(markdown.router, prefix="/api/v1/markdown", tags=["markdown"])


if __name__ == "__main__":
    import uvicorn

    debug = os.getenv("DEBUG", "false").lower() == "true"
    log_level = "debug" if debug else "info"
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level=log_level, reload=debug)
