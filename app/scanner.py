import hashlib
import logging
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import Settings
from .metadata import MetadataProvider
from .storage import load_json, save_json

logger = logging.getLogger("picone.scanner")

VIDEO_EXTENSIONS = {
    ".mp4",
    ".m4v",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".mpeg",
    ".mpg",
}


class MediaLibrary:
    def __init__(self, settings: Settings, metadata_provider: MetadataProvider, cache_file: Path) -> None:
        self.settings = settings
        self.metadata_provider = metadata_provider
        self.cache_file = cache_file

        self._lock = threading.Lock()
        self._last_scan_monotonic = 0.0
        self._index: dict[str, Any] = load_json(
            self.cache_file,
            default={"movies": [], "tv": [], "last_scan": None},
        )

    def scan(self, force: bool = False) -> None:
        with self._lock:
            now = time.monotonic()
            age = now - self._last_scan_monotonic
            if (
                not force
                and self._last_scan_monotonic > 0
                and age < self.settings.scan_interval_seconds
            ):
                return

            movies = self._scan_movies()
            tv = self._scan_tv()

            self._index = {
                "movies": movies,
                "tv": tv,
                "last_scan": datetime.now(timezone.utc).isoformat(),
            }
            self._last_scan_monotonic = now
            save_json(self.cache_file, self._index)

            tv_episode_count = sum(len(show["episodes"]) for show in tv)
            logger.info(
                "Indexed media library: %d movies, %d shows, %d episodes",
                len(movies),
                len(tv),
                tv_episode_count,
            )

    def get_movies(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        self.scan(force=force_refresh)
        return list(self._index.get("movies", []))

    def get_tv(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        self.scan(force=force_refresh)
        return list(self._index.get("tv", []))

    def get_last_scan(self) -> str | None:
        return self._index.get("last_scan")

    def search(self, query: str, force_refresh: bool = False) -> dict[str, Any]:
        self.scan(force=force_refresh)
        needle = query.casefold().strip()
        if not needle:
            return {"movies": self.get_movies(), "tv": self.get_tv()}

        matched_movies = [
            item
            for item in self._index.get("movies", [])
            if needle in item.get("title", "").casefold()
            or needle in item.get("filename", "").casefold()
        ]

        matched_shows = []
        for show in self._index.get("tv", []):
            show_name = show.get("show", "")
            matched_episodes = [
                ep
                for ep in show.get("episodes", [])
                if needle in ep.get("title", "").casefold()
                or needle in show_name.casefold()
                or needle in ep.get("filename", "").casefold()
            ]
            if matched_episodes:
                matched_shows.append({"show": show_name, "episodes": matched_episodes})

        return {"movies": matched_movies, "tv": matched_shows}

    def resolve_stream_path(self, stream_path: str) -> Path:
        sanitized = stream_path.strip().strip("/\\")
        category, separator, relative = sanitized.partition("/")
        if not separator or not relative:
            raise FileNotFoundError("Invalid stream path")

        if category == "movies":
            root = self.settings.media_movies_dir
        elif category == "tv":
            root = self.settings.media_tv_dir
        else:
            raise FileNotFoundError("Unknown media category")

        root_resolved = root.resolve()
        candidate = (root_resolved / relative).resolve()

        if root_resolved not in candidate.parents and candidate != root_resolved:
            raise PermissionError("Path traversal detected")

        if not candidate.is_file() or candidate.suffix.lower() not in VIDEO_EXTENSIONS:
            raise FileNotFoundError("Media file not found")

        return candidate

    def _scan_movies(self) -> list[dict[str, Any]]:
        root = self.settings.media_movies_dir
        if not root.exists():
            logger.warning("Movies directory not found: %s", root)
            return []

        entries: list[dict[str, Any]] = []
        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
                continue

            rel_path = file_path.relative_to(root).as_posix()
            stream_path = f"movies/{rel_path}"
            metadata = self.metadata_provider.get_movie_metadata(file_path.stem)
            stat = file_path.stat()

            entries.append(
                {
                    "id": self._make_id(stream_path),
                    "title": metadata.get("title") or self._clean_title(file_path.stem),
                    "filename": file_path.name,
                    "relative_path": rel_path,
                    "stream_path": stream_path,
                    "poster_url": metadata.get("poster_url"),
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                }
            )

        entries.sort(key=lambda item: item["title"].casefold())
        return entries

    def _scan_tv(self) -> list[dict[str, Any]]:
        root = self.settings.media_tv_dir
        if not root.exists():
            logger.warning("TV directory not found: %s", root)
            return []

        shows: dict[str, list[dict[str, Any]]] = {}

        for file_path in sorted(root.rglob("*")):
            if not file_path.is_file() or file_path.suffix.lower() not in VIDEO_EXTENSIONS:
                continue

            rel_path = file_path.relative_to(root).as_posix()
            rel_parts = Path(rel_path).parts
            show_name = self._clean_title(rel_parts[0]) if len(rel_parts) > 1 else "Unknown Show"

            season, episode = self._extract_episode(file_path.stem)
            stream_path = f"tv/{rel_path}"
            stat = file_path.stat()

            episode_payload = {
                "id": self._make_id(stream_path),
                "title": self._clean_title(file_path.stem),
                "filename": file_path.name,
                "relative_path": rel_path,
                "stream_path": stream_path,
                "show": show_name,
                "season": season,
                "episode": episode,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            }
            shows.setdefault(show_name, []).append(episode_payload)

        grouped = []
        for show_name, episodes in shows.items():
            episodes.sort(key=lambda ep: (ep.get("season") or 0, ep.get("episode") or 0, ep["title"]))
            grouped.append({"show": show_name, "episodes": episodes})

        grouped.sort(key=lambda item: item["show"].casefold())
        return grouped

    @staticmethod
    def _make_id(stream_path: str) -> str:
        return hashlib.sha1(stream_path.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _clean_title(name: str) -> str:
        cleaned = re.sub(r"[._]+", " ", name)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -._")
        return cleaned.title() if cleaned else name

    @staticmethod
    def _extract_episode(file_stem: str) -> tuple[int | None, int | None]:
        match = re.search(r"[Ss](\d{1,2})[Ee](\d{1,2})", file_stem)
        if not match:
            return None, None
        return int(match.group(1)), int(match.group(2))
