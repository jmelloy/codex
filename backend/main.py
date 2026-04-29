import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from routers import images, tags


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables on startup
    Base.metadata.create_all(bind=engine)
    # Ensure thumbnails directory exists
    Path("./thumbnails").mkdir(exist_ok=True)
    yield


app = FastAPI(title="Diffusion Viewer API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(images.router)
app.include_router(tags.router)

# Serve thumbnails statically
thumbnails_dir = Path("./thumbnails")
thumbnails_dir.mkdir(exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=str(thumbnails_dir)), name="thumbnails")


@app.get("/api/health")
def health():
    return {"status": "ok"}
