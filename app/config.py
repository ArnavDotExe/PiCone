import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        self.media_movies_dir = Path(os.getenv("MEDIA_MOVIES_DIR", "/media/movies"))
        self.media_tv_dir = Path(os.getenv("MEDIA_TV_DIR", "/media/tv"))
        self.cache_dir = Path(os.getenv("CACHE_DIR", "/app/data"))

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
