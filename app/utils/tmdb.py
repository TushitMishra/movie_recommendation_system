import os
import urllib.parse
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE = "https://image.tmdb.org/t/p/original"

# Inline SVG — works offline; placeholder.com is often blocked → blank images.
_SVG_FALLBACK = """<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450">
<rect fill="#1e1e26" width="100%" height="100%" rx="12"/>
<text x="50%" y="46%" fill="#a8a8b2" font-size="14" text-anchor="middle" font-family="system-ui,sans-serif">No poster</text>
<text x="50%" y="54%" fill="#6e6e78" font-size="11" text-anchor="middle" font-family="system-ui,sans-serif">TMDB</text>
</svg>"""
FALLBACK_POSTER = "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(_SVG_FALLBACK)

REQUEST_TIMEOUT = 10
HEADERS = {"Accept": "application/json"}
_CACHE_VERSION = 4


def resolve_tmdb_api_key(config: Optional[Dict[str, Any]] = None) -> str:
    """Prefer env (TMDB_API_KEY / TMDB_KEY), then config.yaml."""
    env_k = (
        (os.environ.get("TMDB_API_KEY") or os.environ.get("TMDB_KEY") or "").strip()
    )
    if env_k:
        return env_k
    if config and isinstance(config.get("api"), dict):
        return (config["api"].get("tmdb_key") or "").strip()
    return ""


def validate_tmdb_key(api_key: str) -> Tuple[bool, str]:
    """Quick health check so the UI can explain N/A instead of failing silently."""
    if not api_key:
        return False, "No TMDB API key. Set environment variable TMDB_API_KEY or add api.tmdb_key in config/config.yaml."
    try:
        r = requests.get(
            f"{BASE_URL}/configuration",
            params={"api_key": api_key},
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )
        if r.status_code == 200:
            return True, ""
        if r.status_code == 401:
            return False, "TMDB rejected the API key (401 Unauthorized). Create a free key at themoviedb.org/settings/api."
        return False, f"TMDB configuration request failed (HTTP {r.status_code})."
    except requests.RequestException as exc:
        return False, f"Cannot reach api.themoviedb.org ({exc.__class__.__name__}). Check internet / firewall / DNS."


def _pick_best_search_hit(results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Prefer a result that has a poster (fewer broken / empty cards)."""
    if not results:
        return None
    for hit in results[:10]:
        if hit.get("poster_path"):
            return hit
    return results[0]


def _search_movie_impl(movie_name: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Uncached HTTP search — safe to call from worker threads (no Streamlit context)."""
    if not api_key or not (movie_name or "").strip():
        return None
    try:
        response = requests.get(
            f"{BASE_URL}/search/movie",
            params={
                "api_key": api_key,
                "query": movie_name.strip(),
                "language": "en-US",
                "include_adult": "false",
            },
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )
        if response.status_code == 401:
            return None
        response.raise_for_status()
        res = response.json()
        raw = res.get("results") or []
        return _pick_best_search_hit(raw)
    except requests.RequestException:
        return None


@lru_cache(maxsize=8192)
def tmdb_search_movie_raw(movie_name: str, api_key: str) -> Optional[Dict[str, Any]]:
    """Parallel-safe TMDB movie search (LRU cache)."""
    return _search_movie_impl(movie_name.strip(), api_key)


@st.cache_data(show_spinner=False, ttl=600)
def get_movie(movie_name: str, api_key: str, _v: int = _CACHE_VERSION) -> Optional[Dict[str, Any]]:
    return tmdb_search_movie_raw(movie_name, api_key)


@st.cache_data(show_spinner=False)
def get_poster(movie: Optional[Dict[str, Any]]) -> str:
    try:
        if movie and movie.get("poster_path"):
            return f"{IMAGE_BASE}{movie['poster_path']}"
    except Exception:
        pass
    return FALLBACK_POSTER


def build_movie_card_dict(title: str, movie: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Poster + meta for recommendation cards (works with optional TMDB payload)."""
    if not movie:
        return {
            "title": title,
            "poster": FALLBACK_POSTER,
            "rating": "N/A",
            "year": "N/A",
            "tmdb_id": None,
        }
    release_date = movie.get("release_date") or ""
    year = release_date[:4] if release_date else "N/A"
    rating = movie.get("vote_average")
    pretty_rating = f"{rating:.1f}" if isinstance(rating, (int, float)) else "N/A"
    mid = movie.get("id")
    try:
        tmdb_id = int(mid) if mid is not None else None
    except (TypeError, ValueError):
        tmdb_id = None
    return {
        "title": movie.get("title", title),
        "poster": get_poster(movie),
        "rating": pretty_rating,
        "year": year,
        "tmdb_id": tmdb_id,
    }


def _pick_youtube_trailer(videos: List[Dict[str, Any]]) -> Optional[str]:
    """Prefer official trailer; fall back to teaser / featurette on YouTube."""
    candidates = []
    for video in videos:
        if video.get("site") != "YouTube":
            continue
        key = video.get("key") or ""
        if not key:
            continue
        vtype = (video.get("type") or "").lower()
        priority = {"trailer": 0, "teaser": 1, "featurette": 2}.get(vtype, 9)
        official = 0 if video.get("official") else 1
        candidates.append((priority, official, key))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]))
    return f"https://www.youtube.com/embed/{candidates[0][2]}"


@st.cache_data(show_spinner=False, ttl=600)
def get_trailer(movie_id: Optional[int], api_key: str, _v: int = _CACHE_VERSION) -> Optional[str]:
    if not movie_id or not api_key:
        return None
    try:
        response = requests.get(
            f"{BASE_URL}/movie/{int(movie_id)}/videos",
            params={"api_key": api_key},
            timeout=REQUEST_TIMEOUT,
            headers=HEADERS,
        )
        if response.status_code == 401:
            return None
        response.raise_for_status()
        res = response.json()
        return _pick_youtube_trailer(res.get("results") or [])
    except requests.RequestException:
        return None


@st.cache_data(show_spinner=False)
def get_backdrop(movie: Optional[Dict[str, Any]]) -> Optional[str]:
    try:
        if movie and movie.get("backdrop_path"):
            return f"{BACKDROP_BASE}{movie['backdrop_path']}"
    except Exception:
        pass
    return None
