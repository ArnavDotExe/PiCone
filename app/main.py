import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .metadata import MetadataProvider
from .progress import PlaybackProgressStore
from .scanner import MediaLibrary
from .streaming import build_streaming_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("picone.api")

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
STATIC_DIR = BASE_DIR / "static"

settings = Settings()
settings.cache_dir.mkdir(parents=True, exist_ok=True)

metadata_provider = MetadataProvider(
    api_key=settings.tmdb_api_key,
    cache_file=settings.cache_dir / "metadata_cache.json",
    max_entries=settings.metadata_cache_entries,
)
library = MediaLibrary(
    settings=settings,
    metadata_provider=metadata_provider,
    cache_file=settings.cache_dir / "media_index.json",
)
progress_store = PlaybackProgressStore(settings.cache_dir / "playback_progress.json")


class ProgressPayload(BaseModel):
    seconds: float = Field(ge=0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting PiCone media server")
    library.scan(force=True)
    yield
    logger.info("Stopping PiCone media server")


app = FastAPI(title="PiCone", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.middleware("http")
async def request_logger(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "%s %s -> %d %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/", response_class=FileResponse)
def root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/player", response_class=FileResponse)
def player_page() -> FileResponse:
    return FileResponse(WEB_DIR / "player.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/movies")
def list_movies(refresh: bool = False) -> dict:
    movies = library.get_movies(force_refresh=refresh)
    return {
        "count": len(movies),
        "last_scan": library.get_last_scan(),
        "items": movies,
    }


@app.get("/tv")
def list_tv(refresh: bool = False) -> dict:
    shows = library.get_tv(force_refresh=refresh)
    episodes_count = sum(len(show.get("episodes", [])) for show in shows)
    return {
        "count_shows": len(shows),
        "count_episodes": episodes_count,
        "last_scan": library.get_last_scan(),
        "shows": shows,
    }


@app.get("/search")
def search_media(q: str, refresh: bool = False) -> dict:
    if not q.strip():
        return {"movies": [], "tv": []}
    return library.search(q, force_refresh=refresh)


@app.get("/stream/{media_path:path}")
def stream_media(media_path: str, request: Request):
    try:
        file_path = library.resolve_stream_path(media_path)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    range_header = request.headers.get("range")
    return build_streaming_response(
        file_path=file_path,
        range_header=range_header,
        chunk_size=settings.stream_chunk_size,
    )


@app.get("/progress/{media_id}")
def get_progress(media_id: str) -> dict:
    return progress_store.get(media_id)


@app.post("/progress/{media_id}")
def update_progress(media_id: str, payload: ProgressPayload) -> dict:
    return progress_store.set(media_id, payload.seconds)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080)
