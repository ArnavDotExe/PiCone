const titleEl = document.getElementById("playerTitle");
const statusEl = document.getElementById("playerStatus");
const player = document.getElementById("videoPlayer");

const params = new URLSearchParams(window.location.search);
const streamPath = params.get("path") || "";
const mediaTitle = params.get("title") || "Unknown media";
const mediaId = params.get("id") || "";

let lastSavedSecond = -1;

function encodeStreamPath(path) {
    return path.split("/").map((part) => encodeURIComponent(part)).join("/");
}

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
    }
    return response.json();
}

async function saveProgress(seconds) {
    if (!mediaId || !Number.isFinite(seconds) || seconds < 0) {
        return;
    }

    const rounded = Math.floor(seconds);
    if (rounded === lastSavedSecond) {
        return;
    }
    lastSavedSecond = rounded;

    try {
        await fetch(`/progress/${encodeURIComponent(mediaId)}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ seconds: rounded }),
            keepalive: true,
        });
    } catch (error) {
        statusEl.textContent = `Progress save warning: ${error.message}`;
    }
}

async function resumeProgress() {
    if (!mediaId) {
        return;
    }

    try {
        const progress = await fetchJson(`/progress/${encodeURIComponent(mediaId)}`);
        const resumeAt = Number(progress.seconds || 0);

        if (resumeAt > 5) {
            const seek = () => {
                if (Number.isFinite(player.duration) && resumeAt < Math.max(player.duration - 10, 0)) {
                    player.currentTime = resumeAt;
                    statusEl.textContent = `Resumed at ${Math.floor(resumeAt)}s`;
                }
            };
            if (player.readyState >= 1) {
                seek();
            } else {
                player.addEventListener("loadedmetadata", seek, { once: true });
            }
        }
    } catch (error) {
        statusEl.textContent = `Resume lookup warning: ${error.message}`;
    }
}

function initPlayer() {
    titleEl.textContent = mediaTitle;

    if (!streamPath) {
        statusEl.textContent = "Missing stream path";
        return;
    }

    player.src = `/stream/${encodeStreamPath(streamPath)}`;
    player.addEventListener("error", () => {
        statusEl.textContent = "Playback error. Verify file path and browser codec support.";
    });

    player.addEventListener("pause", () => {
        saveProgress(player.currentTime);
    });

    player.addEventListener("ended", () => {
        saveProgress(0);
    });

    setInterval(() => {
        if (!player.paused && !player.seeking) {
            saveProgress(player.currentTime);
        }
    }, 5000);

    window.addEventListener("beforeunload", () => {
        saveProgress(player.currentTime);
    });

    resumeProgress();
}

initPlayer();
