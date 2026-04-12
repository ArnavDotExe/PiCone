# PiCone

PiCone is a lightweight, self-hosted media server built for Raspberry Pi 3 (ARMv7, 32-bit). It is designed for local-network direct playback with no transcoding.

## Features

- Fast scan/index of mounted movie and TV directories
- REST API for movies, TV episodes, and search
- Direct HTTP streaming with byte range support (seek in browser player)
- No transcoding (low CPU and memory use)
- Optional TMDb metadata (title/poster) with JSON cache
- Playback position memory in JSON cache
- Simple responsive web UI for phone/laptop browsers

## API

- `GET /movies` -> list movies
- `GET /tv` -> list shows and episodes
- `GET /stream/{path}` -> stream media with range support
- `GET /search?q=...` -> search movies and episodes
- `GET /progress/{media_id}` -> get saved position
- `POST /progress/{media_id}` -> update saved position

## Project Layout

- `app/` backend modules
- `web/` HTML pages
- `static/` CSS and JavaScript
- `data/` JSON caches and playback history (mounted volume)

## Run on Raspberry Pi + OMV

1. Install Docker and Docker Compose plugin on OMV host.
2. Copy this project to the Pi.
3. Adjust volume paths in `docker-compose.yml` to your OMV media mount paths.
4. Create `.env` from `.env.example` if you want TMDb metadata.
5. Start service:

```bash
docker compose up -d --build
```

6. Open in browser:

- `http://<pi-ip>:8080`

## OMV Path Notes

Typical OMV mount paths look like:

- `/srv/dev-disk-by-uuid-.../Media/Movies`
- `/srv/dev-disk-by-uuid-.../Media/TV`

Set these on the left side of each volume mapping in `docker-compose.yml`.

## Performance Tips for Pi 3

- Keep `SCAN_INTERVAL_SECONDS` >= 180 to reduce rescans.
- Keep `STREAM_CHUNK_SIZE` at 512KB unless your network is unstable.
- Prefer direct-play compatible files (H.264/H.265 in MP4/MKV).
- Use wired ethernet for best seek and startup performance.

## Notes

- This server is intended for trusted local networks.
- Browser playback depends on codec support of the client device.
