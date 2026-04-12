import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .storage import load_json, save_json


class PlaybackProgressStore:
    def __init__(self, cache_file: Path) -> None:
        self.cache_file = cache_file
        self._lock = threading.Lock()
        self._data: dict[str, Any] = load_json(self.cache_file, default={"positions": {}})

        if "positions" not in self._data or not isinstance(self._data["positions"], dict):
            self._data["positions"] = {}

    def get(self, media_id: str) -> dict[str, Any]:
        entry = self._data["positions"].get(media_id)
        if not isinstance(entry, dict):
            return {"seconds": 0, "updated_at": None}
        return {
            "seconds": max(float(entry.get("seconds", 0)), 0.0),
            "updated_at": entry.get("updated_at"),
        }

    def set(self, media_id: str, seconds: float) -> dict[str, Any]:
        safe_seconds = max(float(seconds), 0.0)
        updated_at = datetime.now(timezone.utc).isoformat()

        with self._lock:
            self._data["positions"][media_id] = {
                "seconds": round(safe_seconds, 2),
                "updated_at": updated_at,
            }
            save_json(self.cache_file, self._data)

        return self._data["positions"][media_id]
