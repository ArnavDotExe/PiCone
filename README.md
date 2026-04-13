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

## Run without Docker (systemd)

This runs PiCone directly on Raspberry Pi OS using Python + systemd.

### Automated install (recommended)

From the project root, run:

```bash
chmod +x install.sh
./install.sh
```

If your apt repositories are managed externally (for example OMV) and already have
Python installed, you can skip apt package installation:

```bash
SKIP_APT=1 ./install.sh
```

The script installs system packages, sets up `.venv`, installs Python dependencies,
creates `.env` from `.env.example`, creates media/cache folders, and enables the
`picone` systemd service.

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

4. Create `.env` from template and edit values:

```bash
cp .env.example .env
```

5. Configure `.env` (example):

```bash
MEDIA_MOVIES_DIR=/home/pi/media/movies
MEDIA_TV_DIR=/home/pi/media/tv
CACHE_DIR=/home/pi/PiCone/data
TMDB_API_KEY=
SCAN_INTERVAL_SECONDS=300
STREAM_CHUNK_SIZE=524288
```

6. Create media and cache folders (or use your own paths):

```bash
mkdir -p /home/pi/media/movies /home/pi/media/tv /home/pi/PiCone/data
```

7. Test-run once from shell:

```bash
cd /home/pi/PiCone
source .venv/bin/activate
python -m app.main
```

8. Create systemd service `/etc/systemd/system/picone.service`:

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
EnvironmentFile=/home/pi/PiCone/.env
ExecStart=/home/pi/PiCone/.venv/bin/python -m app.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

9. Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now picone
sudo systemctl status picone
```

10. Open in browser:

- `http://<pi-ip>:8080`

## Performance Tips for Pi 3

- Keep `SCAN_INTERVAL_SECONDS` >= 180 to reduce rescans.
- Keep `STREAM_CHUNK_SIZE` at 512KB unless your network is unstable.
- Prefer direct-play compatible files (H.264/H.265 in MP4/MKV).
- Use wired ethernet for best seek and startup performance.

## Notes

- This server is intended for trusted local networks.
- Browser playback depends on codec support of the client device.
