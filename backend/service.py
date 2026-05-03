import os
import sys

# Ensure project root is on path so artifact paths resolve correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.recommendation_engine import RecommendationEngine
from pipelines.utils import fetch_poster, load_config

# Load once at module level
_engine = RecommendationEngine()
_config = load_config()
_api_key = (
    os.environ.get("TMDB_API_KEY") or
    os.environ.get("TMDB_KEY") or
    _config.get("api", {}).get("tmdb_key", "")
).strip()


def get_recommendations(movie_name, top_n=5):
    """Return a list of recommendation dicts with title + poster."""
    titles = _engine.recommend(movie_name, top_n=top_n)

    if titles == ["Movie not found in database"]:
        return [{"title": "Movie not found in database", "poster": "", "overview": "", "trailer": ""}]

    formatted = []
    for title in titles:
        poster = fetch_poster(title, _api_key) if _api_key else ""
        formatted.append({
            "title": title,
            "poster": poster,
            "overview": "",
            "trailer": "",
        })

    return formatted