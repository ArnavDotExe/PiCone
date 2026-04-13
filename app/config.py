import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self) -> None:
        default_movies = BASE_DIR / "media" / "movies"
        default_tv = BASE_DIR / "media" / "tv"
        default_cache = BASE_DIR / "data"

        self.media_movies_dir = Path(os.getenv("MEDIA_MOVIES_DIR", str(default_movies))).expanduser()
        self.media_tv_dir = Path(os.getenv("MEDIA_TV_DIR", str(default_tv))).expanduser()
        self.cache_dir = Path(os.getenv("CACHE_DIR", str(default_cache))).expanduser()

        self.tmdb_api_key = os.getenv("TMDB_API_KEY", "").strip() or None

        self.scan_interval_seconds = self._int_env("SCAN_INTERVAL_SECONDS", 300, minimum=10)
        self.stream_chunk_size = self._int_env("STREAM_CHUNK_SIZE", 512 * 1024, minimum=64 * 1024)
        self.metadata_cache_entries = self._int_env("METADATA_CACHE_ENTRIES", 2000, minimum=100)

    @staticmethod
    def _int_env(name: str, default: int, minimum: int) -> int:
        raw_value = os.getenv(name)
        if raw_value is None:
            return default
        try:
            parsed = int(raw_value)
        except ValueError:
            return default
        return max(parsed, minimum)
