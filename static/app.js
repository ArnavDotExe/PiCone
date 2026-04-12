const state = {
    movies: [],
    tvShows: [],
};

const moviesGrid = document.getElementById("moviesGrid");
const tvGrid = document.getElementById("tvGrid");
const moviesCount = document.getElementById("moviesCount");
const tvCount = document.getElementById("tvCount");
const statusLine = document.getElementById("statusLine");
const searchInput = document.getElementById("searchInput");
const refreshBtn = document.getElementById("refreshBtn");

let searchTimer = null;

function openPlayer(item) {
    const params = new URLSearchParams({
        path: item.stream_path,
        title: item.title,
        id: item.id,
    });
    window.location.href = `/player?${params.toString()}`;
}

function createCard(item, subtitle = "") {
    const card = document.createElement("article");
    card.className = "media-card";

    let thumb;
    if (item.poster_url) {
        thumb = document.createElement("img");
        thumb.className = "media-thumb";
        thumb.loading = "lazy";
        thumb.src = item.poster_url;
        thumb.alt = item.title || "Poster";
        thumb.addEventListener("error", () => {
            const fallback = document.createElement("div");
            fallback.className = "media-thumb";
            thumb.replaceWith(fallback);
        });
    } else {
        thumb = document.createElement("div");
        thumb.className = "media-thumb";
    }

    const meta = document.createElement("div");
    meta.className = "media-meta";

    const titleEl = document.createElement("p");
    titleEl.className = "media-title";
    titleEl.textContent = item.title || item.filename || "Untitled";

    const subEl = document.createElement("p");
    subEl.className = "media-sub";
    subEl.textContent = subtitle || item.filename || "";

    meta.appendChild(titleEl);
    meta.appendChild(subEl);
    card.appendChild(thumb);
    card.appendChild(meta);

    card.addEventListener("click", () => openPlayer(item));
    return card;
}

function flattenEpisodes(shows) {
    const episodes = [];
    for (const show of shows) {
        for (const ep of show.episodes || []) {
            episodes.push({
                ...ep,
                title: ep.title || ep.filename,
                subtitle: show.show,
            });
        }
    }
    return episodes;
}

function renderMovies(movies) {
    moviesGrid.innerHTML = "";
    for (const movie of movies) {
        moviesGrid.appendChild(createCard(movie, movie.filename));
    }
    moviesCount.textContent = String(movies.length);
}

function renderTv(shows) {
    tvGrid.innerHTML = "";
    const episodes = flattenEpisodes(shows);
    for (const episode of episodes) {
        const sub = episode.season && episode.episode
            ? `${episode.subtitle} • S${String(episode.season).padStart(2, "0")}E${String(episode.episode).padStart(2, "0")}`
            : `${episode.subtitle}`;
        tvGrid.appendChild(createCard(episode, sub));
    }
    tvCount.textContent = String(episodes.length);
}

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
    }
    return response.json();
}

async function loadLibrary(refresh = false) {
    statusLine.textContent = refresh ? "Refreshing library..." : "Loading library...";
    const refreshParam = refresh ? "?refresh=true" : "";

    const [moviesData, tvData] = await Promise.all([
        fetchJson(`/movies${refreshParam}`),
        fetchJson(`/tv${refreshParam}`),
    ]);

    state.movies = moviesData.items || [];
    state.tvShows = tvData.shows || [];

    renderMovies(state.movies);
    renderTv(state.tvShows);
    statusLine.textContent = `Last scan: ${moviesData.last_scan || "unknown"}`;
}

async function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
        renderMovies(state.movies);
        renderTv(state.tvShows);
        statusLine.textContent = "Showing full library";
        return;
    }

    statusLine.textContent = `Searching for "${query}"...`;
    const data = await fetchJson(`/search?q=${encodeURIComponent(query)}`);
    renderMovies(data.movies || []);
    renderTv(data.tv || []);
    statusLine.textContent = `Search results for "${query}"`;
}

searchInput.addEventListener("input", () => {
    if (searchTimer) {
        clearTimeout(searchTimer);
    }
    searchTimer = setTimeout(() => {
        performSearch().catch((error) => {
            statusLine.textContent = `Search failed: ${error.message}`;
        });
    }, 250);
});

refreshBtn.addEventListener("click", () => {
    loadLibrary(true).catch((error) => {
        statusLine.textContent = `Refresh failed: ${error.message}`;
    });
});

loadLibrary().catch((error) => {
    statusLine.textContent = `Failed to load media library: ${error.message}`;
});
