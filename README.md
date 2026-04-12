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

## Run with Docker on Raspberry Pi 3

No OMV is required. PiCone can run directly on Raspberry Pi OS with Docker.

1. Install Docker and Docker Compose plugin:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

2. Copy this project to the Pi and open the project folder.
3. Create your local media folders (or use your own existing paths):

```bash
mkdir -p /home/pi/media/movies /home/pi/media/tv
```

4. Set host media paths in `.env`:

```bash
HOST_MOVIES_DIR=/home/pi/media/movies
HOST_TV_DIR=/home/pi/media/tv
```

5. Optionally add `TMDB_API_KEY` to `.env`.
6. Start service:

```bash
docker compose up -d --build
```

7. Open in browser:

- `http://<pi-ip>:8080`

## Run without Docker (systemd)

This runs PiCone directly on Raspberry Pi OS using Python + systemd.

1. Install system packages:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
```

2. Copy this project to the Pi, for example at `/home/pi/PiCone`.
3. Create virtual environment and install dependencies:

```bash
cd /home/pi/PiCone
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

4. Create media and cache folders (or use your own paths):

```bash
mkdir -p /home/pi/media/movies /home/pi/media/tv /home/pi/PiCone/data
```

5. Test-run once from shell:

```bash
cd /home/pi/PiCone
MEDIA_MOVIES_DIR=/home/pi/media/movies \
MEDIA_TV_DIR=/home/pi/media/tv \
CACHE_DIR=/home/pi/PiCone/data \
SCAN_INTERVAL_SECONDS=300 \
STREAM_CHUNK_SIZE=524288 \
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```

6. Create systemd service `/etc/systemd/system/picone.service`:

```ini
[Unit]
Description=PiCone Media Server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/PiCone
Environment=MEDIA_MOVIES_DIR=/home/pi/media/movies
Environment=MEDIA_TV_DIR=/home/pi/media/tv
Environment=CACHE_DIR=/home/pi/PiCone/data
Environment=TMDB_API_KEY=
Environment=SCAN_INTERVAL_SECONDS=300
Environment=STREAM_CHUNK_SIZE=524288
ExecStart=/home/pi/PiCone/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

7. Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now picone
sudo systemctl status picone
```

8. Open in browser:

- `http://<pi-ip>:8080`

## OMV Path Notes

Typical OMV mount paths look like:

- `/srv/dev-disk-by-uuid-.../Media/Movies`
- `/srv/dev-disk-by-uuid-.../Media/TV`

Set these in `.env` as `HOST_MOVIES_DIR` and `HOST_TV_DIR`.

## Performance Tips for Pi 3

- Keep `SCAN_INTERVAL_SECONDS` >= 180 to reduce rescans.
- Keep `STREAM_CHUNK_SIZE` at 512KB unless your network is unstable.
- Prefer direct-play compatible files (H.264/H.265 in MP4/MKV).
- Use wired ethernet for best seek and startup performance.

## Notes

- This server is intended for trusted local networks.
- Browser playback depends on codec support of the client device.
