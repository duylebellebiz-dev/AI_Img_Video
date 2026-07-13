from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import get_settings
from app.database import Base, engine
from app.routers import batch, branding, edit
from app.services.storage_service import StorageService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Phase 1 MVP: create tables directly instead of Alembic migrations.
    Base.metadata.create_all(bind=engine)
    yield


settings = get_settings()

app = FastAPI(title="NailSocial AI - Image Pipeline", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(batch.router)
app.include_router(edit.router)
app.include_router(branding.router)

(settings.storage_path / "generated").mkdir(parents=True, exist_ok=True)
(settings.storage_path / "original").mkdir(parents=True, exist_ok=True)
(settings.storage_path / "branding").mkdir(parents=True, exist_ok=True)

_storage = StorageService(settings)


def _serve(path: Path) -> FileResponse:
    """Local storage_root is just a cache in front of R2 — a host without a
    persistent disk (e.g. Render's free web service) can lose local files on
    restart, so pull the file back from R2 on a cache miss before serving."""
    _storage.ensure_local(path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)


@app.get("/media/generated/{job_id}/{filename}", name="generated")
def media_generated(job_id: str, filename: str) -> FileResponse:
    job_id = Path(job_id).name
    filename = Path(filename).name
    return _serve(settings.storage_path / "generated" / job_id / filename)


@app.get("/media/original/{job_id}/{kind}/{filename}", name="original")
def media_original(job_id: str, kind: str, filename: str) -> FileResponse:
    job_id = Path(job_id).name
    kind = Path(kind).name
    filename = Path(filename).name
    return _serve(settings.storage_path / "original" / job_id / kind / filename)


@app.get("/media/branding/{filename}", name="branding")
def media_branding(filename: str) -> FileResponse:
    filename = Path(filename).name
    return _serve(settings.storage_path / "branding" / filename)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "mock_claude": not settings.has_anthropic_key,
        "mock_gemini": not settings.has_gemini_key,
    }
