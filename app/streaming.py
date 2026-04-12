import mimetypes
from pathlib import Path
from typing import Iterator

from fastapi import HTTPException
from fastapi.responses import StreamingResponse


def _iter_file_range(file_path: Path, start: int, end: int, chunk_size: int) -> Iterator[bytes]:
    with file_path.open("rb") as handle:
        handle.seek(start)
        remaining = end - start + 1

        while remaining > 0:
            chunk = handle.read(min(chunk_size, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def _invalid_range(file_size: int) -> HTTPException:
    return HTTPException(
        status_code=416,
        detail="Requested Range Not Satisfiable",
        headers={"Content-Range": f"bytes */{file_size}"},
    )


def _parse_range_header(range_header: str, file_size: int) -> tuple[int, int]:
    if not range_header.lower().startswith("bytes="):
        raise _invalid_range(file_size)

    spec = range_header.split("=", 1)[1].split(",", 1)[0].strip()
    if "-" not in spec:
        raise _invalid_range(file_size)

    start_raw, end_raw = spec.split("-", 1)

    try:
        if not start_raw:
            suffix_length = int(end_raw)
            if suffix_length <= 0:
                raise _invalid_range(file_size)
            start = max(file_size - suffix_length, 0)
            end = file_size - 1
        else:
            start = int(start_raw)
            end = int(end_raw) if end_raw else file_size - 1
    except ValueError as exc:
        raise _invalid_range(file_size) from exc

    if start < 0 or end < start or start >= file_size:
        raise _invalid_range(file_size)

    end = min(end, file_size - 1)
    return start, end


def build_streaming_response(file_path: Path, range_header: str | None, chunk_size: int) -> StreamingResponse:
    file_size = file_path.stat().st_size
    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"

    status_code = 200
    start = 0
    end = file_size - 1
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Disposition": f'inline; filename="{file_path.name}"',
        "Cache-Control": "no-store",
    }

    if range_header:
        start, end = _parse_range_header(range_header, file_size)
        status_code = 206
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"

    headers["Content-Length"] = str(end - start + 1)

    return StreamingResponse(
        _iter_file_range(file_path, start, end, chunk_size),
        status_code=status_code,
        headers=headers,
        media_type=content_type,
    )
