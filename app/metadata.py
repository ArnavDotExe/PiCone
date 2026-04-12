import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from .storage import load_json, save_json

logger = logging.getLogger("picone.metadata")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MetadataProvider:
    def __init__(self, api_key: str | None, cache_file: Path, max_entries: int = 2000) -> None:
        self.api_key = api_key
        self.cache_file = cache_file
        self.max_entries = max_entries
        self._cache: dict[str, Any] = load_json(self.cache_file, default={"movies": {}})

        if "movies" not in self._cache or not isinstance(self._cache["movies"], dict):
            self._cache["movies"] = {}

    def get_movie_metadata(self, raw_name: str) -> dict[str, Any]:
        guessed_title, guessed_year = self._guess_title(raw_name)
        cache_key = f"{guessed_title}|{guessed_year or ''}".strip("|")

        cached = self._cache["movies"].get(cache_key)
        if isinstance(cached, dict):
            return cached

        payload = {
            "title": guessed_title,
            "poster_url": None,
            "updated_at": _utc_now(),
        }

        if self.api_key:
            try:
                remote = self._fetch_tmdb(guessed_title, guessed_year)
                if remote:
                    payload.update(remote)
            except Exception as exc:  # noqa: BLE001
                logger.warning("TMDb lookup failed for %s: %s", raw_name, exc)

        self._cache["movies"][cache_key] = payload
        self._prune_cache()
        save_json(self.cache_file, self._cache)
        return payload

    def _fetch_tmdb(self, title: str, year: str | None) -> dict[str, Any] | None:
        query_params = {
            "api_key": self.api_key,
            "query": title,
            "include_adult": "false",
        }
        if year:
            query_params["year"] = year

        url = f"https://api.themoviedb.org/3/search/movie?{urlencode(query_params)}"
        with urlopen(url, timeout=4) as response:  # nosec B310
            body = response.read()

        data = json.loads(body.decode("utf-8"))
        results = data.get("results") or []
        if not results:
            return None

        first = results[0]
        poster_path = first.get("poster_path")
        poster_url = f"https://image.tmdb.org/t/p/w342{poster_path}" if poster_path else None

        return {
            "title": first.get("title") or title,
            "poster_url": poster_url,
            "updated_at": _utc_now(),
        }

    def _guess_title(self, raw_name: str) -> tuple[str, str | None]:
        cleaned = re.sub(r"[._]+", " ", raw_name).strip()
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", cleaned)
        year = year_match.group(1) if year_match else None
        if year_match:
            cleaned = cleaned.replace(year_match.group(0), "")

        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -._")
        title = cleaned.title() if cleaned else raw_name
        return title, year

    def _prune_cache(self) -> None:
        movies = self._cache["movies"]
        if len(movies) <= self.max_entries:
            return

        sorted_items = sorted(
            movies.items(),
            key=lambda item: item[1].get("updated_at", ""),
            reverse=True,
        )
        self._cache["movies"] = dict(sorted_items[: self.max_entries])
